"""SVG assembly and fonts: the HTML loads the bundled faces whole; each SVG embeds a subset of the glyphs it uses."""
from __future__ import annotations

import base64
import io
import re
import unicodedata
from functools import cache

from fontTools import subset
from fontTools.ttLib import TTFont

from . import outline
from .browser import call
from .config import FONTS_DIR, MM_PER_PX, PRINT_FLOOR_PT
from .findings import finding
from .lint import VOID_WARN_PX

# Bundled faces, loaded through @font-face so layout never depends on installed fonts.
FONTS = [("Inter", 400, "Inter-Regular.woff2"), ("Inter", 500, "Inter-Medium.woff2"),
         ("Inter", 600, "Inter-SemiBold.woff2"), ("Inter", 700, "Inter-Bold.woff2"),
         ("Inter", 800, "Inter-ExtraBold.woff2"), ("DejaVu Sans Mono", 400, "DejaVuSansMono.woff2")]


def font_face(family: str, weight: int, data: bytes) -> str:
    uri = "data:font/woff2;base64," + base64.b64encode(data).decode("ascii")
    return f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; src: url({uri}) format('woff2'); }}"


@cache
def font_css() -> str:
    return "\n".join(font_face(fam, w, (FONTS_DIR / file).read_bytes()) for fam, w, file in FONTS)


def subset_font_css(used: dict[str, str]) -> str:
    """@font-face rules holding only the glyphs each bundled face draws. `used` maps 'Family|weight' to text."""
    rules = []
    for key, text in used.items():
        family, weight = key.split("|")
        faces = [f for f in FONTS if f[0] == family]
        if not faces:
            continue  # not bundled: the viewer's own fonts decide
        _, w, file = min(faces, key=lambda f: abs(f[1] - int(weight)))  # nearest weight, as the browser picks
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.drop_tables.append("FFTM")  # FontForge timestamp; fontTools cannot subset it and warns
        sub = subset.Subsetter(opts)
        font = subset.load_font(str(FONTS_DIR / file), opts)
        sub.populate(text=text)
        sub.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, opts)
        rules.append(font_face(family, w, buf.getvalue()))
    return "\n".join(rules)


@cache
def covered(file: str) -> frozenset[int]:
    """The code points a bundled face has glyphs for."""
    return frozenset(TTFont(str(FONTS_DIR / file)).getBestCmap())


def font_findings(layout: dict) -> list[dict]:
    """Text the SVG cannot carry with it: a family that is not bundled, or characters the bundled face lacks (CJK,
    emoji, some symbols). Chromium would borrow a system font for both, so the page and its SVG raster agree here
    and parity cannot see it, but another machine or viewer draws something else. Named by the group the text is in."""
    first: dict[str, str] = {}  # family -> the group of its first text line
    chars: dict[tuple[str, str], str] = {}  # (family, group) -> its characters

    def walk(items, group):
        for it in items:
            if it["kind"] == "group":
                walk(it["items"], it["id"])
            elif it["kind"] == "text":
                add(it["font"]["family"], group, it["text"])
            elif it["kind"] == "svg":  # connector labels and step numbers, drawn by the router in each flow's group
                for i, body in re.findall(r'<g id="flow-(\d+)"[^>]*>(.*?)</g>', it["svg"], re.S):
                    for family, text in re.findall(r'<text[^>]*font-family="([^"]*)"[^>]*>(.*?)</text>', body):
                        add(family, f"flows/{i}", text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))

    def add(family, group, text):
        family = family.split(",")[0].strip().strip("'\"")
        first.setdefault(family, group)
        chars[family, group] = chars.get((family, group), "") + text
    walk(layout["items"], "(plate)")
    files = {fam: [f for f in FONTS if f[0] == fam] for fam in first}
    out = [finding("font", group, f"text set in {family}, which is not bundled, so the SVG cannot embed it")
           for family, group in first.items() if not files[family]]
    for (family, group), text in chars.items():
        if not files[family]:
            continue
        # Every bundled weight of a family covers the same characters; check against the regular face.
        file = min(files[family], key=lambda f: abs(f[1] - 400))[2]
        missing = sorted({ch for ch in text if ord(ch) not in covered(file) and not ch.isspace()
                          and unicodedata.category(ch) not in ("Cc", "Cf")})
        if missing:
            listed = ", ".join(f"'{ch}' (U+{ord(ch):04X})" for ch in missing)
            out.append(finding("font", group, f"{listed} {'is' if len(missing) == 1 else 'are'} not in {family}, so a viewer "
                               f"draws {'it' if len(missing) == 1 else 'them'} with whatever font it has"))
    return out


