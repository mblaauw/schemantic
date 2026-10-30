"""Review crops: the plate cut into pieces a model can read. A whole plate shown to a model is scaled down until
11 px notes blur; a crop per part keeps text at one and a half to two times its size. The parts follow the layout:
the title block, each panel with a gutter around it (so arrow ends and labels show), and the footer. A part too long
to stay sharp is cut into overlapping pieces along its long side; the title block stays whole.

Every build writes every crop. After the first round the report lists first the parts that changed: each part is
compared with the last round's snapshot, measured from its own corner, so a part that only moved (because a row above
it grew) is still the same part."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

from .spec import card_id

LONG_EDGE = 1568        # px: what a model reads without scaling an image down
MIN_SCALE = 1.5         # a crop is cut into pieces rather than shown smaller than this
RASTER_SCALE = 2        # the raster the crops are cut from
MARGIN = 24             # CSS px around a panel: arrow ends, labels and step badges in the gutter
OVERLAP = 48            # CSS px shared by neighbouring pieces, so a card cut by one edge is whole in the other


def part_names(spec: dict) -> list[str]:
    return ["titleblock"] + [p["id"] for p in spec["panels"]] + ["footer"]


def signatures(snap: dict, spec: dict) -> dict[str, str]:
    """Each part's content from a structural snapshot, measured from the part's own corner: its boxes, the text inside
    it, and the arrows that start or end in it."""
    home = {p["id"]: p["id"] for p in spec["panels"]}
    home |= {card_id(p, i, c): p["id"] for p in spec["panels"] for i, c in enumerate(p.get("cards", []))}
    out = {}
    for part in part_names(spec):
        box = snap["boxes"].get(part)
        if box is None:
            continue
        rel = lambda x, y, box=box: [x - box[0], y - box[1]]
        own = {k: rel(*b[:2]) + rel(*b[2:]) for k, b in snap["boxes"].items() if k == part or k.startswith(part + ".")}
        text = sorted(rel(x, y) + [t] for x, y, t in snap["text"] if box[0] <= x <= box[2] and box[1] <= y <= box[3])
        flows = [[f["from"], f["to"], f["label"], [rel(*pt) for pt in f["points"]]]
                 for f in snap["flows"] if part in (home.get(f["from"]), home.get(f["to"]))]
        out[part] = json.dumps([own, text, flows], sort_keys=True)
    return out


def changed_parts(old: dict | None, new: dict, spec: dict) -> list[str] | None:
    """The parts whose content differs between two snapshots, in reading order; None without an old one."""
    if old is None:
        return None
    a, b = signatures(old, spec), signatures(new, spec)
    return [part for part in b if a.get(part) != b[part]]


def moved_parts(old: dict, new: dict, spec: dict) -> list[str]:
    """The parts whose corner is somewhere else: a row above them grew, or the plate was rearranged."""
    a, b = old["boxes"], new["boxes"]
    return [part for part in part_names(spec) if part in a and part in b and max(abs(a[part][0] - b[part][0]), abs(a[part][1] - b[part][1])) > 2]


def boxes(layout: dict, spec: dict) -> list[tuple[str, list[float]]]:
    """(name, CSS box) for each part, in reading order: title block, panels in spec order, footer."""
    found: dict[str, list[float]] = {}

    def walk(items):
        for it in items:
            if it["kind"] == "group":
                found[it["id"]] = it["box"]
                walk(it["items"])
    walk(layout["items"])
    return [(n, found[n]) for n in part_names(spec) if n in found]


def pieces(box: list[float], width: float, height: float, whole: bool = False) -> list[list[float]]:
    """The box with MARGIN around it, kept on the plate, cut along its long side into as few overlapping pieces as
    keep each at MIN_SCALE or more. A whole part (the title block: the claim is read in one go) is never cut."""
    x0, y0 = max(box[0] - MARGIN, 0), max(box[1] - MARGIN, 0)
    x1, y1 = min(box[2] + MARGIN, width), min(box[3] + MARGIN, height)
    wide = x1 - x0 >= y1 - y0
    lo, hi = (x0, x1) if wide else (y0, y1)
    most = LONG_EDGE / MIN_SCALE
    n = 1 if whole else max(1, math.ceil((hi - lo - OVERLAP) / (most - OVERLAP)))
    step = (hi - lo - OVERLAP) / n
    out = []
    for k in range(n):
        a, z = lo + k * step, lo + (k + 1) * step + OVERLAP
        out.append([a, y0, z, y1] if wide else [x0, a, x1, z])
    return out


def write_crops(layout: dict, spec: dict, raster: Path, dest: Path) -> list[dict]:
    """Cut the plate raster (at RASTER_SCALE) into review crops in dest. Returns, in reading order, each crop's part,
    path and scale (image px per CSS px), and the overview of the whole plate first."""
    dest.mkdir(parents=True, exist_ok=True)
    plate = Image.open(raster).convert("RGB")
    k = plate.size[0] / layout["width"]  # the raster's own scale, which a fractional canvas rounds
    out = []

    def save(img: Image.Image, name: str, part: str) -> None:
        fit = min(1, LONG_EDGE / max(img.size))
        if fit < 1:
            img = img.resize((round(img.size[0] * fit), round(img.size[1] * fit)), Image.LANCZOS)
        path = dest / f"{name}.png"
        img.save(path, optimize=True)
        out.append({"part": part, "path": str(path), "scale": round(k * fit, 2)})

    save(plate, "00-overview", "the whole plate")
    for i, (name, box) in enumerate(boxes(layout, spec), 1):
        cut = pieces(box, layout["width"], layout["height"], whole=name == "titleblock")
        for j, piece in enumerate(cut, 1):
            label = name if len(cut) == 1 else f"{name}, piece {j} of {len(cut)}"
            suffix = "" if len(cut) == 1 else f"-{j}"
            save(plate.crop(tuple(round(v * k) for v in piece)), f"{i:02d}-{name}{suffix}", label)
    return out
