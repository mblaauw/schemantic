"""Build the plate's HTML: the template, the theme, and the grid the archetype derives."""
from __future__ import annotations

import re
from functools import cache

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import archetypes
from .config import CANVAS_SIZES, ICONS, TEMPLATES
from .export import font_css
from .spec import FOOTER_WEIGHTS, footer_panels, load_locale, open_questions


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
    heights = spec["layout"].get("row_heights") or g.heights
    return {
        "columns": " var(--gutter-x) ".join(g.columns),
        "rows": " var(--gutter-y) ".join("minmax(0, 1fr)" if h == "fill" else "auto" for h in heights),
        "areas": " ".join('"' + " ".join(line) + '"' for line in lines),
        "groups": g.groups,
    }


@cache
def icon_markup(name: str) -> str:
    raw = (ICONS / f"{name}.svg").read_text(encoding="utf-8")
    inner = raw[raw.index(">", raw.index("<svg")) + 1: raw.rindex("</svg>")]
    inner = re.sub(r'<path stroke="none" d="M0 0h24v24H0z" fill="none"\s*/>', "", inner)
    return re.sub(r"\s+", " ", inner).strip()


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


def panels_for_render(spec: dict) -> list[dict]:
    """Panels with the archetype's defaults filled in (the hub frame, a layer's card row, nesting)."""
    arche = archetypes.get(spec["archetype"])
    return [{**p, **arche.panel_defaults(spec, p)} for p in spec["panels"]]


def build_html(spec: dict, theme_css: str = "") -> str:
    loc = load_locale(spec["canvas"]["lang"])
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["j2", "html"]))
    css = "\n".join([font_css(), (TEMPLATES / "tokens.css").read_text(encoding="utf-8"), theme_css,
                     (TEMPLATES / "components.css").read_text(encoding="utf-8")])
    canvas = spec["canvas"]
    badge = loc["badge"].format(part=canvas["part"], of=canvas["of"]) if canvas.get("part") and canvas.get("of") else None
    footer = spec.get("footer") or {}
    fcols = footer.get("columns") or [FOOTER_WEIGHTS[name] for name in footer_panels(spec)]
    return env.get_template("plate.html.j2").render(
        spec=spec, panels=panels_for_render(spec), lang=canvas["lang"], L=loc, css=css,
        width=width, height=height, badge=badge, grid=grid_css(spec), footer=footer,
        footer_columns=" ".join(f"minmax(0, {w}fr)" for w in fcols),
        legend=legend_entries(spec, loc), open_questions=open_questions(spec),
        icons=icon_markup, tree_rows=tree_rows, matrix_values=matrix_values)
