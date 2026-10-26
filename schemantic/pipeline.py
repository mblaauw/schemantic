"""One pipeline, one Chromium: check the spec, lay out, route, lint, export the SVG, check parity against the same
page, and write the PNG. `lint` is this without the deliverables."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from .browser import launch, open_plate, rasterise_svg
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


def build(spec_path: str | Path, out: str | Path, *, deliver: bool = True, scale: float = 2,
          theme: str | Path | None = None, theme_css: str = "") -> dict:
    """Run the whole pipeline. With deliver, writes <out>/<name>.svg and .png; work files go to <out>/_work/.
    Returns the report: errors and warnings (each with a hint), density, parity, and the paths written."""
    spec_path, out = Path(spec_path), Path(out)
    name, work = spec_path.stem, Path(out) / "_work"
    report = {"spec": str(spec_path), "errors": [], "warnings": [], "density": {}, "voids": {}, "parity": None,
              "svg": None, "png": None, "snapshot": None, "fonts": [], "flow_problems": []}
    spec, issues = read_spec(spec_path)
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
                page = open_plate(browser, html, spec)
                flows = draw_flows(page, spec)
                issues += problems_as_findings(flows)
                dom = dom_lint(page, flows["segs"])
                issues += dom["issues"]
                svg, fonts = export_svg(page, spec)
                svg_path = (out if deliver else work) / f"{name}.svg"
                svg_path.write_text(svg, encoding="utf-8")
                snap_path = work / f"{name}.snapshot.json"
                snap_path.write_text(json.dumps(snapshot(page, svg, flows["segs"]), indent=1, ensure_ascii=False),
                                     encoding="utf-8")
                # Parity: the page as laid out (connectors included) against the SVG rasterised at the same scale.
                page.locator("#plate").screenshot(path=str(work / "html.png"))
                page.close()
                rasterise_svg(browser, svg_path, work / "svg.png", scale=1)
                par = image_diff(work / "html.png", work / "svg.png", work / "parity-diff.png")
                if deliver:
                    rasterise_svg(browser, svg_path, out / f"{name}.png", scale=scale)
                    report["png"] = str(out / f"{name}.png")
            finally:
                browser.close()
        if par["fail"]:
            issues.append({"level": "error", "check": "svg-parity", "id": "(plate)", "detail": par["detail"]})
        elif par["count"]:
            issues.append({"level": "warning", "check": "svg-parity", "id": "(plate)", "detail": par["detail"]})
        report.update(density=dom["density"], voids=dom["voids"], fonts=fonts, svg=str(svg_path) if deliver else None, snapshot=str(snap_path),
                      parity={"pixels": par["count"], "regions": par["regions"], "detail": par["detail"]},
                      flow_problems=[dict(flow=spec["flows"][x["i"]], check=x["check"], problem=x["problem"])
                                     for x in flows["problems"]])
    report["errors"] = [with_hint(i) for i in issues if i["level"] == "error"]
    report["warnings"] = [with_hint(i) for i in issues if i["level"] == "warning"]
    return report
