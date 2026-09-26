#!/usr/bin/env python3
"""Generate the SVG assets for the ezat141 GitHub profile README.

Every file here ends up inside an <img> on github.com, which decides most of the
choices below:

  * GitHub serves repo SVGs with `Content-Security-Policy: default-src 'none'`, so an
    SVG cannot load a web font, a script, or even a data: image. Display text is
    therefore converted to outlines (Sora, SIL OFL 1.1) so it looks identical on every
    OS, and logos are inlined as paths.
  * Long body copy stays as <text> in a system font stack — outlining it would make
    each card several times larger. Because the fallback font is unknown, it is
    wrapped against Sora's metrics plus a safety margin; Sora runs wide, so the
    real text always fits.
  * Images start animating when the page loads, not when they scroll into view.
    Only the hero, which is above the fold, uses a one-shot entrance. Everything
    further down uses slow ambient loops, because an entrance would already be over.
  * Motion is CSS wherever possible so `prefers-reduced-motion` can switch it off.
    SMIL is used only for movement along a path; those elements carry the `motion`
    class so the same media query hides them.
  * The resting (un-animated) state of every element is its final state. Animations
    start from hidden using `backwards` fill, so with motion disabled nothing is lost.
  * An element with a `transform` attribute is never given a CSS transform animation:
    the CSS value would replace the attribute and the element would jump.

Usage:
    pip install -r scripts/requirements.txt
    python scripts/generate_assets.py           # writes ./assets
"""
from __future__ import annotations

import io
import pathlib
import re
import sys
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent / "assets"

# ── palette ──────────────────────────────────────────────────────────────────
BG0 = "#0A0F1F"     # hero ground
BG1 = "#0E1628"     # panels and cards
BG2 = "#141E36"     # tiles and chips
LINE = "#223052"    # borders, grid, edges
EDGE = "#2A3A62"
CYAN = "#22D3EE"    # primary accent: requests, links, activity
VIOLET = "#A78BFA"  # security: identity, tokens, keys
TEXT = "#E6EDF7"
MUTED = "#9AA8BF"
DIM = "#5F6D8A"

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

BASE_CSS = (
    "@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}}"
    "@keyframes fadeIn{from{opacity:0}}"
    "@keyframes blink{50%{opacity:0}}"
    "@keyframes pulse{from{transform:scale(1);opacity:.75}to{transform:scale(2.2);opacity:0}}"
    ".ring{transform-box:fill-box;transform-origin:center;animation:pulse 2.8s ease-out infinite}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}.motion{display:none}}"
)


def n(v: float, places: int = 1) -> str:
    s = f"{v:.{places}f}"
    if "." in s:  # only trim a fractional part: "280".rstrip("0") would give "28"
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ── type: shaping with HarfBuzz, outlines with fontTools ─────────────────────
class Face:
    def __init__(self, data: bytes):
        self.hbfont = hb.Font(hb.Face(hb.Blob(data)))
        self.tt = TTFont(io.BytesIO(data))
        self.upem = self.tt["head"].unitsPerEm
        self.glyphset = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()

    def _shape(self, text: str, size: float, tracking: float):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf, {"kern": True, "liga": True})
        k = size / self.upem
        x, out = 0.0, []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            if info.codepoint == 0:
                raise ValueError(f"Sora has no glyph for a character in {text!r}")
            out.append((self.order[info.codepoint], x + pos.x_offset * k, pos.y_offset * k))
            x += pos.x_advance * k + tracking
        return out, (x - tracking if out else 0.0), k

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        return self._shape(text, size, tracking)[1]


_faces: dict[int, Face] = {}


def face(weight: int) -> Face:
    if weight not in _faces:
        variable = TTFont(HERE / "fonts" / "Sora.ttf")
        static = instancer.instantiateVariableFont(variable, {"wght": weight})
        buf = io.BytesIO()
        static.save(buf)
        _faces[weight] = Face(buf.getvalue())
    return _faces[weight]


