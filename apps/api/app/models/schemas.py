"""Pydantic schemas shared across ingestion, retrieval, the agent, and the API.

These also define the structured payloads for the ``/chat`` SSE event stream
(``token`` / ``citation`` / ``sources`` / ``done``).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AnswerStatus = Literal["grounded", "idk", "partial"]

# Request-size bounds for /chat. Generous for a real legal question, but finite.
MAX_MESSAGE_CHARS = 4_000
MAX_ANSWER_CHARS = 20_000
MAX_HISTORY_TURNS = 20


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


class HistoryTurn(BaseModel):
    """A prior turn, sent by the client so the agent can resolve follow-ups."""

    question: str = Field(max_length=MAX_MESSAGE_CHARS)
    answer: str = Field(max_length=MAX_ANSWER_CHARS)


class ChatRequest(BaseModel):
    session_id: str | None = None
    # Bounded because the question is interpolated into the prompt verbatim (see
    # prompts.build_messages); without a cap a single request can drive unbounded
    # token cost on an endpoint that is unauthenticated by design.
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    # Recent prior turns (client-supplied) for follow-up context; the agent stays
    # otherwise stateless. Newest last. Only the last few reach the prompt (and
    # truncated at that), so the cap here bounds request-parsing cost, not tokens.
    history: list[HistoryTurn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)
    # When set, answer from this uploaded document instead of the law corpus.
    doc_id: str | None = None
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


# ---- Auth & chat history ----


def _clean_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or "." not in v.split("@")[-1]:
        raise ValueError("Enter a valid email address.")
    return v


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=6, max_length=200)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        return _clean_email(v)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ForgotPasswordResponse(BaseModel):
    message: str
    # Only populated in dev (no email service): the token to complete the reset.
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=200)


class UserOut(BaseModel):
    id: str
    email: str
    name: str = ""


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: str


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    meta: dict | None = None


class ConversationDetail(BaseModel):
    id: str
    title: str
    updated_at: str
    messages: list[MessageOut]


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New chat", max_length=200)


class SaveTurnRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str
    meta: dict | None = None
