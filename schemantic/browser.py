"""One Chromium for the whole pipeline: launch it the same way everywhere, load a plate, call the page scripts."""
from __future__ import annotations

import math
import re
from functools import cache
from pathlib import Path

from PIL import Image

from . import archetypes
from .config import CANVAS_SIZES, JS_DIR, LAUNCH_ARGS
from .doctor import use_kit_browsers

use_kit_browsers()  # before any Playwright starts: a Chromium installed by an offline kit is found without setup

# With a fixed canvas, each gap grows by at most this much; the rest of the surplus stays under the footer.
GAP_CAP = 48

# A plate loads nothing from the network: fonts, icons and styles are bundled, so a build gives the same result on a
# machine without one. Page requests that would leave the machine are refused and reported (see `offline`); anything
# else Chromium tries goes to a proxy that is not there, so not even a DNS lookup leaves.
OFFLINE_ARGS = ["--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=<-loopback>", "--no-pings"]
REMOTE = re.compile(r"^(https?|wss?|ftp)://", re.IGNORECASE)


# common.js first: the other scripts attach their function to the `schemantic` object it creates.
SCRIPTS = ["common.js", "fit.js", "rails.js", "decorate.js", "route.js", "layout.js", "lint.js"]


def launch(playwright):
    return playwright.chromium.launch(args=LAUNCH_ARGS + OFFLINE_ARGS)


def offline(page, refused: list[str] | None = None) -> None:
    """Refuse every request from the page that would leave the machine, noting its URL in `refused`."""
    def refuse(route):
        if refused is not None:
            refused.append(route.request.url)
        route.abort()
    page.route(REMOTE, refuse)


@cache
def page_scripts() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in SCRIPTS)


@cache
def fonts_ready() -> str:
    return (JS_DIR / "fonts-ready.js").read_text(encoding="utf-8")


def height_mode(spec: dict) -> str:
    # Paper too takes the content's height: the plate is fitted to the sheet afterwards (config.paper_fit).
    return spec["canvas"].get("height", "fit")


def open_plate(browser, html: str, spec: dict, scale: float = 1, refused: list[str] | None = None, even: bool = True):
    """Load the plate, wait for its fonts, set the canvas height (fit or fixed), and draw the decorations. Requests
    for the network are refused and noted in `refused`."""
    width, height = CANVAS_SIZES[spec["canvas"]["size"]]
    page = browser.new_page(viewport={"width": math.ceil(width), "height": math.ceil(height)}, device_scale_factor=scale)
    offline(page, refused)
    page.set_content(html)
    page.evaluate(fonts_ready())
    page.add_script_tag(content=page_scripts())
    gaps = len(archetypes.get(spec["archetype"]).grid(spec).rows)  # row gutters plus the gap above the footer
    # A slide keeps its 16:9 shape even when the content is short.
    min_height = round(width * 9 / 16) if spec["canvas"]["size"] == "landscape-16x9" else 0
    h = call(page, "fit", {"mode": height_mode(spec), "height": height, "gaps": gaps, "cap": GAP_CAP,
                           "minHeight": min_height, "even": even})
    page.set_viewport_size({"width": math.ceil(width), "height": math.ceil(h)})
    call(page, "rails")
    call(page, "decorate")
    return page


def call(page, name: str, arg=None):
    """Call a page script's function, e.g. call(page, "route", flows). Playwright calls the function it is given
    with `arg`, so no glue code is needed."""
    return page.evaluate(f"schemantic.{name}", arg)


def svg_size(svg_path: Path) -> tuple[float, float]:
    head = svg_path.read_text(encoding="utf-8")[:400]
    w, h = (re.search(rf'{k}="([\d.]+)"', head).group(1) for k in ("width", "height"))
    return float(w), float(h)


def rasterise_svg(browser, svg_path: Path, png_path: Path, scale: float = 2, refused: list[str] | None = None) -> None:
    """Screenshot the SVG (in CSS px) at `scale` (dpi / 96), and record the dpi in the PNG."""
    width, height = svg_size(svg_path)
    page = browser.new_page(viewport={"width": math.ceil(width), "height": math.ceil(height)}, device_scale_factor=scale)
    offline(page, refused)
    page.goto(svg_path.resolve().as_uri())
    page.evaluate(fonts_ready())
    page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": width, "height": height})
    page.close()
    with Image.open(png_path) as im:
        img = im.copy()
    img.save(png_path, dpi=(96 * scale, 96 * scale))


def on_sheet(plate_png: Path, fit: dict, dpi: float) -> None:
    """Put a plate raster (made at fit['scale'] * dpi / 96) on a white sheet of exactly the paper's size at dpi."""
    px = lambda mm: round(mm / 25.4 * dpi)  # noqa: E731
    sheet = Image.new("RGB", (px(fit["sheet_mm"][0]), px(fit["sheet_mm"][1])), "white")
    with Image.open(plate_png) as im:
        sheet.paste(im.convert("RGB"), (px(fit["offset_mm"][0]), px(fit["offset_mm"][1])))
    sheet.save(plate_png, dpi=(dpi, dpi))
