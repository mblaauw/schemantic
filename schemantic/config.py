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

# Paper presets in millimetres. The canvas is the sheet at 96 px per inch, rounded to whole CSS px (a fractional
# canvas makes Chromium resample screenshots); the PNG is then sized to the exact sheet at --dpi.
PAPER_MM = {"a3-landscape": (420, 297), "a4-landscape": (297, 210)}
PRINT_SIZES = set(PAPER_MM)
CANVAS_SIZES = {"landscape-4x3": (1600, 1200), "landscape-16x9": (1920, 1080),
                **{k: (round(w / 25.4 * 96), round(h / 25.4 * 96)) for k, (w, h) in PAPER_MM.items()}}


def png_size(size: str, width: float, height: float, scale: float) -> tuple[int, int]:
    """Pixel size of the PNG: the exact sheet at scale * 96 dpi for paper, else the canvas times the scale."""
    if size in PAPER_MM:
        w, h = PAPER_MM[size]
        return round(w / 25.4 * 96 * scale), round(h / 25.4 * 96 * scale)
    return round(width * scale), round(height * scale)
TYPE_FLOOR_PX = 11


@cache
def tokens() -> dict[str, str]:
    """Custom properties declared in templates/tokens.css, by name (with the leading dashes)."""
    css = (TEMPLATES / "tokens.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", css)}


def token_px(name: str) -> float:
    return float(tokens()[name].removesuffix("px"))
