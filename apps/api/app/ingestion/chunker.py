"""Structure-aware chunking.

Split on markdown headers first (so each chunk stays within one section and carries
a ``section`` label for citations), then enforce a token budget with a recursive
character splitter. Token counts are approximated (~4 chars/token) to avoid a
tokenizer dependency.
"""

from __future__ import annotations

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.ingestion.loader import Document
from app.models.schemas import Chunk

_HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
]


def approx_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token)."""
    return max(1, len(text) // 4)


def chunk_documents(
    documents: list[Document],
    *,
    chunk_tokens: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Split loaded documents into indexed ``Chunk`` objects."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_HEADERS,
        strip_headers=False,
    )
    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_tokens,
        chunk_overlap=chunk_overlap,
        length_function=approx_tokens,
    )

    chunks: list[Chunk] = []
    for doc in documents:
        ordinal = 0
        for section_doc in header_splitter.split_text(doc.text):
            section = _section_label(section_doc.metadata, default=doc.title)
            for piece in size_splitter.split_text(section_doc.page_content):
                text = piece.strip()
                if not text:
                    continue
                chunks.append(
                    Chunk(
                        id=f"{doc.doc_id}#{ordinal}",
                        doc_id=doc.doc_id,
                        ordinal=ordinal,
                        content=text,
                        section=section,
                        source=doc.source,
                        token_count=approx_tokens(text),
                    )
                )
                ordinal += 1
    return chunks


def _section_label(metadata: dict[str, str], default: str) -> str:
    """Build a ``H1 > H2 > H3`` breadcrumb from header-split metadata."""
    parts = [metadata[key] for key in ("h1", "h2", "h3", "h4") if metadata.get(key)]
    return " > ".join(parts) if parts else default
