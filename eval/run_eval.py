"""Evaluation harness for Knowledge Copilot.

Runs the golden set against the retriever and (optionally) the full generation
pipeline, then reports quantified quality metrics.

Two tiers of metrics:

1. Retrieval + refusal metrics (default) — computed offline from embeddings only,
   so they run WITHOUT a GROQ_API_KEY:
     * retrieval hit rate @k   (expected source appears in retrieved chunks)
     * context precision @k    (fraction of retrieved chunks from expected sources)
     * refusal accuracy        (genuinely unanswerable questions correctly refused)
     * over-refusal rate       (answerable questions wrongly refused by the gate)

2. Generation metrics (--generate) — require GROQ_API_KEY:
     * citation validity       (every [n] marker maps to a real retrieved chunk)
     * answered rate           (answerable questions actually answered)

RAGAS (--ragas) is attempted if installed and configured; it is optional and the
harness degrades gracefully if it cannot run.

Usage (from repo root):
    python eval/run_eval.py                # retrieval + refusal metrics (offline)
    python eval/run_eval.py --generate     # + generation/citation metrics (needs key)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable
from pathlib import Path

# Make the `app` package importable (it lives under apps/api).
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.agent.pipeline import run_chat  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.embeddings import get_embedder  # noqa: E402
from app.models.schemas import DoneEvent, RetrievedChunk, TokenEvent  # noqa: E402
from app.retrieval.reranker import get_reranker  # noqa: E402
from app.retrieval.vector_store import VectorStore  # noqa: E402

GOLDEN_SET = Path(__file__).resolve().parent / "golden_set.jsonl"


def load_golden() -> list[dict]:
    rows = []
    for line in GOLDEN_SET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def retrieval_metrics(rows: list[dict], store: VectorStore) -> dict[str, float]:
    settings = get_settings()
    embedder = get_embedder()

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]

    hits = 0
    precision_sum = 0.0
    precision_n = 0
    over_refusals = 0

    for r in answerable:
        retrieved = store.search(embedder.embed_one(r["question"]), settings.top_k)
        best = max((x.score for x in retrieved), default=0.0)
        refused = not retrieved or best < settings.relevance_threshold
        if refused:
            over_refusals += 1

        expected = set(r["expected_source_ids"])
        retrieved_docs = [x.chunk.doc_id for x in retrieved]
        if expected:
            if expected & set(retrieved_docs):
                hits += 1
            if retrieved_docs:
                relevant = sum(1 for d in retrieved_docs if d in expected)
                precision_sum += relevant / len(retrieved_docs)
                precision_n += 1

    correct_refusals = 0
    for r in unanswerable:
        retrieved = store.search(embedder.embed_one(r["question"]), settings.top_k)
        best = max((x.score for x in retrieved), default=0.0)
        if not retrieved or best < settings.relevance_threshold:
            correct_refusals += 1

    return {
        "retrieval_hit_rate": hits / len(answerable) if answerable else 0.0,
        "context_precision": precision_sum / precision_n if precision_n else 0.0,
        "over_refusal_rate": over_refusals / len(answerable) if answerable else 0.0,
        "refusal_accuracy": correct_refusals / len(unanswerable) if unanswerable else 0.0,
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
    }


def _hit_and_precision(
    rows: list[dict], retrieve: Callable[[str], list[RetrievedChunk]]
) -> tuple[float, float]:
    """Hit rate @k and context precision @k for a retrieval function."""
    answerable = [r for r in rows if r["answerable"] and r["expected_source_ids"]]
    hits = 0
    precision_sum = 0.0
    precision_n = 0
    for r in answerable:
        docs = [x.chunk.doc_id for x in retrieve(r["question"])]
        expected = set(r["expected_source_ids"])
        if expected & set(docs):
            hits += 1
        if docs:
            precision_sum += sum(1 for d in docs if d in expected) / len(docs)
            precision_n += 1
    hit_rate = hits / len(answerable) if answerable else 0.0
    precision = precision_sum / precision_n if precision_n else 0.0
    return hit_rate, precision


def ablation(rows: list[dict], store: VectorStore) -> None:
    """Compare vector-only retrieval vs vector + cross-encoder rerank."""
    settings = get_settings()
    embedder = get_embedder()
    reranker = get_reranker()

    def vector_only(q: str) -> list[RetrievedChunk]:
        return store.search(embedder.embed_one(q), settings.top_k)

    def vector_plus_rerank(q: str) -> list[RetrievedChunk]:
        candidates = store.search(embedder.embed_one(q), settings.rerank_candidates)
        return reranker.rerank(q, candidates, settings.top_k)

    v_hit, v_prec = _hit_and_precision(rows, vector_only)
    r_hit, r_prec = _hit_and_precision(rows, vector_plus_rerank)

    print("\n=== Retrieval ablation (answerable questions) ===")
    print(f"  {'config':<22}{'hit_rate@k':>12}{'context_prec@k':>18}")
    print(f"  {'vector-only':<22}{v_hit:>12.3f}{v_prec:>18.3f}")
    print(f"  {'vector + rerank':<22}{r_hit:>12.3f}{r_prec:>18.3f}")


async def _collect_answer(question: str, store: VectorStore) -> tuple[str, str]:
    """Run the full pipeline and return (answer_text, answer_status)."""
    parts: list[str] = []
    status = "partial"
    async for event in run_chat(question, store):
        if event.event == "token" and isinstance(event.data, TokenEvent):
            parts.append(event.data.text)
        elif event.event == "done" and isinstance(event.data, DoneEvent):
            status = event.data.answer_status
    return "".join(parts), status


async def generation_metrics(rows: list[dict], store: VectorStore) -> dict[str, float]:
    import re

    marker_re = re.compile(r"\[(\d+)\]")
    settings = get_settings()
    embedder = get_embedder()

    answerable = [r for r in rows if r["answerable"]]
    answered = 0
    valid_citations = 0
    cited = 0

    for r in answerable:
        retrieved = store.search(embedder.embed_one(r["question"]), settings.top_k)
        answer, status = await _collect_answer(r["question"], store)
        if status == "grounded":
            answered += 1
        markers = [int(m) for m in marker_re.findall(answer)]
        if markers:
            cited += 1
            if all(1 <= m <= len(retrieved) for m in markers):
                valid_citations += 1

    return {
        "answered_rate": answered / len(answerable) if answerable else 0.0,
        "citation_validity": valid_citations / cited if cited else 0.0,
        "n_cited": cited,
    }


def print_table(title: str, metrics: dict[str, float]) -> None:
    print(f"\n=== {title} ===")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key:<22} {value:.3f}")
        else:
            print(f"  {key:<22} {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Copilot eval harness")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Also run generation metrics (requires GROQ_API_KEY).",
    )
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="Compare vector-only vs vector+rerank retrieval.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI gate: exit non-zero if offline metrics fall below thresholds.",
    )
    args = parser.parse_args()

    settings = get_settings()
    try:
        store = VectorStore.load(settings.data_path)
    except FileNotFoundError as exc:
        raise SystemExit(f"{exc}") from exc

    rows = load_golden()
    print(f"Loaded {len(rows)} golden Q/A pairs; index has {len(store)} chunks.")

    metrics = retrieval_metrics(rows, store)
    print_table("Retrieval + refusal metrics", metrics)

    if args.ablation:
        ablation(rows, store)

    if args.generate:
        if not settings.groq_api_key:
            print("\n[--generate skipped] GROQ_API_KEY not set.")
        else:
            gen = asyncio.run(generation_metrics(rows, store))
            print_table("Generation metrics", gen)

    if args.check:
        _enforce_gate(metrics)


# Minimum acceptable offline metrics; CI fails the build if any is breached.
_THRESHOLDS = {
    "retrieval_hit_rate": (0.90, "min"),
    "refusal_accuracy": (0.90, "min"),
    "over_refusal_rate": (0.10, "max"),
}


def _enforce_gate(metrics: dict[str, float]) -> None:
    failures = []
    for name, (bound, kind) in _THRESHOLDS.items():
        value = metrics[name]
        if (kind == "min" and value < bound) or (kind == "max" and value > bound):
            failures.append(f"{name}={value:.3f} violates {kind} {bound}")
    if failures:
        print("\nEVAL GATE FAILED:")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)
    print("\nEVAL GATE PASSED")


if __name__ == "__main__":
    main()
