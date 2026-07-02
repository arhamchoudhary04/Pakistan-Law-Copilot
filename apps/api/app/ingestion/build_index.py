"""Ingestion entrypoint: load -> chunk -> embed -> build & persist FAISS index.

Run from ``apps/api`` (or anywhere; paths resolve from the repo root):

    python -m app.ingestion.build_index
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.embeddings import get_embedder
from app.ingestion.chunker import chunk_documents
from app.ingestion.loader import load_corpus
from app.retrieval.vector_store import VectorStore


def build_index() -> VectorStore:
    """Build the vector index from the configured corpus and persist it."""
    settings = get_settings()

    print(f"Loading corpus from {settings.corpus_path} ...")
    documents = load_corpus(settings.corpus_path)
    print(f"  loaded {len(documents)} document(s)")

    chunks = chunk_documents(
        documents,
        chunk_tokens=settings.chunk_tokens,
        chunk_overlap=settings.chunk_overlap,
    )
    print(f"  produced {len(chunks)} chunk(s)")
    if not chunks:
        raise SystemExit("No chunks produced — is the corpus empty?")

    print(f"Embedding with {settings.embed_model} ...")
    embedder = get_embedder()
    vectors = embedder.embed([c.content for c in chunks])

    store = VectorStore.build(dim=settings.embed_dim, chunks=chunks, vectors=vectors)
    store.save(settings.data_path)
    print(f"Indexed {len(store)} chunk(s) -> {settings.data_path}")
    return store


if __name__ == "__main__":
    build_index()
