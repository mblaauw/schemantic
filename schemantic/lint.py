"""Layout checks, in two kinds. On the measured page (js/lint.js): text, overlap, containment, canvas fit, arrows,
chips, density. On the layout document alone, no page needed: paint the SVG cannot draw, fonts it cannot carry,
widowed title lines, and print size on paper."""
from __future__ import annotations

import re
import unicodedata

from .browser import call
from .config import MM_PER_PX, PRINT_FLOOR_PT, SLIDE_FLOOR_PX, TYPE_FLOOR_PX
from .export import FONTS, covered, num
from .findings import finding

# A run of empty space inside a body panel longer than this reads as a hole in the plate (review question 4).
VOID_WARN_PX = 96
VOID_ERROR_PX = 160
# Cards a row-spanning panel spreads further apart than this share of their height (and this many px) float, and
# read as holes: name-only cards 40 px apart do, cards with notes and bullets 47 px apart do not.
SPREAD_SHARE = 0.75
SPREAD_FLOOR_PX = 32
# The footer is context; above this share of the plate's height it competes with the body (review question 6). A
# footer of two lines of principles or questions over a legend on two lines is about FOOTER_FLOOR_PX tall and passes on
# any plate, since on a short plate there is nothing left to cut (measured on the eval plates: 106 to 114 px).
FOOTER_SHARE = 0.125
FOOTER_FLOOR_PX = 116
# Cards stacked in one column at least this wide, whose text fills less than this share of them, leave half a card
# empty: they should flow into columns.
WIDE_CARD_PX = 560
CARD_FILL = 0.5


def layout_findings(layout: dict, spec: dict, fit: dict | None) -> list[dict]:
    """Every check on the layout document: paint, fonts, widows, and print size when the plate goes on paper."""
    return (paint_findings(layout["unsupported"]) + font_findings(layout) + widow_findings(layout, spec)
            + (print_findings(layout, fit) if fit else []))


def paint_findings(unsupported: list[dict]) -> list[dict]:
    """CSS the SVG cannot draw (js/layout.js), one finding per element kind and property, at its first place."""
    seen: dict[tuple, list[str]] = {}
    for u in unsupported:
        seen.setdefault((u["element"], u["property"], u["value"]), []).append(u["id"])
    return [finding("paint", ids[0], f"{element} uses {prop}: {value}, which the SVG cannot draw"
                    + (f" ({len(ids)} elements)" if len(ids) > 1 else ""))
            for (element, prop, value), ids in seen.items()]


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


def widow_findings(layout: dict, spec: dict) -> list[dict]:
    """A topic, title or subtitle whose last line is a single word (from the line breaks in the layout document)."""
    block = next((it for it in layout["items"] if it["kind"] == "group" and it["id"] == "titleblock"), None)
    if not block:
        return []
    runs: list[list[str]] = []  # consecutive lines in one font are one text
    last = None
    for it in block["items"]:
        if it["kind"] != "text":
            continue
        font = (it["font"]["size"], it["font"]["weight"])
        if font != last:
            runs.append([])
        runs[-1].append(it["text"])
        last = font
    out = []
    for lines in runs:
        field = next((f for f in ("title", "subtitle", "topic") if " ".join(spec.get(f, "").split()) == " ".join(lines)), None)
        if field and len(lines) > 1 and len(lines[-1].split()) == 1:
            out.append(finding("widow", field, f"the {field} breaks over {len(lines)} lines and leaves '{lines[-1]}' on its own",
                               level="warning"))
    return out


def dom_lint(page, segs: list[dict], slide: bool = False) -> dict:
    """{issues, density, voids} for the plate in `page`, with the routed connectors in `segs`."""
    return call(page, "lint", {"floor": SLIDE_FLOOR_PX if slide else TYPE_FLOOR_PX, "segs": segs,
                               "voidWarn": VOID_WARN_PX, "voidError": VOID_ERROR_PX, "spreadShare": SPREAD_SHARE,
                               "spreadFloor": SPREAD_FLOOR_PX, "footerShare": FOOTER_SHARE, "footerFloor": FOOTER_FLOOR_PX,
                               "wideCard": WIDE_CARD_PX, "cardFill": CARD_FILL})
