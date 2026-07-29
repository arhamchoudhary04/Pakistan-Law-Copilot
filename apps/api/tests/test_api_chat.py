"""``/chat``, ``/documents``, and ``/health`` over HTTP.

The SSE stream is parsed with a mirror of the browser-side parser in
``apps/web/lib/sse.ts``, so a change to the framing fails a Python test rather than
silently breaking the UI. That framing has bitten this project before: sse-starlette
separates events with CRLF-CRLF, which holds no ``\\n\\n`` to split on.
"""

from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from tests.conftest import StubStore


def parse_sse_like_the_browser(raw: str) -> list[tuple[str, dict]]:
    """Mirror of ``streamChat``/``parseFrame`` in apps/web/lib/sse.ts.

    Kept literal (normalize CRLF, split on a blank line, read ``event:``/``data:``
    lines) so it fails for the same reasons the real client would.
    """
    buffer = raw.replace("\r\n", "\n")
    events: list[tuple[str, dict]] = []
    for frame in buffer.split("\n\n"):
        if not frame.strip():
            continue
        event: str | None = None
        data_lines: list[str] = []
        for line in frame.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if event and data_lines:
            events.append((event, json.loads("\n".join(data_lines))))
    return events


def _chat(test_client: TestClient, message: str = "What are my rights if I am arrested?", **body):
    return test_client.post("/chat", json={"message": message, **body})


# ---- the SSE contract ----


def test_chat_stream_is_parseable_by_the_browser_client(chat_client: TestClient):
    resp = _chat(chat_client)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_like_the_browser(resp.text)
    assert events, "the browser-side parser recovered no events from the stream"
    names = [name for name, _ in events]
    assert names[0] == "stage", "the inspector needs stage events first"
    assert names[-1] == "done", "done must terminate the stream"
    assert {"token", "citation", "sources"} <= set(names)


def test_chat_emits_one_stage_event_per_agent_node(chat_client: TestClient):
    events = parse_sse_like_the_browser(_chat(chat_client).text)
    stages = [payload["stage"] for name, payload in events if name == "stage"]
    # rewrite is disabled in the stub settings but the node still reports itself.
    assert stages == ["rewrite", "retrieve", "grade", "rerank", "generate", "verify"]
    assert all("latency_ms" in p for n, p in events if n == "stage")


def test_stage_payloads_match_the_documented_shape(chat_client: TestClient):
    events = parse_sse_like_the_browser(_chat(chat_client).text)
    _, stage = next((n, p) for n, p in events if n == "stage")
    assert set(stage) == {"stage", "detail", "latency_ms"}


def test_grounded_answer_streams_tokens_and_a_valid_citation(chat_client: TestClient):
    events = parse_sse_like_the_browser(_chat(chat_client).text)

    answer = "".join(p["text"] for n, p in events if n == "token")
    assert "magistrate" in answer

    citations = [p for n, p in events if n == "citation"]
    assert [c["marker"] for c in citations] == [1]
    assert citations[0]["chunk_id"] == "constitution-fundamental-rights.md#10"
    assert citations[0]["section"].startswith("Article 10")

    sources = next(p for n, p in events if n == "sources")
    assert sources["retrieved"][0]["used"] is True

    done = next(p for n, p in events if n == "done")
    assert done["answer_status"] == "grounded"
    assert done["attempts"] == 1
    assert done["message_id"]


def test_every_citation_marker_points_at_a_real_source(chat_client: TestClient):
    """The anti-fabrication guarantee, on the wire."""
    events = parse_sse_like_the_browser(_chat(chat_client).text)
    markers = [p["marker"] for n, p in events if n == "citation"]
    n_sources = len(next(p for n, p in events if n == "sources")["retrieved"])
    assert all(1 <= m <= n_sources for m in markers)


def test_weak_evidence_refuses_without_inventing_citations(chat_client: TestClient):
    """Below RELEVANCE_THRESHOLD the gate refuses before the LLM is consulted."""
    chat_client.app.state.store = StubStore(score=0.31)

    events = parse_sse_like_the_browser(_chat(chat_client, "What is the capital of France?").text)
    names = [n for n, _ in events]

    assert "citation" not in names
    assert next(p for n, p in events if n == "done")["answer_status"] == "idk"
    assert "fallback" in [p["stage"] for n, p in events if n == "stage"]
    answer = "".join(p["text"] for n, p in events if n == "token")
    assert "don't know" in answer.lower()
    assert "0.31" in answer  # the refusal reports the score it saw


