"""--outline-text: replace every <text> in an exported SVG with glyph outlines, for hand-off to tools that ignore
embedded fonts. Text is shaped with HarfBuzz from the same bundled fonts Chromium used, so the outlines land where
the text was. Needs the optional `uharfbuzz` package (`pip install "schemantic[outline]"`)."""
from __future__ import annotations

import io
import re
from functools import cache

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from .config import FONTS_DIR
from .export import FONTS

TEXT = re.compile(r"<text(?P<attrs>[^>]*)>(?P<body>.*?)</text>", re.S)
ATTR = re.compile(r'([\w:-]+)="([^"]*)"')
KEEP = ("fill", "fill-opacity", "data-label")  # attributes carried over to the path


@cache
def _font(file: str):
    import uharfbuzz as hb
    tt = TTFont(str(FONTS_DIR / file))
    tt.flavor = None  # woff2 -> plain sfnt, which HarfBuzz reads
    buf = io.BytesIO()
    tt.save(buf)
    face = hb.Face(hb.Blob(buf.getvalue()))
    font = hb.Font(face)
    upem = tt["head"].unitsPerEm
    font.scale = (upem, upem)
    return tt, font, upem


def _face(family: str, weight: str) -> str:
    family = family.split(",")[0].strip().strip("'\"")
    faces = [f for f in FONTS if f[0] == family] or [f for f in FONTS if f[0] == "Inter"]
    return min(faces, key=lambda f: abs(f[1] - int(float(weight or 400))))[2]


def _unescape(t: str) -> str:
    return t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")


def _outline(attrs: dict, text: str) -> str:
    import uharfbuzz as hb
    tt, font, upem = _font(_face(attrs.get("font-family", "Inter"), attrs.get("font-weight", "400")))
    size = float(attrs["font-size"])
    scale = size / upem
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf)
    width = sum(p.x_advance for p in buf.glyph_positions) * scale
    x = float(attrs["x"]) - (width / 2 if attrs.get("text-anchor") == "middle" else 0)
    y = float(attrs["y"])
    glyphs = tt.getGlyphSet()
    pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        name = tt.getGlyphName(info.codepoint)
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x + pos.x_offset * scale, y - pos.y_offset * scale)))
        x += pos.x_advance * scale
    keep = " ".join(f'{k}="{v}"' for k, v in attrs.items() if k in KEEP)
    return f'<path d="{pen.getCommands()}" {keep}/>'


def outline_text(svg: str) -> str:
    """The SVG with every <text> element replaced by a <path> of its glyphs, and no embedded fonts."""
    def repl(m):
        attrs = dict(ATTR.findall(m.group("attrs")))
        return _outline(attrs, _unescape(m.group("body")))
    svg = TEXT.sub(repl, svg)
    return re.sub(r"<defs><style>.*?</style></defs>\n", "", svg, flags=re.S)
