"""The RAG pipeline — drives the LangGraph agent and emits SSE events.

The agent graph (see ``graph.py``) runs the full rewrite -> retrieve -> grade ->
rerank -> generate -> verify loop to completion *before* any answer token is
sent. This is deliberate for a trust-first product: the user only ever sees a
self-verified answer, never an unsupported claim that later gets retracted.

Events emitted (see project spec §11, extended with ``stage`` for the inspector):
    stage    -> {"stage": "...", "detail": "...", "latency_ms": 12.3}   (one per node)
    token    -> {"text": "..."}
    citation -> {"marker": 1, "chunk_id": "...", "source": "...", "section": "..."}
    sources  -> {"retrieved": [{"chunk_id": "...", "score": .., "rerank_score": .., "used": true}]}
    done     -> {"message_id": "...", "answer_status": "grounded|idk|partial", "attempts": 1}
"""

from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass

from app.agent.graph import AgentState, get_graph
from app.models.schemas import (
    CitationEvent,
    DoneEvent,
    RetrievedChunk,
    SourceItem,
    SourcesEvent,
    TokenEvent,
)
from app.retrieval.vector_store import VectorStore

_WORD_RE = re.compile(r"\S+\s*")


@dataclass
class Event:
    """A single SSE event: an event name and a serializable payload model."""

    event: str
    data: object  # a pydantic BaseModel; serialized by the router


def _tokenize(text: str) -> Iterator[str]:
    """Split a finished answer into word-ish chunks for token-by-token streaming."""
    yield from _WORD_RE.findall(text)


def _sources_event(retrieved: list[RetrievedChunk]) -> SourcesEvent:
    return SourcesEvent(
        retrieved=[
            SourceItem(
                chunk_id=r.chunk.id,
                score=round(r.score, 4),
                rerank_score=round(r.rerank_score, 4) if r.rerank_score is not None else None,
                used=r.used,
                section=r.chunk.section,
                source=r.chunk.source,
            )
            for r in retrieved
        ]
    )


def _initial_state(question: str) -> AgentState:
    return {
        "question": question,
        "feedback": "",
        "attempts": 0,
        "queries": [],
        "candidates": [],
        "retrieved": [],
        "answer": "",
        "used_markers": [],
        "status": "",
        "can_retry": True,
        "retry": False,
        "trace": [],
    }


async def run_chat(question: str, store: VectorStore) -> AsyncIterator[Event]:
    """Run the agent for one question, yielding SSE events."""
    message_id = str(uuid.uuid4())
    graph = get_graph()

    state: AgentState = await graph.ainvoke(
        _initial_state(question), config={"configurable": {"store": store}}
    )

    # 1. Inspector trace — one stage event per node that ran.
    for stage in state.get("trace", []):
        yield Event("stage", stage)

    answer = state.get("answer", "")
    retrieved = state.get("retrieved") or state.get("candidates") or []

    # 2. Stream the verified answer, token by token.
    for token in _tokenize(answer):
        yield Event("token", TokenEvent(text=token))

    # 3. Structured citations for the markers the verified answer actually used.
    for marker in state.get("used_markers", []):
        item = retrieved[marker - 1]
        item.used = True
        yield Event(
            "citation",
            CitationEvent(
                marker=marker,
                chunk_id=item.chunk.id,
                source=item.chunk.source,
                section=item.chunk.section,
            ),
        )

    # 4. Full retrieval set (for the inspector) and the terminal done event.
    yield Event("sources", _sources_event(retrieved))
    yield Event(
        "done",
        DoneEvent(
            message_id=message_id,
            answer_status=state.get("status") or "partial",  # type: ignore[arg-type]
            attempts=state.get("attempts", 1),
        ),
    )
