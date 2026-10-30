"""Load a spec and check it without a browser: the schema, then what the schema cannot express."""
from __future__ import annotations

import json
import re
from functools import cache
from itertools import pairwise
from pathlib import Path

import jsonschema
import yaml

from . import archetypes, icons, roles
from .config import LOCALES, SCHEMA
from .findings import finding

# Default footer widths per column, by its first section, relative to each other.
FOOTER_WEIGHTS = {"context": 1.5, "principles": 1.4, "open_questions": 1.1, "notes": 1.1, "legend": 0.9}
# With more footer columns than this (the legend strip not counted), open questions or notes of at most
# FOOTER_STACK_MAX items stack under another column instead of taking one of their own.
FOOTER_MAX_COLUMNS = 3
FOOTER_STACK_MAX = 2
# What a starter spec marks for the author to fill in.
PLACEHOLDER = re.compile(r"\bTODO\b")


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
    with open(LOCALES / f"{lang}.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@cache
def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


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
    names = {n for r in grid.rows for n in r if n != "."} - set(grid.bands)
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
    return out


def semantic_errors(spec: dict, theme_css: str = "") -> list[dict]:
    """Checks the schema cannot express: ids, placement, roles, flows, footer, chips, icons, language."""
    arche = archetypes.REGISTRY[spec["archetype"]]  # the schema names only built archetypes
    # Ids first: a colliding id makes every later check (and the router) look in the wrong place.
    out = id_errors(spec) or layout_errors(spec, arche)
    if any(f["level"] == "error" for f in out):
        return out
    out += roles.role_findings(spec, theme_css) + roles.role_fit_findings(spec) + slide_findings(spec)

    for i, p in enumerate(spec["panels"]):
        if len(p.get("cards", [])) > arche.max_cards:
            out.append(finding("schema", f"panels/{i}/cards", f"{len(p['cards'])} cards; a panel holds {arche.max_cards}: "
                               "split it, or the plate"))
        if p.get("weights"):
            blocks = len(p.get("patterns", [])) + (1 if p.get("cards") else 0)
            if p.get("arrange") != "row":
                out.append(finding("layout", p["id"], "weights only apply when arrange is row"))
            elif len(p["weights"]) != blocks:
                out.append(finding("layout", p["id"], f"{len(p['weights'])} weights for {blocks} blocks (patterns first, then cards)"))

    known = {p["id"] for p in spec["panels"]}
    for p in spec["panels"]:
        known |= {card_id(p, i, c) for i, c in enumerate(p.get("cards", []))}
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

    out += orphans(spec, arche) + story_findings(spec, known)

    canvas = spec["canvas"]
    if ("part" in canvas) != ("of" in canvas):
        missing = "canvas.part" if "part" not in canvas else "canvas.of"
        out.append(finding("canvas", missing, "give both part and of, or neither; the badge needs both"))
    elif "part" in canvas and canvas["part"] > canvas["of"]:
        out.append(finding("canvas", "canvas.part", f"part {canvas['part']} of {canvas['of']}; part cannot be larger than of"))
    fcols = (spec.get("footer") or {}).get("columns")
    layout = [col for col in footer_layout(spec) if col != ["legend"]]  # the legend is a strip under the columns
    if fcols and len(fcols) != len(layout):
        shown = "; ".join(" + ".join(col) for col in layout)
        out.append(finding("layout", "footer.columns", f"{len(fcols)} widths for {len(layout)} footer columns ({shown})"))
    oq = (spec.get("footer") or {}).get("open_questions") or {}
    warnings = [ch["text"] for p in spec["panels"] for ch in p.get("chips", []) if ch["kind"] == "warning"]
    warnings += [f["text"] for f in flags(spec) if f["kind"] == "warning"]
    if warnings and not oq.get("from_chips"):
        for c in (c for c in warnings if c not in oq.get("extra", [])):
            out.append(finding("chip-mirror", "footer.open_questions", f"warning not repeated in open questions: '{c}'"))

    out += traceability(spec)

    focused = [p["id"] for p in spec["panels"] if p.get("focus")]
    focused += [card_id(p, i, c) for p in spec["panels"] for i, c in enumerate(p.get("cards", [])) if c.get("focus")]
    focused += [f"flows/{i}" for i, f in enumerate(spec.get("flows", [])) if f.get("focus")]
    if len(focused) > 1:
        out.append(finding("focus", focused[1], f"{len(focused)} elements have focus ({', '.join(focused)}); a plate has one point"))
    if spec.get("flows") and not spec.get("flows_mean"):
        out.append(finding("flows-mean", "flows_mean", "the plate has flows but does not say what an arrow means", level="warning"))

    known = icons.index()  # the allowlist: a name never becomes a path unless the index has it
    for icon in iter_icons(spec):
        if icon not in known:
            close = icons.suggest(icon)
            out.append(finding("icon", icon, f"no icon named '{icon}'",
                               hint=f"Closest: {', '.join(close)}. Search with: schemantic icons <word>." if close else
                                    "Search with: schemantic icons <word>."))

    loc = load_locale(spec["canvas"]["lang"])
    text = "\n".join(iter_strings(spec)).lower()
    for term, bad in (loc.get("never_translate") or {}).items():
        for b in bad:
            # Substring, not whole word: Dutch compounds hide the term ("productcatalogus").
            if re.search(re.escape(b.lower()), text):
                out.append(finding("language", term, f"'{b}' found; keep the technical term '{term}' in English"))
    return out


def orphans(spec: dict, arche: archetypes.Archetype) -> list[dict]:
    """On a plate with flows, a panel that no flow touches (neither it nor one of its cards) reads as left over."""
    ends = {f[end] for f in spec.get("flows", []) for end in ("from", "to")}
    if not ends:
        return []
    free = arche.standalone(spec)
    return [finding("orphan", p["id"], f"no flow reaches panel '{p['id']}' or its cards, while the rest of the plate is connected",
                    level="warning")
            for p in spec["panels"]
            if p["id"] not in free and not ends & ({p["id"]} | {card_id(p, i, c) for i, c in enumerate(p.get("cards", []))})]


def story_findings(spec: dict, known: set[str]) -> list[dict]:
    """Each story is a route a finger can follow: every step exists and a flow runs from it to the next (or joins
    them both ways). A break names the step, and says so when only the panels around the two cards are joined."""
    joined = {(f["from"], f["to"]) for f in spec.get("flows", [])}
    joined |= {(f["to"], f["from"]) for f in spec.get("flows", []) if f.get("both")}
    home = {card_id(p, i, c): p["id"] for p in spec["panels"] for i, c in enumerate(p.get("cards", []))}
    out = []
    for n, s in enumerate(spec.get("stories", [])):
        where = f"stories/{n}"
        missing = [step for step in s["path"] if step not in known]
        if missing:
            out += [finding("story", where, f"story '{s['name']}' names '{step}', which is no panel or card id") for step in missing]
            continue
        for a, b in pairwise(s["path"]):
            if (a, b) in joined:
                continue
            detail = f"story '{s['name']}' breaks between '{a}' and '{b}': no flow from '{a}' to '{b}'"
            if (home.get(a, a), home.get(b, b)) in joined:
                detail += f" (a flow joins their panels, '{home.get(a, a)}' to '{home.get(b, b)}'; the route goes through the cards)"
            out.append(finding("story", where, detail))
    drawn = [n for n, s in enumerate(spec.get("stories", [])) if s.get("draw")]
    out += [finding("story", f"stories/{n}", "only one story is drawn: a plate numbers one route") for n in drawn[1:]]
    if drawn:
        out += [finding("story", f"flows/{n}", f"the drawn story numbers its own flows; drop this flow's step {f['step']}")
                for n, f in enumerate(spec.get("flows", [])) if f.get("step")]
    return out


def drawn_story(spec: dict) -> dict | None:
    return next((s for s in spec.get("stories", []) if s.get("draw")), None)


def number_story(spec: dict) -> dict:
    """A drawn story numbers the flows along its route, 1 to n, so the reader sees the route the title names. Runs on
    a spec that checked clean: every step of the story has its flow, and no flow has a step of its own."""
    story = drawn_story(spec)
    if not story:
        return spec
    flows = [dict(f) for f in spec["flows"]]
    for n, (a, b) in enumerate(pairwise(story["path"]), 1):
        f = next(f for f in flows if (f["from"], f["to"]) == (a, b) or f.get("both") and (f["from"], f["to"]) == (b, a))
        f.setdefault("step", n)  # a route that passes one flow twice keeps its first number
    return {**spec, "flows": flows}


def traceability(spec: dict) -> list[dict]:
    """With `sources` declared, every card says where it comes from, and every ref names a declared source."""
    ids = {s["id"] for s in spec.get("sources", [])}
    if not ids:
        return []
    out = []
    for p in spec["panels"]:
        for i, c in enumerate(p.get("cards", [])):
            cid = card_id(p, i, c)
            if not c.get("refs"):
                out.append(finding("traceability", cid, f"card '{c['name']}' has no refs; say which source it comes from",
                                   level="warning"))
            for ref in c.get("refs", []):
                head = ref.split(":", 1)[0].strip()
                if head not in ids:
                    out.append(finding("traceability", cid, f"ref '{ref}' does not start with a declared source id ({', '.join(sorted(ids))})",
                                       level="warning"))
    return out


def check(spec: dict, theme_css: str = "") -> list[dict]:
    """Schema first; semantic checks only on a spec that has the right shape."""
    return schema_errors(spec) or placeholders(spec) + semantic_errors(spec, theme_css)


def placeholders(spec) -> list[dict]:
    """Text a starter (`schemantic new`) left for the author: every string with TODO in it, by its path."""
    out = []

    def walk(v, where):
        if isinstance(v, str) and PLACEHOLDER.search(v):
            out.append(finding("placeholder", where or "(root)", f"still a placeholder: '{v}'"))
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{where}/{k}" if where else str(k))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{where}/{i}")
    walk(spec, "")
    return out


