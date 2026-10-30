"""Panel roles: colour with a meaning, named in the legend. Built-in roles live in tokens.css; a theme adds a role by
declaring its four colour tokens and a legend label per language."""
from __future__ import annotations

import re

from .findings import finding

BUILT_IN = ["platform", "data", "external", "actor"]
PARTS = ("head", "sub", "body", "line")


def css_tokens(css: str) -> dict[str, str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", css)}


def theme_roles(theme_css: str) -> dict[str, dict[str, str]]:
    """Roles a theme defines: {role: {lang: legend label}}."""
    toks = css_tokens(theme_css)
    names = {m.group(1) for k in toks if (m := re.fullmatch(r"--([a-z][a-z0-9-]*)-head", k))} - set(BUILT_IN) - {"frame"}
    return {n: {k.rsplit("-", 1)[1]: v.strip("\"'") for k, v in toks.items() if k.startswith(f"--{n}-label-")} for n in sorted(names)}


def role_css(theme_css: str = "") -> str:
    """The .role-<name> rules: each maps the generic --head/--sub/--body/--line to the role's tokens."""
    names = [*BUILT_IN, "frame", *theme_roles(theme_css)]
    return "\n".join(f".role-{n} {{ " + " ".join(f"--{p}: var(--{n}-{p});" for p in PARTS) + " }" for n in names)


def legend_label(role: str, lang: str, locale: dict, theme_css: str = "") -> str | None:
    if role in BUILT_IN:
        return locale["legend"][role]
    return theme_roles(theme_css).get(role, {}).get(lang)


# Icons that show a person or a group: the cue that a card is people rather than a system.
PEOPLE_ICONS = {"user", "users", "friends", "man", "woman", "headset", "id-badge", "id-badge-2", "school"}


def is_person(icon: str | None) -> bool:
    return bool(icon) and (icon in PEOPLE_ICONS or icon.startswith(("user-", "users-")))


def role_fit_findings(spec: dict) -> list[dict]:
    """A panel coloured as people whose cards look like systems, or the reverse, judged by the cards' icons: at least
    two cards, two thirds of them pointing the other way; or a panel that mixes the two, at least two of each and more
    than a third of each. One person beside a row of tools is left alone. A warning, since icons are only a hint. Lanes
    are left out: their cards are steps or items, not things."""
    if spec["archetype"] in ("swimlane", "roadmap"):
        return []
    out = []
    for p in spec["panels"]:
        cards = [c for c in p.get("cards", []) if c.get("icon")]
        people = sum(is_person(c["icon"]) for c in cards)
        if len(cards) < 2 or p["role"] not in BUILT_IN:
            continue
        if p["role"] == "actor" and len(cards) - people >= 2 * len(cards) / 3:
            out.append(finding("role-fit", p["id"], f"coloured as people and teams, but {len(cards) - people} of its "
                               f"{len(cards)} cards show systems or things", level="warning"))
        elif p["role"] != "actor" and people >= 2 * len(cards) / 3:
            out.append(finding("role-fit", p["id"], f"coloured as {p['role']}, but {people} of its {len(cards)} cards show "
                               "people", level="warning"))
        elif (fewest := min(people, len(cards) - people)) >= 2 and fewest * 3 > len(cards):
            out.append(finding("role-fit", p["id"], f"mixes people ({people}) and systems or things ({len(cards) - people}) "
                               "under one colour", level="warning"))
    return out


def role_findings(spec: dict, theme_css: str = "") -> list[dict]:
    """Unknown roles and theme roles without a legend label are errors."""
    out = []
    known = set(BUILT_IN) | set(theme_roles(theme_css))
    for p in spec["panels"]:
        role = p["role"]
        if role not in known:
            out.append(finding("role", p["id"],
                               f"role '{role}' is not built in ({', '.join(BUILT_IN)}) and the theme does not define it"))
        elif role not in BUILT_IN and not theme_roles(theme_css)[role].get(spec["canvas"]["lang"]):
            out.append(finding("role", p["id"],
                               f"the theme defines role '{role}' without --{role}-label-{spec['canvas']['lang']}"))
    return out