# ---- failure modes ----


def test_chat_returns_503_when_no_index_is_loaded(client: TestClient):
    """The `client` fixture runs lifespan against an empty data dir, so there is none."""
    resp = _chat(client)
    assert resp.status_code == 503
    assert "build_index" in resp.json()["detail"]


def test_chat_with_an_unknown_doc_id_is_404(chat_client: TestClient):
    resp = _chat(chat_client, doc_id="does-not-exist")
    assert resp.status_code == 404
    assert "upload it again" in resp.json()["detail"]


# ---- request validation ----


def test_chat_rejects_an_empty_or_oversized_message(chat_client: TestClient):
    assert _chat(chat_client, message="").status_code == 422
    # The question is interpolated into the prompt verbatim, so it must be bounded.
    assert _chat(chat_client, message="x" * 4_001).status_code == 422
    assert _chat(chat_client, message="x" * 4_000).status_code == 200


def test_chat_rejects_an_unbounded_history(chat_client: TestClient):
    turn = {"question": "q", "answer": "a"}
    assert _chat(chat_client, history=[turn] * 20).status_code == 200
    assert _chat(chat_client, history=[turn] * 21).status_code == 422


def test_chat_rejects_an_oversized_history_answer(chat_client: TestClient):
    turn = {"question": "q", "answer": "x" * 20_001}
    assert _chat(chat_client, history=[turn]).status_code == 422


# ---- /documents upload guards ----


def _blank_pdf() -> bytes:
    """A structurally valid PDF with no extractable text (stands in for a scan)."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_upload_rejects_a_non_pdf_filename(client: TestClient):
    resp = client.post("/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400
    assert "Only PDF" in resp.json()["detail"]


def test_upload_rejects_a_body_over_the_size_limit(client: TestClient):
    oversized = b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024 + 1)
    resp = client.post("/documents", files={"file": ("big.pdf", oversized, "application/pdf")})
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()


def test_upload_rejects_bytes_that_are_not_a_pdf(client: TestClient):
    resp = client.post(
        "/documents", files={"file": ("fake.pdf", b"not a pdf at all", "application/pdf")}
    )
    assert resp.status_code == 400
    assert "Could not read" in resp.json()["detail"]


def test_upload_rejects_a_pdf_with_no_extractable_text(client: TestClient):
    """An image-only scan reaches the parser fine but yields nothing to index."""
    resp = client.post(
        "/documents", files={"file": ("scan.pdf", _blank_pdf(), "application/pdf")}
    )
    assert resp.status_code == 400
    assert "extractable text" in resp.json()["detail"]


async def test_read_capped_aborts_without_buffering_the_whole_body():
    """Exercised directly: a lying Content-Length skips the fast path above."""
    from fastapi import HTTPException

    from app.routers.documents import _read_capped

    class _EndlessUpload:
        """Pretends to be an UploadFile that never runs out of bytes."""

        def __init__(self) -> None:
            self.served = 0

        async def read(self, size: int = -1) -> bytes:
            self.served += size
            return b"\0" * size

    upload = _EndlessUpload()
    try:
        await _read_capped(upload, 4 * 1024 * 1024)  # type: ignore[arg-type]
    except HTTPException as exc:
        assert exc.status_code == 413
    else:
        raise AssertionError("_read_capped never aborted on an endless body")

    # It must stop shortly past the limit, not keep draining the stream.
    assert upload.served <= 5 * 1024 * 1024


# ---- /health ----


def test_health_reports_no_index_when_none_is_loaded(client: TestClient):
    body = client.get("/health").json()
    assert body == {"status": "ok", "index_loaded": False, "chunks": 0}


def test_health_reports_the_loaded_index(chat_client: TestClient):
    body = chat_client.get("/health").json()
    assert body == {"status": "ok", "index_loaded": True, "chunks": 1}