def slide_findings(spec: dict) -> list[dict]:
    """A slide holds less than a document plate: past SLIDE_BUDGET it is two slides."""
    if spec["canvas"].get("profile") != "slide":
        return []
    from .config import SLIDE_BUDGET
    n = {"panels": len(spec["panels"]), "cards": sum(len(p.get("cards", [])) for p in spec["panels"])}
    over = [f"{n[k]} {k} (a slide holds {v})" for k, v in SLIDE_BUDGET.items() if n[k] > v]
    return [finding("slide-budget", "canvas.profile", "; ".join(over), level="warning")] if over else []


def card_id(panel: dict, i: int, card: dict) -> str:
    return card.get("id") or f"{panel['id']}.card{i}"


def card_panels(spec: dict) -> list[dict]:
    """The panels whose cards can carry a flag, in reading order: the body's, then the footer's context cards."""
    context = (spec.get("footer") or {}).get("context")
    return spec["panels"] + ([{"id": "footer.context", "cards": context["cards"]}] if context else [])


def open_questions(spec: dict) -> list[dict]:
    """Open questions in reading order, labelled Q1, Q2, ... (V1 in Dutch): panel by panel, its warning flags and then
    its warning chips (with from_chips, or when listed in extra), then the other extra questions. `id` is the card
    or chip that shows the same label in the body, so a reader can go from the footer to the place and back."""
    oq = (spec.get("footer") or {}).get("open_questions") or {}
    extra = oq.get("extra", [])
    shown = lambda text: oq.get("from_chips") or text in extra  # noqa: E731
    items = []
    for p in card_panels(spec):
        for i, c in enumerate(p.get("cards", [])):
            if (c.get("flag") or {}).get("kind") == "warning" and shown(c["flag"]["text"]):
                items.append((c["flag"]["text"], card_id(p, i, c)))
        for k, ch in enumerate(p.get("chips", [])):
            if ch["kind"] == "warning" and shown(ch["text"]):
                items.append((ch["text"], f"{p['id']}.chip{k}"))
    items += [(q, None) for q in extra if q not in {text for text, _ in items}]
    prefix = load_locale(spec["canvas"]["lang"])["markers"]["question"]
    return [{"label": f"{prefix}{n}", "text": text, "id": at} for n, (text, at) in enumerate(items, 1)]


