"""Convert official Pakistani legal PDFs into structured markdown for ingestion.

Legal statutes have a natural citable unit: the numbered Article (Constitution)
or Section (Acts). This converter extracts the PDF text, cleans the repeating
page headers and mojibake, drops the table-of-contents, and emits one markdown
file per act where each provision is a `##` heading (e.g. "## Article 9. Security
of person"). The existing MarkdownHeaderTextSplitter then produces chunks whose
`section` label is the exact provision — which is what makes legal citations
precise and verifiable.

This is a source-prep step, run once when adding an act:

    python -m app.ingestion.legal_pdf

It reads PDFs listed in SOURCES from the raw dir and writes to the corpus dir.
It intentionally does NOT invent any legal text — it only transforms text
extracted verbatim from the official PDF.

Heuristics for Pakistani legal drafting:
- A section's title ends with ".—" (period + dash) before the substantive text,
  so we split the heading line there to get a clean title + inline body.
- The table-of-contents lists every provision number before the body repeats
  them; we keep the LAST occurrence of each number (the real body), which drops
  the TOC and the stray preamble text that attaches to the last TOC entry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from app.core.config import REPO_ROOT

RAW_DIR = REPO_ROOT / "data" / "raw"
CORPUS_DIR = REPO_ROOT / "data" / "corpus"

# A heading line: an optional amendment footnote marker ("1["), then a provision
# number ("9", "9A", "2B"), then the rest of the line.
_HEADING_RE = re.compile(r"^(?:\d+\[)?(\d+[A-Z]{0,3})\.\s+(\S.*)$")
# In Pakistani drafting a section's title ends with a dash before the body text.
# The dash is extracted variably: em/en/two-em dash, or 2+ hyphens/underscores.
_TITLE_SPLIT_RE = re.compile(r"\.\s*(?:[—–⸺]|[-_]{2,})\s*")
_PAGE_HEADER_RE = re.compile(r"^\s*Page \d+ of \d+\s*$")
_PART_RE = re.compile(r"^(PART\b.*|CHAPTER\b.*)$")
# Provisions with less body than this are treated as table-of-contents noise.
_MIN_BODY_CHARS = 180
# A line is only a real heading if it splits into a short title via ".—".
_MAX_TITLE_CHARS = 90
# Reject absurd provision numbers (footnote/date artifacts, e.g. "40164.").
# 999 covers the big codes (PPC to 511, CrPC to 565) while still rejecting
# 4+ digit page/footnote artifacts.
_MAX_PROVISION_NUM = 999


@dataclass
class Source:
    pdf: str  # filename under data/raw
    out: str  # output markdown filename under data/corpus
    title: str  # act title (H1)
    unit: str  # "Article" | "Section"
    source_url: str


# NOTE: The Constitution's Fundamental Rights chapter is NOT auto-converted here.
# Full-Constitution auto-parsing is unreliable (amendment footnotes + Schedules
# with colliding numbering), and citation accuracy is critical for a legal tool,
# so Articles 8-28 are hand-verified in data/corpus/constitution-fundamental-rights.md.
# This converter handles single statutes, where per-section parsing is reliable.
SOURCES: list[Source] = [
    Source(
        pdf="peca-2016.pdf",
        out="peca-2016.md",
        title="The Prevention of Electronic Crimes Act, 2016 (PECA)",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
    Source(
        pdf="punjab-rented-premises-2009.pdf",
        out="punjab-rented-premises-act-2009.md",
        title="The Punjab Rented Premises Act, 2009",
        unit="Section",
        source_url="https://punjabcode.punjab.gov.pk/",
    ),
    Source(
        pdf="punjab-consumer-protection-2005.pdf",
        out="punjab-consumer-protection-act-2005.md",
        title="The Punjab Consumer Protection Act, 2005",
        unit="Section",
        source_url="https://punjablaws.punjab.gov.pk/",
    ),
    Source(
        pdf="standing-orders-1968.pdf",
        out="standing-orders-ordinance-1968.md",
        title="The Industrial and Commercial Employment (Standing Orders) Ordinance, 1968",
        unit="Section",
        source_url="https://punjabcode.punjab.gov.pk/",
    ),
    Source(
        pdf="muslim-family-laws-1961.pdf",
        out="muslim-family-laws-ordinance-1961.md",
        title="The Muslim Family Laws Ordinance, 1961",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
    Source(
        pdf="harassment-women-workplace-2010.pdf",
        out="harassment-of-women-workplace-act-2010.md",
        title="The Protection against Harassment of Women at the Workplace Act, 2010",
        unit="Section",
        source_url="https://kpcode.kp.gov.pk/",
    ),
    Source(
        pdf="rti-2017.pdf",
        out="right-of-access-to-information-act-2017.md",
        title="The Right of Access to Information Act, 2017",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
    Source(
        pdf="ppc-1860.pdf",
        out="pakistan-penal-code-1860.md",
        title="The Pakistan Penal Code, 1860 (PPC)",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
    Source(
        pdf="crpc-1898.pdf",
        out="code-of-criminal-procedure-1898.md",
        title="The Code of Criminal Procedure, 1898 (CrPC)",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
    Source(
        pdf="dissolution-muslim-marriages-1939.pdf",
        out="dissolution-of-muslim-marriages-act-1939.md",
        title="The Dissolution of Muslim Marriages Act, 1939",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
    Source(
        pdf="dowry-bridal-gifts-1976.pdf",
        out="dowry-and-bridal-gifts-act-1976.md",
        title="The Dowry and Bridal Gifts (Restriction) Act, 1976",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
    Source(
        pdf="contract-act-1872.pdf",
        out="contract-act-1872.md",
        title="The Contract Act, 1872",
        unit="Section",
        source_url="https://pakistancode.gov.pk/",
    ),
]


@dataclass
class Provision:
    number: str
    title: str
    context: str
    body_lines: list[str] = field(default_factory=list)

    @property
    def body(self) -> str:
        return "\n".join(self.body_lines).strip()


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _clean(text: str) -> str:
    text = text.replace("�", "-")  # mojibake for dashes: on-line, Real-time
    text = text.replace("\x0c", "\n")  # form feeds
    lines = [ln.rstrip() for ln in text.splitlines() if not _PAGE_HEADER_RE.match(ln)]
    return "\n".join(lines)


# Appended Schedules restart their own numbering (e.g. the Legislative Lists),
# which would collide with real Article/Section numbers. Truncate before them.
# Real headings look like "1[FIRST SCHEDULE" or "FOURTH SCHEDULE" (no "THE").
_SCHEDULE_RE = re.compile(
    r"^\s*\d*\s*\[?\s*(?:THE\s+)?"
    r"(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH)\s+SCHEDULE",
    re.MULTILINE,
)


def _truncate_before_schedules(text: str) -> str:
    """Drop appended Schedules, skipping the table-of-contents copy near the top."""
    floor = len(text) // 3  # TOC lives in the first third; the real schedules follow.
    match = _SCHEDULE_RE.search(text, floor)
    return text[: match.start()] if match else text


def _parse_heading(rest: str) -> tuple[str, str] | None:
    """Split a heading line's remainder into (title, inline_body).

    Returns None if it doesn't look like a real provision heading.
    """
    m = _TITLE_SPLIT_RE.search(rest)
    if m:
        title = rest[: m.start()].strip()
        inline = rest[m.end() :].strip()
        if 0 < len(title) <= _MAX_TITLE_CHARS:
            return title, inline
        return None
    # No ".—" delimiter: only accept if the whole remainder is a short title.
    if len(rest) <= _MAX_TITLE_CHARS:
        return rest.strip(), ""
    return None


def _split_provisions(text: str) -> list[Provision]:
    provisions: list[Provision] = []
    context = ""
    current: Provision | None = None

    for line in text.splitlines():
        stripped = line.strip()
        part = _PART_RE.match(stripped)
        if part:
            context = part.group(1).strip()
            continue
        heading = _HEADING_RE.match(stripped)
        if heading:
            digits = "".join(ch for ch in heading.group(1) if ch.isdigit())
            if int(digits) > _MAX_PROVISION_NUM:
                heading = None  # footnote/date artifact, not a real provision number
        parsed = _parse_heading(heading.group(2)) if heading else None
        if heading and parsed:
            title, inline = parsed
            current = Provision(number=heading.group(1), title=title, context=context)
            if inline:
                current.body_lines.append(inline)
            provisions.append(current)
        elif current is not None:
            current.body_lines.append(line)
    return provisions


def _dedupe_keep_last(provisions: list[Provision]) -> list[Provision]:
    """Keep the last occurrence of each provision number (the body, not the TOC)."""
    last_index: dict[str, int] = {}
    for i, p in enumerate(provisions):
        last_index[p.number] = i
    return [p for i, p in enumerate(provisions) if last_index[p.number] == i]


def _to_markdown(source: Source, provisions: list[Provision]) -> tuple[str, int]:
    out = [f"# {source.title}", ""]
    kept = 0
    for p in provisions:
        if len(p.body) < _MIN_BODY_CHARS:  # drop TOC/stub entries
            continue
        crumb = f" ({p.context})" if p.context else ""
        out.append(f"## {source.unit} {p.number}. {p.title}{crumb}")
        out.append("")
        out.append(p.body)
        out.append("")
        kept += 1
    return "\n".join(out), kept


def convert(source: Source) -> int:
    text = _truncate_before_schedules(_clean(_extract_text(RAW_DIR / source.pdf)))
    provisions = _dedupe_keep_last(_split_provisions(text))
    markdown, kept = _to_markdown(source, provisions)
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    (CORPUS_DIR / source.out).write_text(markdown, encoding="utf-8")
    return kept


def main() -> None:
    for source in SOURCES:
        if not (RAW_DIR / source.pdf).exists():
            print(f"SKIP {source.pdf} (not found in {RAW_DIR})")
            continue
        print(f"{source.pdf} -> {source.out}: {convert(source)} provision(s)")


if __name__ == "__main__":
    main()