def on_paper(svg: str, fit: dict) -> str:
    """The SVG at the sheet's size in mm, the plate centred on it at fit['scale']: only the root's size and viewBox
    change, so the drawing stays in CSS px and editors keep their coordinates."""
    unit = MM_PER_PX * fit["scale"]  # mm per CSS px on paper
    (w_mm, h_mm), (ox, oy) = fit["sheet_mm"], fit["offset_mm"]
    head = re.match(r'(<svg[^>]*?) width="[\d.]+" height="[\d.]+" viewBox="[^"]*"', svg)
    return (f'{head.group(1)} width="{num(w_mm)}mm" height="{num(h_mm)}mm" '
            f'viewBox="{num(-ox / unit)} {num(-oy / unit)} {num(w_mm / unit)} {num(h_mm / unit)}"' + svg[head.end():])


def print_findings(layout: dict, fit: dict) -> list[dict]:
    """On paper, the smallest text must stay at PRINT_FLOOR_PT or more after the plate is scaled to the sheet, and a
    plate much shorter than its sheet leaves blank bands above and below it."""
    out = []
    band = fit["offset_mm"][1] / MM_PER_PX
    if band > VOID_WARN_PX:
        out.append(finding("void", "canvas.size",
                           f"the plate fills {1 - 2 * band / (fit['sheet_mm'][1] / MM_PER_PX):.0%} of the "
                           f"{fit['size']} sheet's height, leaving {band:.0f}px blank above and below it; let it grow "
                           f"taller (fewer card_columns, another row) or use a screen size", level="warning"))
    sizes = []

    def walk(items):
        for it in items:
            if it["kind"] == "group":
                walk(it["items"])
            elif it["kind"] == "text":
                sizes.append(float(it["font"]["size"]))
            elif it["kind"] == "svg":
                sizes.extend(float(s) for s in re.findall(r'<text[^>]*font-size="([\d.]+)"', it["svg"]))
    walk(layout["items"])
    smallest = min(sizes, default=0) * MM_PER_PX * fit["scale"] * 72 / 25.4
    if not sizes or smallest >= PRINT_FLOOR_PT:
        return out
    return out + [finding("print-size", "canvas.size",
                          f"the plate is {num(layout['width'])} x {num(layout['height'])} px, so {fit['size']} prints "
                          f"it at {fit['scale']:.0%} and its smallest text at {smallest:.1f} pt (the floor is "
                          f"{PRINT_FLOOR_PT} pt)")]


def measure(page) -> dict:
    """The layout document of the laid-out page: groups, rects, lines, text lines, icons and drawn connectors, at the
    positions Chromium measured (see js/layout.js). Everything the SVG needs, and nothing it has to look up."""
    return call(page, "layout")


def num(v: float) -> str:
    """A coordinate rounded to two decimals, in the shortest form: 12, 12.5, 12.35."""
    v = round(float(v), 2)
    s = repr(v)
    return "0" if v == 0 else s[:-2] if s.endswith(".0") else s


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def paint(p: dict | None, key: str) -> str:
    if not p:
        return ""
    return f'{key}="{p["color"]}"' + (f' {key}-opacity="{num(p["opacity"])}"' if "opacity" in p else "")


