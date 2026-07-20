from app.ingestion.chunker import approx_tokens, chunk_documents
from app.ingestion.loader import Document


def test_chunker_produces_sectioned_chunks():
    doc = Document(
        doc_id="sample.md",
        title="Sample",
        source="sample.md",
        text=(
            "# Sample\n\nIntro text.\n\n"
            "## Section A\n\nContent about A that is reasonably long.\n\n"
            "## Section B\n\nContent about B.\n"
        ),
    )
    chunks = chunk_documents([doc], chunk_tokens=600, chunk_overlap=80)

    assert chunks, "expected at least one chunk"
    assert all(c.doc_id == "sample.md" for c in chunks)
    # Ordinals are unique and contiguous within the document.
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    # Header hierarchy is captured in the section label.
    sections = " ".join(c.section for c in chunks)
    assert "Section A" in sections and "Section B" in sections


def test_approx_tokens_is_positive():
    assert approx_tokens("") == 1
    assert approx_tokens("a" * 40) == 10
