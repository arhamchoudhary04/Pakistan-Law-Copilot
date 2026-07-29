"""FastAPI application entrypoint.

On startup we load the persisted FAISS index into ``app.state.store`` so every
request reuses one in-memory index. If no index exists yet, the app still starts
(so ``/health`` works) and ``/chat`` returns a clear 503 telling you to ingest.

Run:  uvicorn app.main:app --reload   (from apps/api)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.ratelimit import RateLimitMiddleware
from app.db.store import get_account_store
from app.retrieval.vector_store import VectorStore
from app.routers import auth, chat, conversations, documents, health

logger = logging.getLogger("app")


def _enforce_security(settings: Settings) -> None:
    """Fail fast on insecure auth config in production; warn about it in dev."""
    problems = settings.security_problems()
    if not problems:
        return
    if settings.is_production:
        raise RuntimeError(
            "Refusing to start in production with insecure auth config:\n  - "
            + "\n  - ".join(problems)
        )
    for problem in problems:
        logger.warning("insecure dev config (APP_ENV=%s): %s", settings.app_env, problem)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    try:
        app.state.store = VectorStore.load(settings.data_path)
        logger.info("Loaded index: %d chunk(s) from %s", len(app.state.store), settings.data_path)
    except FileNotFoundError as exc:
        app.state.store = None
        logger.warning("No index loaded (%s). /chat will return 503 until you ingest.", exc)
    # Open (and create, first run) the accounts/history database up front.
    get_account_store()
    logger.info("Accounts DB ready at %s", settings.app_db_path)
    yield


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    _enforce_security(settings)
    app = FastAPI(
        title="Knowledge Copilot API",
        version="0.1.0",
        description="Grounded, citation-first RAG over a trusted corpus.",
        lifespan=lifespan,
    )
    # Starlette makes the last-added middleware outermost, so registering the limiter
    # first leaves CORS wrapping it. A 429 without CORS headers reaches the browser as
    # an opaque network failure.
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware, trust_proxy_headers=settings.rate_limit_trust_proxy
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, tags=["auth"])
    app.include_router(conversations.router, tags=["conversations"])
    app.include_router(chat.router, tags=["chat"])
    app.include_router(documents.router, tags=["documents"])
    return app


app = create_app()
