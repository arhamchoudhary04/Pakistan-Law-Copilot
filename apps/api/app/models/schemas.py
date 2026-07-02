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
    """A chunk returned by retrieval, with its relevance score and usage flag."""

    chunk: Chunk
    score: float
    used: bool = False


# ---- API request models ----


class ChatOptions(BaseModel):
    show_inspector: bool = True


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)
    options: ChatOptions = Field(default_factory=ChatOptions)


# ---- SSE event payloads ----


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
    used: bool
    section: str = ""
    source: str = ""


class SourcesEvent(BaseModel):
    retrieved: list[SourceItem]


class DoneEvent(BaseModel):
    message_id: str
    answer_status: AnswerStatus
