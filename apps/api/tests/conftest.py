"""Fixtures for the TestClient-level tests.

``DATA_DIR`` points at ``tmp_path`` and the lru_caches around it are cleared per
test, so nothing here can reach the real ``.data/app.db``. The embedder and LLM are
stubbed, so the suite needs no network, no key, and no model download.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.agent import graph
from app.core.config import Settings, get_settings
from app.db.store import AccountStore, get_account_store
from app.models.schemas import Chunk, RetrievedChunk

TEST_SECRET = "test-secret-not-the-insecure-default"


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_account_store.cache_clear()


@pytest.fixture
def test_env(tmp_path, monkeypatch) -> Iterator[None]:
    """Isolate every cached setting in a tmp dir.

    Env vars outrank the repo-root .env in pydantic-settings, which is what makes
    this override the developer's real config.
    """
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("AUTH_SECRET", TEST_SECRET)
    monkeypatch.setenv("AUTH_DEV_RESET", "true")  # so the reset flow is exercisable
    monkeypatch.setenv("GRAPH_ENABLED", "false")
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture
def store(tmp_path) -> AccountStore:
    return AccountStore(tmp_path / "store-under-test.db")


@pytest.fixture
def client(test_env) -> Iterator[TestClient]:
    """TestClient with lifespan run but no index loaded: the 503 case for /chat."""
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


# ---- Stubs for the chat pipeline ----

_SRC = "constitution-fundamental-rights.md"


class StubEmbedder:
    def embed_one(self, text: str) -> np.ndarray:
        return np.ones(2, dtype=np.float32)


class StubLLM:
    """Streams a fixed answer citing [1], so verify() reports 'grounded'."""

    async def stream(self, messages, **kwargs) -> AsyncIterator[str]:
        for tok in ["You must be produced before a magistrate ", "within 24 hours [1]."]:
            yield tok


class StubStore:
    """Stands in for a VectorStore: one hit, scored above the gate by default."""

    def __init__(self, score: float = 0.87) -> None:
        self._score = score

    def search(self, vec, k) -> list[RetrievedChunk]:
        chunk = Chunk(
            id=f"{_SRC}#10",
            doc_id=_SRC,
            ordinal=0,
            content="A person arrested shall be produced before a magistrate.",
            section="Article 10. Safeguards as to arrest and detention",
            source=_SRC,
        )
        return [RetrievedChunk(chunk=chunk, score=self._score)]

    def __len__(self) -> int:
        return 1


@pytest.fixture
def stub_agent(monkeypatch) -> None:
    settings = Settings(
        rewrite_enabled=False,  # skip the extra LLM round-trip
        rerank_enabled=False,  # skip the cross-encoder download
        verify_enabled=True,
        graph_enabled=False,
        auth_secret=TEST_SECRET,
    )
    monkeypatch.setattr(graph, "get_settings", lambda: settings)
    monkeypatch.setattr(graph, "get_embedder", lambda: StubEmbedder())
    monkeypatch.setattr(graph, "get_llm", lambda: StubLLM())


@pytest.fixture
def chat_client(test_env, stub_agent) -> Iterator[TestClient]:
    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        app.state.store = StubStore()  # after lifespan, which would reset it
        yield test_client


# ---- Helpers ----


def signup(test_client: TestClient, email: str, password: str = "correct-horse") -> str:
    resp = test_client.post(
        "/auth/signup", json={"email": email, "name": "Test User", "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
