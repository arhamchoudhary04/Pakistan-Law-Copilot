# Pakistan Law Copilot

A **grounded, citation-first** assistant over Pakistani law. It answers **only**
from official legal sources, cites the exact provision, and says *"I don't know"*
when the law doesn't cover the question — the opposite of a chatbot that
confidently makes things up. **Legal information, not legal advice.**

It answers everyday "know your rights" questions — *"What are my rights if I'm
arrested?"*, *"Do I have a right to a fair trial?"*, *"Someone shared my private
photos without consent — what does the law say?"* — grounding each answer in the
Constitution or a statute and linking to the exact Article/Section.

**Corpus (v1, everyday-rights) — 8 acts, ~270 chunks:**
- **Constitution of Pakistan — Fundamental Rights** (Part II, Chapter 1, Articles 8–28),
  hand-verified against the official text for citation accuracy.
- **Muslim Family Laws Ordinance, 1961** — marriage, talaq/divorce, maintenance, polygamy.
- **Prevention of Electronic Crimes Act, 2016 (PECA)** — cybercrime, online harassment.
- **Protection against Harassment of Women at the Workplace Act, 2010** — workplace harassment.
- **Right of Access to Information Act, 2017** — requesting public records.
- **Punjab Rented Premises Act, 2009** — landlord/tenant rights, eviction.
- **Punjab Consumer Protection Act, 2005** — defective products, services.
- **Industrial and Commercial Employment (Standing Orders) Ordinance, 1968** — employment, retrenchment.

Rent and consumer protection are provincial subjects, so the Punjab statutes are
used (labelled as such). Sources: official public texts via
[pakistancode.gov.pk](https://pakistancode.gov.pk/),
[punjabcode.punjab.gov.pk](https://punjabcode.punjab.gov.pk/), and
[kpcode.kp.gov.pk](https://kpcode.kp.gov.pk/). The architecture is domain-agnostic —
drop more acts' PDFs in and swap `data/corpus/` to retarget it.

This repo implements the backend through **Phase 2**: ingestion (PDF → structured
markdown → chunk → embed → FAISS), a **LangGraph agent** with query rewrite,
cross-encoder reranking, a relevance gate with graceful refusal, and
self-verification; a streaming `/chat` endpoint with inline citations and a
per-stage inspector trace; a Next.js web UI; and an evaluation harness with a
retrieval ablation.

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
| Ingestion | `pypdf` → structured markdown (per Article/Section), then header + token chunking |
| Eval | Golden set + custom retrieval/refusal metrics + ablation |
| Web UI | Next.js (App Router) + TypeScript + Tailwind, custom SSE-over-fetch client |

Qdrant, Neo4j graph retrieval, Postgres/Redis, document upload, and auth are
**intentionally deferred** to later phases.

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

### Regenerating a statute from its PDF (optional)

Statutes are converted from their official PDF to structured markdown (one heading
per Section/Article) by `app/ingestion/legal_pdf.py`. To add or refresh one, drop
the official PDF in `data/corpus/../data/raw/` and run `python -m app.ingestion.legal_pdf`.
The Constitution's Fundamental Rights chapter is **hand-verified** (not auto-parsed)
because citation accuracy is critical — see the note in `legal_pdf.py`.

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
  -d '{"message": "Do I have a right to a fair trial?"}'
```

You'll see `stage` events (the per-node inspector trace), then `token` events stream
the answer, then `citation` and `sources` events (with `rerank_score`), then `done`
with `answer_status: grounded`. This one cites **Article 10A**.

### Try the refusal path

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

Nothing clears the relevance threshold, so it returns `answer_status: idk` with no
fabricated citations.

## Web UI

A Next.js chat UI (`apps/web`) consumes the SSE stream: streaming answer, inline
clickable citation chips → source drawer, a collapsible **Retrieval Inspector**
(per-stage latency + ranked chunks with cosine/rerank scores), and a trust-state
badge (grounded / I-don't-know / partial).

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000  (expects the API on :8000)
```

Set `NEXT_PUBLIC_API_URL` if the API is not at `http://localhost:8000`. The API's
`CORS_ORIGINS` allows `http://localhost:3000` and `:3001` (Next's fallback port).

## Languages — English, Urdu & Roman Urdu

Ask in **English, Urdu (Urdu script), or Roman Urdu** (Urdu in Latin letters). The
corpus stays in the authoritative English legal text; language is handled at the two
ends:

- The agent's `rewrite` node **translates the question to English** for retrieval
  (and, importantly, reranking runs against that English query — an English-only
  cross-encoder scoring a Urdu question would otherwise demote the correct article).
- The `generate` node **replies in the user's language and script**, while keeping
  provision names and citations in English (e.g. answers in Urdu still cite
  "Article 25A"). The UI renders Urdu-script messages right-to-left.

Translation reuses the existing Groq call, so it adds no extra API cost. Requires
the `GROQ_API_KEY` (non-English retrieval depends on the translation step).

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
questions correctly refused), and over-refusal rate over the 33-item golden set in
`eval/golden_set.jsonl` (31 answerable across all 8 acts, 2 uncovered).

Current results: `retrieval_hit_rate 1.00`, `over_refusal_rate 0.00`,
`refusal_accuracy 1.00`. Two layers guard against wrong answers: the cosine **gate**
refuses clearly off-topic questions (e.g. "capital of France", 0.47), and for
questions that are *legally adjacent but uncovered* (e.g. a tax question that
retrieves a near-miss just over the gate) the **LLM refuses** because the retrieved
context doesn't actually answer them (verified end-to-end).

### Retrieval ablation — an honest, non-obvious result

| config | hit_rate@k | context_precision@k |
|---|---|---|
| vector-only | 1.000 | **0.742** |
| vector + rerank | 1.000 | 0.729 |

On this legal corpus (8 acts, ~270 chunks), the cross-encoder reranker **slightly
hurts** precision — the `ms-marco` reranker is trained on web passages, not statutes,
so it's less calibrated on legal text. (On the earlier FastAPI corpus it helped:
0.71 → 0.75.) The lesson: reranking is not a universal win; measure it per corpus.
A legal-domain reranker would likely recover the gain.

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

## Disclaimer & attribution

**This is legal information, not legal advice.** Answers are generated from a
limited corpus and may be incomplete or out of date. Always verify against the
cited official source and consult a qualified lawyer for your specific situation.

The corpus under `data/corpus/` is derived from official public texts of Pakistani
law (the Constitution and Acts) obtained from [pakistancode.gov.pk](https://pakistancode.gov.pk/).
The Fundamental Rights chapter is hand-transcribed from the official Constitution
text; PECA 2016 is parsed from its official PDF. Provided for informational/
educational use.
