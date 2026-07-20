"""Parser tests for legal_pdf.py.

Feeds synthetic statute text through the same functions ``convert()`` chains
(clean -> split -> dedupe -> markdown), no PDF needed. Locks in the tricky cases:
short-but-real provisions survive, TOC stubs drop, TOC duplicates yield to the body,
and footnote/artifact lines aren't mistaken for headings.
"""

from app.ingestion.legal_pdf import (
    Source,
    _clean,
    _dedupe_keep_last,
    _parse_heading,
    _split_provisions,
    _to_markdown,
)

_SOURCE = Source(
    pdf="test.pdf", out="test.md", title="The Test Act, 1900", unit="Section",
    source_url="https://example.test/",
)


def _to_md(text: str) -> str:
    """Run the parsing pipeline the way convert() does, minus PDF extraction."""
    provisions = _dedupe_keep_last(_split_provisions(_clean(text)))
    markdown, _ = _to_markdown(_SOURCE, provisions)
    return markdown


# ---- _clean ----


def test_clean_drops_page_headers_and_fixes_mojibake():
    # U+FFFD (the replacement char) is how the PDF extractor renders dashes.
    cleaned = _clean("Page 1 of 12\nReal�time protection applies.\nPage 2 of 12")
    assert "Page 1 of 12" not in cleaned
    assert "Page 2 of 12" not in cleaned
    assert "Real-time protection applies." in cleaned  # mojibake -> dash


# ---- _parse_heading ----


def test_parse_heading_splits_title_from_body_on_dash():
    assert _parse_heading("Security of person.— No person shall be deprived of life.") == (
        "Security of person",
        "No person shall be deprived of life.",
    )


def test_parse_heading_accepts_various_dash_variants():
    # em (U+2014), en (U+2013), horizontal bar (U+2015, e.g. Family Courts Act), 2+ hyphens
    for dash in ["—", "–", "―", "--"]:
        title, body = _parse_heading(f"Title.{dash} Body text here.")  # type: ignore[misc]
        assert title == "Title"
        assert body == "Body text here."


def test_parse_heading_rejects_amendment_footnote():
    assert _parse_heading("ins. by the Criminal Law (Amdt.) Act, 1926, s. 2.") is None


def test_parse_heading_rejects_long_untitled_line():
    long_line = "This is a long paragraph of body text with no title delimiter " * 3
    assert _parse_heading(long_line) is None


# ---- full pipeline ----

# A synthetic statute: a table-of-contents block (bare titles, no body) followed
# by the real body. Mirrors the real PDFs the parser was built against.
_STATUTE = """PART I
1. Short title and commencement.
2. Theft defined.
3. Punishment for theft.
PART I
1. Short title and commencement.— This Act may be called the Test Act, 1900.
2. Theft defined.— Whoever, intending to take dishonestly any movable property \
out of the possession of any person without that person's consent, moves that \
property, is said to commit theft.
3. Punishment for theft.— Imprisonment which may extend to three years, or with \
fine, or with both.
4A. ins. by the Amending Act, 1926, s. 2.
40164. Artifact heading.— A page/footnote artifact with an absurd provision number.
"""


def test_short_but_real_provision_survives():
    # Section 3's body (~70 chars) is short but a real punishment clause. The
    # regression this guards against dropped it as "table-of-contents noise".
    md = _to_md(_STATUTE)
    assert "## Section 3. Punishment for theft" in md
    assert "may extend to three years" in md


def test_toc_stub_is_dropped_but_duplicate_body_kept():
    md = _to_md(_STATUTE)
    # Only ONE heading per real section (the body copy), not the TOC copy too.
    assert md.count("## Section 2. Theft defined") == 1
    assert "intending to take dishonestly" in md  # the real body, not the TOC stub


def test_footnote_line_is_not_a_provision():
    md = _to_md(_STATUTE)
    assert "## Section 4A" not in md


def test_absurd_provision_number_rejected():
    # The >999 guard means no bogus provision *heading* is created for the artifact
    # (its stray text may still attach to the previous section's body — that's fine).
    md = _to_md(_STATUTE)
    assert "## Section 40164" not in md


def test_part_context_is_attached_as_breadcrumb():
    md = _to_md(_STATUTE)
    assert "(PART I)" in md
