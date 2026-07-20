"""RAG pipeline: drives the LangGraph agent and emits SSE events.

The graph runs to completion (verify included) before any answer token is sent, so
the client only ever receives a self-verified answer.

Events:
    stage    -> {"stage", "detail", "latency_ms"}   (one per node; powers the inspector)
    token    -> {"text"}
    citation -> {"marker", "chunk_id", "source", "section"}
    sources  -> {"retrieved": [{"chunk_id", "score", "rerank_score", "used"}]}
    done     -> {"message_id", "answer_status", "attempts"}
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
                via_graph=r.via_graph,
                section=r.chunk.section,
                source=r.chunk.source,
            )
            for r in retrieved
        ]
    )


def _initial_state(question: str, history: list[tuple[str, str]], mode: str) -> AgentState:
    return {
        "question": question,
        "history": history,
        "mode": mode,
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


async def run_chat(
    question: str,
    store: VectorStore,
    history: list[tuple[str, str]] | None = None,
    mode: str = "law",
) -> AsyncIterator[Event]:
    """Run the agent for one question, yielding SSE events.

    Streams the graph with ``astream`` so each node's ``stage`` event fires as it
    finishes (live progress during the multi-second run); the answer is emitted only
    once the verified run completes. ``history`` lets the rewrite node resolve follow-ups.
    """
    message_id = str(uuid.uuid4())
    graph = get_graph()

    # 1. Inspector trace — emit each stage event live as its node completes.
    final: AgentState = {}
    emitted = 0
    async for state in graph.astream(
        _initial_state(question, history or [], mode),
        config={"configurable": {"store": store}},
        stream_mode="values",
    ):
        final = state
        trace = state.get("trace", [])
        for stage in trace[emitted:]:
            yield Event("stage", stage)
        emitted = len(trace)

    answer = final.get("answer", "")
    retrieved = final.get("retrieved") or final.get("candidates") or []

    # 2. Stream the verified answer, token by token.
    for token in _tokenize(answer):
        yield Event("token", TokenEvent(text=token))

    # 3. Structured citations for the markers the verified answer actually used.
    for marker in final.get("used_markers", []):
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
            answer_status=final.get("status") or "partial",  # type: ignore[arg-type]
            attempts=final.get("attempts", 1),
        ),
    )
