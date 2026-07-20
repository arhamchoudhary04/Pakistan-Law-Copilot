"""Rule-based extraction of legal cross-references.

Provisions cite each other explicitly ("subject to Article 251", "under section 7").
We extract those references from the text with regex (no LLM) to build the edges of
the citation graph. These helpers are shared by the graph builder and the hybrid
retriever, so both agree on how a chunk maps to a provision key.
"""

from __future__ import annotations

import re

from app.models.schemas import Chunk

# The provision this chunk belongs to, parsed from its section breadcrumb
# ("... > Article 25. Equality of citizens" / "... > Section 7. Talaq (CHAPTER ...)").
_PROVISION_RE = re.compile(r"(?:Article|Section)\s+(\d+[A-Z]{0,3})\.")
# References to other provisions in the body text.
_REF_RE = re.compile(r"(?:Article|[Ss]ection)\s+(\d+[A-Z]{0,3})\b")


def provision_number(section: str) -> str | None:
    """Return the provision number a chunk belongs to (last match wins), or None."""
    matches = _PROVISION_RE.findall(section or "")
    return matches[-1] if matches else None


def provision_key(doc_id: str, number: str) -> str:
    """Stable node key: unique per Act + provision number."""
    return f"{doc_id}#{number}"


def chunk_key(chunk: Chunk) -> str | None:
    """The provision key a chunk belongs to, or None if not parseable."""
    number = provision_number(chunk.section)
    return provision_key(chunk.doc_id, number) if number else None


def extract_reference_numbers(text: str) -> set[str]:
    """Return the set of provision numbers referenced in the given body text."""
    return {m for m in _REF_RE.findall(text or "")}