class Glyphs:
    """Outlined text with each glyph defined once per document and placed with <use>.

    Outlining every label in full made the tech-stack panel ~185 KB, most of it the same
    few letters redrawn. Glyphs are stored in integer font units and scaled at the point
    of use. Callers must never put a CSS transform animation on the returned <use>
    elements themselves — each carries a transform attribute that the animation would
    replace — so animated text is wrapped in a <g> instead.
    """

    def __init__(self):
        self.defs: dict[str, str] = {}

    def text(self, weight, text, size, x, y, tracking=0.0, per_glyph=False):
        f = face(weight)
        shaped, width, k = f._shape(text, size, tracking)
        uses = []
        for name, gx, gy in shaped:
            gid = f"g{weight}-" + re.sub(r"[^A-Za-z0-9_.-]", "_", name)
            if gid not in self.defs:
                pen = SVGPathPen(f.glyphset, ntos=lambda v: n(v, 0))
                f.glyphset[name].draw(pen)
                self.defs[gid] = pen.getCommands()
            if self.defs[gid]:
                uses.append(f'<use href="#{gid}" transform="translate({n(x + gx, 2)} {n(y - gy, 2)}) '
                            f'scale({n(k, 5)} {n(-k, 5)})"/>')
        return (uses if per_glyph else "".join(uses)), width

    def svg(self) -> str:
        return "".join(f'<path id="{i}" d="{d}"/>' for i, d in self.defs.items() if d)


def wrap(text: str, size: float, max_width: float, safety: float = 1.06) -> list[str]:
    measure = face(400)
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if measure.width(trial, size) * safety <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


# ── logos ────────────────────────────────────────────────────────────────────
# Colours that disappear on navy are lifted, keeping each logo recognisable.
RECOLOR = {
    "apachekafka": {"#231f20": TEXT},
    "maven": {"#000000": TEXT, "#000": TEXT},
    "hibernate": {"#59666c": "#A9B6BC"},
    "mysql": {"#00618a": "#4AA8D8"},
}
DEFAULT_FILL = {"apachekafka": TEXT, "maven": TEXT}  # paths that rely on implicit black
# Wordmark logos: crop to the mark itself, and give them a wider slot where they appear.
VIEWBOX = {"oracle": "11 51 106 26"}
WIDE = {"oracle": 1.4}
_icon_uses = 0


def icon(name: str, x: float, y: float, size: float) -> str:
    global _icon_uses
    _icon_uses += 1
    raw = (HERE / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    inner = re.search(r"<svg[^>]*>(.*)</svg>", raw, re.S).group(1)
    inner = re.sub(r"<!--.*?-->", "", inner, flags=re.S)
    # Coordinates are deliberately NOT rounded here. devicon writes compact path syntax
    # where arc flags run into the next number ("0 0064.205" is flag, flag, 64.205), so a
    # regex that treats "0064.205" as one number deletes both flags and the browser
    # silently drops the rest of the path. Doing this safely needs a real path parser.
    ids = set(re.findall(r'\bid="([^"]+)"', inner))
    if ids:  # gradients inside one logo must not collide with another's
        prefix = f"{name}{_icon_uses}-"
        inner = re.sub(
            r'(\bid="|url\(#|href="#)([^")]+)',
            lambda m: m.group(1) + (prefix + m.group(2) if m.group(2) in ids else m.group(2)),
            inner,
        )
    for src, dst in RECOLOR.get(name, {}).items():
        inner = re.sub(re.escape(src) + r"(?![0-9a-fA-F])", dst, inner, flags=re.I)
    fill = f' fill="{DEFAULT_FILL[name]}"' if name in DEFAULT_FILL else ""
    return (f'<svg x="{n(x)}" y="{n(y)}" width="{n(size)}" height="{n(size)}" '
            f'viewBox="{VIEWBOX.get(name, "0 0 128 128")}"{fill}>{inner}</svg>')


def svg_open(w: float, h: float, title: str, desc: str = "") -> str:
    d = f'<desc id="d">{escape(desc)}</desc>' if desc else ""
    labelled = "t d" if desc else "t"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{n(w)}" height="{n(h)}" viewBox="0 0 {n(w)} {n(h)}" role="img" '
            f'aria-labelledby="{labelled}"><title id="t">{escape(title)}</title>{d}')


def write(rel: str, content: str) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {rel:<34} {len(content.encode()) / 1024:6.1f} KB")


# ── hero ─────────────────────────────────────────────────────────────────────
def typed(text, x, y, size, start, step, colors=None, cls="mono"):
    """One <text> per character on a fixed monospace grid, so the reveal and the cursor
    stay aligned whichever monospace font the viewer's OS supplies."""
    cw = size * 0.6
    out = []
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        fill = (colors or {}).get(i, MUTED)
        out.append(f'<text x="{n(x + i * cw)}" y="{n(y)}" font-size="{n(size)}" fill="{fill}" '
                   f'class="{cls} tc" style="animation-delay:{start + (i + 1) * step:.3f}s">'
                   f'{escape(ch)}</text>')
    return "".join(out), cw


