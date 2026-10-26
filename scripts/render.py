#!/usr/bin/env python3
"""Render a plate spec to SVG and PNG.

Usage: python3 scripts/render.py <spec.yaml> [--out DIR] [--scale 2]

Writes <name>.svg and <name>.png to DIR (default: out/). The intermediate HTML goes to
DIR/_work/ for debugging only; it is not a deliverable. Exits 1 if the spec is invalid or a
flow cannot be drawn; run lint.py for the full layout checks.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platelib as pl  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("--out", default="out")
    ap.add_argument("--scale", type=float, default=2, help="PNG pixel ratio (default 2)")
    a = ap.parse_args()

    spec_path = Path(a.spec)
    spec, errors = pl.read_spec(spec_path)
    errors = errors or pl.schema_errors(spec) or pl.semantic_errors(spec)
    errors = [e for e in errors if e["level"] == "error"]
    if errors:
        print(json.dumps({"rendered": False, "errors": errors}, indent=2, ensure_ascii=False))
        return 1

    out = Path(a.out)
    (out / "_work").mkdir(parents=True, exist_ok=True)
    name = spec_path.stem
    html = pl.build_html(spec)
    (out / "_work" / f"{name}.html").write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = pl.open_plate(browser, html, spec)
        flows = pl.draw_flows(page, spec)
        svg, fonts = pl.export_svg(page, spec)
        svg_path, png_path = out / f"{name}.svg", out / f"{name}.png"
        svg_path.write_text(svg, encoding="utf-8")
        snap = pl.snapshot(page, svg, flows["segs"])
        (out / "_work" / f"{name}.snapshot.json").write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
        pl.rasterise_svg(browser, svg_path, spec, png_path, scale=a.scale)
        browser.close()

    report = {"rendered": True, "svg": str(svg_path), "png": str(png_path), "fonts": fonts,
              "flow_problems": [dict(flow=spec["flows"][x["i"]], check=x["check"], problem=x["problem"]) for x in flows["problems"]]}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if flows["problems"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # the skill reads JSON; a traceback would leave it guessing
        print(json.dumps({"rendered": False, "errors": [pl.internal_error(exc)]}, indent=2, ensure_ascii=False))
        sys.exit(1)
