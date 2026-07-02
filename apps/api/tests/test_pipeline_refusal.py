"""The refusal path is the point of the project — test it hermetically.

We stub the embedder (so no model download) and use an empty index so nothing
clears the relevance threshold. The pipeline must refuse with answer_status
'idk' and must NOT emit any citation events.
"""

import numpy as np

from app.agent import pipeline
from app.models.schemas import DoneEvent
from app.retrieval.vector_store import VectorStore


class _StubEmbedder:
    def embed_one(self, text: str) -> np.ndarray:
        return np.zeros(2, dtype=np.float32)


async def test_refuses_on_empty_index(monkeypatch):
    monkeypatch.setattr(pipeline, "get_embedder", lambda: _StubEmbedder())
    store = VectorStore.build(dim=2, chunks=[], vectors=np.zeros((0, 2), dtype=np.float32))

    events = [e async for e in pipeline.run_chat("anything at all?", store)]

    event_names = [e.event for e in events]
    assert "token" in event_names
    assert "citation" not in event_names  # never fabricate citations on refusal

    done = [e.data for e in events if e.event == "done"]
    assert len(done) == 1
    assert isinstance(done[0], DoneEvent)
    assert done[0].answer_status == "idk"
