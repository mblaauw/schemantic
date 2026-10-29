"""Build the plate's HTML: the template, the theme, and the grid the archetype derives."""
from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import archetypes, icons, roles
from .config import CANVAS_SIZES, TEMPLATES
from .export import font_css
from .spec import FOOTER_WEIGHTS, card_id, flags, footer_layout, load_locale, notes, open_questions


def grid_css(spec: dict) -> dict:
    """The body grid for CSS: gutter tracks between columns and rows; an area that spans cells also spans the
    gutter between them."""
    g = archetypes.get(spec["archetype"]).grid(spec)
    rows = g.rows
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
    # Rows take their content height; the canvas fits them (or a fixed canvas spreads its surplus over the gutters,
    # see js/fit.js).
    gutter = "calc(var(--gutter-y) + var(--gap-extra, 0px))"
    return {
        "columns": " var(--gutter-x) ".join(g.columns),
        "rows": f" {gutter} ".join(["auto"] * m),
        "areas": " ".join('"' + " ".join(line) + '"' for line in lines),
        "groups": g.groups, "group_kind": g.group_kind, "bands": g.bands, "zones": g.zones,
    }


def icon_markup(name: str) -> str:
    return icons.bodies()[name]


def tree_rows(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        stripped = line.lstrip(" ")
        out.append({"depth": (len(line) - len(stripped)) // 2, "text": stripped})
    return out


def matrix_values(pt: dict) -> list[str]:
    used = {v for r in pt["rows"] for v in r["cells"]}
    return [v for v in ("full", "partial", "none") if v in used]


def legend_entries(spec: dict, loc: dict, theme_css: str = "") -> list[dict]:
    """The legend, generated from what the plate uses: roles, what arrows mean and their styles, steps, change
    statuses, focus, and chip or flag kinds."""
    lg, lang = loc["legend"], spec["canvas"]["lang"]
    entries, seen = [], []
    for p in spec["panels"]:
        role = p["role"]
        if role not in seen:
            seen.append(role)
            entries.append({"kind": "role", "key": role, "label": roles.legend_label(role, lang, loc, theme_css)})
    flows = spec.get("flows", [])
    if flows:
        mean = spec.get("flows_mean")
        entries.append({"kind": "arrow", "key": "arrow", "label": lg[f"mean_{mean}"] if mean else lg["arrow"]})
        # The meaning entry already shows a solid arrow, so only the other line styles get an entry.
        styles = [s for s in ("async", "optional") if any(f.get("style") == s for f in flows)]
        entries += [{"kind": "line", "key": s, "label": lg[f"style_{s}"]} for s in styles]
        if any(f.get("step") for f in flows):
            entries.append({"kind": "step", "key": "step", "label": lg["step"]})
    things = [p for p in spec["panels"]] + [c for p in spec["panels"] for c in p.get("cards", [])]
    for st in ("new", "changed", "planned", "deprecated", "removed"):
        if any(t.get("status") == st for t in things):
            entries.append({"kind": "status", "key": st, "label": lg[f"status_{st}"]})
    if any(t.get("focus") for t in things + spec.get("flows", [])):
        entries.append({"kind": "focus", "key": "focus", "label": lg["focus"]})
    kinds = [ch["kind"] for p in spec["panels"] for ch in p.get("chips", [])] + [f["kind"] for f in flags(spec)]
    for k in ("warning", "info"):
        if k in kinds:
            entries.append({"kind": "chip", "key": k, "label": lg[k]})
    return entries


def panels_for_render(spec: dict) -> list[dict]:
    """Panels with the archetype's defaults filled in (the hub frame, a layer's card row, nesting)."""
    arche = archetypes.get(spec["archetype"])
    pinned = chips_pinned(spec)
    rows = arche.grid(spec).rows
    # A panel spanning several rows (a rail, a side spoke) spreads its cards over its height instead of leaving one hole.
    spread = {n for n in {n for r in rows for n in r} if sum(n in r for r in rows) > 1}
    loud = focal_panels(spec)
    return [{**p, "role": p["role"], "chips_bottom": p["id"] in pinned, "spread": p["id"] in spread,
             "quiet": loud is not None and p["id"] not in loud, **arche.panel_defaults(spec, p)} for p in spec["panels"]]


def focal_panels(spec: dict) -> set[str] | None:
    """The panels a plate's focus is about: the focused panel, the panel of a focused card, or the panels at both ends
    of a focused flow. The other panels get quiet headers so the eye goes there first. None without a focus."""
    owner = {p["id"]: p["id"] for p in spec["panels"]}
    owner |= {card_id(p, i, c): p["id"] for p in spec["panels"] for i, c in enumerate(p.get("cards", []))}
    loud = {p["id"] for p in spec["panels"] if p.get("focus")}
    loud |= {p["id"] for p in spec["panels"] for c in p.get("cards", []) if c.get("focus")}
    for f in spec.get("flows", []):
        if f.get("focus"):
            loud |= {owner.get(f["from"]), owner.get(f["to"])} - {None}
    return loud or None


def chips_pinned(spec: dict) -> set[str]:
    """With layout.chips_at: bottom, chips are pinned to the bottom of their panel, but only in grid rows where every
    panel has chips, so they line up. Otherwise chips sit right under the content."""
    if spec["layout"].get("chips_at") != "bottom":
        return set()
    g = archetypes.get(spec["archetype"]).grid(spec)
    has = {p["id"] for p in spec["panels"] if p.get("chips")}
    out = set()
    for row in g.rows:
        ids = {m for n in row if n != "." for m in g.groups.get(n, [n])}
        if ids <= has:
            out |= ids
    return out


def build_html(spec: dict, theme_css: str = "") -> str:
    loc = load_locale(spec["canvas"]["lang"])
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["j2", "html"]))
    # Theme after the tokens (and the profile's), so it overrides them; role rules last, so a theme's own roles get theirs.
    profile = (TEMPLATES / "profile-slide.css").read_text(encoding="utf-8") if spec["canvas"].get("profile") == "slide" else ""
    css = "\n".join([font_css(), (TEMPLATES / "tokens.css").read_text(encoding="utf-8"), profile, theme_css,
                     (TEMPLATES / "components.css").read_text(encoding="utf-8"), roles.role_css(theme_css)])
    canvas = spec["canvas"]
    badge = loc["badge"].format(part=canvas["part"], of=canvas["of"]) if canvas.get("part") and canvas.get("of") else None
    footer = spec.get("footer") or {}
    layout = footer_layout(spec)
    legend = legend_entries(spec, loc, theme_css)
    fcols = footer.get("columns") or [FOOTER_WEIGHTS[col[0]] for col in layout if col != ["legend"]] or [1]
    return env.get_template("plate.html.j2").render(
        spec=spec, panels=(panels := panels_for_render(spec)), panel_by_id={p['id']: p for p in panels}, lang=canvas["lang"], L=loc, css=css,
        width=width, height=height, badge=badge, grid=grid_css(spec), footer=footer,
        footer_columns=" ".join(f"minmax(0, {w}fr)" for w in fcols),
        legend=legend, footer_layout=layout, open_questions=open_questions(spec), notes=notes(spec),
        flag_of={f['card']: f for f in flags(spec)},
        question_at={q["id"]: q["label"] for q in open_questions(spec) if q["id"]},
        icons=icon_markup, tree_rows=tree_rows, matrix_values=matrix_values)
