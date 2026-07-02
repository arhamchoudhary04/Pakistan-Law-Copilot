"""Liveness / readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    """Report liveness and whether an index is loaded."""
    store = getattr(request.app.state, "store", None)
    return {
        "status": "ok",
        "index_loaded": store is not None,
        "chunks": len(store) if store is not None else 0,
    }
