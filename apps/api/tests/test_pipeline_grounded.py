"""Grounded generation path: stub the embedder + LLM so no model/key is needed.

Verifies that when evidence clears the gate and the model returns an answer with
[n] markers, the pipeline emits matching citation events, flags the used chunks,
and reports answer_status 'grounded'.
"""

from collections.abc import AsyncIterator

import numpy as np

from app.agent import pipeline
from app.models.schemas import Chunk, DoneEvent, RetrievedChunk


class _StubEmbedder:
    def embed_one(self, text: str) -> np.ndarray:
        return np.ones(2, dtype=np.float32)


class _StubLLM:
    async def stream(self, messages, **kwargs) -> AsyncIterator[str]:
        for tok in ["Use ", "a type annotation ", "like item_id: int [1]. ", "Also [2]."]:
            yield tok


def _retrieved() -> list[RetrievedChunk]:
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


async def test_grounded_answer_emits_citations(monkeypatch):
    monkeypatch.setattr(pipeline, "get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr(pipeline, "get_llm", lambda: _StubLLM())

    class _Store:
        def search(self, vec, k):
            return _retrieved()

    events = [e async for e in pipeline.run_chat("How do I type a path param?", _Store())]

    kinds = [e.event for e in events]
    assert kinds.count("token") == 4
    citations = [e.data for e in events if e.event == "citation"]
    assert {c.marker for c in citations} == {1, 2}
    assert all(c.source == "path-parameters.md" for c in citations)

    sources = next(e.data for e in events if e.event == "sources")
    assert all(s.used for s in sources.retrieved)  # both markers were used

    done = next(e.data for e in events if e.event == "done")
    assert isinstance(done, DoneEvent)
    assert done.answer_status == "grounded"
