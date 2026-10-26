"""Paths, canvas presets, and the design tokens Python needs (read from tokens.css, so they live in one place)."""
from __future__ import annotations

import re
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
ICONS = ROOT / "assets" / "icons"
FONTS_DIR = ROOT / "assets" / "fonts"
JS_DIR = Path(__file__).resolve().parent / "js"

CANVAS_SIZES = {"landscape-4x3": (1600, 1200), "landscape-16x9": (1920, 1080)}
TYPE_FLOOR_PX = 11


@cache
def tokens() -> dict[str, str]:
    """Custom properties declared in templates/tokens.css, by name (with the leading dashes)."""
    css = (TEMPLATES / "tokens.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", css)}


def token_px(name: str) -> float:
    return float(tokens()[name].removesuffix("px"))