def hero() -> None:
    W, H, X = 1200, 400, 64
    nodes = {
        "client": (800, 205, DIM), "gatekeeper": (920, 205, CYAN),
        "authcore": (1045, 120, VIOLET), "ledger": (1045, 290, CYAN),
        "postgres": (1150, 70, MUTED), "redis": (1150, 170, MUTED),
    }
    edges = [("client", "gatekeeper"), ("gatekeeper", "authcore"), ("gatekeeper", "ledger"),
             ("authcore", "postgres"), ("authcore", "redis")]

    whoami = "$ whoami"
    tagline = "> secure REST APIs, OAuth2 / JWT & microservices on the JVM"
    t1_start, t1_step = 0.25, 0.07
    t2_start, t2_step = 2.45, 0.032
    t2_end = t2_start + len(tagline) * t2_step

    css = BASE_CSS + (
        f".mono{{font-family:{MONO}}}.sans{{font-family:{SANS}}}"
        "@keyframes tc{from{opacity:0}}"
        ".tc{animation:tc .01s linear backwards}"
        ".lt{animation:fadeUp .6s cubic-bezier(.2,.7,.2,1) backwards}"
        ".up{animation:fadeUp .7s cubic-bezier(.2,.7,.2,1) backwards}"
        ".in{animation:fadeIn 1s ease backwards}"
        "@keyframes draw{from{stroke-dashoffset:150}}"
        ".draw{stroke-dasharray:150;animation:draw .8s ease-out 1.65s backwards}"
        "@keyframes flow{to{stroke-dashoffset:-18}}"
        ".flow{stroke-dasharray:3 6;animation:flow 1.4s linear infinite}"
        f"@keyframes mv1{{to{{transform:translateX({n(len(whoami) * 10.8)}px)}}}}"
        "@keyframes hide{to{opacity:0}}"
        f".c1{{animation:mv1 {len(whoami) * t1_step:.2f}s steps({len(whoami)},end) {t1_start}s both,"
        f"hide .01s linear {t1_start + len(whoami) * t1_step + 0.35:.2f}s forwards}}"
        f"@keyframes mv2{{to{{transform:translateX({n(len(tagline) * 10.2)}px)}}}}"
        f".c2{{animation:fadeIn .01s linear {t2_start}s backwards,"
        f"mv2 {len(tagline) * t2_step:.2f}s steps({len(tagline)},end) {t2_start}s both,"
        f"blink 1.05s step-end {t2_end:.2f}s infinite}}"
    )

    o = [svg_open(W, H, "Ezzat Mohamed — Java Backend Developer",
                  "Spring Boot, API security and distributed systems. The background shows a "
                  "request flowing through an API gateway to an authorization server and a "
                  "resource server, which verifies tokens against the authorization server's "
                  "published keys.")]
    o.append(f"<style>{css}</style>")
    o.append(
        "<defs>"
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>'
        f'<radialGradient id="gC" cx=".84" cy=".2" r=".55"><stop offset="0" stop-color="{CYAN}" stop-opacity=".15"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="gV" cx=".06" cy="1" r=".62"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
        '<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<circle cx="1.5" cy="1.5" r="1.1" fill="#1B2744"/></pattern>'
        f'<linearGradient id="accent" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}"/>'
        f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
        "__GLYPHS__</defs>"
    )
    G = Glyphs()
    o.append('<g clip-path="url(#frame)">')
    o.append(f'<rect width="{W}" height="{H}" fill="{BG0}"/>'
             f'<rect width="{W}" height="{H}" fill="url(#dots)" opacity=".6"/>'
             f'<rect width="{W}" height="{H}" fill="url(#gC)"/><rect width="{W}" height="{H}" fill="url(#gV)"/>')

    # the platform, drawn as it actually works
    for a, b in edges:
        (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
        o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{EDGE}" stroke-width="1.5"/>')
    lx, ly1, ly2 = nodes["ledger"][0], nodes["ledger"][1], nodes["authcore"][1]
    o.append(f'<path d="M{lx} {ly1} L{lx} {ly2}" stroke="{VIOLET}" stroke-opacity=".7" '
             f'stroke-width="1.5" fill="none" class="flow"/>')
    o.append(f'<text x="{lx + 14}" y="{(ly1 + ly2) / 2 + 4}" font-size="11" fill="{VIOLET}" '
             f'fill-opacity=".85" class="mono" letter-spacing="1">JWKS</text>')

    packets = [
        ("M800 205 L920 205 L1045 290", CYAN, 3.6, 1.2),
        ("M800 205 L920 205 L1045 120", VIOLET, 3.6, 3.0),
        (f"M{lx} {ly1} L{lx} {ly2}", VIOLET, 2.8, 2.2),
        ("M1045 120 L1150 170", CYAN, 2.4, 3.9),
        ("M1045 120 L1150 70", CYAN, 2.4, 4.7),
    ]
    o.append('<g class="motion">')
    for d, c, dur, begin in packets:
        o.append(
            f'<g opacity="0"><circle r="7" fill="{c}" opacity=".22"/><circle r="3.2" fill="{c}"/>'
            f'<animateMotion path="{d}" dur="{dur}s" begin="{begin}s" repeatCount="indefinite" '
            'keyPoints="0;1;1" keyTimes="0;0.62;1" calcMode="linear"/>'
            f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.06;0.56;0.62;1" '
            f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/></g>'
        )
    o.append("</g>")

    for label, (cx, cy, c) in nodes.items():
        if label == "gatekeeper":
            o.append(f'<circle cx="{cx}" cy="{cy}" r="17" fill="none" stroke="{c}" class="ring motion"/>')
        o.append(f'<circle cx="{cx}" cy="{cy}" r="17" fill="{BG1}" stroke="{c}" stroke-width="1.6"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="3.6" fill="{c}"/>'
                 f'<text x="{cx}" y="{cy + 36}" font-size="12" fill="{MUTED}" text-anchor="middle" '
                 f'class="mono">{label}</text>')

    # left column: identity
    chars, cw1 = typed(whoami, X, 98, 18, t1_start, t1_step, colors={0: CYAN})
    o.append(chars)
    o.append(f'<rect x="{X}" y="82" width="10" height="20" fill="{CYAN}" class="c1 motion"/>')

    letters, name_w = G.text(700, "Ezzat Mohamed", 68, X - 3, 178, per_glyph=True)
    for i, use in enumerate(letters):  # the animation sits on the <g>, never on the <use>
        o.append(f'<g class="lt" fill="{TEXT}" style="animation-delay:{0.9 + i * 0.045:.3f}s">{use}</g>')
    o.append(f'<path d="M{X} 202 H{X + 132}" stroke="url(#accent)" stroke-width="3" '
             'stroke-linecap="round" class="draw"/>')

    title, _ = G.text(600, "Java Backend Developer", 29, X - 1, 244)
    o.append(f'<g class="up" fill="{TEXT}" style="animation-delay:1.5s">{title}</g>')

    parts, x = [], X
    for i, seg in enumerate(["Spring Boot", "API Security", "Distributed Systems"]):
        if i:
            parts.append(f'<circle cx="{n(x + 11)}" cy="272" r="2.4" fill="{CYAN}"/>')
            x += 22
        d, w = G.text(500, seg, 19, x, 279)
        parts.append(f'<g fill="{MUTED}">{d}</g>')
        x += w
    o.append(f'<g class="up" style="animation-delay:1.75s">{"".join(parts)}</g>')

    chars, cw2 = typed(tagline, X, 336, 17, t2_start, t2_step, colors={0: CYAN})
    o.append(chars)
    o.append(f'<rect x="{X}" y="321" width="9.5" height="19" fill="{CYAN}" class="c2 motion"/>')

    o.append(f'<text x="{X}" y="372" font-size="13" fill="{DIM}" class="mono in" '
             'style="animation-delay:2.2s">Cairo, Egypt · open to backend roles &amp; contract work</text>')

    o.append("</g>")
    o.append(f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="19.5" fill="none" '
             f'stroke="{LINE}" stroke-width="1.5"/>')
    o.append("</svg>")

    assert X + name_w < 760 and X + len(tagline) * cw2 < 760, "hero text collides with the graph"
    write("hero.svg", "".join(o).replace("__GLYPHS__", G.svg()))


# ── section divider ──────────────────────────────────────────────────────────
def divider() -> None:
    W, H = 1200, 24
    css = BASE_CSS + (
        "@keyframes slide{from{transform:translateX(-180px)}to{transform:translateX(1200px)}}"
        ".p1{animation:slide 6.5s cubic-bezier(.45,0,.55,1) infinite}"
    )
    write("divider.svg", "".join([
        svg_open(W, H, "section divider"),
        f"<style>{css}</style><defs>"
        f'<linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="{EDGE}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{EDGE}"/><stop offset="1" stop-color="{EDGE}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="pl" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>'
        "</defs>",
        f'<rect y="11.5" width="{W}" height="1" fill="url(#ln)"/>',
        '<rect y="11" width="180" height="2" fill="url(#pl)" class="p1 motion"/>',
        f'<rect x="596" y="8" width="8" height="8" transform="rotate(45 600 12)" fill="none" '
        f'stroke="{CYAN}" stroke-width="1.2"/>',
        "</svg>",
    ]))


# ── pills: navigation and contact ────────────────────────────────────────────
def pill(rel, label, idx, h=44, size=15, glyph=None, alt=None):
    f = face(600)
    tw = f.width(label, size)
    pad, lead = 20, (26 if glyph else 12)
    W = pad + lead + tw + pad
    G = Glyphs()
    d, _ = G.text(600, label, size, pad + lead, h / 2 + size * 0.36)
    css = BASE_CSS + (
        f"@keyframes sheen{{0%{{transform:translateX(-70px)}}28%,100%{{transform:translateX({n(W + 10)}px)}}}}"
        f".sh{{animation:sheen 8s ease-in-out {0.6 + idx * 0.35:.2f}s infinite backwards}}"
    )
    if glyph == "linkedin":
        mark = (f'<rect x="{pad}" y="{h / 2 - 9}" width="18" height="18" rx="4" fill="{CYAN}"/>'
                f'<g fill="{BG0}">{G.text(700, "in", 11.5, pad + 3.6, h / 2 + 4.3)[0]}</g>')
    elif glyph == "email":
        y0 = h / 2 - 7
        mark = (f'<rect x="{pad}" y="{y0}" width="19" height="14" rx="2.5" fill="none" stroke="{CYAN}" stroke-width="1.6"/>'
                f'<path d="M{pad + 1.5} {y0 + 2} L{pad + 9.5} {y0 + 8} L{pad + 17.5} {y0 + 2}" fill="none" '
                f'stroke="{CYAN}" stroke-width="1.6" stroke-linejoin="round"/>')
    else:
        mark = f'<circle cx="{pad + 3}" cy="{h / 2}" r="3" fill="{CYAN}"/>'
    write(rel, "".join([
        svg_open(W, h, alt or label),
        f"<style>{css}</style><defs>"
        f'<clipPath id="c"><rect width="{n(W)}" height="{h}" rx="{h / 2}"/></clipPath>'
        '<linearGradient id="s" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".13"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        f"</linearGradient>{G.svg()}</defs>",
        f'<rect x=".75" y=".75" width="{n(W - 1.5)}" height="{h - 1.5}" rx="{h / 2 - .75}" fill="{BG1}" '
        f'stroke="{LINE}" stroke-width="1.5"/>',
        mark,
        f'<g fill="{TEXT}">{d}</g>',
        f'<g clip-path="url(#c)"><rect width="60" height="{h}" fill="url(#s)" class="sh motion"/></g>',
        "</svg>",
    ]))


# ── tech stack ───────────────────────────────────────────────────────────────
STACK = [
    ("Core", CYAN, [("i", "java", "Java"), ("i", "spring", "Spring Boot"),
                    ("i", "hibernate", "JPA / Hibernate"), ("i", "maven", "Maven"),
                    ("c", "Spring Security"), ("c", "REST APIs")]),
    ("Security", VIOLET, [("c", "OAuth2"), ("c", "OpenID Connect"), ("c", "JWT / JWKS"),
                          ("c", "Spring Authorization Server"), ("c", "Keycloak"), ("c", "RBAC"),
                          ("c", "Multi-tenancy")]),
    ("Data", CYAN, [("i", "postgresql", "PostgreSQL"), ("i", "oracle", "Oracle"), ("i", "mysql", "MySQL"),
                    ("i", "mongodb", "MongoDB"), ("i", "redis", "Redis"), ("c", "Flyway")]),
    ("Messaging & Infra", CYAN, [("i", "apachekafka", "Kafka"), ("i", "docker", "Docker"), ("i", "git", "Git"),
                                 ("c", "Spring Cloud Gateway"), ("c", "Eureka"), ("c", "Zipkin")]),
    ("Testing & Docs", CYAN, [("i", "junit", "JUnit 5"), ("i", "swagger", "OpenAPI"), ("c", "Mockito"),
                              ("c", "Testcontainers"), ("c", "WireMock")]),
]


def tech_stack() -> None:
    W, LX, IX, RX = 880, 26, 190, 856
    TILE, ICON, GAP, CHIP_H = 60, 34, 10, 32
    lab = face(500)
    G = Glyphs()
    body, wave_i, y = [], 0, 28

    for g, (group, color, items) in enumerate(STACK):
        placed, line, x = [], [], IX
        for it in items:
            if it[0] == "i":
                w = max(78, lab.width(it[2], 12) + 12)
            else:
                w = lab.width(it[1], 13) + 30
            if line and x + w > RX:
                placed.append(line)
                line, x = [], IX
            line.append((it, x, w))
            x += w + GAP
        placed.append(line)

        top = y
        for li, row in enumerate(placed):
            has_tile = any(it[0] == "i" for it, _, _ in row)
            row_h = 90 if has_tile else 42
            if li == 0:
                cy = y + (TILE / 2 if has_tile else CHIP_H / 2 + 2)
                d, _ = G.text(600, group.upper(), 11, LX + 14, cy + 4, tracking=1.4)
                body.append(f'<circle cx="{LX + 3}" cy="{n(cy)}" r="3.2" fill="{color}"/>'
                            f'<g fill="{MUTED}">{d}</g>')
            for it, x, w in row:
                if it[0] == "i":
                    tx = x + (w - TILE) / 2
                    lw = lab.width(it[2], 12)
                    d, _ = G.text(500, it[2], 12, x + (w - lw) / 2, y + TILE + 19)
                    body.append(
                        f'<rect x="{n(tx)}" y="{y}" width="{TILE}" height="{TILE}" rx="14" fill="{BG2}" '
                        f'stroke="{LINE}"/>'
                        + icon(it[1], tx + (TILE - ICON * WIDE.get(it[1], 1)) / 2,
                               y + (TILE - ICON * WIDE.get(it[1], 1)) / 2, ICON * WIDE.get(it[1], 1))
                        + f'<rect x="{n(tx)}" y="{y}" width="{TILE}" height="{TILE}" rx="14" fill="none" '
                          f'stroke="{color}" stroke-width="1.5" class="wv" style="animation-delay:{wave_i * 0.3:.2f}s"/>'
                        + f'<g fill="{MUTED}">{d}</g>')
                else:
                    cyc = y + (TILE / 2 - CHIP_H / 2 if has_tile else 2)
                    lw = lab.width(it[1], 13)
                    d, _ = G.text(500, it[1], 13, x + (w - lw) / 2, cyc + CHIP_H / 2 + 4.6)
                    border = VIOLET if color == VIOLET else LINE
                    body.append(
                        f'<rect x="{n(x)}" y="{n(cyc)}" width="{n(w)}" height="{CHIP_H}" rx="{CHIP_H / 2}" '
                        f'fill="{BG2}" stroke="{border}" stroke-opacity="{".55" if color == VIOLET else "1"}"/>'
                        + f'<rect x="{n(x)}" y="{n(cyc)}" width="{n(w)}" height="{CHIP_H}" rx="{CHIP_H / 2}" '
                          f'fill="none" stroke="{color}" stroke-width="1.5" class="wv" '
                          f'style="animation-delay:{wave_i * 0.3:.2f}s"/>'
                        + f'<g fill="{TEXT}">{d}</g>')
                wave_i += 1
            y += row_h
        if g < len(STACK) - 1:
            body.append(f'<line x1="{LX}" y1="{y + 6}" x2="{RX}" y2="{y + 6}" stroke="{LINE}" '
                        'stroke-dasharray="2 5"/>')
            y += 22
    H = y + 12

    period = max(9.0, wave_i * 0.3 + 2)
    css = BASE_CSS + (
        "@keyframes wave{0%{stroke-opacity:0}4%{stroke-opacity:.9}11%,100%{stroke-opacity:0}}"
        f".wv{{stroke-opacity:0;animation:wave {period:.1f}s ease-in-out infinite backwards}}"
    )
    alt = "; ".join(f"{g}: " + ", ".join(it[2] if it[0] == "i" else it[1] for it in items)
                    for g, _, items in STACK)
    write("tech-stack.svg", "".join([
        svg_open(W, H, "Tech stack", alt),
        f"<style>{css}</style>",
        '<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
        f'<circle cx="1.5" cy="1.5" r="1" fill="#18233F"/></pattern>{G.svg()}</defs>',
        f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="{BG1}" stroke="{LINE}" stroke-width="1.5"/>',
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="url(#dots)" opacity=".7"/>',
        "".join(body),
        "</svg>",
    ]))


# ── project cards ────────────────────────────────────────────────────────────
PROJECTS = [
    dict(slug="authcore", repo="authcore", title="AuthCore", tag="Identity", accent=VIOLET,
         desc="Multi-tenant OAuth2 and OpenID Connect authorization server. Refresh tokens "
              "rotate with reuse detection, signing keys and client secrets rotate while it "
              "runs, and a revoked token stops working immediately.",
         icons=["java", "spring", "postgresql", "redis"], chips=["OAuth2 · OIDC"],
         foot="65 tests · Testcontainers"),
    dict(slug="gatekeeper", repo="gatekeeper", title="GateKeeper", tag="Gateway", accent=CYAN,
         desc="Reactive zero-trust API gateway on Spring Cloud Gateway and Netty. Verifies JWTs "
              "against JWKS with a pinned issuer, authenticates API keys, and strips forged "
              "identity headers.",
         icons=["java", "spring", "redis"], chips=["WebFlux", "WireMock"],
         foot="70 tests · WireMock + Redis"),
    dict(slug="ledger-service", repo="ledger-service", title="ledger-service", tag="Resource server",
         accent=VIOLET,
         desc="OAuth2 resource server that trusts nothing upstream. It verifies every token "
              "itself and enforces tenant isolation, so bypassing the gateway gains an "
              "attacker nothing.",
         icons=["java", "spring"], chips=["JWT", "Multi-tenancy"],
         foot="26 tests · no Docker needed"),
    dict(slug="ecommerce-microservices", repo="E-commerce-Microservices-", title="E-commerce Microservices",
         tag="Microservices", accent=CYAN,
         desc="Eight Spring Boot services behind a Keycloak-secured gateway, with Eureka "
              "discovery, a config server, Kafka-driven order and payment events, and "
              "Zipkin tracing.",
         icons=["java", "spring", "apachekafka", "postgresql", "mongodb", "docker"], chips=["Keycloak"],
         foot="8 services · Docker Compose"),
    dict(slug="spring-boot-api-starter", repo="spring-boot-api-starter", title="spring-boot-api-starter",
         tag="Template", accent=CYAN,
         desc="Production-shaped Spring Boot 3 REST API: JWT auth, RBAC, per-field validation, "
              "one error contract across controllers and the security chain, Flyway, OpenAPI "
              "and Docker.",
         icons=["java", "spring", "postgresql", "docker", "swagger"], chips=["Flyway"],
         foot="23 tests · no Docker needed"),
]


def cards() -> None:
    W, PX, SIZE, LH = 440, 24, 14, 21
    for p in PROJECTS:
        p["lines"] = wrap(p["desc"], SIZE, W - 2 * PX)
    max_lines = max(len(p["lines"]) for p in PROJECTS)
    desc_y = 106
    tech_y = desc_y + (max_lines - 1) * LH + 22
    foot_y = tech_y + 26 + 20
    H = foot_y + 46

    for idx, p in enumerate(PROJECTS):
        a = p["accent"]
        G = Glyphs()
        title, tw = G.text(700, p["title"], 22, PX - 1, 72)
        assert PX + tw < W - PX, f"{p['title']} is too wide for the card"
        tag = p["tag"].upper()
        tg = face(600)
        tag_w = tg.width(tag, 10.5, tracking=1.1) + 22
        tag_d, _ = G.text(600, tag, 10.5, W - PX - tag_w + 11, 36.2, tracking=1.1)

        desc = "".join(
            f'<tspan x="{PX}" dy="{0 if i == 0 else LH}">{escape(line)}</tspan>'
            for i, line in enumerate(p["lines"]))

        tech, x = [], PX
        for name in p["icons"]:
            tech.append(icon(name, x, tech_y, 24))
            x += 32
        chip = face(500)
        for c in p["chips"]:
            cw = chip.width(c, 11.5) + 20
            d, _ = G.text(500, c, 11.5, x + 10, tech_y + 16.3)
            tech.append(f'<rect x="{n(x)}" y="{tech_y + 1}" width="{n(cw)}" height="22" rx="11" '
                        f'fill="{BG2}" stroke="{LINE}"/><g fill="{MUTED}">{d}</g>')
            x += cw + 8
        assert x < W - PX + 8, f"{p['title']} tech row overflows"

        cta_w = face(600).width("Open repository", 12.5)
        cta, _ = G.text(600, "Open repository", 12.5, W - PX - cta_w - 16, foot_y + 27)
        ax = W - PX - 9
        arrow = (f'<path d="M{n(ax - 5)} {foot_y + 22.5} H{n(ax + 4)} M{n(ax)} {foot_y + 18.5} '
                 f'L{n(ax + 4)} {foot_y + 22.5} L{n(ax)} {foot_y + 26.5}" fill="none" stroke="{CYAN}" '
                 'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')

        css = BASE_CSS + (
            f".mono{{font-family:{MONO}}}.sans{{font-family:{SANS}}}"
            f"@keyframes sheen{{0%{{transform:translateX(-160px)}}35%,100%{{transform:translateX({W + 40}px)}}}}"
            f".sh{{animation:sheen 10s ease-in-out {1.2 + idx * 1.6:.1f}s infinite backwards}}"
        )
        alt = f'{p["title"]} — {p["desc"]} {p["foot"]}.'
        write(f"cards/{p['slug']}.svg", "".join([
            svg_open(W, H, p["title"], alt),
            f"<style>{css}</style><defs>"
            f'<clipPath id="c"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
            f'<radialGradient id="g" cx="1" cy="0" r=".9"><stop offset="0" stop-color="{a}" stop-opacity=".13"/>'
            f'<stop offset="1" stop-color="{a}" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="s" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".5" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
            f"</linearGradient>{G.svg()}</defs>",
            '<g clip-path="url(#c)">',
            f'<rect width="{W}" height="{H}" fill="{BG1}"/><rect width="{W}" height="{H}" fill="url(#g)"/>',
            f'<g class="sh motion"><rect x="0" width="120" height="{H}" fill="url(#s)"/></g>',
            "</g>",
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="15.5" fill="none" stroke="{LINE}" stroke-width="1.5"/>',
            f'<text x="{PX}" y="36" font-size="12.5" fill="{DIM}" class="mono">ezat141 / {escape(p["repo"])}</text>',
            f'<rect x="{n(W - PX - tag_w)}" y="21" width="{n(tag_w)}" height="21" rx="10.5" fill="none" '
            f'stroke="{a}" stroke-opacity=".5"/><g fill="{a}">{tag_d}</g>',
            f'<g fill="{TEXT}">{title}</g>',
            f'<text x="{PX}" y="{desc_y}" font-size="{SIZE}" fill="{MUTED}" class="sans">{desc}</text>',
            "".join(tech),
            f'<line x1="{PX}" y1="{foot_y}" x2="{W - PX}" y2="{foot_y}" stroke="{LINE}"/>',
            f'<circle cx="{PX + 4}" cy="{foot_y + 23}" r="4" fill="none" stroke="{a}" class="ring motion"/>',
            f'<circle cx="{PX + 4}" cy="{foot_y + 23}" r="4" fill="{a}"/>',
            f'<text x="{PX + 16}" y="{foot_y + 27}" font-size="12.5" fill="{MUTED}" class="mono">{escape(p["foot"])}</text>',
            f'<g fill="{CYAN}">{cta}</g>', arrow,
            "</svg>",
        ]))


def main() -> None:
    print(f"writing to {OUT}")
    hero()
    divider()
    for i, (label, slug) in enumerate([("About", "about"), ("Tech Stack", "tech-stack"),
                                       ("Projects", "projects"), ("Contact", "contact")]):
        pill(f"nav/{slug}.svg", label, i)
    pill("contact/linkedin.svg", "LinkedIn", 0, h=48, size=16, glyph="linkedin", alt="LinkedIn profile")
    pill("contact/email.svg", "ezat71101@gmail.com", 1, h=48, size=16, glyph="email", alt="Email")
    tech_stack()
    cards()


if __name__ == "__main__":
    main()
