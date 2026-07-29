"""Shared fixtures for the API-level (TestClient) tests.

Two things have to be true for these tests to be safe and hermetic:

1. **The real database is never touched.** ``DATA_DIR`` is pointed at ``tmp_path``
   and both ``get_settings`` and ``get_account_store`` are ``lru_cache``d, so their
   caches are cleared around every test. Without that, a test would read and write
   the developer's actual ``.data/app.db``.
2. **No model is ever downloaded.** The embedder and LLM are stubbed, so nothing
   here needs network access, a GROQ_API_KEY, or the ~130MB fastembed model.
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
    """Point every cached setting at an isolated tmp dir for the duration of a test.

    Environment variables outrank the repo-root ``.env`` in pydantic-settings, so
    setting them here overrides the developer's real configuration.
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
    """A bare AccountStore on its own SQLite file (no app, no HTTP)."""
    return AccountStore(tmp_path / "store-under-test.db")


@pytest.fixture
def client(test_env) -> Iterator[TestClient]:
    """A TestClient with lifespan run but *no* vector index loaded.

    Entering the context manager runs the lifespan, which creates the accounts DB
    and tries to load an index. There is none in tmp_path, so ``app.state.store``
    stays ``None`` — which is exactly the state ``/chat`` must answer 503 for.
    """
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


# ---- Stubs for the chat pipeline (no model download, no API key) ----

_SRC = "constitution-fundamental-rights.md"


class StubEmbedder:
    def embed_one(self, text: str) -> np.ndarray:
        return np.ones(2, dtype=np.float32)


class StubLLM:
    """Streams a fixed answer that cites [1], so verify() reports 'grounded'."""

    async def stream(self, messages, **kwargs) -> AsyncIterator[str]:
        for tok in ["You must be produced before a magistrate ", "within 24 hours [1]."]:
            yield tok


class StubStore:
    """Stands in for a VectorStore: one high-cosine hit, so the gate passes."""

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
    """Replace the agent's embedder, LLM, and settings with offline stubs."""
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
    """A TestClient whose ``/chat`` is wired to the stub store and stub LLM."""
    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        app.state.store = StubStore()  # set after lifespan, which would reset it
        yield test_client


# ---- Helpers ----


def signup(test_client: TestClient, email: str, password: str = "correct-horse") -> str:
    """Register an account and return its bearer token."""
    resp = test_client.post(
        "/auth/signup", json={"email": email, "name": "Test User", "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
