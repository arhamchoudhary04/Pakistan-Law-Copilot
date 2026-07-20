"""LangGraph agent: the self-correcting RAG pipeline.

LangGraph (rather than a plain chain) because the verification loop needs explicit
state and conditional edges.

    rewrite -> retrieve -> grade --(weak)--> fallback -> END
                              |
                          (relevant)
                              v
                    rerank -> generate -> verify --(ok/exhausted)--> END
                              ^                       |
                              +---------(retry)-------+

grade is the relevance gate: it refuses on low cosine before the LLM is called, and
stays cosine-based (calibrated to RELEVANCE_THRESHOLD) even though rerank reorders
afterwards. verify checks every claim maps to a citation and loops back with feedback,
hard-capped at max_attempts. Verification finishes before any token reaches the client,
so the user never sees a claim that later gets retracted.
"""

from __future__ import annotations

import logging
import operator
import re
from functools import lru_cache
from time import perf_counter
from typing import Annotated, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.agent.prompts import build_messages, build_rewrite_messages
from app.core.config import get_settings
from app.core.embeddings import get_embedder
from app.core.llm import LLMError, get_llm
from app.models.schemas import RetrievedChunk, StageEvent
from app.retrieval.graph_refs import chunk_key
from app.retrieval.graph_store import get_graph_store
from app.retrieval.reranker import get_reranker

IDK_MESSAGE = "I don't know based on the available sources."
_MARKER_RE = re.compile(r"\[(\d+)\]")

logger = logging.getLogger("app")


class AgentState(TypedDict, total=False):
    question: str
    history: list[tuple[str, str]]
    mode: str  # "law" (default) | "document" (answering from an uploaded PDF)
    feedback: str
    attempts: int
    queries: list[str]
    candidates: list[RetrievedChunk]  # merged, pre-rerank
    retrieved: list[RetrievedChunk]  # final top-k after rerank
    answer: str
    used_markers: list[int]
    status: str  # "" | "relevant" | "grounded" | "partial" | "idk"
    can_retry: bool
    retry: bool
    trace: Annotated[list[StageEvent], operator.add]


def _ms(t0: float) -> float:
    return round((perf_counter() - t0) * 1000, 1)


def refusal_text(question: str, candidates: list[RetrievedChunk], mode: str = "law") -> str:
    best = max((c.score for c in candidates), default=0.0)
    where = "the uploaded document" if mode == "document" else "the corpus"
    tail = (
        "Try rephrasing your question."
        if mode == "document"
        else "Try rephrasing, or add sources that cover this topic."
    )
    return (
        f'{IDK_MESSAGE} I searched {where} for "{question}" but the most '
        f"relevant passage scored only {best:.2f}, below the confidence threshold. "
        f"{tail}"
    )


def _store(config: RunnableConfig) -> object:
    return config["configurable"]["store"]


# ---- Nodes ----


async def rewrite_node(state: AgentState, config: RunnableConfig) -> dict:
    t = perf_counter()
    settings = get_settings()
    question = state["question"]
    feedback = state.get("feedback", "")
    history = state.get("history", [])
    queries = [question]
    detail = "rewrite disabled; using original query"
    if settings.rewrite_enabled:
        try:
            parts: list[str] = []
            async for tok in get_llm().stream(
                build_rewrite_messages(question, feedback, history), max_tokens=128
            ):
                parts.append(tok)
            lines = [ln.strip() for ln in "".join(parts).splitlines() if ln.strip()]
            if lines:
                queries = lines[:3]
                detail = f"{len(queries)} queries: {'; '.join(queries)}"
        except LLMError:
            detail = "rewrite unavailable (no LLM); using original query"
    return {
        "queries": queries,
        "trace": [StageEvent(stage="rewrite", detail=detail, latency_ms=_ms(t))],
    }


