"""Shared library for render.py and lint.py.

Pipeline: YAML spec -> schema + semantic checks -> HTML (CSS Grid, tokens) -> Chromium layout
-> flow arrows computed from measured boxes -> native SVG (rect/path/text/line) -> PNG raster of that SVG.
The model never writes coordinates; every position comes from the browser's layout.
"""
from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

import jsonschema
import yaml
from fontTools import subset
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
CANVAS_SIZES = {"landscape-4x3": (1600, 1200), "landscape-16x9": (1920, 1080)}
# Gutters hold the flow arrows: 48 px fits a 32 px arrow with 8 px clearance on both sides.
GUTTER_X = 48
# Row gutters also hold a one-line arrow label at 11 px.
GUTTER_Y = 44
TYPE_FLOOR_PX = 11
# The schema lists every planned archetype; only these have a template. The rest are refused, not drawn as column-flow.
BUILT_ARCHETYPES = ["column-flow", "hub-and-spokes", "layer-cake"]
# Bundled faces (assets/fonts), loaded through @font-face so layout never depends on installed fonts.
# The HTML gets the full files; the SVG gets a subset of the glyphs it uses.
FONTS = [("Inter", 400, "Inter-Regular.woff2"), ("Inter", 500, "Inter-Medium.woff2"),
         ("Inter", 600, "Inter-SemiBold.woff2"), ("Inter", 700, "Inter-Bold.woff2"),
         ("Inter", 800, "Inter-ExtraBold.woff2"), ("DejaVu Sans Mono", 400, "DejaVuSansMono.woff2")]
# Image comparison (SVG parity in lint, golden renders in tests) is structural, not pixel-perfect: Chromium
# snaps HTML text and borders to whole pixels while the SVG keeps fractions. A 1.5 px blur absorbs that.
# The verdict is local, not a share of the canvas: one reworded word leaves about 100 px in one place, which a
# canvas-wide share (0.01 % is 190 px) let through. A change fails when one connected region of the mask, or
# one 32 x 32 tile, holds more than a few pixels.
PARITY_BLUR_PX = 1.5
PARITY_DELTA = 40            # grey-level difference (0-255) after blur
PARITY_REGION_PX = 24        # largest allowed connected region of differing pixels
PARITY_TILE = 32
PARITY_TILE_PX = 12          # largest allowed number of differing pixels in one tile


# ---------------------------------------------------------------- spec

