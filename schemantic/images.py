"""Compare renders: blurred image diffs judged locally, and structural snapshots that name what changed."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from .browser import call

# Image comparison (SVG parity in lint, golden renders in tests) is structural, not pixel-perfect: Chromium
# snaps HTML text and borders to whole pixels while the SVG keeps fractions. A 1.5 px blur absorbs that.
# The verdict is local, not a share of the canvas: one reworded word leaves about 100 px in one place, which a
# canvas-wide share (0.01 % is 190 px) let through. A change fails when one connected region of the mask, or
# one 32 x 32 tile, holds more than a few pixels.
PARITY_BLUR_PX = 1.5
PARITY_DELTA = 40            # grey-level difference (0-255) after blur
# Colour is compared apart from lightness (the Cb and Cr channels of YCbCr), at a finer threshold: a role colour
# swapped for one of the same lightness moves the colour channels by about 25, while the page against its own SVG
# stays under 12 on every example.
PARITY_CHROMA = 12
PARITY_REGION_PX = 24        # largest allowed connected region of differing pixels
PARITY_TILE = 32
PARITY_TILE_PX = 12          # largest allowed number of differing pixels in one tile


def snapshot(page, layout: dict, segs: list[dict]) -> dict:
    """What a plate is made of, rounded to 2 px: every element box by data-id, every text line with its position
    (from the layout document, and the labels the router drew), every connector's points. OS-independent, and a
    diff names what changed."""
    def r2(v):
        return int(round(float(v) / 2) * 2)

    def unescape(t):
        return t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")

    def walk(items):
        for it in items:
            if it["kind"] == "group":
                yield from walk(it["items"])
            elif it["kind"] == "text":
                yield [r2(it["x"]), r2(it["y"]), it["text"]]
            elif it["kind"] == "svg":  # connector labels and step numbers, drawn as SVG by the router
                yield from ([r2(x), r2(y), unescape(t)] for x, y, t in
                            re.findall(r'<text[^>]*?\bx="([-\d.]+)" y="([-\d.]+)"[^>]*>(.*?)</text>', it["svg"]))
    text = list(walk(layout["items"]))
    flows = [{"i": f["i"], "from": f["from"], "to": f["to"], "points": [[r2(x), r2(y)] for x, y in f["points"]],
              "label": (f.get("label") or {}).get("text")} for f in segs]
    return {"boxes": call(page, "boxes"), "text": text, "flows": flows}


def snapshot_diff(old: dict, new: dict, tol: int = 2) -> list[str]:
    """Human-readable differences between two snapshots; geometry within tol px counts as equal."""
    out = []
    near = lambda a, b: len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))
    for k in sorted(set(old["boxes"]) | set(new["boxes"])):
        a, b = old["boxes"].get(k), new["boxes"].get(k)
        if a is None:
            out.append(f"added box {k} at {b}")
        elif b is None:
            out.append(f"removed box {k} (was {a})")
        elif not near(a, b):
            out.append(f"box {k} moved or resized: {a} -> {b}")
    unused = list(new["text"])
    for x, y, t in old["text"]:
        hit = next((n for n in unused if n[2] == t and abs(n[0] - x) <= tol and abs(n[1] - y) <= tol), None)
        if hit:
            unused.remove(hit)
        else:
            out.append(f"text {t!r} at ({x}, {y}) is gone or moved")
    out += [f"text {t!r} at ({x}, {y}) is new or moved" for x, y, t in unused]
    for a, b in zip(old["flows"], new["flows"]):
        if (a["from"], a["to"], a["label"]) != (b["from"], b["to"], b["label"]) or len(a["points"]) != len(b["points"]) \
                or not all(near(p, q) for p, q in zip(a["points"], b["points"])):
            out.append(f"flow {a['i']} ({a['from']} -> {a['to']}) changed: {a['points']} -> {b['points']}")
    if len(old["flows"]) != len(new["flows"]):
        out.append(f"{len(old['flows'])} flows before, {len(new['flows'])} now")
    return out


def image_diff(a_path: Path, b_path: Path, mask_path: Path) -> dict:
    """Compare two renders after a blur. Writes the difference mask to mask_path and returns the pixel count,
    the failing regions (bounding boxes) and whether the difference is large enough anywhere to fail."""
    a = Image.open(a_path).convert("RGB").filter(ImageFilter.GaussianBlur(PARITY_BLUR_PX))
    b = Image.open(b_path).convert("RGB").filter(ImageFilter.GaussianBlur(PARITY_BLUR_PX))
    if a.size != b.size:
        if max(abs(a.size[0] - b.size[0]), abs(a.size[1] - b.size[1])) > 1:
            return {"count": None, "fail": True, "regions": [], "detail": f"size differs: {a.size} vs {b.size}"}
        # A fractional canvas (a paper size) rounds one way in a screenshot and the other in the raster.
        size = (min(a.size[0], b.size[0]), min(a.size[1], b.size[1]))
        a, b = a.crop((0, 0, *size)), b.crop((0, 0, *size))
    # Lightness catches moved shapes and text; colour catches a colour swapped for one of the same lightness (a role
    # or status colour), which a grey comparison misses.
    over = lambda img, limit: img.point(lambda v: 255 if v > limit else 0)
    (ya, cba, cra), (yb, cbb, crb) = a.convert("YCbCr").split(), b.convert("YCbCr").split()
    lum = over(ImageChops.difference(ya, yb), PARITY_DELTA)
    col = over(ImageChops.lighter(ImageChops.difference(cba, cbb), ImageChops.difference(cra, crb)), PARITY_CHROMA)
    mask = ImageChops.lighter(lum, col)
    mask.save(mask_path)
    colour_only = sum(1 for v in ImageChops.subtract(col, lum).tobytes() if v)
    box = mask.getbbox()
    if not box:
        return {"count": 0, "fail": False, "regions": [], "detail": f"0 pixels differ after a {PARITY_BLUR_PX} px blur"}
    crop, (ox, oy) = mask.crop(box), box[:2]
    w = crop.size[0]
    on = {(i % w + ox, i // w + oy) for i, v in enumerate(crop.tobytes()) if v}  # mode L: one byte a pixel
    tiles: dict[tuple[int, int], list] = {}
    for x, y in on:
        tiles.setdefault((x // PARITY_TILE, y // PARITY_TILE), []).append((x, y))
    regions, seen = [], set()
    for start in on:  # 8-connected regions
        if start in seen:
            continue
        stack, pts = [start], []
        seen.add(start)
        while stack:
            x, y = stack.pop()
            pts.append((x, y))
            for nb in ((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                if nb in on and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        regions.append(pts)
    bbox = lambda pts: [min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts) + 1, max(y for _, y in pts) + 1]
    failing = [bbox(r) for r in regions if len(r) > PARITY_REGION_PX]
    failing += [bbox(t) for t in tiles.values() if len(t) > PARITY_TILE_PX and not any(
        f[0] <= t[0][0] < f[2] and f[1] <= t[0][1] < f[3] for f in failing)]
    detail = f"{len(on)} pixels differ after a {PARITY_BLUR_PX} px blur"
    if colour_only:
        detail += f" ({colour_only} in colour only)"
    if failing:
        detail += f"; {len(failing)} region(s) over the limit, first at {failing[0]}"
    return {"count": len(on), "fail": bool(failing), "regions": failing, "colour_only": colour_only, "detail": detail}
