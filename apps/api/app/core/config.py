"""Application configuration.

Loads settings from the repo-root ``.env`` (copy of ``.env.example``) using
pydantic-settings. Every field mirrors a variable documented in ``.env.example``.
Path-like settings (``corpus_dir``, ``data_dir``) are resolved relative to the
repo root so the app behaves the same regardless of the current working dir.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/app/core/config.py -> parents[4] == repo root (knowledge-copilot/)
REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Typed application settings, populated from environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Generation provider (Groq, OpenAI-compatible) ----
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"

    # ---- Embeddings provider (local, fastembed) ----
    embed_provider: str = "fastembed"
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384

    # ---- Retrieval ----
    corpus_dir: str = "data/corpus"
    data_dir: str = ".data"
    top_k: int = 5
    # Tuned for bge-small-en-v1.5, whose cosine scores have a high floor: on the
    # golden set, on-topic questions score >=0.78 and off-topic ones <=0.53, so
    # 0.65 cleanly separates "answer" from "I don't know". Re-tune if you swap models.
    relevance_threshold: float = 0.65
    chunk_tokens: int = 600
    chunk_overlap: int = 80

    # ---- Reranking (cross-encoder, local via fastembed) ----
    rerank_enabled: bool = True
    rerank_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    # Candidates pulled from the vector store (per query) before reranking down to top_k.
    rerank_candidates: int = 12

    # ---- Agent (LangGraph) ----
    # Rewrite the query for retrieval and self-verify the answer; loop back on
    # unsupported claims up to `max_attempts` times, then finalize.
    rewrite_enabled: bool = True
    verify_enabled: bool = True
    max_attempts: int = 2

    # ---- Knowledge graph (Neo4j, optional) ----
    # Hybrid retrieval augments vector hits with graph neighbours (cross-referenced
    # provisions). Falls back to vector-only when disabled or Neo4j is unreachable.
    graph_enabled: bool = False
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # ---- Auth & chat history (local SQLite, separate from the Neo4j graph) ----
    # HMAC secret used to sign session tokens. MUST be set to a long random value
    # in production; the default is only for local development.
    auth_secret: str = "dev-insecure-change-me"
    auth_token_ttl_hours: int = 168  # 7 days
    # No email service is wired up, so password-reset tokens can't be emailed. When
    # true (local dev), the reset token is returned in the API response so the flow
    # works end to end. In production set this false and deliver the token by email.
    auth_dev_reset: bool = True

    # ---- API ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Allow 3000 and 3001 by default — Next.js falls back to 3001 when 3000 is taken.
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # ---- Web ----
    next_public_api_url: str = "http://localhost:8000"

    @property
    def corpus_path(self) -> Path:
        """Absolute path to the corpus directory (resolved from repo root)."""
        return self._resolve(self.corpus_dir)

    @property
    def data_path(self) -> Path:
        """Absolute path to the index/data directory (resolved from repo root)."""
        return self._resolve(self.data_dir)

    @property
    def model_cache_path(self) -> Path:
        """Persistent fastembed model cache (avoids the OS temp dir being cleaned)."""
        return self.data_path / "models"

    @property
    def app_db_path(self) -> Path:
        """SQLite file for user accounts and chat history (under the gitignored .data)."""
        return self.data_path / "app.db"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins parsed from the comma-separated setting."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @staticmethod
    def _resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (REPO_ROOT / path)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
