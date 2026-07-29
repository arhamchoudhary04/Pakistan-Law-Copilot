"""In-memory registry of user-uploaded documents (ephemeral, per-process).

An uploaded PDF is parsed, chunked, embedded into its own FAISS vector store, and
kept in memory under a generated ``doc_id``. ``/chat`` can then answer from it
instead of the law corpus ("understand your document" mode). Nothing is persisted
— fine for a single-process demo; a real deployment would use shared storage.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.config import get_settings
from app.core.embeddings import get_embedder
from app.ingestion.chunker import approx_tokens
from app.models.schemas import Chunk
from app.retrieval.vector_store import VectorStore

# Public so the router can reject an oversized body *before* buffering it; the
# check below stays as defense-in-depth for direct callers (eval scripts, tests).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_DOCS = 20  # simple LRU-ish cap so memory can't grow unbounded


@dataclass
class UploadedDoc:
    doc_id: str
    filename: str
    store: VectorStore
    chunk_count: int


_DOCS: dict[str, UploadedDoc] = {}


def ingest_pdf(filename: str, data: bytes) -> UploadedDoc:
    """Parse, chunk, and embed an uploaded PDF into an in-memory vector store."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large (max 10 MB).")
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - surface a clean 400 to the client
        raise ValueError("Could not read the PDF.") from exc

    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_tokens,
        chunk_overlap=settings.chunk_overlap,
        length_function=approx_tokens,
    )
    doc_id = uuid.uuid4().hex[:12]
    chunks: list[Chunk] = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        for piece in splitter.split_text(text):
            piece = piece.strip()
            if len(piece) < 20:
                continue
            i = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{doc_id}#{i}",
                    doc_id=filename,
                    ordinal=i,
                    content=piece,
                    section=f"{filename} · p.{page_no}",
                    source=filename,
                    token_count=approx_tokens(piece),
                )
            )
    if not chunks:
        raise ValueError("No extractable text found (is it a scanned/image-only PDF?).")

    vectors = get_embedder().embed([c.content for c in chunks])
    store = VectorStore.build(dim=settings.embed_dim, chunks=chunks, vectors=vectors)

    if len(_DOCS) >= _MAX_DOCS:
        _DOCS.pop(next(iter(_DOCS)))  # evict oldest
    doc = UploadedDoc(doc_id=doc_id, filename=filename, store=store, chunk_count=len(chunks))
    _DOCS[doc_id] = doc
    return doc


def get_doc(doc_id: str) -> UploadedDoc | None:
    return _DOCS.get(doc_id)