async def retrieve_node(state: AgentState, config: RunnableConfig) -> dict:
    t = perf_counter()
    settings = get_settings()
    store = _store(config)
    embedder = get_embedder()
    merged: dict[str, RetrievedChunk] = {}
    primary_vec = None
    for query in state["queries"]:
        qvec = embedder.embed_one(query)
        if primary_vec is None:
            primary_vec = qvec
        for rc in store.search(qvec, settings.rerank_candidates):  # type: ignore[attr-defined]
            existing = merged.get(rc.chunk.id)
            if existing is None or rc.score > existing.score:
                merged[rc.chunk.id] = rc
    candidates = list(merged.values())

    # Hybrid: add cross-referenced provisions the vector search missed (law corpus only).
    graph_added = 0
    if state.get("mode", "law") == "law":
        graph_added = _graph_expand(store, candidates, primary_vec)

    best = max((c.score for c in candidates), default=0.0)
    extra = f"; +{graph_added} via graph" if graph_added else ""
    return {
        "candidates": candidates,
        "trace": [
            StageEvent(
                stage="retrieve",
                detail=f"{len(candidates)} candidates; best cosine {best:.3f}{extra}",
                latency_ms=_ms(t),
            )
        ],
    }


def _graph_expand(store: object, candidates: list[RetrievedChunk], query_vec: object) -> int:
    """Add cross-referenced provisions from the graph to the candidate set.

    Returns the number of chunks added. Any failure (graph disabled, Neo4j
    unreachable) is swallowed so retrieval falls back to vector-only.
    """
    if not get_settings().graph_enabled:
        return 0
    graph = get_graph_store()
    if graph is None:
        return 0
    try:
        seeds = {k for c in candidates[:5] if (k := chunk_key(c.chunk))}
        if not seeds:
            return 0
        existing = {chunk_key(c.chunk) for c in candidates}
        new_keys = {k for k in graph.neighbors(list(seeds)) if k not in existing}
        if not new_keys:
            return 0
        added = 0
        for chunk in store.chunks_for_keys(new_keys, chunk_key):  # type: ignore[attr-defined]
            score = store.similarity(query_vec, chunk)  # type: ignore[attr-defined]
            candidates.append(RetrievedChunk(chunk=chunk, score=score, via_graph=True))
            added += 1
        return added
    except Exception:
        return 0


def grade_node(state: AgentState, config: RunnableConfig) -> dict:
    t = perf_counter()
    settings = get_settings()
    candidates = state["candidates"]
    best = max((c.score for c in candidates), default=0.0)
    if not candidates or best < settings.relevance_threshold:
        detail = f"weak evidence (best {best:.3f} < {settings.relevance_threshold}); refusing"
        return {
            "status": "idk",
            "trace": [
                StageEvent(stage="grade", detail=detail, latency_ms=_ms(t))
            ],
        }
    return {
        "status": "relevant",
        "trace": [StageEvent(stage="grade", detail=f"pass (best {best:.3f})", latency_ms=_ms(t))],
    }


def rerank_node(state: AgentState, config: RunnableConfig) -> dict:
    t = perf_counter()
    settings = get_settings()
    candidates = state["candidates"]
    # Rerank against the rewritten (English) query: the cross-encoder is English-only,
    # so scoring a Urdu/Roman-Urdu question against English text demotes the right article.
    queries = state.get("queries") or [state["question"]]
    rerank_query = queries[0]
    if settings.rerank_enabled:
        ranked = get_reranker().rerank(rerank_query, candidates, settings.top_k)
        detail = f"cross-encoder reranked {len(candidates)} -> top {len(ranked)}"
    else:
        ranked = sorted(candidates, key=lambda c: c.score, reverse=True)[: settings.top_k]
        detail = f"rerank disabled; vector top {len(ranked)}"
    return {
        "retrieved": ranked,
        "trace": [StageEvent(stage="rerank", detail=detail, latency_ms=_ms(t))],
    }


