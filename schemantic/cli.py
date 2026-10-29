"""Command line: `schemantic build | lint | series | doctor | icons | gallery | docs | offline | verify | smoke`.
Every command prints JSON and exits 1 on errors; an unexpected failure is an `internal` finding, never a traceback,
because an agent reads the output."""

from __future__ import annotations

import argparse
import json
import sys


def _spec_command(sub, name: str, help_: str, scale: bool):
    p = sub.add_parser(name, help=help_)
    p.add_argument("spec")
    p.add_argument("--out", default="out", help="output folder (default: out)")
    p.add_argument("--theme", help="a CSS file appended after tokens.css (overrides canvas.theme)")
    if scale:
        p.add_argument("--dpi", type=float, default=192, help="PNG resolution: 96 is 1 px per CSS px (default 192)")
        p.add_argument("--outline-text", action="store_true", help="write text as glyph outlines (needs uharfbuzz)")
    return p


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="schemantic", description="From a YAML spec to a finished architecture plate.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    _spec_command(sub, "build", "check, lay out, lint and write <name>.svg and <name>.png", scale=True)
    _spec_command(sub, "lint", "build without writing deliverables; report only", scale=False)
    r = sub.add_parser("series", help="check the parts of a series against each other: numbering, language, arrows, colours")
    r.add_argument("specs", nargs="+")
    d = sub.add_parser("doctor", help="find a Python with the dependencies and prove Chromium starts")
    d.add_argument("--no-install", action="store_true")
    i = sub.add_parser("icons", help="search the icons by name, tag and category: icons [search] <words>")
    i.add_argument("words", nargs="*")
    sub.add_parser("gallery", help="build every example and write the README images to assets/gallery/")
    g = sub.add_parser("docs", help="regenerate references/lint-fixes.md from the findings table")
    g.add_argument("--check", action="store_true", help="exit 1 if the file is out of date instead of writing it")
    o = sub.add_parser("offline", help="write an offline kit (wheels, Chromium, checksums, install.sh) to a new folder")
    o.add_argument("dest")
    v = sub.add_parser("verify", help="check an offline kit's files against its SHA256SUMS")
    v.add_argument("kit")
    s = sub.add_parser("smoke", help="build the reference plate and print its layout digest")
    s.add_argument("--expect", help="the digest it must match (an offline kit's manifest has it)")
    return ap


def run(a) -> tuple[dict, int]:
    if a.cmd == "doctor":
        from . import doctor

        return doctor.diagnose(install=not a.no_install), 0
    if a.cmd == "icons":
        from . import icons

        words = a.words[1:] if a.words[:1] == ["search"] else a.words
        # All the words must match; if none does, any word is better than an empty answer for "identity provider".
        found = (icons.search(words, limit=40) or icons.search(words, limit=40, every=False)) if words else sorted(icons.index())
        return {"icons": found, "count": len(found)}, 0
    if a.cmd == "series":
        from .findings import with_hint
        from .series import series_findings
        found = [with_hint(f) for f in series_findings(a.specs)]
        errors = [f for f in found if f["level"] == "error"]
        return {"errors": errors, "warnings": [f for f in found if f["level"] == "warning"]}, 1 if errors else 0
    if a.cmd in ("offline", "verify", "smoke"):
        from . import offline
        r = offline.bundle(a.dest) if a.cmd == "offline" else offline.verify(a.kit) if a.cmd == "verify" else \
            offline.smoke(a.expect)
        return r, 0 if r["ok"] else 1
    if a.cmd == "gallery":
        from .gallery import build_gallery

        return build_gallery(), 0
    if a.cmd == "docs":
        from .findings import LINT_FIXES, lint_fixes_md

        fresh = lint_fixes_md()
        current = LINT_FIXES.read_text(encoding="utf-8") if LINT_FIXES.exists() else ""
        if a.check:
            return {"path": str(LINT_FIXES), "current": fresh == current}, 0 if fresh == current else 1
        LINT_FIXES.write_text(fresh, encoding="utf-8")
        return {"path": str(LINT_FIXES), "written": True}, 0

    from .pipeline import build

    if a.cmd == "lint":
        r = build(a.spec, a.out, deliver=False, theme=a.theme)
        keep = ("spec", "errors", "warnings", "density", "voids", "parity")
        return {k: r[k] for k in keep}, 1 if r["errors"] else 0
    r = build(a.spec, a.out, scale=a.dpi / 96, theme=a.theme, outline_text=a.outline_text)
    return r, 1 if r["errors"] else 0


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    try:
        report, code = run(a)
    except Exception as exc:  # the skill reads JSON; a traceback would leave it guessing
        from .spec import internal_error

        report, code = {"errors": [internal_error(exc)], "warnings": []}, 1
    if a.cmd == "doctor":
        code = 0 if report.get("ok") else 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
