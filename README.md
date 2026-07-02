# Knowledge Copilot

A **grounded, citation-first** assistant over a trusted document corpus. It answers
**only** from your sources, cites every claim, and says *"I don't know"* when the
evidence is weak — the opposite of a chatbot that confidently makes things up.

This repo currently implements the **backend MVP (Phase 0–1)**: ingest → chunk →
embed → FAISS, a streaming `/chat` endpoint with inline citations, a relevance gate
with graceful refusal, and an evaluation harness. The corpus is a curated markdown
subset of the [FastAPI documentation](https://fastapi.tiangolo.com/) (MIT-licensed).

## Stack

Deliberately lean, free, and local-first:

| Layer | Choice |
|---|---|
| API | FastAPI + Pydantic v2, SSE streaming (`sse-starlette`) |
| Generation | Groq free API (`llama-3.1-8b-instant`), OpenAI-compatible |
| Embeddings | `fastembed` local (`BAAI/bge-small-en-v1.5`, 384-dim), no API key |
| Vector store | FAISS flat inner-product over L2-normalized vectors (cosine) |
| Chunking | Structure-aware (markdown headers) + token-budget splitter |
| Eval | Golden set + custom retrieval/refusal metrics |

Qdrant, a cross-encoder reranker, a LangGraph agent loop, Neo4j graph retrieval,
Postgres/Redis, document upload, auth, and the Next.js web UI are **intentionally
deferred** to later phases.

## Architecture (MVP flow)

```
question
   │
   ▼
embed query (fastembed) ──► FAISS top-k (cosine)
   │
   ▼
relevance gate ── best score < RELEVANCE_THRESHOLD ──► "I don't know" (answer_status=idk)
   │ (evidence is strong)
   ▼
generate with numbered context (Groq, streamed) ──► parse [n] markers
   │
   ▼
SSE events: token · citation · sources · done
```

Citations are **structured data** (chunk ids), not free text the model can
fabricate. The relevance gate is the core trust mechanism — it refuses rather than
guesses when nothing clears the threshold.

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

You'll see `token` events stream the answer, then `citation` and `sources` events,
then `done` with `answer_status: grounded`.

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
event: token     data: {"text": "..."}
event: citation  data: {"marker": 1, "chunk_id": "...", "source": "...", "section": "..."}
event: sources   data: {"retrieved": [{"chunk_id": "...", "score": 0.82, "used": true}, ...]}
event: done      data: {"message_id": "...", "answer_status": "grounded|idk|partial"}
```

## Evaluation

```bash
python eval/run_eval.py            # retrieval + refusal metrics (offline, no key)
python eval/run_eval.py --generate # + generation/citation metrics (needs GROQ_API_KEY)
```

Reports retrieval hit rate, context precision, refusal accuracy (unanswerable
questions correctly refused), and over-refusal rate over the golden set in
`eval/golden_set.jsonl`.

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
