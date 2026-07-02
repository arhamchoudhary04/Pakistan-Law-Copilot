"""Grounded generation path through the LangGraph agent, fully stubbed.

Rewrite and rerank are disabled via settings; the embedder and LLM are stubbed so
no model download or API key is needed. A stub store returns high-cosine
candidates so the gate passes; the stub LLM returns an answer citing [1][2]. The
agent must emit those citations, flag the used chunks, and report 'grounded'.
"""

from collections.abc import AsyncIterator

import numpy as np

from app.agent import graph, pipeline
from app.core.config import Settings
from app.models.schemas import Chunk, DoneEvent, RetrievedChunk


class _StubEmbedder:
    def embed_one(self, text: str) -> np.ndarray:
        return np.ones(2, dtype=np.float32)


class _StubLLM:
    async def stream(self, messages, **kwargs) -> AsyncIterator[str]:
        for tok in ["Use ", "a type annotation [1]. ", "See also [2]."]:
            yield tok


def _candidates() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk=Chunk(id="path-parameters.md#2", doc_id="path-parameters.md",
                        ordinal=2, content="...", section="Path Parameters",
                        source="path-parameters.md"),
            score=0.87,
        ),
        RetrievedChunk(
            chunk=Chunk(id="path-parameters.md#1", doc_id="path-parameters.md",
                        ordinal=1, content="...", section="Declaring a path parameter",
                        source="path-parameters.md"),
            score=0.84,
        ),
    ]


class _StubStore:
    def search(self, vec, k):
        return _candidates()


async def test_grounded_answer_emits_citations(monkeypatch):
    settings = Settings(rewrite_enabled=False, rerank_enabled=False, verify_enabled=True)
    monkeypatch.setattr(graph, "get_settings", lambda: settings)
    monkeypatch.setattr(graph, "get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr(graph, "get_llm", lambda: _StubLLM())

    events = [e async for e in pipeline.run_chat("How do I type a path param?", _StubStore())]

    citations = [e.data for e in events if e.event == "citation"]
    assert {c.marker for c in citations} == {1, 2}
    assert all(c.source == "path-parameters.md" for c in citations)

    sources = next(e.data for e in events if e.event == "sources")
    assert all(s.used for s in sources.retrieved)

    done = next(e.data for e in events if e.event == "done")
    assert isinstance(done, DoneEvent)
    assert done.answer_status == "grounded"
    assert done.attempts == 1
