"""SVG assembly and fonts: the HTML loads the bundled faces whole; each SVG embeds a subset of the glyphs it uses."""
from __future__ import annotations

import base64
import io
from functools import cache

from fontTools import subset

from .browser import call
from .config import FONTS_DIR

# Bundled faces, loaded through @font-face so layout never depends on installed fonts.
FONTS = [("Inter", 400, "Inter-Regular.woff2"), ("Inter", 500, "Inter-Medium.woff2"),
         ("Inter", 600, "Inter-SemiBold.woff2"), ("Inter", 700, "Inter-Bold.woff2"),
         ("Inter", 800, "Inter-ExtraBold.woff2"), ("DejaVu Sans Mono", 400, "DejaVuSansMono.woff2")]


def font_face(family: str, weight: int, data: bytes) -> str:
    uri = "data:font/woff2;base64," + base64.b64encode(data).decode("ascii")
    return f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; src: url({uri}) format('woff2'); }}"


@cache
def font_css() -> str:
    return "\n".join(font_face(fam, w, (FONTS_DIR / file).read_bytes()) for fam, w, file in FONTS)


def subset_font_css(used: dict[str, str]) -> str:
    """@font-face rules holding only the glyphs each bundled face draws. `used` maps 'Family|weight' to text."""
    rules = []
    for key, text in used.items():
        family, weight = key.split("|")
        faces = [f for f in FONTS if f[0] == family]
        if not faces:
            continue  # not bundled: the viewer's own fonts decide
        _, w, file = min(faces, key=lambda f: abs(f[1] - int(weight)))  # nearest weight, as the browser picks
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.drop_tables.append("FFTM")  # FontForge timestamp; fontTools cannot subset it and warns
        sub = subset.Subsetter(opts)
        font = subset.load_font(str(FONTS_DIR / file), opts)
        sub.populate(text=text)
        sub.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, opts)
        rules.append(font_face(family, w, buf.getvalue()))
    return "\n".join(rules)


def export_svg(page, spec: dict) -> tuple[str, list[str]]:
    """The laid-out page as a standalone SVG, and the font faces it uses ('Inter 600', ...)."""
    d = call(page, "exportSvg")
    title = spec["title"] + (f" — {spec['subtitle']}" if spec.get("subtitle") else "")

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;")
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{d["w"]:g}" height="{d["h"]:g}" '
            f'viewBox="0 0 {d["w"]:g} {d["h"]:g}" role="img" lang="{spec["canvas"]["lang"]}">\n'
            f'<title>{esc(title)}</title>\n'
            f'<defs><style>\n{subset_font_css(d["used"])}\n</style></defs>\n')
    fonts = sorted(k.replace("|", " ") for k in d["used"])
    return head + "\n".join(d["items"]) + "\n</svg>\n", fonts
