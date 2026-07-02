"""Cross-encoder reranker (local, via fastembed).

A cross-encoder jointly scores the (query, passage) pair, which is far more
precise than the bi-encoder cosine similarity used for the initial recall. We
pull a larger candidate pool from the vector store, then rerank down to top-k.
This is usually the single biggest precision win in a RAG pipeline; the eval
harness quantifies it (``python eval/run_eval.py --ablation``).

The model is an ONNX cross-encoder served by fastembed, so no torch dependency
is needed and it runs fully locally.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.models.schemas import RetrievedChunk


class Reranker:
    """Reorders candidate chunks by cross-encoder relevance to the query."""

    def __init__(self, model_name: str) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self.model_name = model_name
        self._model = TextCrossEncoder(model_name=model_name)

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        """Score candidates against the query and return the top-k, reranked."""
        if not candidates:
            return []
        scores = list(self._model.rerank(query, [c.chunk.content for c in candidates]))
        for cand, score in zip(candidates, scores, strict=True):
            cand.rerank_score = float(score)
        ranked = sorted(candidates, key=lambda c: c.rerank_score or 0.0, reverse=True)
        return ranked[:top_k]


@lru_cache
def get_reranker() -> Reranker:
    """Return a cached Reranker built from application settings."""
    return Reranker(model_name=get_settings().rerank_model)
