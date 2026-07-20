"""Local embedding provider backed by fastembed.

Uses ``BAAI/bge-small-en-v1.5`` (384-dim). Vectors are L2-normalized so a FAISS
inner-product search yields cosine similarity in [0, 1], which the relevance gate
compares against ``RELEVANCE_THRESHOLD``.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.core.config import get_settings

# Feed fastembed one small batch at a time so it never spawns a worker pool.
_EMBED_BATCH = 128


class Embedder:
    """Thin wrapper over fastembed that returns normalized float32 vectors."""

    def __init__(self, model_name: str, dim: int, cache_dir: str | None = None) -> None:
        # Lazy import so tests can import this module without a model download.
        from fastembed import TextEmbedding

        self.model_name = model_name
        self.dim = dim
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed texts into an ``(n, dim)`` L2-normalized float32 array.

        Batches are kept small on purpose. Given a large list, fastembed forks a
        multiprocessing pool, and on Windows (spawn) each worker reloads the ONNX
        model, ballooning to several GB and sometimes orphaning a worker that never
        exits. One small batch stays in-process and runs fast.
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        out: list[np.ndarray] = []
        for i in range(0, len(texts), _EMBED_BATCH):
            batch = texts[i : i + _EMBED_BATCH]
            out.extend(self._model.embed(batch, batch_size=len(batch)))
        vectors = np.array(out, dtype=np.float32)
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
