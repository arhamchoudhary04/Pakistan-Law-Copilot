"""FastAPI application entrypoint.

On startup we load the persisted FAISS index into ``app.state.store`` so every
request reuses one in-memory index. If no index exists yet, the app still starts
(so ``/health`` works) and ``/chat`` returns a clear 503 telling you to ingest.

Run:  uvicorn app.main:app --reload   (from apps/api)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.store import get_account_store
from app.retrieval.vector_store import VectorStore
from app.routers import auth, chat, conversations, documents, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    try:
        app.state.store = VectorStore.load(settings.data_path)
        print(f"Loaded index: {len(app.state.store)} chunk(s) from {settings.data_path}")
    except FileNotFoundError as exc:
        app.state.store = None
        print(f"No index loaded ({exc}). /chat will return 503 until you ingest.")
    # Open (and create, first run) the accounts/history database up front.
    get_account_store()
    print(f"Accounts DB ready at {settings.app_db_path}")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Knowledge Copilot API",
        version="0.1.0",
        description="Grounded, citation-first RAG over a trusted corpus.",
        lifespan=lifespan,
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
