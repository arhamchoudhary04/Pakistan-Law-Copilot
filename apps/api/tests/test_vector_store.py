import numpy as np

from app.models.schemas import Chunk
from app.retrieval.vector_store import VectorStore


def _chunk(i: int) -> Chunk:
    return Chunk(id=f"d.md#{i}", doc_id="d.md", ordinal=i, content=f"chunk {i}")


def _normalize(v: np.ndarray) -> np.ndarray:
    return (v / np.linalg.norm(v, axis=1, keepdims=True)).astype(np.float32)


def test_build_search_and_ranking():
    chunks = [_chunk(0), _chunk(1), _chunk(2)]
    vectors = _normalize(np.array([[1, 0], [0, 1], [1, 1]], dtype=np.float32))
    store = VectorStore.build(dim=2, chunks=chunks, vectors=vectors)

    query = _normalize(np.array([[1, 0]], dtype=np.float32))[0]
    results = store.search(query, top_k=3)

    assert len(results) == 3
    # Best match is the identical vector, with cosine ~1.0.
    assert results[0].chunk.id == "d.md#0"
    assert results[0].score == max(r.score for r in results)
    assert results[0].score <= 1.0 + 1e-5


def test_save_and_load_roundtrip(tmp_path):
    chunks = [_chunk(0), _chunk(1)]
    vectors = _normalize(np.array([[1, 0], [0, 1]], dtype=np.float32))
    store = VectorStore.build(dim=2, chunks=chunks, vectors=vectors)
    store.save(tmp_path)

    loaded = VectorStore.load(tmp_path)
    assert len(loaded) == 2
    assert loaded.chunks[0].id == "d.md#0"


def test_empty_index_returns_no_results():
    store = VectorStore.build(dim=2, chunks=[], vectors=np.zeros((0, 2), dtype=np.float32))
    assert store.search(np.zeros(2, dtype=np.float32), top_k=5) == []
