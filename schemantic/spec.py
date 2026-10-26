"""Load a spec and check it without a browser: the schema, then what the schema cannot express."""
from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

import jsonschema
import yaml

from . import archetypes
from .config import ICONS, ROOT

# Default footer widths per panel, relative to each other; only the panels present get a track.
FOOTER_WEIGHTS = {"context": 1.5, "principles": 1.4, "open_questions": 1.1, "legend": 0.9}


def finding(check: str, id_: str, detail: str, level: str = "error") -> dict:
    return {"level": level, "check": check, "id": id_, "detail": detail}


def load_spec(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def read_spec(path: str | Path) -> tuple[dict | None, list[dict]]:
    """Load a spec for the CLI: a missing file, broken YAML or a document that is not a mapping becomes a
    `yaml` finding instead of a traceback."""
    def err(detail):
        return None, [finding("yaml", "(file)", detail)]
    try:
        spec = load_spec(path)
    except FileNotFoundError:
        return err(f"no such file: {path}")
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        return err(f"not valid YAML{where}: {getattr(e, 'problem', None) or e}")
    if not isinstance(spec, dict):
        held = type(spec).__name__ if spec is not None else "nothing"
        return err(f"the file holds {held}, not a spec (a mapping of canvas, title, …)")
    return spec, []


def internal_error(exc: Exception) -> dict:
    return finding("internal", "(plate)",
                   f"{type(exc).__name__}: {exc}. This is a Schemantic bug, not a spec problem; report it with the spec.")


@cache
def load_locale(lang: str) -> dict:
    with open(ROOT / "locales" / f"{lang}.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@cache
def schema() -> dict:
    return json.loads((ROOT / "schema" / "plate.schema.json").read_text(encoding="utf-8"))


def schema_errors(spec: dict) -> list[dict]:
    validator = jsonschema.Draft202012Validator(schema())
    out = []
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        out.append(finding("schema", where, err.message))
    return out


def id_errors(spec: dict) -> list[dict]:
    """Panel ids are unique; an explicit card id is unique across the plate and never equals a panel id or a
    card's automatic id (<panel>.card<n>). Each collision is reported once, naming both places."""
    out = []
    panels: dict[str, int] = {}
    for i, p in enumerate(spec["panels"]):
        if p["id"] in panels:
            out.append(finding("id", p["id"], f"panels/{panels[p['id']]} and panels/{i} both use id '{p['id']}'"))
        else:
            panels[p["id"]] = i
    auto = {f"{p['id']}.card{i}" for p in spec["panels"] for i in range(len(p.get("cards", [])))}
    context = ((spec.get("footer") or {}).get("context") or {}).get("cards", [])
    places = [(f"panels/{pi}/cards/{ci}", c) for pi, p in enumerate(spec["panels"]) for ci, c in enumerate(p.get("cards", []))]
    places += [(f"footer/context/cards/{ci}", c) for ci, c in enumerate(context)]
    seen: dict[str, str] = {}
    for where, c in places:
        cid = c.get("id")
        if not cid:
            continue
        if cid in panels:
            out.append(finding("id", cid, f"{where} uses '{cid}', which is already the id of panels/{panels[cid]}"))
        elif cid in auto:
            out.append(finding("id", cid, f"{where} uses '{cid}', which is the automatic id of another card"))
        elif cid in seen:
            out.append(finding("id", cid, f"{seen[cid]} and {where} both use id '{cid}'"))
        else:
            seen[cid] = where
    return out


def layout_errors(spec: dict, arche: archetypes.Archetype) -> list[dict]:
    """Shared placement checks on the archetype's grid: every panel placed once, areas are rectangles."""
    out = []
    ids = arche.placed(spec)
    for n in sorted({n for n in ids if ids.count(n) > 1}):
        out.append(finding("layout", n, "panel is placed more than once in layout"))
    out += arche.validate(spec)
    if out:
        return out
    grid = arche.grid(spec)
    names = {n for r in grid.rows for n in r if n != "."}
    placed = (names - set(grid.groups)) | {n for members in grid.groups.values() for n in members}
    panel_ids = {p["id"] for p in spec["panels"]}
    for n in sorted(placed - panel_ids):
        out.append(finding("layout", "layout", f"'{n}' is placed in the layout but has no panel"))
    for n in sorted(panel_ids - placed):
        out.append(finding("layout", n, "panel is not placed in the layout"))
    for n in sorted(names):
        cells = [(r, c) for r, row in enumerate(grid.rows) for c, v in enumerate(row) if v == n]
        r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
        c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
        if len(cells) != (r1 - r0 + 1) * (c1 - c0 + 1):
            out.append(finding("layout", n, "area is not a rectangle"))
    rh = spec["layout"].get("row_heights")
    if rh and len(rh) != len(grid.rows):
        out.append(finding("layout", "layout.row_heights", f"{len(rh)} heights for {len(grid.rows)} rows"))
    return out


def semantic_errors(spec: dict) -> list[dict]:
    """Checks the schema cannot express: archetype, ids, placement, flows, footer, chips, icons, language."""
    arche = archetypes.get(spec["archetype"])
    if not arche:
        return [finding("archetype", "archetype",
                        f"'{spec['archetype']}' is not built yet; use one of {', '.join(archetypes.BUILT)}")]
    # Ids first: a colliding id makes every later check (and the router) look in the wrong place.
    out = id_errors(spec) or layout_errors(spec, arche)
    if out:
        return out

    for p in spec["panels"]:
        if p.get("weights"):
            blocks = len(p.get("patterns", [])) + (1 if p.get("cards") else 0)
            if p.get("arrange") != "row":
                out.append(finding("layout", p["id"], "weights only apply when arrange is row"))
            elif len(p["weights"]) != blocks:
                out.append(finding("layout", p["id"], f"{len(p['weights'])} weights for {blocks} blocks (patterns first, then cards)"))

    known = {p["id"] for p in spec["panels"]}
    for p in spec["panels"]:
        known |= {c.get("id") or f"{p['id']}.card{i}" for i, c in enumerate(p.get("cards", []))}
        for pt in p.get("patterns", []):
            if pt["type"] == "matrix":
                for r in pt["rows"]:
                    if len(r["cells"]) != len(pt["columns"]):
                        out.append(finding("pattern", p["id"],
                                           f"matrix row '{r['name']}' has {len(r['cells'])} cells for {len(pt['columns'])} columns"))
    for i, f in enumerate(spec.get("flows", [])):
        for end in ("from", "to"):
            if f[end] not in known:
                out.append(finding("flow", f"flows/{i}", f"endpoint '{f[end]}' does not exist"))
        if f["from"] == f["to"]:
            out.append(finding("flow", f"flows/{i}", f"from and to are the same element ('{f['from']}')"))

    canvas = spec["canvas"]
    if ("part" in canvas) != ("of" in canvas):
        missing = "canvas.part" if "part" not in canvas else "canvas.of"
        out.append(finding("canvas", missing, "give both part and of, or neither; the badge needs both"))
    elif "part" in canvas and canvas["part"] > canvas["of"]:
        out.append(finding("canvas", "canvas.part", f"part {canvas['part']} of {canvas['of']}; part cannot be larger than of"))
    fcols = (spec.get("footer") or {}).get("columns")
    present = footer_panels(spec)
    if fcols and len(fcols) != len(present):
        out.append(finding("layout", "footer.columns", f"{len(fcols)} widths for {len(present)} footer panels ({', '.join(present)})"))
    oq = (spec.get("footer") or {}).get("open_questions") or {}
    chips = [ch["text"] for p in spec["panels"] for ch in p.get("chips", []) if ch["kind"] == "warning"]
    if chips and not oq.get("from_chips"):
        for c in (c for c in chips if c not in oq.get("extra", [])):
            out.append(finding("chip-mirror", "footer.open_questions", f"warning chip not repeated in open questions: '{c}'"))

    for icon in iter_icons(spec):
        if not (ICONS / f"{icon}.svg").exists():
            out.append(finding("icon", icon, "icon not in assets/icons; pick one from the registry"))

    loc = load_locale(spec["canvas"]["lang"])
    text = "\n".join(iter_strings(spec)).lower()
    for term, bad in (loc.get("never_translate") or {}).items():
        for b in bad:
            # Substring, not whole word: Dutch compounds hide the term ("productcatalogus").
            if re.search(re.escape(b.lower()), text):
                out.append(finding("language", term, f"'{b}' found; keep the technical term '{term}' in English"))
    return out


def check(spec: dict) -> list[dict]:
    """Schema first; semantic checks only on a spec that has the right shape."""
    return schema_errors(spec) or semantic_errors(spec)


def open_questions(spec: dict) -> list[str]:
    oq = (spec.get("footer") or {}).get("open_questions") or {}
    out = []
    if oq.get("from_chips"):
        out += [ch["text"] for p in spec["panels"] for ch in p.get("chips", []) if ch["kind"] == "warning"]
    out += [q for q in oq.get("extra", []) if q not in out]
    return out


def footer_panels(spec: dict) -> list[str]:
    """The footer panels the template renders, in order; the legend is always there."""
    footer = spec.get("footer") or {}
    present = [("context", bool(footer.get("context"))), ("principles", bool(footer.get("principles"))),
               ("open_questions", bool(open_questions(spec))), ("legend", True)]
    return [name for name, on in present if on]


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
