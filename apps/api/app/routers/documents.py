"""``POST /documents``: upload a PDF to ask questions grounded in it.

Returns a ``doc_id`` the client passes to ``/chat`` to answer from the uploaded
document instead of the law corpus.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.ingestion.uploads import MAX_UPLOAD_BYTES, ingest_pdf

router = APIRouter()

_READ_CHUNK = 1 << 20  # 1 MiB


async def _read_capped(file: UploadFile, limit: int) -> bytes:
    """Read at most ``limit`` bytes, aborting as soon as the body exceeds it.

    ``await file.read()`` with no argument materializes the whole upload in memory,
    so the size check has to happen *while* reading rather than after: a multi-GB
    body would otherwise exhaust memory before any limit was consulted.
    """
    parts: list[bytes] = []
    total = 0
    while piece := await file.read(_READ_CHUNK):
        total += len(piece)
        if total > limit:
            raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
        parts.append(piece)
    return b"".join(parts)


@router.post("/documents")
async def upload_document(
    request: Request, file: Annotated[UploadFile, File()]
) -> dict[str, object]:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Cheap pre-check on the declared size, before reading the body. A missing or
    # dishonest Content-Length is still caught by the capped read below.
    # Note: Starlette has already spooled the multipart body by this point, so a
    # truly early reject also needs a body-size limit at the proxy / ingress.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    data = await _read_capped(file, MAX_UPLOAD_BYTES)

    try:
        # Parsing and embedding are blocking CPU work; keep them off the event loop
        # so concurrent requests and in-flight SSE streams aren't stalled.
        doc = await run_in_threadpool(ingest_pdf, file.filename or "document.pdf", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"doc_id": doc.doc_id, "filename": doc.filename, "chunks": doc.chunk_count}
