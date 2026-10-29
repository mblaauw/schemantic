"""A series is read as one story: the checks no single plate can make. Each part must agree with the others on its
numbering, language and what an arrow means, and a thing that appears in two parts must keep its name's colour (the
role of the panel it is, or sits in)."""
from __future__ import annotations

from pathlib import Path

from .spec import check, read_spec


def _things(spec: dict) -> dict[str, tuple[str, str]]:
    """Every named thing on a plate, by its name in lower case: (role it is drawn in, where it is)."""
    out = {}
    for p in spec["panels"]:
        role = p["role"]
        out.setdefault(p["title"].strip().lower(), (role, p["id"]))
        for i, c in enumerate(p.get("cards", [])):
            out.setdefault(c["name"].strip().lower(), (role, c.get("id") or f"{p['id']}.card{i}"))
    return out


def series_findings(paths: list[str | Path]) -> list[dict]:
    """Findings for a set of spec files, grouped by `canvas.series`; ids are `<file>: <element>`."""
    parts: dict[str, list[tuple[str, dict]]] = {}
    out: list[dict] = []
    for path in paths:
        spec, issues = read_spec(path)
        if spec is None or any(i["level"] == "error" for i in issues + check(spec)):
            out.append({"level": "error", "check": "series", "id": f"{Path(path).name}: (file)",
                        "detail": "the spec does not pass its own checks; build it first"})
            continue
        canvas = spec["canvas"]
        if not canvas.get("series"):
            out.append({"level": "error", "check": "series", "id": f"{Path(path).name}: canvas.series",
                        "detail": "not part of a series: give canvas.series, part and of"})
            continue
        parts.setdefault(canvas["series"], []).append((Path(path).name, spec))

    hints = {"canvas.of": "Give every part the same canvas.of.", "canvas.part": "Number the parts 1 to `of`, once each.",
             "canvas.lang": "Write every part of a series in one language.",
             "flows_mean": "Use one flows_mean across the series, or say in each part's subtitle what its arrows show.",
             "canvas.series": "Build the missing parts too, or lower canvas.of."}

    def add(level, name, where, detail):
        hint = hints.get(where, "Give the thing the same role wherever it appears: the role of its panel.")
        out.append({"level": level, "check": "series", "id": f"{name}: {where}", "detail": detail, "hint": hint})

    for series, members in parts.items():
        first_name, first = members[0]
        of = first["canvas"].get("of")
        numbers = {}
        for name, spec in members:
            c = spec["canvas"]
            if c.get("of") != of:
                add("error", name, "canvas.of", f"says {c.get('of')} parts; {first_name} says {of}")
            if c.get("part") in numbers:
                add("error", name, "canvas.part", f"part {c.get('part')} again (also {numbers[c.get('part')]})")
            numbers[c.get("part")] = name
            if c["lang"] != first["canvas"]["lang"]:
                add("error", name, "canvas.lang", f"in {c['lang']}; {first_name} is in {first['canvas']['lang']}")
            if spec.get("flows") and first.get("flows") and spec.get("flows_mean") != first.get("flows_mean"):
                # A warning: a part may show other flows on purpose, but the same arrow then needs saying so
                add("warning", name, "flows_mean", f"arrows mean '{spec.get('flows_mean')}' here and "
                                                   f"'{first.get('flows_mean')}' in {first_name}")
        missing = [n for n in range(1, (of or 0) + 1) if n not in numbers]
        if missing:
            add("warning", first_name, "canvas.series",
                f"series '{series}' has no part {', '.join(map(str, missing))} among these files")
        seen: dict[str, tuple[str, str, str]] = {}  # name -> (role, where, file)
        for name, spec in sorted(members, key=lambda m: m[1]["canvas"].get("part") or 0):
            for thing, (role, where) in _things(spec).items():
                if thing in seen and seen[thing][0] != role:
                    was_role, was_where, was_file = seen[thing]
                    add("error", name, where, f"'{thing}' is drawn as {role} here and as {was_role} in {was_file} "
                                              f"({was_where}); one thing keeps one colour across the series")
                seen.setdefault(thing, (role, where, name))
    return out