def load_spec(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def read_spec(path: str | Path) -> tuple[dict | None, list[dict]]:
    """Load a spec for the CLIs: a missing file, broken YAML or a document that is not a mapping becomes a
    `yaml` finding instead of a traceback."""
    err = lambda detail: (None, [{"level": "error", "check": "yaml", "id": "(file)", "detail": detail}])
    try:
        spec = load_spec(path)
    except FileNotFoundError:
        return err(f"no such file: {path}")
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        return err(f"not valid YAML{where}: {getattr(e, 'problem', None) or e}")
    if not isinstance(spec, dict):
        return err(f"the file holds {type(spec).__name__ if spec is not None else 'nothing'}, not a spec (a mapping of canvas, title, …)")
    return spec, []


def internal_error(exc: Exception) -> dict:
    return {"level": "error", "check": "internal", "id": "(plate)",
            "detail": f"{type(exc).__name__}: {exc}. This is a Schemantic bug, not a spec problem; report it with the spec."}


def load_locale(lang: str) -> dict:
    with open(ROOT / "locales" / f"{lang}.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def schema_errors(spec: dict) -> list[dict]:
    schema = json.loads((ROOT / "schema" / "plate.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        out.append({"level": "error", "check": "schema", "id": where, "detail": err.message})
    return out


# Layout keys per archetype. column-flow names its grid cells; the others place panels by role and derive the grid.
LAYOUT_KEYS = {
    "column-flow": ({"areas"}, {"areas", "column_widths", "row_heights"}),
    "hub-and-spokes": ({"hub"}, {"hub", "top", "bottom", "left", "right", "row_heights"}),
    "layer-cake": ({"layers"}, {"layers", "left", "right", "row_heights"}),
}
# Rails in a layer cake are this share of a layer's width.
RAIL_WEIGHT = 0.22


def placed_ids(layout: dict) -> list[str]:
    """Panel ids in the order a derived layout places them (duplicates kept, so they can be reported)."""
    out = []
    for key in ("hub", "layers", "top", "bottom", "left", "right"):
        v = layout.get(key)
        out += v if isinstance(v, list) else ([v] if v else [])
    return out


def body_groups(spec: dict) -> dict[str, list[str]]:
    """Spoke rows of a hub, each rendered as its own grid in one body cell, so every row divides the hub's
    width evenly whatever the other row holds. Group names start with '_', which a panel id cannot."""
    if spec["archetype"] != "hub-and-spokes":
        return {}
    lay = spec["layout"]
    return {g: lay[k] for g, k in (("_top", "top"), ("_bottom", "bottom")) if lay.get(k)}


def area_tokens(spec: dict) -> list[list[str]]:
    """The body grid as rows of panel ids or group names ('.' is empty), written by hand or derived."""
    lay, kind = spec["layout"], spec["archetype"]
    if kind == "hub-and-spokes":
        groups = body_groups(spec)
        rows = ([["_top"]] if "_top" in groups else []) + [[lay["hub"]]] + ([["_bottom"]] if "_bottom" in groups else [])
    elif kind == "layer-cake":
        rows = [[layer] for layer in lay["layers"]]
    else:
        return [row.split() for row in lay["areas"]]
    # Side panels span every row, so they face the hub (or every layer) across one gutter.
    return [([lay["left"]] if lay.get("left") else []) + row + ([lay["right"]] if lay.get("right") else []) for row in rows]


def default_row_heights(spec: dict, rows: list[list[str]]) -> list[str]:
    """column-flow rows share the height equally. Spoke rows and layers hug their content (auto tracks still
    stretch into leftover space), so the hub, or the fullest layer, gets the room."""
    if spec["archetype"] == "hub-and-spokes":
        return ["fill" if spec["layout"]["hub"] in row else "auto" for row in rows]
    if spec["archetype"] == "layer-cake":
        return ["auto"] * len(rows)
    return ["fill"] * len(rows)


def column_tracks(spec: dict, ncols: int) -> list[str]:
    """CSS column tracks for the body grid (gutter tracks are added by grid_css)."""
    lay, kind = spec["layout"], spec["archetype"]
    sides = [bool(lay.get("left")), bool(lay.get("right"))]
    fr = lambda w: f"minmax(0, {w}fr)"
    if kind == "hub-and-spokes":
        # A side spoke is as wide as one spoke of the fuller row (counted as at least 2, so a lone spoke never
        # makes the side as wide as the hub). With n spokes in a row, a spoke is (H - (n-1)·gutter)/n of the hub
        # width H; solving for the side width S against the body width (100%) gives S = f·100% + g, so CSS does
        # the arithmetic and the gutters are counted.
        n, ns = max(len(lay.get("top", [])), len(lay.get("bottom", [])), 2), sum(sides)
        a, b = 1 / n, (n - 1) * GUTTER_X / n
        f = a / (1 + ns * a)
        g = f * (ns * b - ns * GUTTER_X) - b
        side = f"calc({f * 100:.4f}% + {g:.2f}px)"
        return [side] * sides[0] + [fr(1)] + [side] * sides[1]
    if kind == "layer-cake":
        return [fr(RAIL_WEIGHT)] * sides[0] + [fr(1)] + [fr(RAIL_WEIGHT)] * sides[1]
    return [fr(w) for w in (lay.get("column_widths") or [1] * ncols)]


def semantic_errors(spec: dict) -> list[dict]:
    """Checks the schema cannot express: archetype, areas, ids, flow endpoints, chips, language."""
    out = []
    err = lambda check, id_, detail, level="error": out.append(
        {"level": level, "check": check, "id": id_, "detail": detail})

    if spec["archetype"] not in BUILT_ARCHETYPES:
        err("archetype", "archetype", f"'{spec['archetype']}' is not built yet; use one of {', '.join(BUILT_ARCHETYPES)}")
        return out
    # Ids first: a colliding id makes every later check (and the router) look in the wrong place.
    out += id_errors(spec)
    if out:
        return out
    required, allowed = LAYOUT_KEYS[spec["archetype"]]
    keys = set(spec["layout"])
    for k in sorted(required - keys):
        err("layout", f"layout.{k}", f"{spec['archetype']} needs layout.{k}")
    for k in sorted(keys - allowed):
        err("layout", f"layout.{k}", f"layout.{k} does not apply to {spec['archetype']}; it takes {', '.join(sorted(allowed))}")
    if out:
        return out
    if spec["archetype"] != "column-flow":
        ids = placed_ids(spec["layout"])
        for n in sorted({n for n in ids if ids.count(n) > 1}):
            err("layout", n, "panel is placed more than once in layout")
        if spec["archetype"] == "hub-and-spokes" and len(ids) < 3:
            err("layout", "layout.hub", "a hub needs at least two spokes (top, bottom, left, right)")
        if out:
            return out

    rows = area_tokens(spec)
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        err("layout", "layout.areas", f"every row needs the same number of cells, got {sorted(widths)}")
        return out
    ncols = widths.pop()
    if ncols > 5 and spec["archetype"] == "column-flow":
        err("budget", "layout.areas", f"{ncols} body columns; the budget is 5. Split the plate.")
    names = {n for r in rows for n in r if n != "."}
    groups = body_groups(spec)
    placed = (names - set(groups)) | {n for ids in groups.values() for n in ids}
    panel_ids = [p["id"] for p in spec["panels"]]
    for n in sorted(placed - set(panel_ids)):
        err("layout", "layout", f"'{n}' is placed in the layout but has no panel")
    for n in sorted(set(panel_ids) - placed):
        err("layout", n, "panel is not placed in the layout")
    for n in names:  # each area must be a rectangle
        cells = [(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if v == n]
        r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
        c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
        if len(cells) != (r1 - r0 + 1) * (c1 - c0 + 1):
            err("layout", n, "area is not a rectangle")
    cw = spec["layout"].get("column_widths")
    if cw and len(cw) != ncols:
        err("layout", "layout.column_widths", f"{len(cw)} widths for {ncols} columns")
    rh = spec["layout"].get("row_heights")
    if rh and len(rh) != len(rows):
        err("layout", "layout.row_heights", f"{len(rh)} heights for {len(rows)} rows")

    for p in spec["panels"]:
        if p.get("weights"):
            blocks = len(p.get("patterns", [])) + (1 if p.get("cards") else 0)
            if p.get("arrange") != "row":
                err("layout", p["id"], "weights only apply when arrange is row")
            elif len(p["weights"]) != blocks:
                err("layout", p["id"], f"{len(p['weights'])} weights for {blocks} blocks (patterns first, then cards)")

    known = set(panel_ids)
    for p in spec["panels"]:
        for i, c in enumerate(p.get("cards", [])):
            known.add(c.get("id") or f"{p['id']}.card{i}")
        for pt in p.get("patterns", []):
            if pt["type"] == "matrix":
                for r in pt["rows"]:
                    if len(r["cells"]) != len(pt["columns"]):
                        err("pattern", p["id"], f"matrix row '{r['name']}' has {len(r['cells'])} cells for {len(pt['columns'])} columns")
    for i, f in enumerate(spec.get("flows", [])):
        for end in ("from", "to"):
            if f[end] not in known:
                err("flow", f"flows/{i}", f"endpoint '{f[end]}' does not exist")
        if f["from"] == f["to"]:
            err("flow", f"flows/{i}", f"from and to are the same element ('{f['from']}')")

    canvas = spec["canvas"]
    if ("part" in canvas) != ("of" in canvas):
        err("canvas", "canvas.part" if "part" not in canvas else "canvas.of", "give both part and of, or neither; the badge needs both")
    elif "part" in canvas and canvas["part"] > canvas["of"]:
        err("canvas", "canvas.part", f"part {canvas['part']} of {canvas['of']}; part cannot be larger than of")
    fcols = (spec.get("footer") or {}).get("columns")
    if fcols and len(fcols) != len(footer_panels(spec)):
        err("layout", "footer.columns", f"{len(fcols)} widths for {len(footer_panels(spec))} footer panels ({', '.join(footer_panels(spec))})")
    oq = (spec.get("footer") or {}).get("open_questions") or {}
    chips = [ch["text"] for p in spec["panels"] for ch in p.get("chips", []) if ch["kind"] == "warning"]
    if chips and not oq.get("from_chips"):
        missing = [c for c in chips if c not in oq.get("extra", [])]
        for c in missing:
            err("chip-mirror", "footer.open_questions", f"warning chip not repeated in open questions: '{c}'")

    for icon in iter_icons(spec):
        if not (ROOT / "assets" / "icons" / f"{icon}.svg").exists():
            err("icon", icon, "icon not in assets/icons; pick one from the registry")

    loc = load_locale(spec["canvas"]["lang"])
    text = "\n".join(iter_strings(spec)).lower()
    for term, bad in (loc.get("never_translate") or {}).items():
        for b in bad:
            # Substring, not whole word: Dutch compounds hide the term ("productcatalogus").
            if re.search(re.escape(b.lower()), text):
                err("language", term, f"'{b}' found; keep the technical term '{term}' in English")
    return out


def id_errors(spec: dict) -> list[dict]:
    """Panel ids are unique; an explicit card id is unique across the plate and never equals a panel id or a
    card's automatic id (<panel>.card<n>). Each collision is reported once, naming both places."""
    out = []
    err = lambda id_, detail: out.append({"level": "error", "check": "id", "id": id_, "detail": detail})
    panels = {}
    for i, p in enumerate(spec["panels"]):
        if p["id"] in panels:
            err(p["id"], f"panels/{panels[p['id']]} and panels/{i} both use id '{p['id']}'")
        else:
            panels[p["id"]] = i
    auto = {f"{p['id']}.card{i}" for p in spec["panels"] for i in range(len(p.get("cards", [])))}
    context = ((spec.get("footer") or {}).get("context") or {}).get("cards", [])
    places = [(f"panels/{pi}/cards/{ci}", c) for pi, p in enumerate(spec["panels"]) for ci, c in enumerate(p.get("cards", []))]
    places += [(f"footer/context/cards/{ci}", c) for ci, c in enumerate(context)]
    seen = {}
    for where, c in places:
        cid = c.get("id")
        if not cid:
            continue
        if cid in panels:
            err(cid, f"{where} uses '{cid}', which is already the id of panels/{panels[cid]}")
        elif cid in auto:
            err(cid, f"{where} uses '{cid}', which is the automatic id of another card")
        elif cid in seen:
            err(cid, f"{seen[cid]} and {where} both use id '{cid}'")
        else:
            seen[cid] = where
    return out


def footer_panels(spec: dict) -> list[str]:
    """The footer panels the template renders, in order; the legend is always there."""
    footer = spec.get("footer") or {}
    present = [("context", bool(footer.get("context"))), ("principles", bool(footer.get("principles"))),
               ("open_questions", bool(open_questions(spec))), ("legend", True)]
    return [name for name, on in present if on]


# Default footer widths per panel, relative to each other; only the panels present get a track.
FOOTER_WEIGHTS = {"context": 1.5, "principles": 1.4, "open_questions": 1.1, "legend": 0.9}


def iter_icons(spec: dict):
    for p in spec["panels"]:
        for c in p.get("cards", []):
            if c.get("icon"):
                yield c["icon"]
        for pt in p.get("patterns", []):
            for t in pt.get("tiers", []):
                if t.get("icon"):
                    yield t["icon"]
    ctx = (spec.get("footer") or {}).get("context") or {}
    for c in ctx.get("cards", []):
        if c.get("icon"):
            yield c["icon"]


def iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in ("id", "icon", "role", "kind", "type", "tier", "layout", "from", "to"):
                yield from iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_strings(v)


# ---------------------------------------------------------------- HTML

def grid_css(spec: dict) -> dict:
    """Insert gutter tracks between columns and rows; an area that spans cells also spans the gutter."""
    rows = area_tokens(spec)
    n, m = len(rows[0]), len(rows)
    lines = []
    for r, row in enumerate(rows):
        line = []
        for c, name in enumerate(row):
            line.append(name)
            if c < n - 1:
                line.append(name if row[c + 1] == name else ".")
        lines.append(line)
        if r < m - 1:
            nxt, gap = rows[r + 1], []
            for c in range(n):
                gap.append(row[c] if nxt[c] == row[c] else ".")
                if c < n - 1:
                    same = row[c] == row[c + 1] == nxt[c] == nxt[c + 1]
                    gap.append(row[c] if same else ".")
            lines.append(gap)
    heights = spec["layout"].get("row_heights") or default_row_heights(spec, rows)
    cols = f" {GUTTER_X}px ".join(column_tracks(spec, n))
    rows_css = f" {GUTTER_Y}px ".join("minmax(0, 1fr)" if h == "fill" else "auto" for h in heights)
    areas = " ".join('"' + " ".join(l) + '"' for l in lines)
    return {"columns": cols, "rows": rows_css, "areas": areas}


_icon_cache: dict[str, str] = {}


def icon_markup(name: str) -> str:
    if name not in _icon_cache:
        raw = (ROOT / "assets" / "icons" / f"{name}.svg").read_text(encoding="utf-8")
        inner = raw[raw.index(">", raw.index("<svg")) + 1: raw.rindex("</svg>")]
        inner = re.sub(r'<path stroke="none" d="M0 0h24v24H0z" fill="none"\s*/>', "", inner)
        _icon_cache[name] = re.sub(r"\s+", " ", inner).strip()
    return _icon_cache[name]


def tree_rows(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        stripped = line.lstrip(" ")
        out.append({"depth": (len(line) - len(stripped)) // 2, "text": stripped})
    return out


def matrix_values(pt: dict) -> list[str]:
    used = {v for r in pt["rows"] for v in r["cells"]}
    return [v for v in ("full", "partial", "none") if v in used]


def legend_entries(spec: dict, loc: dict) -> list[dict]:
    entries, seen = [], set()
    for p in spec["panels"]:
        if p["role"] not in seen:
            seen.add(p["role"])
            entries.append({"kind": "role", "key": p["role"], "label": loc["legend"][p["role"]]})
    if spec.get("flows"):
        entries.append({"kind": "arrow", "key": "arrow", "label": loc["legend"]["arrow"]})
    kinds = []
    for p in spec["panels"]:
        for ch in p.get("chips", []):
            if ch["kind"] not in kinds:
                kinds.append(ch["kind"])
    for k in ("warning", "info"):
        if k in kinds:
            entries.append({"kind": "chip", "key": k, "label": loc["legend"][k]})
    return entries


def open_questions(spec: dict) -> list[str]:
    oq = (spec.get("footer") or {}).get("open_questions") or {}
    out = []
    if oq.get("from_chips"):
        out += [ch["text"] for p in spec["panels"] for ch in p.get("chips", []) if ch["kind"] == "warning"]
    out += [q for q in oq.get("extra", []) if q not in out]
    return out


def font_face(family: str, weight: int, data: bytes) -> str:
    uri = "data:font/woff2;base64," + base64.b64encode(data).decode("ascii")
    return f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; src: url({uri}) format('woff2'); }}"


def font_css() -> str:
    return "\n".join(font_face(fam, w, (ROOT / "assets" / "fonts" / file).read_bytes()) for fam, w, file in FONTS)


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
        font = subset.load_font(str(ROOT / "assets" / "fonts" / file), opts)
        sub.populate(text=text)
        sub.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, opts)
        rules.append(font_face(family, w, buf.getvalue()))
    return "\n".join(rules)


def panels_for_render(spec: dict) -> list[dict]:
    """Panels with the archetype's defaults filled in: the hub is marked, a layer lays its cards out in one row."""
    lay, kind, out = spec["layout"], spec["archetype"], []
    for p in spec["panels"]:
        p = dict(p)
        if kind == "hub-and-spokes" and p["id"] == lay["hub"]:
            p["hub"] = True
        if any(p["id"] in ids for ids in body_groups(spec).values()):
            p["nested"] = True  # placed by its spoke row's grid, not by a body grid area
        if kind == "layer-cake" and p["id"] in lay["layers"] and p.get("cards") and not p.get("card_columns"):
            p["card_columns"] = len(p["cards"])
        out.append(p)
    return out


def build_html(spec: dict) -> str:
    loc = load_locale(spec["canvas"]["lang"])
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["j2", "html"]))
    css = font_css() + "\n" + (ROOT / "templates" / "tokens.css").read_text(encoding="utf-8") + "\n" + \
          (ROOT / "templates" / "components.css").read_text(encoding="utf-8")
    canvas = spec["canvas"]
    badge = loc["badge"].format(part=canvas["part"], of=canvas["of"]) if canvas.get("part") and canvas.get("of") else None
    footer = spec.get("footer") or {}
    fcols = footer.get("columns") or [FOOTER_WEIGHTS[name] for name in footer_panels(spec)]
    return env.get_template("plate.html.j2").render(
        spec=spec, panels=panels_for_render(spec), groups=body_groups(spec), gutter_x=GUTTER_X, lang=canvas["lang"], L=loc, css=css, width=width, height=height, badge=badge,
        grid=grid_css(spec), footer=footer, footer_columns=" ".join(f"minmax(0, {w}fr)" for w in fcols),
        legend=legend_entries(spec, loc), open_questions=open_questions(spec),
        icons=icon_markup, tree_rows=tree_rows, matrix_values=matrix_values)


# ---------------------------------------------------------------- browser

def open_plate(browser, html: str, spec: dict, scale: float = 1):
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.set_content(html)
    page.evaluate(FONTS_READY_JS)
    return page


# Load every declared face before measuring, not only the ones layout has asked for so far.
FONTS_READY_JS = "Promise.all([...document.fonts].map(f => f.load())).then(() => document.fonts.ready).then(() => true)"


FLOWS_JS = r"""
(flows) => {
  // Orthogonal connector router. Endpoints are panels or cards; every route is checked against the measured boxes,
  // so the spec never names a coordinate. Candidates: straight across a gutter, L (one bend), Z through a gutter
  // channel (two bends). The cheapest clear one wins: length + a fixed price per bend + distance off-centre.
  const plate = document.getElementById('plate'), P = plate.getBoundingClientRect();
  const rel = el => { const r = el.getBoundingClientRect(); return {l: r.left - P.left, t: r.top - P.top, r: r.right - P.left, b: r.bottom - P.top}; };
  const byId = id => document.querySelector(`[data-id="${CSS.escape(id)}"]`);
  const css = getComputedStyle(document.documentElement);
  const col = css.getPropertyValue('--arrow').trim(), muted = css.getPropertyValue('--muted').trim();
  const font = css.getPropertyValue('--font').trim().replace(/"/g, "'");
  const r2 = v => Math.round(v * 100) / 100, mid = (a, b) => (a + b) / 2;
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  // PAD: gap between arrow and box. CLEAR: free space kept around every segment. HEAD/WING: arrowhead size.
  const PAD = 7, MIN_OVERLAP = 24, CLEAR = 6, BEND = 60, RADIUS = 8, HEAD = 10, WING = 6, MIN_RUN = 16, LANE = 10;

  // Boxes an arrow must not cross; panel headers count, so a card's arrow never runs through its own title.
  const solids = [...plate.querySelectorAll('[data-kind="panel"], [data-kind="card"], [data-kind="pattern"], [data-kind="chip"], .ph')]
    .map(el => ({el, box: rel(el)}));
  // Channels: the centre line of every gutter between two body panels, plus a lane on either side of it.
  const bodyPanels = [...document.querySelectorAll('#body [data-kind="panel"]')].map(rel);
  const chX = new Map(), chY = new Map();
  for (const a of bodyPanels) for (const b of bodyPanels) {
    if (b.l > a.r && b.l - a.r < 100) { const c = mid(a.r, b.l); [0, -LANE, LANE].forEach(o => chX.set(r2(c + o), Math.abs(o))); }
    if (b.t > a.b && b.t - a.b < 100) { const c = mid(a.b, b.t); [0, -LANE, LANE].forEach(o => chY.set(r2(c + o), Math.abs(o))); }
  }

  const hits = (a, b) => Math.min(a.r, b.r) - Math.max(a.l, b.l) > 0 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 0;
  const segBox = (p, q, m) => ({l: Math.min(p[0], q[0]) - m, r: Math.max(p[0], q[0]) + m, t: Math.min(p[1], q[1]) - m, b: Math.max(p[1], q[1]) + m});
  const span = (a, b, c, d) => Math.min(Math.max(a, b), Math.max(c, d)) - Math.max(Math.min(a, b), Math.min(c, d));
  const collinear = (p, q, u, v) => {  // two parallel segments running on top of each other
    const ph = p[1] === q[1], uh = u[1] === v[1];
    if (ph !== uh) return false;
    return ph ? Math.abs(p[1] - u[1]) < LANE - 2 && span(p[0], q[0], u[0], v[0]) > 0
              : Math.abs(p[0] - u[0]) < LANE - 2 && span(p[1], q[1], u[1], v[1]) > 0;
  };
  const placed = [];
  const clear = (pts, obstacles, both) => {
    const n = pts.length - 1;
    for (let k = 0; k < n; k++) {
      const p = pts[k], q = pts[k + 1], len = Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]);
      if (len < (k === n - 1 || (both && k === 0) ? HEAD + 6 : k === 0 ? 8 : MIN_RUN)) return false;
      const sb = segBox(p, q, CLEAR);
      if (sb.l < 0 || sb.t < 0 || sb.r > P.width || sb.b > P.height) return false;
      if (obstacles.some(o => hits(sb, o))) return false;
      if (placed.some(r => r.pts.some((u, j) => j < r.pts.length - 1 && collinear(p, q, u, r.pts[j + 1])))) return false;
    }
    return true;
  };

  const candidates = (a, b) => {
    const out = [], add = (pts, off) => out.push({pts, off});
    const cx = o => mid(o.l, o.r), cy = o => mid(o.t, o.b);
    // Points on a side: the centre, then the point nearest the other box.
    const pick = (lo, hi, toward) => { const m = mid(lo, hi), n = Math.min(Math.max(toward, lo + 16), hi - 16);
      return hi - lo < 32 || Math.abs(n - m) < 1 ? [[m, 0]] : [[m, 0], [n, Math.abs(n - m)]]; };
    // Straight: across the gap between facing sides, centred on the shared span, then a quarter off-centre.
    const oy = [Math.max(a.t, b.t), Math.min(a.b, b.b)], ox = [Math.max(a.l, b.l), Math.min(a.r, b.r)];
    const along = (lo, hi) => [0, -1, 1].map(s => [mid(lo, hi) + s * (hi - lo) / 4, (hi - lo) / 4 * Math.abs(s)]);
    if (oy[1] - oy[0] > MIN_OVERLAP) for (const [y, off] of along(...oy)) {
      if (a.r <= b.l) add([[a.r + PAD, y], [b.l - PAD, y]], off);
      else if (b.r <= a.l) add([[a.l - PAD, y], [b.r + PAD, y]], off);
    }
    if (ox[1] - ox[0] > MIN_OVERLAP) for (const [x, off] of along(...ox)) {
      if (a.b <= b.t) add([[x, a.b + PAD], [x, b.t - PAD]], off);
      else if (b.b <= a.t) add([[x, a.t - PAD], [x, b.b + PAD]], off);
    }
    // L: leave A vertically, enter B from the side; or leave A sideways, enter B from top or bottom.
    for (const [x, o1] of pick(a.l, a.r, cx(b))) for (const [y, o2] of pick(b.t, b.b, cy(a))) {
      if (x < b.l || x > b.r) {
        const ex = x < b.l ? b.l - PAD : b.r + PAD;
        if (y > a.b) add([[x, a.b + PAD], [x, y], [ex, y]], o1 + o2);
        if (y < a.t) add([[x, a.t - PAD], [x, y], [ex, y]], o1 + o2);
      }
    }
    for (const [y, o1] of pick(a.t, a.b, cy(b))) for (const [x, o2] of pick(b.l, b.r, cx(a))) {
      if (y < b.t || y > b.b) {
        const ey = y < b.t ? b.t - PAD : b.b + PAD;
        if (x > a.r) add([[a.r + PAD, y], [x, y], [x, ey]], o1 + o2);
        if (x < a.l) add([[a.l - PAD, y], [x, y], [x, ey]], o1 + o2);
      }
    }
    // Z: sideways out of A, along a vertical channel, sideways into B (and the same turned a quarter).
    for (const [c, oc] of chX) for (const [y1, o1] of pick(a.t, a.b, cy(b))) for (const [y2, o2] of pick(b.t, b.b, cy(a))) {
      if (Math.abs(y1 - y2) < 1) continue;
      if (a.r < c && c < b.l) add([[a.r + PAD, y1], [c, y1], [c, y2], [b.l - PAD, y2]], oc + o1 + o2);
      if (b.r < c && c < a.l) add([[a.l - PAD, y1], [c, y1], [c, y2], [b.r + PAD, y2]], oc + o1 + o2);
    }
    for (const [c, oc] of chY) for (const [x1, o1] of pick(a.l, a.r, cx(b))) for (const [x2, o2] of pick(b.l, b.r, cx(a))) {
      if (Math.abs(x1 - x2) < 1) continue;
      if (a.b < c && c < b.t) add([[x1, a.b + PAD], [x1, c], [x2, c], [x2, b.t - PAD]], oc + o1 + o2);
      if (b.b < c && c < a.t) add([[x1, a.t - PAD], [x1, c], [x2, c], [x2, b.b + PAD]], oc + o1 + o2);
    }
    const cost = c => c.pts.reduce((s, p, k) => k ? s + Math.abs(p[0] - c.pts[k - 1][0]) + Math.abs(p[1] - c.pts[k - 1][1]) : s, 0)
                      + BEND * (c.pts.length - 2) + c.off * 0.5;
    return out.map(c => ({...c, cost: cost(c)})).sort((p, q) => p.cost - q.cost);
  };

  const problems = [], routed = [];
  const jobs = flows.map((fl, i) => {
    const A = byId(fl.from), B = byId(fl.to);
    if (!A || !B) { problems.push({i, kind: 'endpoint', problem: 'endpoint not found'}); return null; }
    if (A === B) { problems.push({i, kind: 'self', problem: 'from and to are the same element'}); return null; }
    if (A.contains(B) || B.contains(A)) { problems.push({i, kind: 'nested', problem: 'connects a card to its own panel; connect it to another box'}); return null; }
    const obstacles = solids.filter(s => !(s.el === A || s.el === B || s.el.contains(A) || s.el.contains(B) || A.contains(s.el) || B.contains(s.el))).map(s => s.box);
    return {i, fl, A, B, obstacles, cands: candidates(rel(A), rel(B))};
  }).filter(Boolean);
  // Straight flows claim their gutters first; bent ones route around them.
  jobs.sort((p, q) => ((p.cands[0] || {pts: []}).pts.length === 2 ? 0 : 1) - ((q.cands[0] || {pts: []}).pts.length === 2 ? 0 : 1) || p.i - q.i);
  for (const j of jobs) {
    const pick = j.cands.find(c => clear(c.pts, j.obstacles, j.fl.both));
    if (!pick) { problems.push({i: j.i, kind: 'route', problem: 'no clear route between the two boxes; connect their panels instead, or move one so they share a gutter'}); continue; }
    const r = {...j, pts: pick.pts};
    placed.push(r); routed.push(r);
  }

  // Draw: straight arrows as a line, bent ones as a path with rounded corners; heads are filled triangles.
  const head = (tip, from) => {
    const len = Math.hypot(tip[0] - from[0], tip[1] - from[1]), dx = (tip[0] - from[0]) / len, dy = (tip[1] - from[1]) / len;
    const bx = tip[0] - dx * HEAD, by = tip[1] - dy * HEAD;
    return {base: [bx, by], svg: `<path d="M${r2(tip[0])} ${r2(tip[1])}L${r2(bx - dy * WING)} ${r2(by + dx * WING)}L${r2(bx + dy * WING)} ${r2(by - dx * WING)}Z" fill="${col}"/>`};
  };
  const rounded = pts => {
    let d = `M${r2(pts[0][0])} ${r2(pts[0][1])}`;
    for (let k = 1; k < pts.length - 1; k++) {
      const [p, c, n] = [pts[k - 1], pts[k], pts[k + 1]];
      const lin = Math.hypot(c[0] - p[0], c[1] - p[1]), lout = Math.hypot(n[0] - c[0], n[1] - c[1]);
      const rad = Math.min(RADIUS, lin / 2, lout / 2);
      const a = [c[0] - (c[0] - p[0]) / lin * rad, c[1] - (c[1] - p[1]) / lin * rad], b = [c[0] + (n[0] - c[0]) / lout * rad, c[1] + (n[1] - c[1]) / lout * rad];
      d += `L${r2(a[0])} ${r2(a[1])}Q${r2(c[0])} ${r2(c[1])} ${r2(b[0])} ${r2(b[1])}`;
    }
    const e = pts[pts.length - 1];
    return d + `L${r2(e[0])} ${r2(e[1])}`;
  };
  const art = {};
  for (const r of routed) {
    const pts = r.pts.map(p => [...p]), n = pts.length - 1;
    const end = head(pts[n], pts[n - 1]); pts[n] = end.base;
    let heads = end.svg;
    if (r.fl.both) { const start = head(pts[0], pts[1]); pts[0] = start.base; heads = start.svg + heads; }
    art[r.i] = (pts.length === 2
      ? `<line x1="${r2(pts[0][0])}" y1="${r2(pts[0][1])}" x2="${r2(pts[1][0])}" y2="${r2(pts[1][1])}" stroke="${col}" stroke-width="2.5" stroke-linecap="round"/>`
      : `<path d="${rounded(pts)}" fill="none" stroke="${col}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`) + heads;
  }

  const ov = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  ov.setAttribute('data-raw-svg', ''); ov.setAttribute('width', P.width); ov.setAttribute('height', P.height);
  ov.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none;overflow:visible';
  plate.appendChild(ov);

  // Labels: beside a vertical run or above/below a horizontal one, on the longest run first, clear of every box,
  // every arrow and every other label.
  const labelBoxes = [], allBoxes = solids.map(s => s.box);
  const measure = text => {
    ov.innerHTML = `<text x="0" y="0" font-family="${font}" font-size="11.5" font-weight="500">${esc(text)}</text>`;
    const r = ov.firstChild.getBoundingClientRect(); ov.innerHTML = '';
    return {w: r.width, asc: P.top - r.top, desc: r.bottom - P.top};
  };
  for (const r of routed) {
    if (!r.fl.label) continue;
    const {w, asc, desc} = measure(r.fl.label);
    const runs = r.pts.slice(1).map((q, k) => [r.pts[k], q]).sort((s, t) =>
      (Math.abs(t[1][0] - t[0][0]) + Math.abs(t[1][1] - t[0][1])) - (Math.abs(s[1][0] - s[0][0]) + Math.abs(s[1][1] - s[0][1])));
    const spots = [];
    for (const [p, q] of runs) {
      if (p[0] === q[0]) { const y = mid(p[1], q[1]) + 4;
        if (Math.abs(q[1] - p[1]) > asc + desc + 8) spots.push([p[0] + 9, y], [p[0] - 9 - w, y]); }
      else if (Math.abs(q[0] - p[0]) > w + 20) { const x = mid(p[0], q[0]) - w / 2;
        spots.push([x, p[1] - 6 - desc], [x, p[1] + 6 + asc]); }
    }
    const spot = spots.find(([x, y]) => {
      const b = {l: x - 3, r: x + w + 3, t: y - asc - 3, b: y + desc + 3};
      return b.l > 0 && b.t > 0 && b.r < P.width && b.b < P.height && !allBoxes.some(o => hits(b, o)) && !labelBoxes.some(o => hits(b, o))
        && !placed.some(o => o.pts.some((u, j) => j < o.pts.length - 1 && hits(b, segBox(u, o.pts[j + 1], 1.5))));
    });
    if (!spot) { problems.push({i: r.i, kind: 'label', problem: `no room for the label "${r.fl.label}"; shorten it or drop it`}); continue; }
    labelBoxes.push({l: spot[0], r: spot[0] + w, t: spot[1] - asc, b: spot[1] + desc});
    art[r.i] += `<text data-label="${r.i}" x="${r2(spot[0])}" y="${r2(spot[1])}" font-family="${font}" font-size="11.5" font-weight="500" fill="${muted}">${esc(r.fl.label)}</text>`;
    r.label = {x: spot[0], y: spot[1], text: r.fl.label};
  }

  ov.innerHTML = Object.keys(art).sort((p, q) => p - q).map(k => art[k]).join('');
  const panelOf = el => el.closest('[data-kind="panel"]').dataset.id;
  const segs = routed.sort((p, q) => p.i - q.i).map(r => {
    const s = {i: r.i, from: r.fl.from, to: r.fl.to, fromPanel: panelOf(r.A), toPanel: panelOf(r.B), points: r.pts, label: r.label || null};
    if (s.label) s.label.box = rel(ov.querySelector(`[data-label="${r.i}"]`));
    return s;
  });
  return {segs, problems};
}
"""


# Router problem kinds and the lint check each one belongs to.
FLOW_CHECKS = {"route": "arrow-routing", "label": "arrow-label", "endpoint": "flow", "self": "flow", "nested": "flow"}


def draw_flows(page, spec: dict) -> dict:
    out = page.evaluate(FLOWS_JS, spec.get("flows", []))
    for x in out["problems"]:
        x["check"] = FLOW_CHECKS[x["kind"]]
    return out


EXPORT_JS = r"""
() => {
  const plate = document.getElementById('plate'), P = plate.getBoundingClientRect();
  const out = [], used = {};
  const use = (family, weight, s) => { const k = family.split(',')[0].replace(/["']/g, '').trim() + '|' + weight; used[k] = (used[k] || '') + s; };
  const num = v => parseFloat(v) || 0, f = v => Math.round(v * 100) / 100;
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const parse = c => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); const a = p.length > 3 ? p[3] : 1;
    if (a === 0) return null; return ['#' + p.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join(''), a]; };
  const paint = (c, key) => { const pc = parse(c); if (!pc) return null;
    return pc[1] < 1 ? `${key}="${pc[0]}" ${key}-opacity="${f(pc[1])}"` : `${key}="${pc[0]}"`; };
  const rr = (x, y, w, h, r) => { const [tl, tr, br, bl] = r.map(v => Math.max(0, Math.min(v, w / 2, h / 2)));
    return `M${f(x + tl)} ${f(y)}H${f(x + w - tr)}` + (tr ? `A${f(tr)} ${f(tr)} 0 0 1 ${f(x + w)} ${f(y + tr)}` : '') +
      `V${f(y + h - br)}` + (br ? `A${f(br)} ${f(br)} 0 0 1 ${f(x + w - br)} ${f(y + h)}` : '') +
      `H${f(x + bl)}` + (bl ? `A${f(bl)} ${f(bl)} 0 0 1 ${f(x)} ${f(y + h - bl)}` : '') +
      `V${f(y + tl)}` + (tl ? `A${f(tl)} ${f(tl)} 0 0 1 ${f(x + tl)} ${f(y)}` : '') + 'Z'; };
  // Measured at the real size: Chromium rounds ascent per size, so a 100 px probe scaled down drifts by up to a pixel.
  const offsets = {};
  const baseline = cs => { const key = cs.fontFamily + '|' + cs.fontWeight + '|' + cs.fontSize; if (key in offsets) return offsets[key];
    const probe = document.createElement('div');
    probe.style.cssText = `position:absolute;left:-9999px;top:0;font-family:${cs.fontFamily};font-weight:${cs.fontWeight};font-size:${cs.fontSize};line-height:normal;white-space:nowrap`;
    probe.innerHTML = 'H<span style="display:inline-block;width:1px;height:0;vertical-align:baseline"></span>';
    document.body.appendChild(probe);
    const rg = document.createRange(); rg.setStart(probe.firstChild, 0); rg.setEnd(probe.firstChild, 1);
    const top = rg.getClientRects()[0].top, base = probe.lastChild.getBoundingClientRect().bottom;
    probe.remove(); return offsets[key] = base - top; };

  const box = (el, cs) => {
    const r = el.getBoundingClientRect(); const x = r.left - P.left, y = r.top - P.top, w = r.width, h = r.height;
    if (w < 0.5 || h < 0.5) return;
    const sides = ['Top', 'Right', 'Bottom', 'Left'];
    const bw = sides.map(s => cs[`border${s}Style`] === 'none' ? 0 : num(cs[`border${s}Width`]));
    const bc = sides.map(s => cs[`border${s}Color`]);
    const rad = ['TopLeft', 'TopRight', 'BottomRight', 'BottomLeft'].map(s => num(cs[`border${s}Radius`]));
    const fill = paint(cs.backgroundColor, 'fill');
    const id = el.dataset && el.dataset.id ? ` data-id="${esc(el.dataset.id)}"` : '';
    const sameR = rad.every(v => v === rad[0]);
    const uniform = bw[0] > 0 && bw.every(v => v === bw[0]) && bc.every(c => c === bc[0]);
    if (uniform) {
      const s = bw[0], st = paint(bc[0], 'stroke'); if (!st && !fill) return;
      const ix = x + s / 2, iy = y + s / 2, iw = w - s, ih = h - s, ir = rad.map(v => Math.max(0, v - s / 2));
      const pa = `${fill || 'fill="none"'} ${st || ''} stroke-width="${f(s)}"`;
      out.push(sameR ? `<rect${id} x="${f(ix)}" y="${f(iy)}" width="${f(iw)}" height="${f(ih)}"${ir[0] ? ` rx="${f(ir[0])}"` : ''} ${pa}/>`
                     : `<path${id} d="${rr(ix, iy, iw, ih, ir)}" ${pa}/>`);
      return;
    }
    if (fill) out.push(sameR ? `<rect${id} x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}"${rad[0] ? ` rx="${f(rad[0])}"` : ''} ${fill}/>`
                             : `<path${id} d="${rr(x, y, w, h, rad)}" ${fill}/>`);
    const L = [[x, y + bw[0] / 2, x + w, y + bw[0] / 2], [x + w - bw[1] / 2, y, x + w - bw[1] / 2, y + h],
               [x, y + h - bw[2] / 2, x + w, y + h - bw[2] / 2], [x + bw[3] / 2, y, x + bw[3] / 2, y + h]];
    L.forEach((l, i) => { if (bw[i] > 0) { const st = paint(bc[i], 'stroke'); if (st)
      out.push(`<line x1="${f(l[0])}" y1="${f(l[1])}" x2="${f(l[2])}" y2="${f(l[3])}" ${st} stroke-width="${f(bw[i])}"/>`); } });
  };

  const text = node => {
    const el = node.parentElement, cs = getComputedStyle(el), s = node.textContent;
    if (!s.trim() || cs.visibility === 'hidden') return;
    const fs = num(cs.fontSize), ascent = baseline(cs), pre = cs.whiteSpace.startsWith('pre');
    use(cs.fontFamily, cs.fontWeight, s);
    const attrs = `font-family="${esc(cs.fontFamily.replace(/"/g, "'"))}" font-size="${f(fs)}" font-weight="${cs.fontWeight}" ${paint(cs.color, 'fill')}${pre ? ' xml:space="preserve"' : ''}`;
    const lines = []; let cur = null; const rg = document.createRange();
    for (let i = 0; i < s.length; i++) {
      rg.setStart(node, i); rg.setEnd(node, i + 1);
      const rects = rg.getClientRects(); if (!rects.length) continue; const q = rects[0];
      if (!cur || Math.abs(q.top - cur.top) > fs * 0.5) { cur = {top: q.top, left: null, t: ''}; lines.push(cur); }
      if (cur.left === null) { if (!pre && s[i].trim() === '') continue; cur.left = q.left; }
      cur.t += s[i];
    }
    for (const l of lines) {
      let t = pre ? l.t.replace(/\s+$/, '') : l.t.replace(/\s+/g, ' ').trim();
      if (!t || l.left === null) continue;
      out.push(`<text x="${f(l.left - P.left)}" y="${f(l.top - P.top + ascent)}" ${attrs}>${esc(t)}</text>`);
    }
  };

  const icon = (el, cs) => {
    const r = el.getBoundingClientRect(), c = parse(cs.color);
    out.push(`<g transform="translate(${f(r.left - P.left)} ${f(r.top - P.top)}) scale(${(r.width / 24).toFixed(4)})" fill="none" stroke="${c ? c[0] : '#000'}" stroke-width="${el.getAttribute('stroke-width') || 1.75}" stroke-linecap="round" stroke-linejoin="round">${el.innerHTML}</g>`);
  };

  const walk = node => {
    if (node.nodeType === 3) { text(node); return; }
    if (node.nodeType !== 1) return;
    const cs = getComputedStyle(node);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    if (node.hasAttribute('data-raw-svg')) { out.push(node.innerHTML);
      for (const t of node.querySelectorAll('text')) use(t.getAttribute('font-family'), t.getAttribute('font-weight') || '400', t.textContent);
      return; }
    if (node.hasAttribute('data-icon')) { icon(node, cs); return; }
    box(node, cs);
    for (const c of node.childNodes) walk(c);
  };
  walk(plate);
  return {w: f(P.width), h: f(P.height), items: out, used};
}
"""


def export_svg(page, spec: dict) -> tuple[str, list[str]]:
    d = page.evaluate(EXPORT_JS)
    title = spec["title"] + (f" — {spec['subtitle']}" if spec.get("subtitle") else "")
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{d["w"]:g}" height="{d["h"]:g}" '
            f'viewBox="0 0 {d["w"]:g} {d["h"]:g}" role="img" lang="{spec["canvas"]["lang"]}">\n'
            f'<title>{esc(title)}</title>\n'
            f'<defs><style>\n{subset_font_css(d["used"])}\n</style></defs>\n')
    fonts = sorted(k.replace("|", " ") for k in d["used"])
    return head + "\n".join(d["items"]) + "\n</svg>\n", fonts


SNAPSHOT_JS = r"""
() => {
  const P = document.getElementById('plate').getBoundingClientRect(), r2 = v => Math.round(v / 2) * 2, out = {};
  for (const el of document.querySelectorAll('#plate [data-id]')) {
    const r = el.getBoundingClientRect();
    out[el.dataset.id] = [r.left - P.left, r.top - P.top, r.right - P.left, r.bottom - P.top].map(r2);
  }
  return out;
}
"""


def snapshot(page, svg: str, segs: list[dict]) -> dict:
    """What a plate is made of, rounded to 2 px: every element box by data-id, every text line of the SVG with
    its position, every connector's points. OS-independent, and a diff names what changed."""
    r2 = lambda v: int(round(float(v) / 2) * 2)
    unescape = lambda t: t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")
    text = [[r2(x), r2(y), unescape(t)] for x, y, t in re.findall(r'<text[^>]*?\bx="([-\d.]+)" y="([-\d.]+)"[^>]*>(.*?)</text>', svg)]
    flows = [{"i": f["i"], "from": f["from"], "to": f["to"], "points": [[r2(x), r2(y)] for x, y in f["points"]],
              "label": (f.get("label") or {}).get("text")} for f in segs]
    return {"boxes": page.evaluate(SNAPSHOT_JS), "text": text, "flows": flows}


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
    a = Image.open(a_path).convert("L").filter(ImageFilter.GaussianBlur(PARITY_BLUR_PX))
    b = Image.open(b_path).convert("L").filter(ImageFilter.GaussianBlur(PARITY_BLUR_PX))
    if a.size != b.size:
        return {"count": None, "fail": True, "regions": [], "detail": f"size differs: {a.size} vs {b.size}"}
    mask = ImageChops.difference(a, b).point(lambda v: 255 if v > PARITY_DELTA else 0)
    mask.save(mask_path)
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
    if failing:
        detail += f"; {len(failing)} region(s) over the limit, first at {failing[0]}"
    return {"count": len(on), "fail": bool(failing), "regions": failing, "detail": detail}


def rasterise_svg(browser, svg_path: Path, spec: dict, png_path: Path, scale: float = 2) -> None:
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.goto(svg_path.resolve().as_uri())
    page.evaluate(FONTS_READY_JS)
    page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": width, "height": height})
    page.close()
