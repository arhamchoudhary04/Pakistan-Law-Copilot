# Knowledge Copilot

A **grounded, citation-first** assistant over a trusted document corpus. It answers
**only** from your sources, cites every claim, and says *"I don't know"* when the
evidence is weak — the opposite of a chatbot that confidently makes things up.

This repo implements the backend through **Phase 2**: ingestion (chunk → embed →
FAISS), a **LangGraph agent** with query rewrite, cross-encoder reranking, a
relevance gate with graceful refusal, and self-verification; a streaming `/chat`
endpoint with inline citations and a per-stage inspector trace; and an evaluation
harness with a retrieval ablation. The corpus is a curated markdown subset of the
[FastAPI documentation](https://fastapi.tiangolo.com/) (MIT-licensed).

## Stack

Deliberately lean, free, and local-first:

| Layer | Choice |
|---|---|
| API | FastAPI + Pydantic v2, SSE streaming (`sse-starlette`) |
| Agent | LangGraph state machine (rewrite → retrieve → grade → rerank → generate → verify) |
| Generation | Groq free API (`llama-3.1-8b-instant`), OpenAI-compatible |
| Embeddings | `fastembed` local (`BAAI/bge-small-en-v1.5`, 384-dim), no API key |
| Reranker | `fastembed` local cross-encoder (`Xenova/ms-marco-MiniLM-L-6-v2`, ONNX, no torch) |
| Vector store | FAISS flat inner-product over L2-normalized vectors (cosine) |
| Chunking | Structure-aware (markdown headers) + token-budget splitter |
| Eval | Golden set + custom retrieval/refusal metrics + ablation |

Qdrant, Neo4j graph retrieval, Postgres/Redis, document upload, auth, and the
Next.js web UI are **intentionally deferred** to later phases.

## Architecture (agent flow)

The `/chat` request is driven by a LangGraph agent (`app/agent/graph.py`):

```
rewrite ──► retrieve ──► grade ──(weak evidence)──► fallback ("I don't know")
                           │
                       (relevant)
                           ▼
                 rerank ──► generate ──► verify ──(ok / attempts exhausted)──► answer
                           ▲                 │
                           └──(unsupported)──┘   loop back with feedback, capped at MAX_ATTEMPTS
```

- **rewrite** expands the question into retrieval queries (falls back to the raw
  query if the LLM is unavailable).
- **grade** is the trust gate: it refuses (cosine below `RELEVANCE_THRESHOLD`) rather
  than guess. The gate stays cosine-based even though reranking reorders afterwards.
- **rerank** is a cross-encoder that reorders candidates — the biggest precision win
  (quantified by the ablation below).
- **verify** checks every claim maps to a valid citation and loops back with feedback
  on unsupported claims, bounded by `MAX_ATTEMPTS`.

Citations are **structured data** (chunk ids), not free text the model can fabricate.
Verification runs *before* any token reaches the client, so the user only ever sees a
self-verified answer — never an unsupported claim that later gets retracted.

## Setup

Requires Python 3.11+.

```bash
# 1. Create a virtualenv and install the API (editable) with dev extras
python -m venv .venv
# Windows:  .venv\Scripts\activate       macOS/Linux:  source .venv/bin/activate
pip install -e "apps/api[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY (free, no card: https://console.groq.com/keys)
# Retrieval + the refusal path work WITHOUT a key; generation needs it.
```

## Build the index (ingest the corpus)

```bash
cd apps/api
python -m app.ingestion.build_index
```

This loads `data/corpus`, chunks it, embeds with fastembed (downloads ~130MB on
first run), and writes a FAISS index + `chunks.json` into `.data/`.

## Run the API

```bash
cd apps/api
uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- Health:     http://localhost:8000/health

### Try a grounded question

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I declare the type of a path parameter in FastAPI?"}'
```

You'll see `stage` events (the per-node inspector trace), then `token` events stream
the answer, then `citation` and `sources` events (with `rerank_score`), then `done`
with `answer_status: grounded`.

### Try the refusal path

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

Nothing clears the relevance threshold, so it returns `answer_status: idk` with no
fabricated citations.

## SSE event contract

```
event: stage     data: {"stage": "rerank", "detail": "...", "latency_ms": 12.3}
event: token     data: {"text": "..."}
event: citation  data: {"marker": 1, "chunk_id": "...", "source": "...", "section": "..."}
event: sources   data: {"retrieved": [{"chunk_id": "...", "score": 0.82, "rerank_score": 8.76, "used": true}, ...]}
event: done      data: {"message_id": "...", "answer_status": "grounded|idk|partial", "attempts": 1}
```

The `stage` events (one per agent node, with latency) power the Retrieval Inspector.

## Evaluation

```bash
python eval/run_eval.py             # retrieval + refusal metrics (offline, no key)
python eval/run_eval.py --ablation  # + vector-only vs vector+rerank comparison
python eval/run_eval.py --generate  # + generation/citation metrics (needs GROQ_API_KEY)
```

Reports retrieval hit rate, context precision, refusal accuracy (unanswerable
questions correctly refused), and over-refusal rate over the golden set in
`eval/golden_set.jsonl`.

### Retrieval ablation

Cross-encoder reranking improves ranking precision on the golden set:

| config | hit_rate@k | context_precision@k |
|---|---|---|
| vector-only | 1.000 | 0.707 |
| vector + rerank | 1.000 | 0.747 |

(Hit rate is already saturated on this small 54-chunk corpus; the gain shows up as
higher context precision — the reranker ranks the on-topic chunks above near-misses.)

## Quality gates

```bash
cd apps/api
ruff check .
mypy app
pytest
```

## Swap the corpus

Drop your own markdown files into `data/corpus/` (or point `CORPUS_DIR` elsewhere),
re-run `build_index`, and restart the API. Nothing else changes.

## Attribution

The bundled corpus under `data/corpus/` is a condensed, curated derivative of the
FastAPI documentation, which is MIT-licensed (© Sebastián Ramírez). It is included
solely as sample source material for this grounded-RAG demo.
