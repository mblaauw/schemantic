"""The bundled Tabler outline icons, searchable by name, tag and category (assets/icons/index.json)."""
from __future__ import annotations

import difflib
import json
import re
from functools import cache

from .config import ICONS


@cache
def index() -> dict[str, dict]:
    return json.loads((ICONS / "index.json").read_text(encoding="utf-8"))


@cache
def bodies() -> dict[str, str]:
    """Every icon's drawing (what goes inside its 24 x 24 <svg>), by name: one file instead of 4,879."""
    return json.loads((ICONS / "icons.json").read_text(encoding="utf-8"))


@cache
def synonyms() -> dict[str, list[str]]:
    """Architecture words Tabler does not tag (queue, topic, gateway, ...) mapped to the best-fitting icons."""
    raw = json.loads((ICONS / "synonyms.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _score(name: str, meta: dict, word: str) -> int:
    word = word.lower()
    parts = name.split("-")
    if name == word:
        return 10
    if name in synonyms().get(word, []):
        return 8 - synonyms()[word].index(name)  # the curated order is the order of fit
    if word in parts:
        return 6
    if word in name:
        return 4
    if word in meta["tags"]:
        return 3
    if any(word in t for t in meta["tags"]) or word == meta["category"].lower():
        return 1
    return 0


def search(words: list[str], limit: int = 20, every: bool = True) -> list[str]:
    """Icon names matching the words (all of them, or any with every=False), best first."""
    words = [w for w in words if w]
    scored = []
    for name, meta in index().items():
        scores = [_score(name, meta, w) for w in words]
        if (all(scores) if every else any(scores)) and words:
            scored.append((-sum(scores), len(name), name))
    return [n for _, _, n in sorted(scored)[:limit]]


def suggest(name: str, n: int = 3) -> list[str]:
    """The closest icon names to an unknown one: by its words, then by spelling."""
    words = [w for w in re.split(r"[-_\s]+", name.lower()) if w]
    if name.lower() in synonyms():
        return search([name.lower()], n)
    return search(words, n) or search(words, n, every=False) or difflib.get_close_matches(name, list(index()), n, 0.4)
