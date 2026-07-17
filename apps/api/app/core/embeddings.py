"""Local embedding provider backed by fastembed.

Uses ``BAAI/bge-small-en-v1.5`` (384-dim) by default. Vectors are L2-normalized
so that a FAISS inner-product search yields cosine similarity in ``[0, 1]``,
which the relevance gate compares against ``RELEVANCE_THRESHOLD``.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.core.config import get_settings


class Embedder:
    """Thin wrapper over fastembed that returns normalized float32 vectors."""

    def __init__(self, model_name: str, dim: int, cache_dir: str | None = None) -> None:
        # Imported lazily so importing this module (e.g. in tests) is cheap and
        # doesn't trigger a model download until embeddings are actually needed.
        from fastembed import TextEmbedding

        self.model_name = model_name
        self.dim = dim
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts -> ``(n, dim)`` L2-normalized float32 array."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = np.array(list(self._model.embed(texts)), dtype=np.float32)
        return self._normalize(vectors)

    def embed_one(self, text: str) -> np.ndarray:
        """Embed a single text -> ``(dim,)`` L2-normalized float32 vector."""
        return self.embed([text])[0]

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vectors / norms).astype(np.float32)


@lru_cache
def get_embedder() -> Embedder:
    """Return a cached Embedder built from application settings."""
    settings = get_settings()
    return Embedder(
        model_name=settings.embed_model,
        dim=settings.embed_dim,
        cache_dir=str(settings.model_cache_path),
    )
