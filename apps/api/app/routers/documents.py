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
    """Read at most ``limit`` bytes, aborting once the body exceeds it.

    An argument-less ``file.read()`` materializes the whole upload, so the check has
    to happen while reading, otherwise a multi-GB body exhausts memory first.
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

    # Cheap reject on the declared size; a missing or lying Content-Length falls
    # through to the capped read. Starlette has already spooled the body by now, so
    # a truly early reject also needs a body limit at the ingress.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    data = await _read_capped(file, MAX_UPLOAD_BYTES)

    try:
        # Parsing and embedding block; keep them off the loop.
        doc = await run_in_threadpool(ingest_pdf, file.filename or "document.pdf", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"doc_id": doc.doc_id, "filename": doc.filename, "chunks": doc.chunk_count}