async def generate_node(state: AgentState, config: RunnableConfig) -> dict:
    t = perf_counter()
    retrieved = state["retrieved"]
    feedback = state.get("feedback", "")
    parts: list[str] = []
    try:
        async for tok in get_llm().stream(
            build_messages(state["question"], retrieved, feedback, state.get("mode", "law"))
        ):
            parts.append(tok)
        answer = "".join(parts).strip()
        gen = StageEvent(stage="generate", detail=f"{len(answer)} chars", latency_ms=_ms(t))
        return {"answer": answer, "can_retry": True, "trace": [gen]}
    except LLMError as exc:
        logger.warning("generate: LLM unavailable: %s", exc)
        gen = StageEvent(stage="generate", detail="LLM unavailable", latency_ms=_ms(t))
        return {
            "answer": f"[generation unavailable] {exc}",
            "can_retry": False,
            "status": "partial",
            "trace": [gen],
        }


def verify_node(state: AgentState, config: RunnableConfig) -> dict:
    t = perf_counter()
    settings = get_settings()
    answer = state["answer"]
    retrieved = state["retrieved"]
    attempts = state.get("attempts", 0) + 1

    if not state.get("can_retry", True):
        skipped = StageEvent(
            stage="verify", detail="skipped (generation unavailable)", latency_ms=_ms(t)
        )
        return {
            "used_markers": [],
            "status": "partial",
            "attempts": attempts,
            "retry": False,
            "trace": [skipped],
        }

    markers = [int(m) for m in _MARKER_RE.findall(answer)]
    used = sorted({m for m in markers if 1 <= m <= len(retrieved)})
    invalid = sorted({m for m in markers if not 1 <= m <= len(retrieved)})
    is_refusal = IDK_MESSAGE.lower() in answer.lower()
    unsupported = (not is_refusal) and (not used or bool(invalid))

    if settings.verify_enabled and unsupported and attempts < settings.max_attempts:
        fb = (
            f"answer cited invalid markers {invalid}"
            if invalid
            else "answer had no valid citations"
        )
        retrying = StageEvent(
            stage="verify", detail=f"unsupported ({fb}); retrying", latency_ms=_ms(t)
        )
        return {"feedback": fb, "attempts": attempts, "retry": True, "trace": [retrying]}

    status = "idk" if is_refusal else ("grounded" if used else "partial")
    detail = (
        f"verified; {len(used)} citation(s)"
        if used
        else ("refusal" if is_refusal else "no valid citations; partial")
    )
    return {
        "used_markers": used,
        "status": status,
        "attempts": attempts,
        "retry": False,
        "trace": [StageEvent(stage="verify", detail=detail, latency_ms=_ms(t))],
    }


def fallback_node(state: AgentState, config: RunnableConfig) -> dict:
    t = perf_counter()
    candidates = state.get("candidates", [])
    return {
        "answer": refusal_text(state["question"], candidates, state.get("mode", "law")),
        "retrieved": candidates,
        "used_markers": [],
        "status": "idk",
        "attempts": max(state.get("attempts", 0), 1),
        "trace": [StageEvent(stage="fallback", detail="returned I-don't-know", latency_ms=_ms(t))],
    }


# ---- Routing ----


def route_after_grade(state: AgentState) -> str:
    return "fallback" if state.get("status") == "idk" else "rerank"


def route_after_verify(state: AgentState) -> str:
    return "rewrite" if state.get("retry") else "end"


@lru_cache
def get_graph():  # type: ignore[no-untyped-def]
    """Build and compile the agent graph once (cached)."""
    builder = StateGraph(AgentState)
    builder.add_node("rewrite", rewrite_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("grade", grade_node)
    builder.add_node("rerank", rerank_node)
    builder.add_node("generate", generate_node)
    builder.add_node("verify", verify_node)
    builder.add_node("fallback", fallback_node)

    builder.add_edge(START, "rewrite")
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("retrieve", "grade")
    builder.add_conditional_edges(
        "grade", route_after_grade, {"rerank": "rerank", "fallback": "fallback"}
    )
    builder.add_edge("rerank", "generate")
    builder.add_edge("generate", "verify")
    builder.add_conditional_edges("verify", route_after_verify, {"rewrite": "rewrite", "end": END})
    builder.add_edge("fallback", END)
    return builder.compile()
