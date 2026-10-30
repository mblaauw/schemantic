"""The plate as text: the claim, panels with their cards, flows, stories, open questions and principles. Used as the SVG's
<desc>, as the <name>.md written next to the images, and as review input. The focus element comes first."""
from __future__ import annotations

from .spec import assumed_items, card_id, flags, load_locale, open_questions


def _focus_first(spec: dict) -> list[dict]:
    panels = list(spec["panels"])
    focus = [p for p in panels if p.get("focus") or any(c.get("focus") for c in p.get("cards", []))]
    return focus + [p for p in panels if p not in focus]


def _card(c: dict, cid: str, flag_of: dict, loc: dict) -> str:
    bits = [c["name"] + (f" ({c['qualifier']})" if c.get("qualifier") else "")]
    if c.get("status"):
        bits.append(f"[{loc['status'][c['status']]}]")
    if c.get("assumed"):
        bits.append(f"[{loc['status']['assumed']}]")
    if c.get("note"):
        bits.append(f"— {c['note']}")
    if cid in flag_of:
        bits.append(f"[{flag_of[cid]['label']}]")
    if c.get("focus"):
        bits.append("(focus)")
    return " ".join(bits)


def lines(spec: dict) -> list[str]:
    """Plain outline lines, indented two spaces per level."""
    loc = load_locale(spec["canvas"]["lang"])
    names = {p["id"]: p["title"] for p in spec["panels"]}
    flag_of = {f["card"]: f for f in flags(spec)}
    out = []
    for p in _focus_first(spec):
        head = p["title"] + (f" — {p['subtitle']}" if p.get("subtitle") else "")
        if p.get("status"):
            head += f" [{loc['status'][p['status']]}]"
        out.append(head + (" (focus)" if p.get("focus") else ""))
        for i, c in enumerate(p.get("cards", [])):
            cid = card_id(p, i, c)
            names[cid] = c["name"]
            out.append("  " + _card(c, cid, flag_of, loc))
            out += [f"    {b}" for b in c.get("bullets", [])]
        for ch in p.get("chips", []):
            out.append(f"  ({ch['kind']}) {ch['text']}")
    for f in spec.get("flows", []):
        label = f" ({f['label']})" if f.get("label") else ""
        arrow = "<->" if f.get("both") else "->"
        mark = f" [{loc['status']['assumed']}]" if f.get("assumed") else ""
        out.append(f"{names.get(f['from'], f['from'])} {arrow} {names.get(f['to'], f['to'])}{label}{mark}")
    out += [f"{s['name']}: {' -> '.join(names.get(step, step) for step in s['path'])}" for s in spec.get("stories", [])]
    return out


def desc(spec: dict) -> str:
    """Text for the SVG's <desc>: the subtitle, then the outline."""
    return "\n".join(([spec["subtitle"], ""] if spec.get("subtitle") else []) + lines(spec))


def _zone_lines(zones: list[dict], titles: dict, depth: int = 0) -> list[str]:
    """Where everything runs, as a nested list: each zone with its kind, the panels in it, and the zones inside it."""
    out = []
    for z in zones:
        kind = f"{z['kind']}: " if z.get("kind") else ""
        held = ", ".join(titles[pid] for pid in z.get("panels", []))
        out.append("  " * depth + f"- {kind}{z['title']}" + (f" ({held})" if held else ""))
        out += _zone_lines(z.get("zones", []), titles, depth + 1)
    return out


def markdown(spec: dict) -> str:
    """<name>.md: the title as heading, the claim, panels and cards, flows, stories, open questions, principles."""
    loc = load_locale(spec["canvas"]["lang"])
    flag_of = {f["card"]: f for f in flags(spec)}
    names = {p["id"]: p["title"] for p in spec["panels"]}
    md = [f"# {spec['title']}", ""] + ([f"*{spec['topic']}*", ""] if spec.get("topic") else [])
    if spec.get("subtitle"):
        md += [spec["subtitle"], ""]
    for p in _focus_first(spec):
        status = f" [{loc['status'][p['status']]}]" if p.get("status") else ""
        md += [f"## {p['title']}{status}" + (" (focus)" if p.get("focus") else ""), ""]
        if p.get("subtitle"):
            md += [p["subtitle"], ""]
        for i, c in enumerate(p.get("cards", [])):
            cid = card_id(p, i, c)
            names[cid] = c["name"]
            md.append(f"- {_card(c, cid, flag_of, loc)}")
            md += [f"  - {b}" for b in c.get("bullets", [])]
        md += [f"- *{ch['text']}*" for ch in p.get("chips", [])]
        md.append("")
    zones = spec["layout"].get("zones")
    if zones:
        md += [f"## {loc['footer']['zones']}", ""] + _zone_lines(zones, {p["id"]: p["title"] for p in spec["panels"]})
        outside = [p["title"] for p in spec["panels"] if p["id"] in spec["layout"].get("outside", [])]
        md += [f"- {loc['footer']['outside']}: {', '.join(outside)}"] if outside else []
        md.append("")
    context = (spec.get("footer") or {}).get("context")
    if context:
        md += [f"## {context['title']}", ""]
        md += [f"- {_card(c, card_id({'id': 'footer.context'}, i, c), flag_of, loc)}" for i, c in enumerate(context["cards"])]
        md.append("")
    if spec.get("flows"):
        md += [f"## {loc['footer']['flows']}", ""]
        for f in spec["flows"]:
            label = f" — {f['label']}" if f.get("label") else ""
            mark = f" [{loc['status']['assumed']}]" if f.get("assumed") else ""
            md.append(f"- {names.get(f['from'], f['from'])} → {names.get(f['to'], f['to'])}{label}{mark}")
        md.append("")
    if spec.get("stories"):
        md += [f"## {loc['footer']['stories']}", ""]
        md += [f"- {s['name']}: {' → '.join(names.get(step, step) for step in s['path'])}" for s in spec["stories"]]
        md.append("")
    questions = open_questions(spec)
    if questions:
        md += [f"## {loc['footer']['open_questions']}", ""]
        md += [f"- {q['label']} {q['text']}" for q in questions]
        md.append("")
    principles = (spec.get("footer") or {}).get("principles") or []
    if principles:
        md += [f"## {loc['footer']['principles']}", ""] + [f"- {p}" for p in principles] + [""]
    assumed = assumed_items(spec) + (spec.get("brief") or {}).get("assumptions", [])
    if assumed:
        md += [f"## {loc['footer']['assumptions']}", ""] + [f"- {a}" for a in assumed] + [""]
    notes = [f for f in flags(spec) if f["kind"] == "info"]
    if notes:
        md += [f"## {loc['footer']['notes']}", ""] + [f"- {n['label']} {n['text']}" for n in notes] + [""]
    return "\n".join(md)
