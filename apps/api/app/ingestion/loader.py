"""Corpus loader.

Reads markdown files from the configured corpus directory into ``Document``
objects. The document id is the path relative to the corpus root (stable and
human-readable), which downstream chunks reference for citations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}


@dataclass
class Document:
    """A raw source document loaded from the corpus."""

    doc_id: str
    title: str
    source: str
    text: str


def load_corpus(corpus_dir: Path) -> list[Document]:
    """Load all markdown documents under ``corpus_dir`` (recursively)."""
    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"Corpus directory not found: {corpus_dir}. "
            "Add markdown files there or set CORPUS_DIR."
        )

    documents: list[Document] = []
    for path in sorted(corpus_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        rel = path.relative_to(corpus_dir).as_posix()
        documents.append(
            Document(
                doc_id=rel,
                title=_derive_title(text, fallback=path.stem),
                source=rel,
                text=text,
            )
        )
    return documents


def _derive_title(text: str, fallback: str) -> str:
    """Use the first markdown H1 as the title, else the filename stem."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback
