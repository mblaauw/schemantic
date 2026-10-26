"""One Chromium for the whole pipeline: launch it the same way everywhere, load a plate, call the page scripts."""
from __future__ import annotations

from functools import cache
from pathlib import Path

from .config import CANVAS_SIZES, JS_DIR

# Without this flag Linux Chromium hints glyphs and rounds their advances to whole pixels, so text runs a few
# pixels wider than on macOS and lines wrap differently. With it, layout is the same on both.
LAUNCH_ARGS = ["--font-render-hinting=none"]


# common.js first: the other scripts attach their function to the `schemantic` object it creates.
SCRIPTS = ["common.js", "route.js", "export.js", "lint.js", "snapshot.js"]


def launch(playwright):
    return playwright.chromium.launch(args=LAUNCH_ARGS)


@cache
def page_scripts() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in SCRIPTS)


@cache
def fonts_ready() -> str:
    return (JS_DIR / "fonts-ready.js").read_text(encoding="utf-8")


def open_plate(browser, html: str, spec: dict, scale: float = 1):
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.set_content(html)
    page.evaluate(fonts_ready())
    page.add_script_tag(content=page_scripts())
    return page


def call(page, name: str, arg=None):
    """Call a page script's function, e.g. call(page, "route", flows). Playwright calls the function it is given
    with `arg`, so no glue code is needed."""
    return page.evaluate(f"schemantic.{name}", arg)


def rasterise_svg(browser, svg_path: Path, spec: dict, png_path: Path, scale: float = 2) -> None:
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page.goto(svg_path.resolve().as_uri())
    page.evaluate(fonts_ready())
    page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": width, "height": height})
    page.close()
