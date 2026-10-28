"""One pipeline, one Chromium: check the spec, lay out, route, lint, export the SVG, check parity against the same
page, and write the PNG. `lint` is this without the deliverables. Deliverables are written to <out>/_work/ first and
move to <out>/ only when the build has no errors, so a failed build never publishes a plate."""
from __future__ import annotations

import hashlib
import json
import os
import platform
from importlib.metadata import version
from pathlib import Path

from playwright.sync_api import sync_playwright

from . import __version__, outline
from .browser import launch, open_plate, rasterise_svg, svg_size
from .config import PRINT_SIZES, ROOT, png_size
from .export import export_svg
from .findings import with_hint
from .html import build_html
from .images import image_diff, snapshot
from .lint import dom_lint
from .route import draw_flows, problems_as_findings
from .spec import check, read_spec


def load_theme(spec: dict, spec_path: Path, theme: str | Path | None) -> tuple[str, list[dict]]:
    """The theme CSS: the --theme file if given, else canvas.theme relative to the spec, else none."""
    named = (spec.get("canvas") or {}).get("theme") if isinstance(spec.get("canvas"), dict) else None
    path = Path(theme) if theme else (spec_path.parent / named if named else None)
    if path is None:
        return "", []
    if not path.is_file():
        return "", [{"level": "error", "check": "canvas", "id": "canvas.theme", "detail": f"theme file not found: {path}"}]
    return path.read_text(encoding="utf-8"), []


def manifest(spec: dict, spec_path: Path, theme_css: str, chromium: str) -> dict:
    """What made this plate, so a render can be reproduced: versions, and digests of the spec, theme and fonts."""
    digest = lambda data: hashlib.sha256(data).hexdigest()[:16]
    return {"schemantic": __version__, "spec_version": spec.get("spec_version", 1), "spec_sha256": digest(spec_path.read_bytes()),
            "theme_sha256": digest(theme_css.encode()) if theme_css else None, "chromium": chromium,
            "playwright": version("playwright"), "python": platform.python_version(), "platform": platform.system().lower(),
            "fonts": {f.name: digest(f.read_bytes()) for f in sorted((ROOT / "assets" / "fonts").glob("*.woff2"))}}


def build(spec_path: str | Path, out: str | Path, *, deliver: bool = True, scale: float = 2,
          theme: str | Path | None = None, theme_css: str = "", outline_text: bool = False) -> dict:
    """Run the whole pipeline. With deliver, writes <out>/<name>.svg and .png; work files go to <out>/_work/.
    Returns the report: errors and warnings (each with a hint), density, parity, the build manifest, and the paths
    published (None when the build has errors; then `preview` names the unpublished files in _work/)."""
    spec_path, out = Path(spec_path), Path(out)
    name, work = spec_path.stem, Path(out) / "_work"
    report = {"spec": str(spec_path), "errors": [], "warnings": [], "density": {}, "voids": {}, "parity": None,
              "svg": None, "png": None, "outline": None, "snapshot": None, "fonts": [], "flow_problems": [], "build": None, "preview": None}
    spec, issues = read_spec(spec_path)
    staged: dict[str, Path] = {}  # deliverables written to _work/, waiting for a clean report
    if not issues:
        file_css, issues = load_theme(spec, spec_path, theme)
        theme_css = "\n".join(c for c in (file_css, theme_css) if c)
    if not issues:
        issues = check(spec, theme_css)
    if not any(i["level"] == "error" for i in issues):
        work.mkdir(parents=True, exist_ok=True)
        html = build_html(spec, theme_css)
        (work / f"{name}.html").write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            browser = launch(p)
            try:
                report["build"] = manifest(spec, spec_path, theme_css, browser.version)
                page = open_plate(browser, html, spec)
                flows = draw_flows(page, spec)
                issues += problems_as_findings(flows)
                dom = dom_lint(page, flows["segs"])
                issues += dom["issues"]
                svg, fonts = export_svg(page, spec)
                snap = snapshot(page, svg, flows["segs"])
                svg_path = work / f"{name}.svg"
                # Parity checks the layout with real text. With outline_text the deliverable has glyph paths instead,
                # and the text version stays in _work/ for the parity check.
                parity_svg = work / f"{name}.text.svg" if outline_text else svg_path
                parity_svg.write_text(svg, encoding="utf-8")
                if outline_text:
                    from .glyphs import outline_text as to_paths
                    svg_path.write_text(to_paths(svg), encoding="utf-8")
                snap_path = work / f"{name}.snapshot.json"
                snap_path.write_text(json.dumps(snap, indent=1, ensure_ascii=False),
                                     encoding="utf-8")
                # Parity: the page as laid out (connectors included) against the SVG rasterised at the same scale.
                page.locator("#plate").screenshot(path=str(work / "html.png"))
                page.close()
                rasterise_svg(browser, parity_svg, work / "svg.png", scale=1)
                par = image_diff(work / "html.png", work / "svg.png", work / "parity-diff.png")
                if deliver:
                    (work / f"{name}.md").write_text(outline.markdown(spec), encoding="utf-8")
                    (work / f"{name}.build.json").write_text(json.dumps(report["build"], indent=1) + "\n", encoding="utf-8")
                    size = spec["canvas"]["size"]
                    rasterise_svg(browser, svg_path, work / f"{name}.png", scale=scale,
                                  size=png_size(size, *svg_size(svg_path), scale) if size in PRINT_SIZES else None)
                    staged = {k: work / f"{name}.{ext}" for k, ext in
                              (("svg", "svg"), ("png", "png"), ("outline", "md"), ("manifest", "build.json"))}
            finally:
                browser.close()
        if par["fail"]:
            issues.append({"level": "error", "check": "svg-parity", "id": "(plate)", "detail": par["detail"]})
        elif par["count"]:
            issues.append({"level": "warning", "check": "svg-parity", "id": "(plate)", "detail": par["detail"]})
        report.update(density=dom["density"], voids=dom["voids"], fonts=fonts, snapshot=str(snap_path),
                      parity={"pixels": par["count"], "regions": par["regions"], "detail": par["detail"]},
                      flow_problems=[dict(flow=spec["flows"][x["i"]], check=x["check"], problem=x["problem"])
                                     for x in flows["problems"]])
    report["errors"] = [with_hint(i) for i in issues if i["level"] == "error"]
    if staged:
        if report["errors"]:
            report["preview"] = {k: str(v) for k, v in staged.items()}
        else:
            out.mkdir(parents=True, exist_ok=True)
            for k, src in staged.items():
                os.replace(src, out / src.name)  # atomic per file: a reader sees the old plate or the new one
                if k != "manifest":
                    report[k] = str(out / src.name)
    report["warnings"] = [with_hint(i) for i in issues if i["level"] == "warning"]
    return report
