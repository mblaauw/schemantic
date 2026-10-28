"""Panel roles: colour with a meaning, named in the legend. Built-in roles live in tokens.css; a theme adds a role by
declaring its four colour tokens and a legend label per language."""
from __future__ import annotations

import re

BUILT_IN = ["platform", "data", "external", "actor"]
# Old names still accepted for one release, with a `deprecated` warning.
ALIASES = {"storage": "data"}
PARTS = ("head", "sub", "body", "line")


def css_tokens(css: str) -> dict[str, str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", css)}


def theme_roles(theme_css: str) -> dict[str, dict[str, str]]:
    """Roles a theme defines: {role: {lang: legend label}}."""
    toks = css_tokens(theme_css)
    names = {m.group(1) for k in toks if (m := re.fullmatch(r"--([a-z][a-z0-9-]*)-head", k))} - set(BUILT_IN) - {"frame"}
    return {n: {k.rsplit("-", 1)[1]: v.strip("\"'") for k, v in toks.items() if k.startswith(f"--{n}-label-")} for n in sorted(names)}


def canonical(role: str) -> str:
    return ALIASES.get(role, role)


def role_css(theme_css: str = "") -> str:
    """The .role-<name> rules: each maps the generic --head/--sub/--body/--line to the role's tokens."""
    names = [*BUILT_IN, "frame", *theme_roles(theme_css)]
    return "\n".join(f".role-{n} {{ " + " ".join(f"--{p}: var(--{n}-{p});" for p in PARTS) + " }" for n in names)


def legend_label(role: str, lang: str, locale: dict, theme_css: str = "") -> str | None:
    role = canonical(role)
    if role in BUILT_IN:
        return locale["legend"][role]
    return theme_roles(theme_css).get(role, {}).get(lang)


def role_findings(spec: dict, theme_css: str = "") -> list[dict]:
    """Unknown roles and theme roles without a legend label are errors; old role names are deprecated."""
    out, seen = [], set()
    known = set(BUILT_IN) | set(theme_roles(theme_css))
    for p in spec["panels"]:
        role = p["role"]
        if role in ALIASES and role not in seen:
            out.append({"level": "warning", "check": "deprecated", "id": p["id"],
                        "detail": f"role '{role}' is now '{ALIASES[role]}'; '{role}' works until the next release"})
        elif canonical(role) not in known:
            out.append({"level": "error", "check": "role", "id": p["id"],
                        "detail": f"role '{role}' is not built in ({', '.join(BUILT_IN)}) and the theme does not define it"})
        elif canonical(role) not in BUILT_IN and not theme_roles(theme_css)[role].get(spec["canvas"]["lang"]):
            out.append({"level": "error", "check": "role", "id": p["id"],
                        "detail": f"the theme defines role '{role}' without --{role}-label-{spec['canvas']['lang']}"})
        seen.add(role)
    return out
