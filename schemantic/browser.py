"""One Chromium for the whole pipeline: launch it the same way everywhere, load a plate, call the page scripts."""
from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from . import archetypes
from .config import CANVAS_SIZES, JS_DIR

# With a fixed canvas, each gap grows by at most this much; the rest of the surplus stays under the footer.
GAP_CAP = 48

# Without this flag Linux Chromium hints glyphs and rounds their advances to whole pixels, so text runs a few
# pixels wider than on macOS and lines wrap differently. With it, layout is the same on both.
LAUNCH_ARGS = ["--font-render-hinting=none"]


# common.js first: the other scripts attach their function to the `schemantic` object it creates.
SCRIPTS = ["common.js", "fit.js", "decorate.js", "route.js", "export.js", "lint.js", "snapshot.js"]


def launch(playwright):
    return playwright.chromium.launch(args=LAUNCH_ARGS)


@cache
def page_scripts() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in SCRIPTS)


@cache
def fonts_ready() -> str:
    return (JS_DIR / "fonts-ready.js").read_text(encoding="utf-8")


def height_mode(spec: dict) -> str:
    if spec["layout"].get("row_heights"):
        return "legacy"
    return spec["canvas"].get("height", "fit")


def open_plate(browser, html: str, spec: dict, scale: float = 1):
    """Load the plate, wait for its fonts, set the canvas height (fit or fixed), and draw the decorations."""
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.set_content(html)
    page.evaluate(fonts_ready())
    page.add_script_tag(content=page_scripts())
    gaps = len(archetypes.get(spec["archetype"]).grid(spec).rows)  # row gutters plus the gap above the footer
    h = call(page, "fit", {"mode": height_mode(spec), "width": width, "height": height, "gaps": gaps, "cap": GAP_CAP})
    page.set_viewport_size({"width": width, "height": int(h)})
    call(page, "decorate")
    return page


def call(page, name: str, arg=None):
    """Call a page script's function, e.g. call(page, "route", flows). Playwright calls the function it is given
    with `arg`, so no glue code is needed."""
    return page.evaluate(f"schemantic.{name}", arg)


def svg_size(svg_path: Path) -> tuple[int, int]:
    head = svg_path.read_text(encoding="utf-8")[:400]
    w, h = (re.search(rf'{k}="([\d.]+)"', head).group(1) for k in ("width", "height"))
    return round(float(w)), round(float(h))


def rasterise_svg(browser, svg_path: Path, png_path: Path, scale: float = 2) -> None:
    width, height = svg_size(svg_path)
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.goto(svg_path.resolve().as_uri())
    page.evaluate(fonts_ready())
    page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": width, "height": height})
    page.close()
