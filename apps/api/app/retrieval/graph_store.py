"""Neo4j-backed knowledge graph of legal cross-references.

Graph model:
    (:Provision {key, act, number, title}) -[:IN_ACT]-> (:Act {name})
    (:Provision) -[:REFERENCES]-> (:Provision)      # cross-reference, same Act

The graph is optional: if it is disabled or Neo4j is unreachable, retrieval falls
back to vector-only. Edges are built deterministically from provision text (see
``graph_refs``), so nothing here calls an LLM.
"""

from __future__ import annotations

from functools import lru_cache

from neo4j import GraphDatabase

from app.core.config import get_settings
from app.models.schemas import Chunk
from app.retrieval.graph_refs import (
    extract_reference_numbers,
    provision_key,
    provision_number,
)


class GraphStore:
    """Thin Neo4j client for building and querying the cross-reference graph."""

    def __init__(self, uri: str, user: str, password: str, database: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=30)
        self._database = database

    def verify(self) -> bool:
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._driver.close()

    def build(self, chunks: list[Chunk]) -> dict[str, int]:
        """(Re)build the graph from corpus chunks. Wipes and repopulates."""
        provisions: dict[str, dict[str, str]] = {}
        for c in chunks:
            number = provision_number(c.section)
            if not number:
                continue
            key = provision_key(c.doc_id, number)
            provisions.setdefault(
                key,
                {
                    "key": key,
                    "act": c.doc_id,
                    "number": number,
                    "title": c.section.split(">")[-1].strip(),
                },
            )

        known = set(provisions)
        edges: set[tuple[str, str]] = set()
        for c in chunks:
            number = provision_number(c.section)
            if not number:
                continue
            src = provision_key(c.doc_id, number)
            for ref in extract_reference_numbers(c.content):
                tgt = provision_key(c.doc_id, ref)
                if tgt in known and tgt != src:
                    edges.add((src, tgt))

        rows = list(provisions.values())
        edge_rows = [{"src": s, "tgt": t} for s, t in edges]
        with self._driver.session(database=self._database) as session:
            session.run("MATCH (n) DETACH DELETE n")
            session.run(
                "UNWIND $rows AS r "
                "MERGE (p:Provision {key: r.key}) "
                "SET p.act = r.act, p.number = r.number, p.title = r.title "
                "MERGE (a:Act {name: r.act}) "
                "MERGE (p)-[:IN_ACT]->(a)",
                rows=rows,
            )
            session.run(
                "UNWIND $edges AS e "
                "MATCH (a:Provision {key: e.src}), (b:Provision {key: e.tgt}) "
                "MERGE (a)-[:REFERENCES]->(b)",
                edges=edge_rows,
            )
        return {"provisions": len(rows), "references": len(edge_rows)}

    def neighbors(self, keys: list[str]) -> set[str]:
        """Return provision keys 1 hop away (either direction) from the given keys."""
        if not keys:
            return set()
        with self._driver.session(database=self._database) as session:
            result = session.run(
                "MATCH (p:Provision)-[:REFERENCES]-(n:Provision) "
                "WHERE p.key IN $keys RETURN DISTINCT n.key AS key",
                keys=list(keys),
            )
            return {record["key"] for record in result}

    def stats(self) -> dict[str, int]:
        def _count(session, query: str) -> int:
            record = session.run(query).single()
            return int(record["c"]) if record else 0

        with self._driver.session(database=self._database) as session:
            return {
                "provisions": _count(session, "MATCH (p:Provision) RETURN count(p) AS c"),
                "references": _count(session, "MATCH ()-[r:REFERENCES]->() RETURN count(r) AS c"),
            }


@lru_cache
def get_graph_store() -> GraphStore | None:
    """Return a cached GraphStore, or None if the graph is disabled/unconfigured.

    Connectivity is NOT verified here (avoids a network dependency at startup);
    callers wrap graph queries so an unreachable Neo4j degrades to vector-only.
    """
    settings = get_settings()
    if not settings.graph_enabled or not settings.neo4j_uri or not settings.neo4j_password:
        return None
    return GraphStore(
        uri=settings.neo4j_uri,
        user=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
