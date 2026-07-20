"""``POST /documents``: upload a PDF to ask questions grounded in it.

Returns a ``doc_id`` the client passes to ``/chat`` to answer from the uploaded
document instead of the law corpus.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.ingestion.uploads import ingest_pdf

router = APIRouter()


@router.post("/documents")
async def upload_document(file: Annotated[UploadFile, File()]) -> dict[str, object]:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    data = await file.read()
    try:
        doc = ingest_pdf(file.filename or "document.pdf", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"doc_id": doc.doc_id, "filename": doc.filename, "chunks": doc.chunk_count}
