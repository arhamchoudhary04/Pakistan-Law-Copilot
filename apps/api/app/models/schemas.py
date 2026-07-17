"""Pydantic schemas shared across ingestion, retrieval, the agent, and the API.

These also define the structured payloads for the ``/chat`` SSE event stream
(``token`` / ``citation`` / ``sources`` / ``done``) described in the project spec.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AnswerStatus = Literal["grounded", "idk", "partial"]


class Chunk(BaseModel):
    """A single indexed passage of a source document."""

    id: str
    doc_id: str
    ordinal: int
    content: str
    section: str = ""
    source: str = ""
    token_count: int = 0


class RetrievedChunk(BaseModel):
    """A chunk returned by retrieval, with its relevance score and usage flag.

    ``score`` is the vector cosine similarity (0..1, used by the relevance gate).
    ``rerank_score`` is the cross-encoder logit assigned during reranking, if any.
    """

    chunk: Chunk
    score: float
    rerank_score: float | None = None
    used: bool = False
    via_graph: bool = False  # added by graph expansion (cross-reference), not vector search


# ---- API request models ----


class ChatOptions(BaseModel):
    show_inspector: bool = True


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)
    options: ChatOptions = Field(default_factory=ChatOptions)


# ---- SSE event payloads ----


class StageEvent(BaseModel):
    """One pipeline stage's result — powers the Retrieval Inspector."""

    stage: str
    detail: str = ""
    latency_ms: float = 0.0


class TokenEvent(BaseModel):
    text: str


class CitationEvent(BaseModel):
    marker: int
    chunk_id: str
    source: str
    section: str


class SourceItem(BaseModel):
    chunk_id: str
    score: float
    rerank_score: float | None = None
    used: bool
    via_graph: bool = False
    section: str = ""
    source: str = ""


class SourcesEvent(BaseModel):
    retrieved: list[SourceItem]


class DoneEvent(BaseModel):
    message_id: str
    answer_status: AnswerStatus
    attempts: int = 1
