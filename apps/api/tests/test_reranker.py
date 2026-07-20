"""Reranker reordering logic, with a stubbed cross-encoder (no model download)."""

from app.models.schemas import Chunk, RetrievedChunk
from app.retrieval.reranker import Reranker


class _FakeModel:
    """Stand-in for fastembed's TextCrossEncoder."""

    def __init__(self, scores):
        self._scores = scores

    def rerank(self, query, documents):
        return list(self._scores)


def _rc(i: int, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(id=f"d.md#{i}", doc_id="d.md", ordinal=i, content=f"c{i}"),
        score=score,
    )


def test_rerank_reorders_by_cross_encoder_score():
    # Vector order is 0,1,2; cross-encoder prefers chunk 2, then 0, then 1.
    reranker = object.__new__(Reranker)
    reranker.model_name = "stub"
    reranker._model = _FakeModel([0.2, -1.0, 5.0])

    candidates = [_rc(0, 0.9), _rc(1, 0.8), _rc(2, 0.7)]
    ranked = reranker.rerank("q", candidates, top_k=2)

    assert [r.chunk.id for r in ranked] == ["d.md#2", "d.md#0"]
    assert ranked[0].rerank_score == 5.0
    assert all(r.rerank_score is not None for r in ranked)


def test_rerank_empty_is_safe():
    reranker = object.__new__(Reranker)
    reranker._model = _FakeModel([])
    assert reranker.rerank("q", [], top_k=5) == []
