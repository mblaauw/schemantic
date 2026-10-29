"""`schemantic new <archetype> <path>`: a starter spec to fill in. It has every part a finished plate needs (brief,
sources, panels with refs, flows, a story, a principle, an open question) and the archetype's own layout keys, with
TODO wherever the sources must speak; lint names each TODO left (check: placeholder)."""
from __future__ import annotations

from pathlib import Path

import yaml

from . import archetypes
from .config import SCHEMA, STARTERS
from .spec import finding, placeholders


def starter(archetype: str, lang: str = "en") -> str:
    """The starter's text: the shared head (brief, sources, canvas, title), the archetype's body, the shared footer."""
    head, foot = ((STARTERS / f"_{part}.yaml").read_text(encoding="utf-8") for part in ("head", "foot"))
    body = (STARTERS / f"{archetype}.yaml").read_text(encoding="utf-8")
    return (f"# yaml-language-server: $schema={SCHEMA}\n" + head.replace("{archetype}", archetype).replace("{lang}", lang)
            + "\n" + body + foot)


def new(archetype: str, path: str | Path, lang: str = "en") -> dict:
    """Write a starter to path, never over an existing file. Returns the path and how many TODOs it holds."""
    path = Path(path)
    if archetype not in archetypes.BUILT:
        return {"errors": [finding("archetype", archetype, f"no starter for '{archetype}'; use one of {', '.join(archetypes.BUILT)}")]}
    if path.exists():
        return {"errors": [finding("yaml", str(path), "the file already exists; give a new path, so no spec is overwritten")]}
    text = starter(archetype, lang)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"errors": [], "path": str(path), "archetype": archetype, "todo": len(placeholders(yaml.safe_load(text))),
            "next": f"replace every TODO with what the sources say, then build: schemantic build {path}"}
