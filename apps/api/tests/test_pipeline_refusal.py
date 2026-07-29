"""The refusal path is the point of the project, so test it hermetically.

We stub the embedder and LLM (so no model download / API key) and use an empty
index so nothing clears the relevance gate. The agent must refuse with
answer_status 'idk', run the grade->fallback branch, and emit NO citation events.
"""

from collections.abc import AsyncIterator

import numpy as np

from app.agent import graph, pipeline
from app.core.llm import LLMError
from app.models.schemas import DoneEvent
from app.retrieval.vector_store import VectorStore


class _StubEmbedder:
    def embed_one(self, text: str) -> np.ndarray:
        return np.zeros(2, dtype=np.float32)


class _NoLLM:
    async def stream(self, messages, **kwargs) -> AsyncIterator[str]:
        raise LLMError("no key in test")
        yield  # pragma: no cover - marks this an async generator


async def test_refuses_on_empty_index(monkeypatch):
    monkeypatch.setattr(graph, "get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr(graph, "get_llm", lambda: _NoLLM())
    store = VectorStore.build(dim=2, chunks=[], vectors=np.zeros((0, 2), dtype=np.float32))

    events = [e async for e in pipeline.run_chat("anything at all?", store)]

    names = [e.event for e in events]
    assert "token" in names
    assert "citation" not in names  # never fabricate citations on refusal

    stages = [e.data.stage for e in events if e.event == "stage"]
    assert "grade" in stages and "fallback" in stages

    done = [e.data for e in events if e.event == "done"]
    assert len(done) == 1
    assert isinstance(done[0], DoneEvent)
    assert done[0].answer_status == "idk"
