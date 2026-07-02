"""``POST /chat`` — streams a grounded answer over Server-Sent Events.

Event contract (spec §11, extended with ``stage`` for the Retrieval Inspector):
    stage    -> pipeline node result: {stage, detail, latency_ms}
    token    -> {text}
    citation -> {marker, chunk_id, source, section}
    sources  -> {retrieved: [{chunk_id, score, rerank_score, used}, ...]}
    done     -> {message_id, answer_status: grounded|idk|partial, attempts}
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent.pipeline import run_chat
from app.models.schemas import ChatRequest
from app.retrieval.vector_store import VectorStore

router = APIRouter()


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> EventSourceResponse:
    """Stream the answer to a question as SSE events."""
    store: VectorStore | None = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Index not loaded. Run: python -m app.ingestion.build_index",
        )

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        async for event in run_chat(body.message, store):
            # Client disconnected — stop generating (and stop paying the LLM).
            if await request.is_disconnected():
                break
            data = event.data
            payload = data.model_dump_json() if isinstance(data, BaseModel) else str(data)
            yield {"event": event.event, "data": payload}

    return EventSourceResponse(event_generator())
