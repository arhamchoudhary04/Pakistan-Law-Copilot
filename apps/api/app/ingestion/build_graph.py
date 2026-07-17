"""Populate the Neo4j cross-reference graph from the indexed corpus.

Run after building the vector index:

    python -m app.ingestion.build_graph

Reads the persisted chunks, extracts intra-Act cross-references (rule-based, no
LLM), and writes provision/act nodes + REFERENCES edges into Neo4j.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.retrieval.graph_store import get_graph_store
from app.retrieval.vector_store import VectorStore


def build_graph() -> None:
    settings = get_settings()
    store = get_graph_store()
    if store is None:
        raise SystemExit(
            "Graph is disabled or unconfigured. Set GRAPH_ENABLED=true and "
            "NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD in .env."
        )
    if not store.verify():
        raise SystemExit(
            f"Could not connect to Neo4j at {settings.neo4j_uri}. "
            "Check the instance is running and the credentials/URI are correct."
        )

    vector_store = VectorStore.load(settings.data_path)
    print(f"Loaded {len(vector_store)} chunk(s); building cross-reference graph ...")
    result = store.build(vector_store.chunks)
    print(f"Graph built: {result['provisions']} provisions, {result['references']} references.")
    store.close()


if __name__ == "__main__":
    build_graph()
