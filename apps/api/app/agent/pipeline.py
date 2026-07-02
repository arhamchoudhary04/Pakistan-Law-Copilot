"""The RAG pipeline — the heart of the MVP.

Flow: embed the query -> FAISS top-k -> relevance gate -> (refuse) or
(generate a grounded, cited answer). Emits the structured SSE events consumed by
the ``/chat`` endpoint: ``token`` / ``citation`` / ``sources`` / ``done``.

The relevance gate is the whole point of the project: if no retrieved chunk
clears ``RELEVANCE_THRESHOLD`` we refuse with an honest "I don't know" instead of
guessing. Protect this path.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.agent.prompts import build_messages
from app.core.config import get_settings
from app.core.embeddings import get_embedder
from app.core.llm import LLMError, get_llm
from app.models.schemas import (
    CitationEvent,
    DoneEvent,
    RetrievedChunk,
    SourceItem,
    SourcesEvent,
    TokenEvent,
)
from app.retrieval.vector_store import VectorStore

IDK_MESSAGE = "I don't know based on the available sources."
_MARKER_RE = re.compile(r"\[(\d+)\]")


@dataclass
class Event:
    """A single SSE event: an event name and a serializable payload model."""

    event: str
    data: object  # a pydantic BaseModel; serialized by the router


def _refusal_text(question: str, retrieved: list[RetrievedChunk]) -> str:
    best = max((r.score for r in retrieved), default=0.0)
    return (
        f"{IDK_MESSAGE} I searched the corpus for \"{question}\" but the most "
        f"relevant passage scored only {best:.2f}, below the confidence threshold. "
        "Try rephrasing, or add sources that cover this topic."
    )


def _sources_event(retrieved: list[RetrievedChunk]) -> SourcesEvent:
    return SourcesEvent(
        retrieved=[
            SourceItem(
                chunk_id=r.chunk.id,
                score=round(r.score, 4),
                used=r.used,
                section=r.chunk.section,
                source=r.chunk.source,
            )
            for r in retrieved
        ]
    )


async def run_chat(question: str, store: VectorStore) -> AsyncIterator[Event]:
    """Run the RAG pipeline for one question, yielding SSE events."""
    settings = get_settings()
    message_id = str(uuid.uuid4())

    # 1. Retrieve.
    query_vec = get_embedder().embed_one(question)
    retrieved = store.search(query_vec, settings.top_k)
    best_score = max((r.score for r in retrieved), default=0.0)

    # 2. Relevance gate -> refuse on weak evidence.
    if not retrieved or best_score < settings.relevance_threshold:
        yield Event("token", TokenEvent(text=_refusal_text(question, retrieved)))
        yield Event("sources", _sources_event(retrieved))
        yield Event("done", DoneEvent(message_id=message_id, answer_status="idk"))
        return

    # 3. Generate a grounded answer, streaming tokens.
    messages = build_messages(question, retrieved)
    answer_parts: list[str] = []
    try:
        async for token in get_llm().stream(messages):
            answer_parts.append(token)
            yield Event("token", TokenEvent(text=token))
    except LLMError as exc:
        yield Event("token", TokenEvent(text=f"[generation unavailable] {exc}"))
        yield Event("sources", _sources_event(retrieved))
        yield Event("done", DoneEvent(message_id=message_id, answer_status="partial"))
        return

    answer = "".join(answer_parts)

    # 4. Map [n] markers actually used -> citations, and flag used chunks.
    used_markers = sorted(
        {int(m) for m in _MARKER_RE.findall(answer) if 1 <= int(m) <= len(retrieved)}
    )
    for marker in used_markers:
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

    yield Event("sources", _sources_event(retrieved))

    status = _classify(answer, used_markers)
    yield Event("done", DoneEvent(message_id=message_id, answer_status=status))


def _classify(answer: str, used_markers: list[int]) -> str:
    """Grounded if cited; idk if the model refused; partial otherwise."""
    if IDK_MESSAGE.lower() in answer.lower() and not used_markers:
        return "idk"
    if used_markers:
        return "grounded"
    return "partial"
