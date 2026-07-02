"""FAISS-backed vector store.

Uses a flat inner-product index over L2-normalized vectors, so the returned
scores are cosine similarities in ``[0, 1]``. The index is persisted alongside a
``chunks.json`` sidecar that maps FAISS row ids back to chunk metadata, which is
what makes retrieved passages citable.
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from app.models.schemas import Chunk, RetrievedChunk

_INDEX_FILE = "index.faiss"
_CHUNKS_FILE = "chunks.json"


class VectorStore:
    """A flat cosine-similarity FAISS index with chunk metadata."""

    def __init__(self, dim: int, index: faiss.Index, chunks: list[Chunk]) -> None:
        self.dim = dim
        self.index = index
        self.chunks = chunks

    @classmethod
    def build(cls, dim: int, chunks: list[Chunk], vectors: np.ndarray) -> VectorStore:
        """Build a new index from chunks and their (normalized) vectors."""
        if len(chunks) != vectors.shape[0]:
            raise ValueError("chunks and vectors length mismatch")
        index = faiss.IndexFlatIP(dim)
        if vectors.shape[0]:
            index.add(vectors.astype(np.float32))
        return cls(dim=dim, index=index, chunks=list(chunks))

    def save(self, data_dir: Path) -> None:
        """Persist the FAISS index and chunk metadata to ``data_dir``."""
        data_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(data_dir / _INDEX_FILE))
        payload = {
            "dim": self.dim,
            "chunks": [c.model_dump() for c in self.chunks],
        }
        (data_dir / _CHUNKS_FILE).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, data_dir: Path) -> VectorStore:
        """Load a persisted index. Raises ``FileNotFoundError`` if missing."""
        index_path = data_dir / _INDEX_FILE
        chunks_path = data_dir / _CHUNKS_FILE
        if not index_path.exists() or not chunks_path.exists():
            raise FileNotFoundError(
                f"No index found in {data_dir}. "
                "Run: python -m app.ingestion.build_index"
            )
        payload = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunks = [Chunk.model_validate(c) for c in payload["chunks"]]
        index = faiss.read_index(str(index_path))
        return cls(dim=int(payload["dim"]), index=index, chunks=chunks)

    def search(self, query_vector: np.ndarray, top_k: int) -> list[RetrievedChunk]:
        """Return the top-k most similar chunks with cosine scores."""
        if self.index.ntotal == 0:
            return []
        query = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query, k)
        results: list[RetrievedChunk] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0:
                continue
            results.append(
                RetrievedChunk(chunk=self.chunks[int(idx)], score=float(score))
            )
        return results

    def __len__(self) -> int:
        return int(self.index.ntotal)
