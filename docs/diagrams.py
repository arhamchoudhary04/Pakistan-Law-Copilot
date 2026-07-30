"""Generate the README diagrams as SVG.

Run: python docs/diagrams.py

Boxes are sized from their text rather than the other way round, so a label can
never overflow its box. The layout is then checked for overlaps and for anything
escaping the viewBox before a file is written.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

OUT = Path(__file__).parent

# A deep neutral slate, so saturated hues stay vivid on top of it. The app's own
# palette is warm brass, which is right for reading long legal prose and wrong for
# a diagram: every category would come out the same colour.
CANVAS = "#0E1117"
SURFACE = "#151A22"
CARD = "#1C222C"
ELEVATED = "#232B37"
LINE = "#2A3140"
LINE_STRONG = "#3B475A"
INK = "#E9EEF5"
MUTED = "#9AA6B8"
FAINT = "#6E7A8C"

# One hue per concern, so colour carries meaning rather than decoration.
CYAN = "#22D3EE"      # client / browser
AMBER = "#FBBF24"     # API layer
VIOLET = "#A78BFA"    # agent / orchestration
EMERALD = "#34D399"   # retrieval and models
PINK = "#F472B6"      # data stores
SKY = "#60A5FA"       # ingestion, build time
ORANGE = "#FB923C"    # the one external service
LIME = "#A3E635"      # quality and CI
GREEN = "#4ADE80"     # answer released
ROSE = "#FB7185"      # refused

ACCENT = AMBER
ACCENT_HI = "#FCD34D"
GROUNDED = GREEN
IDK = ROSE


SANS = "ui-sans-serif,-apple-system,Segoe UI,Inter,Helvetica,Arial,sans-serif"
SERIF = "Georgia,Cambria,serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# Conservative average glyph width as a fraction of font size. Overestimating is
# the safe direction: it only ever makes a box wider than it strictly needs.
_W_REG = 0.55
_W_BOLD = 0.60
_W_MONO = 0.62


def text_w(s: str, size: float, weight: str = "regular") -> float:
    f = {"regular": _W_REG, "bold": _W_BOLD, "mono": _W_MONO}[weight]
    return len(s) * size * f


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    label: str = ""

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def overlaps(self, o: Box, pad: float = 0.0) -> bool:
        return not (
            self.right + pad <= o.x
            or o.right + pad <= self.x
            or self.bottom + pad <= o.y
            or o.bottom + pad <= self.y
        )


@dataclass
class Canvas:
    w: float
    h: float
    parts: list[str] = field(default_factory=list)
    boxes: list[Box] = field(default_factory=list)

    def add(self, s: str) -> None:
        self.parts.append(s)

    def track(self, b: Box) -> Box:
        self.boxes.append(b)
        return b

    # ---- primitives ----

    def rect(self, b: Box, fill: str, stroke: str = "", r: float = 10, sw: float = 1,
             fill_op: float = 1.0, stroke_op: float = 1.0) -> None:
        # Opacity goes in its own attribute: an #RRGGBBAA fill is CSS Color 4, and a
        # renderer that doesn't implement it paints the colour solid instead.
        st = (
            f' stroke="{stroke}" stroke-width="{sw}" stroke-opacity="{stroke_op}"'
            if stroke else ""
        )
        self.add(
            f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" rx="{r}" '
            f'fill="{fill}" fill-opacity="{fill_op}"{st}/>'
        )

    def text(
        self,
        x: float,
        y: float,
        s: str,
        size: float = 13,
        fill: str = INK,
        weight: str = "400",
        anchor: str = "start",
        family: str = SANS,
        spacing: str = "0",
    ) -> None:
        self.add(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'letter-spacing="{spacing}">{esc(s)}</text>'
        )

    def head(self, x: float, y: float, facing: str, fill: str, s: float = 5.0) -> None:
        """An arrowhead drawn as a real polygon.

        Markers would be less code, but they are the one SVG feature renderers
        disagree about, and a diagram with no arrowheads reads as a wiring diagram.
        """
        pts = {
            "right": f"{x},{y} {x - s * 1.6},{y - s} {x - s * 1.6},{y + s}",
            "left": f"{x},{y} {x + s * 1.6},{y - s} {x + s * 1.6},{y + s}",
            "down": f"{x},{y} {x - s},{y - s * 1.6} {x + s},{y - s * 1.6}",
            "up": f"{x},{y} {x - s},{y + s * 1.6} {x + s},{y + s * 1.6}",
        }[facing]
        self.add(f'<polygon points="{pts}" fill="{fill}"/>')

    def path(self, d: str, stroke: str, sw: float = 1.5, dash: str = "") -> None:
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" fill="none" '
            f'stroke-linejoin="round" stroke-linecap="round"{ds}/>'
        )

    def connect(self, a: Box, b: Box, stroke: str, sw: float = 1.6,
                dash: str = "", gap: float = 7) -> None:
        """Route a to b with right angles only. Diagonals across a panel look wrong."""
        if abs(a.cy - b.cy) < 2 and b.x > a.right:  # same row, left to right
            self.path(f"M {a.right} {a.cy} H {b.x - gap}", stroke, sw, dash)
            self.head(b.x - 1, b.cy, "right", stroke)
        elif abs(a.cx - b.cx) < 2 and b.y > a.bottom:  # stacked, downwards
            self.path(f"M {a.cx} {a.bottom} V {b.y - gap}", stroke, sw, dash)
            self.head(b.cx, b.y - 1, "down", stroke)
        elif b.x > a.right:  # different rows: out, across, in
            mid = (a.right + b.x) / 2
            self.path(f"M {a.right} {a.cy} H {mid} V {b.cy} H {b.x - gap}", stroke, sw, dash)
            self.head(b.x - 1, b.cy, "right", stroke)
        else:  # b below and offset: down, across, down
            mid = (a.bottom + b.y) / 2
            self.path(f"M {a.cx} {a.bottom} V {mid} H {b.cx} V {b.y - gap}", stroke, sw, dash)
            self.head(b.cx, b.y - 1, "down", stroke)

    def render(self, title: str) -> str:
        body = "\n".join(self.parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
            f'width="{self.w}" height="{self.h}" role="img" aria-label="{esc(title)}">\n'
            f'<rect width="{self.w}" height="{self.h}" rx="14" fill="{CANVAS}"/>\n'
            f"{body}\n</svg>\n"
        )


# ---------------------------------------------------------------- shared pieces


def panel(c: Canvas, b: Box, title: str, hue: str = "") -> None:
    """A titled group container, tinted by the hue of whatever it holds."""
    c.rect(b, SURFACE, hue or LINE, r=12, stroke_op=0.30 if hue else 1.0)
    if hue:
        c.add(f'<rect x="{b.x}" y="{b.y}" width="4" height="{b.h}" rx="2" '
              f'fill="{hue}" fill-opacity="0.85"/>')
    c.text(b.x + (18 if hue else 16), b.y + 24, title.upper(), size=10.5,
           fill=hue or FAINT, weight="700", spacing="1.4")


def node(
    c: Canvas,
    x: float,
    y: float,
    title: str,
    sub: str = "",
    *,
    hue: str = "",
    min_w: float = 0,
    pad: float = 18,
    title_size: float = 13.5,
    sub_size: float = 10.5,
) -> Box:
    """A card sized to its own text, so nothing can overflow."""
    w = max(text_w(title, title_size, "bold"), text_w(sub, sub_size)) + pad * 2
    w = max(w, min_w)
    h = 52 if sub else 38
    b = c.track(Box(x, y, w, h, title))
    c.rect(b, CARD, hue or LINE, r=9, sw=1.4 if hue else 1,
           stroke_op=0.55 if hue else 1.0)
    if hue:
        c.rect(b, hue, "", r=9, fill_op=0.10)
    ty = b.y + (21 if sub else 24)
    c.text(b.cx, ty, title, size=title_size, weight="600", fill=hue or INK, anchor="middle")
    if sub:
        c.text(b.cx, b.y + 38, sub, size=sub_size, fill=MUTED, anchor="middle")
    return b


def pill(c: Canvas, x: float, y: float, label: str, ver: str = "", *,
         hue: str = "", key: bool = False) -> Box:
    """A tech chip: name plus an optional version, sized to content."""
    fs, vs = 12.5, 10.5
    w = text_w(label, fs, "bold") + (text_w(ver, vs, "mono") + 9 if ver else 0) + 26
    b = c.track(Box(x, y, w, 30, label))
    c.rect(b, ELEVATED if key else CARD, hue, r=15, sw=1.4 if key else 1,
           stroke_op=0.65 if key else 0.28)
    if key:
        c.rect(b, hue, "", r=15, fill_op=0.14)
    c.text(b.x + 13, b.y + 19.5, label, size=fs, weight="600", fill=hue if key else INK)
    if ver:
        c.text(b.right - 13, b.y + 19, ver, size=vs, fill=FAINT, anchor="end", family=MONO)
    return b


def heading(c: Canvas, x: float, y: float, title: str, sub: str) -> None:
    c.text(x, y, title, size=19, weight="600", fill=INK, family=SERIF)
    c.text(x, y + 20, sub, size=12, fill=FAINT)


def legend(c: Canvas, x: float, y: float, items: list[tuple[str, str]]) -> None:
    cx = x
    for colour, label in items:
        c.add(f'<circle cx="{cx + 5}" cy="{y - 4}" r="4.5" fill="{colour}"/>')
        c.text(cx + 16, y, label, size=11, fill=MUTED)
        cx += text_w(label, 11) + 42


# ---------------------------------------------------------------- architecture


def architecture() -> str:
    c = Canvas(1180, 684)
    heading(c, 34, 44, "System architecture",
            "Everything except the Groq call runs locally, offline and free.")

    # --- top band: the request path, left to right
    p1 = c.track(Box(34, 84, 268, 244))
    panel(c, p1, "Client", CYAN)
    ui = node(c, 54, 122, "Next.js UI", "App Router, TypeScript", min_w=228, hue=CYAN)
    node(c, 54, 192, "SSE over fetch", "EventSource is GET only", min_w=228, hue=CYAN)
    node(c, 54, 262, "Tailwind", "design tokens", min_w=228, hue=CYAN)

    p2 = c.track(Box(322, 84, 306, 244))
    panel(c, p2, "API", AMBER)
    rl = node(c, 342, 122, "Rate limit", "sliding window, per endpoint",
              min_w=266, hue=AMBER)
    api = node(c, 342, 192, "FastAPI", "Pydantic v2, typed boundaries", min_w=266, hue=AMBER)
    db = node(c, 342, 262, "SQLite", "accounts and chat history", min_w=266, hue=PINK)

    p3 = c.track(Box(648, 84, 498, 244))
    panel(c, p3, "Agent", VIOLET)
    ag = node(c, 668, 192, "LangGraph", "state machine", min_w=214, hue=VIOLET)
    vf = node(c, 912, 192, "verify loop", "retry on unsupported claims", min_w=214, hue=VIOLET)
    c.text(668, 145, "rewrite -> retrieve -> grade -> rerank -> generate -> verify",
           size=10.5, fill=VIOLET, family=MONO)

    # --- middle band: what the agent calls out to
    p4 = c.track(Box(34, 356, 1112, 132))
    panel(c, p4, "Models and stores", EMERALD)
    svc = []
    for i, (t, s, acc) in enumerate([
        ("fastembed", "bge-small, ONNX", EMERALD),
        ("FAISS", "1,872 chunks", PINK),
        ("cross-encoder", "MiniLM, ONNX", EMERALD),
        ("Neo4j", "provision graph", PINK),
        ("Groq", "llama-3.1-8b", ORANGE),
    ]):
        svc.append(node(c, 54 + i * 220, 400, t, s, min_w=190, hue=acc))

    # --- bottom band: build time only
    p5 = c.track(Box(34, 508, 1112, 132))
    panel(c, p5, "Ingestion, offline", SKY)
    ing = []
    for i, (t, s) in enumerate([
        ("Official PDFs", "pakistancode.gov.pk"),
        ("pypdf", "to structured markdown"),
        ("chunker", "one provision per chunk"),
        ("embed and index", "writes the FAISS store"),
    ]):
        ing.append(node(c, 54 + i * 275, 552, t, s, min_w=245, hue=SKY))

    # --- connectors
    c.connect(ui, rl, CYAN, 1.9)
    c.connect(rl, api, AMBER, 1.9)
    c.connect(api, ag, AMBER, 1.9)
    c.connect(api, db, PINK, 1.6)
    c.connect(ag, vf, VIOLET, 1.7)

    # a bus from the agent down to every model and store
    bus_y = 344
    c.path(f"M {ag.cx} {ag.bottom} V {bus_y}", VIOLET, 1.7)
    c.path(f"M {svc[0].cx} {bus_y} H {svc[-1].cx}", VIOLET, 1.7)
    for s in svc:
        c.path(f"M {s.cx} {bus_y} V {s.y - 7}", VIOLET, 1.7)
        c.head(s.cx, s.y - 1, "down", VIOLET)

    for a, b in zip(ing, ing[1:], strict=False):
        c.connect(a, b, SKY, 1.6, dash="5 4")
    # the index built here is the one the agent reads at query time
    c.path(f"M {ing[-1].cx} {ing[-1].y} V {svc[1].bottom + 26} H {svc[1].cx} "
           f"V {svc[1].bottom + 7}", SKY, 1.6, dash="5 4")
    c.head(svc[1].cx, svc[1].bottom + 1, "up", SKY)

    legend(c, 34, 662, [(CYAN, "client"), (AMBER, "API"), (VIOLET, "agent"),
                        (EMERALD, "models"), (PINK, "data stores"),
                        (SKY, "build time only")])
    _check(c, exclude_panels=[p1, p2, p3, p4, p5])
    return c.render("System architecture")


# ---------------------------------------------------------------- agent flow


def gate(c: Canvas, x: float, y: float, title: str, test: str, hue: str = AMBER,
         w: float = 176) -> Box:
    """A decision node: brass-edged, with the actual test in mono underneath."""
    b = c.track(Box(x, y, w, 64, title))
    c.rect(b, ELEVATED, hue, r=9, sw=1.8, stroke_op=0.8)
    c.rect(b, hue, "", r=9, fill_op=0.14)
    c.text(b.cx, b.y + 26, title, size=13.5, weight="700", fill=hue, anchor="middle")
    c.text(b.cx, b.y + 45, test, size=10.5, fill=MUTED, anchor="middle", family=MONO)
    return b


def outcome(c: Canvas, x: float, y: float, title: str, sub: str, colour: str,
            w: float = 218) -> Box:
    b = c.track(Box(x, y, w, 64, title))
    c.rect(b, CARD, colour, r=9, sw=1.6, stroke_op=0.7)
    c.rect(b, colour, "", r=9, fill_op=0.11)
    c.text(b.cx, b.y + 26, title, size=13.5, weight="700", fill=colour, anchor="middle")
    c.text(b.cx, b.y + 45, sub, size=10, fill=MUTED, anchor="middle")
    return b


def agent_flow() -> str:
    c = Canvas(1180, 474)
    heading(c, 34, 44, "The agent",
            "A state machine, because the verification loop needs conditional edges.")

    y = 128
    q = node(c, 34, y, "question", "EN / UR / Roman", min_w=150, hue=CYAN)
    rw = node(c, 222, y, "rewrite", "to English queries", min_w=166, hue=VIOLET)
    rt = node(c, 426, y, "retrieve", "vector + graph", min_w=158, hue=EMERALD)
    g = gate(c, 622, y - 6, "grade", "cosine >= 0.65 ?")
    rr = node(c, 836, y, "rerank", "cross-encoder", min_w=150, hue=EMERALD)
    gen = node(c, 1002, y, "generate", "[n] markers", min_w=122, hue=ORANGE)

    v = gate(c, 878, 246, "verify", "every marker real ?", w=246)
    fb = outcome(c, 590, 246, "fallback", "I don't know, plus the score", IDK, w=250)
    out = outcome(c, 34, 352, "stream to client", "tokens and citations", GROUNDED, w=250)

    # main path
    hues = (CYAN, VIOLET, EMERALD, AMBER, EMERALD)
    for (a, b), hue in zip(((q, rw), (rw, rt), (rt, g), (g, rr), (rr, gen)), hues, strict=True):
        c.connect(a, b, hue, 1.9)
    c.text((g.right + rr.x) / 2, g.cy - 13, "pass", size=10, fill=AMBER, anchor="middle")

    c.connect(g, fb, ROSE, 1.7)
    c.text(g.cx + 9, g.bottom + 34, "below threshold", size=10, fill=IDK)
    c.connect(gen, v, ORANGE, 1.7)

    # retry, routed above the main row so it never crosses the output edges
    top = 96
    c.path(f"M {v.right} {v.cy} H {c.w - 22} V {top} H {rw.cx} V {rw.y - 7}", AMBER, 1.6,
           dash="5 4")
    c.head(rw.cx, rw.y - 1, "down", AMBER)
    c.text(rw.cx + 12, top - 7, "unsupported claim, retry with feedback", size=10, fill=AMBER)

    # both outcomes converge on the stream
    for src in (fb, v):
        c.path(f"M {src.cx} {src.bottom} V {out.cy} H {out.right + 7}", GROUNDED, 1.6)
    c.head(out.right + 1, out.cy, "left", GROUNDED)

    legend(c, 34, 452, [(VIOLET, "agent step"), (EMERALD, "retrieval"),
                        (AMBER, "decision"), (GREEN, "answer released"),
                        (ROSE, "refused, no citations")])
    _check(c, exclude_panels=[])
    return c.render("The agent state machine")


# ---------------------------------------------------------------- validation


def _check(c: Canvas, exclude_panels: list[Box]) -> None:
    """Fail loudly rather than emit a diagram that renders wrong."""
    ids = {id(b) for b in exclude_panels}
    inner = [b for b in c.boxes if id(b) not in ids]
    for b in c.boxes:
        assert b.x >= 0 and b.y >= 0, f"{b.label!r} starts outside the viewBox"
        assert b.right <= c.w + 0.5, f"{b.label!r} overflows width ({b.right} > {c.w})"
        assert b.bottom <= c.h + 0.5, f"{b.label!r} overflows height ({b.bottom} > {c.h})"
    for i, a in enumerate(inner):
        for b in inner[i + 1 :]:
            assert not a.overlaps(b, pad=-0.5), f"{a.label!r} overlaps {b.label!r}"


def main() -> None:
    for name, svg in (
        ("architecture.svg", architecture()),
        ("agent-flow.svg", agent_flow()),
    ):
        ET.fromstring(svg)  # well-formed or bust
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"  wrote docs/{name}  ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
