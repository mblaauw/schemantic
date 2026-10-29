"""Paths, canvas presets, Chromium's flags, and the design tokens Python needs (read from tokens.css, so they live in one
place). Standard library only: the doctor imports it on a Python that has no dependencies yet."""
from __future__ import annotations

import re
from functools import cache
from pathlib import Path

# Everything a render needs ships inside the package, so an installed wheel works; ROOT is the repository (the skill
# folder), for what only a checkout has: examples, references, the gallery.
PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
TEMPLATES = PACKAGE / "templates"
ICONS = PACKAGE / "icons"
FONTS_DIR = PACKAGE / "fonts"
LOCALES = PACKAGE / "locales"
SCHEMA = PACKAGE / "schema" / "plate.schema.json"
STARTERS = PACKAGE / "starters"
JS_DIR = PACKAGE / "js"

# Without the first flag Linux Chromium hints glyphs and rounds their advances to whole pixels, so text runs a few
# pixels wider than on macOS and lines wrap differently. Without the second it antialiases text with colour fringes
# (subpixel, for LCD screens), which macOS headless does not; grey antialiasing makes the pixels match too.
LAUNCH_ARGS = ["--font-render-hinting=none", "--disable-lcd-text"]

# Paper presets in millimetres. A print plate is laid out at the sheet's width at 96 px per inch (whole CSS px), so
# its type prints at its own size, and takes its content's height like a screen plate. On paper it is centred, and
# scaled down to fit when it is taller than the sheet; lint fails it when its smallest text would then print below
# PRINT_FLOOR_PT. The SVG gets the sheet's size in mm; the PNG is the exact sheet at --dpi.
PAPER_MM = {"a3-landscape": (420, 297), "a4-landscape": (297, 210)}
MM_PER_PX = 25.4 / 96
PRINT_FLOOR_PT = 6
PRINT_SIZES = set(PAPER_MM)
CANVAS_SIZES = {"landscape-4x3": (1600, 1200), "landscape-16x9": (1920, 1080),
                **{k: (round(w / 25.4 * 96), round(h / 25.4 * 96)) for k, (w, h) in PAPER_MM.items()}}


def paper_fit(size: str, width: float, height: float) -> dict | None:
    """How a plate of width x height CSS px sits on its sheet: `scale` (1 at 96 px per inch, less when the plate is
    taller than the sheet), the sheet in mm, and the plate's offset from the sheet's corner in mm, centred."""
    if size not in PAPER_MM:
        return None
    w_mm, h_mm = PAPER_MM[size]
    scale = min(1.0, w_mm / (width * MM_PER_PX), h_mm / (height * MM_PER_PX))
    return {"size": size, "scale": scale, "sheet_mm": (w_mm, h_mm),
            "offset_mm": ((w_mm - width * MM_PER_PX * scale) / 2, (h_mm - height * MM_PER_PX * scale) / 2)}
TYPE_FLOOR_PX = 11
SLIDE_FLOOR_PX = 13          # the slide profile reads from across a room
SLIDE_BUDGET = {"panels": 5, "cards": 18}  # more than this is two slides


@cache
def tokens() -> dict[str, str]:
    """Custom properties declared in tokens.css, by name (with the leading dashes)."""
    css = (TEMPLATES / "tokens.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", css)}


def token_px(name: str) -> float:
    return float(tokens()[name].removesuffix("px"))