def flags(spec: dict) -> list[dict]:
    """Card flags in plate order: {card, kind, text, label}. A warning flag shows its open question's label (Q2); an
    info flag is a note, labelled N1, N2, ... and listed in the footer's notes."""
    asked = {q["id"]: q["label"] for q in open_questions(spec) if q["id"]}
    prefix = load_locale(spec["canvas"]["lang"])["markers"]["note"]
    out, n = [], 0
    for p in card_panels(spec):
        for i, c in enumerate(p.get("cards", [])):
            if c.get("flag"):
                cid = card_id(p, i, c)
                if c["flag"]["kind"] == "info":
                    n += 1
                out.append({"card": cid, **c["flag"],
                            "label": f"{prefix}{n}" if c["flag"]["kind"] == "info" else asked.get(cid, "?")})
    return out


def notes(spec: dict) -> list[dict]:
    """Info flags, for the footer's notes panel."""
    return [{"label": f["label"], "text": f["text"]} for f in flags(spec) if f["kind"] == "info"]


def footer_panels(spec: dict) -> list[str]:
    """The footer panels the template renders, in order; the legend is always there."""
    footer = spec.get("footer") or {}
    present = [("context", bool(footer.get("context"))), ("principles", bool(footer.get("principles"))),
               ("open_questions", bool(open_questions(spec))), ("notes", bool(notes(spec))), ("legend", True)]
    return [name for name, on in present if on]


def footer_layout(spec: dict) -> list[list[str]]:
    """Footer columns, each a list of sections. When there would be too many columns, short open questions and notes
    stack under the column with the least text (principles or open questions), so the footer stays low."""
    present = footer_panels(spec)
    footer = spec.get("footer") or {}
    size = {"open_questions": open_questions(spec), "notes": notes(spec)}
    text = {"principles": sum(len(p) for p in footer.get("principles", [])),
            "open_questions": sum(len(q["text"]) for q in size["open_questions"]),
            "notes": sum(len(q["text"]) for q in size["notes"])}
    cols: list[list[str]] = []
    many = len([n for n in present if n != "legend"]) > FOOTER_MAX_COLUMNS
    for name in present:
        hosts = [c for c in cols if c[0] in ("principles", "open_questions")]
        if many and name in size and hosts and len(size[name]) <= FOOTER_STACK_MAX:
            host = min(hosts, key=lambda c: sum(text[s] for s in c))
            host.append(name)
        else:
            cols.append([name])
    return cols


def iter_icons(spec: dict):
    for p in spec["panels"]:
        for c in p.get("cards", []):
            if c.get("icon"):
                yield c["icon"]
        for pt in p.get("patterns", []):
            for t in pt.get("tiers", []) + pt.get("steps", []):
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
            if k not in ("id", "icon", "role", "kind", "type", "tier", "layout", "from", "to", "refs", "sources", "brief", "path"):
                yield from iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_strings(v)
