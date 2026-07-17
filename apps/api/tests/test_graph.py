"""Graph reference extraction (pure) and hybrid expansion (stubbed, no Neo4j)."""

from app.agent import graph
from app.agent.graph import _graph_expand
from app.core.config import Settings
from app.models.schemas import Chunk, RetrievedChunk
from app.retrieval.graph_refs import (
    chunk_key,
    extract_reference_numbers,
    provision_number,
)


def _chunk(doc: str, section: str, content: str = "") -> Chunk:
    return Chunk(id=f"{doc}:{section}", doc_id=doc, ordinal=0, content=content, section=section)


# ---- graph_refs (pure) ----


def test_provision_number_parses_article_and_section():
    assert provision_number("Constitution > Article 25. Equality of citizens") == "25"
    assert provision_number("PECA > Section 7A. Attendance (CHAPTER I)") == "7A"
    assert provision_number("An act with no provision heading") is None


def test_extract_reference_numbers():
    text = "Subject to Article 251, and as provided in section 7 and Section 13A."
    assert extract_reference_numbers(text) == {"251", "7", "13A"}


def test_chunk_key():
    c = _chunk("muslim.md", "Muslim Family Laws > Section 8. Dissolution")
    assert chunk_key(c) == "muslim.md#8"


# ---- hybrid expansion (stubbed) ----


class _StubGraph:
    def neighbors(self, keys):
        return {"muslim.md#2"}  # §8 references §2 (Definitions)


class _StubStore:
    def chunks_for_keys(self, keys, key_fn):
        return [_chunk("muslim.md", "Muslim Family Laws > Section 2. Definitions")]

    def similarity(self, query_vec, chunk):
        return 0.55


def test_graph_expand_adds_cross_referenced_provision(monkeypatch):
    monkeypatch.setattr(graph, "get_settings", lambda: Settings(graph_enabled=True))
    monkeypatch.setattr(graph, "get_graph_store", lambda: _StubGraph())

    candidates = [
        RetrievedChunk(
            chunk=_chunk("muslim.md", "Muslim Family Laws > Section 8. Dissolution"),
            score=0.79,
        )
    ]
    added = _graph_expand(_StubStore(), candidates, query_vec=None)

    assert added == 1
    graph_chunks = [c for c in candidates if c.via_graph]
    assert len(graph_chunks) == 1
    assert chunk_key(graph_chunks[0].chunk) == "muslim.md#2"


def test_graph_expand_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(graph, "get_settings", lambda: Settings(graph_enabled=False))
    candidates = [
        RetrievedChunk(chunk=_chunk("m.md", "Act > Section 1. Foo"), score=0.8)
    ]
    assert _graph_expand(_StubStore(), candidates, query_vec=None) == 0