def rounded(x: float, y: float, w: float, h: float, radii: list[float]) -> str:
    tl, tr, br, bl = (max(0, min(r, w / 2, h / 2)) for r in radii)
    d = f"M{num(x + tl)} {num(y)}H{num(x + w - tr)}" + (f"A{num(tr)} {num(tr)} 0 0 1 {num(x + w)} {num(y + tr)}" if tr else "")
    d += f"V{num(y + h - br)}" + (f"A{num(br)} {num(br)} 0 0 1 {num(x + w - br)} {num(y + h)}" if br else "")
    d += f"H{num(x + bl)}" + (f"A{num(bl)} {num(bl)} 0 0 1 {num(x)} {num(y + h - bl)}" if bl else "")
    return d + f"V{num(y + tl)}" + (f"A{num(tl)} {num(tl)} 0 0 1 {num(x + tl)} {num(y)}" if tl else "") + "Z"


def svg_items(items: list[dict]) -> list[str]:
    """SVG for the items of a layout document, one line each; a group opens and closes on lines of its own."""
    out = []
    for it in items:
        k = it["kind"]
        if k == "group":
            refs = f' data-refs="{esc(it["refs"])}"' if it.get("refs") else ""
            out.append(f'<g id="{esc(it["type"] + "-" + it["id"])}" data-id="{esc(it["id"])}"{refs} '
                       f'inkscape:label="{esc(it["label"])}">')
            out += svg_items(it["items"])
            out.append("</g>")
        elif k == "rect":
            r = it["radii"]
            stroke = f' {paint(it["stroke"], "stroke")} stroke-width="{num(it["strokeWidth"])}"' if it.get("stroke") else ""
            fill = paint(it["fill"], "fill") or ('fill="none"' if stroke else "")
            if all(v == r[0] for v in r):
                rx = f' rx="{num(r[0])}"' if r[0] else ""
                out.append(f'<rect x="{num(it["x"])}" y="{num(it["y"])}" width="{num(it["w"])}" height="{num(it["h"])}"{rx} '
                           f'{fill}{stroke}/>')
            else:
                out.append(f'<path d="{rounded(it["x"], it["y"], it["w"], it["h"], r)}" {fill}{stroke}/>')
        elif k == "line":
            out.append(f'<line x1="{num(it["x1"])}" y1="{num(it["y1"])}" x2="{num(it["x2"])}" y2="{num(it["y2"])}" '
                       f'{paint(it["stroke"], "stroke")} stroke-width="{num(it["strokeWidth"])}"/>')
        elif k == "text":
            font = it["font"]
            fill = paint(it["fill"], "fill")
            out.append(f'<text x="{num(it["x"])}" y="{num(it["y"])}" font-family="{esc(font["family"].replace(chr(34), chr(39)))}" '
                       f'font-size="{num(font["size"])}" font-weight="{font["weight"]}"{" " + fill if fill else ""}'
                       f'{" xml:space=" + chr(34) + "preserve" + chr(34) if it["preserve"] else ""}>{esc(it["text"])}</text>')
        elif k == "icon":
            out.append(f'<g transform="translate({num(it["x"])} {num(it["y"])}) scale({it["size"] / 24:.4f})" fill="none" '
                       f'stroke="{it["stroke"]}" stroke-width="{it["strokeWidth"]}" stroke-linecap="round" '
                       f'stroke-linejoin="round">{it["svg"]}</g>')
        elif k == "svg":
            out.append(it["svg"])
    return out


def export_svg(layout: dict, spec: dict) -> tuple[str, list[str]]:
    """The layout document as a standalone SVG, and the font faces it uses ('Inter 600', ...)."""
    title = spec["title"] + (f" — {spec['subtitle']}" if spec.get("subtitle") else "")
    w, h = layout["width"], layout["height"]
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            f'width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}" role="img" lang="{spec["canvas"]["lang"]}">\n'
            f'<title>{esc_text(title)}</title>\n<desc>{esc_text(outline.desc(spec))}</desc>\n'
            f'<defs><style>\n{subset_font_css(layout["used"])}\n</style></defs>\n')
    fonts = sorted(k.replace("|", " ") for k in layout["used"])
    return head + "\n".join(svg_items(layout["items"])) + "\n</svg>\n", fonts


def esc_text(s: str) -> str:
    """Element content: only & and < need escaping (as the title and desc always were)."""
    return s.replace("&", "&amp;").replace("<", "&lt;")
