#!/usr/bin/env python3
"""Lint the specs of a judged eval round again with the code as it is now, and set each check beside what the judges said.

Usage: python evals/replay.py <runs dir> [--show <check>] [--spec-only] [--jobs N]

A round costs a hundred agent runs; its specs and verdicts stay. A new check, or a changed one, is tried on them first:
does it fire on the plates a judge faulted for that kind of defect, and stay quiet on the ones the judges passed? No agent
runs, so it says nothing about what an agent would do with the finding, only whether the finding is true.

Per check: the plates it fires on, how many of those a judge faulted for the kind of defect the check is about, and how
many plates the judges faulted for that kind in all. `--show` lists each finding of one check beside the judge's own words.
`--spec-only` runs the checks that need no browser, in seconds instead of minutes.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from schemantic import pipeline  # noqa: E402

# The review question a judge's defect answers, from the word it starts with (evals/judge.md asks for one line each).
KINDS = [("holes", r"holes?"), ("path", r"path"), ("truth", r"truth|open ends"), ("colour", r"colou?r"), ("arrows", r"arrows?"),
         ("words", r"words"), ("message", r"message"), ("footer", r"footer"), ("series", r"series")]
# The kind of defect each check is there to prevent; a check not listed is reported without a comparison.
ABOUT = {"story": "path", "route-end": "path", "orphan": "path", "traceability": "truth", "brief-only": "truth",
         "role-fit": "colour", "void": "holes", "card-width": "holes", "arrow-crossing": "arrows", "arrow-routing": "arrows",
         "arrow-label": "arrows", "footer-share": "footer", "series": "series"}


def kind(defect: str) -> str:
    head = re.sub(r"^\W*(q\d+\W*)?", "", defect.lower())[:24]
    return next((k for k, pattern in KINDS if re.match(rf"({pattern})\b", head)), "other")


def judged_kinds(judge: dict) -> dict[str, list[str]]:
    out = collections.defaultdict(list)
    for d in judge.get("defects", []):
        out[kind(d)].append(d)
    for d in judge.get("invented", []):
        out["truth"].append(f"Invented: {d}")
    return out


def delivered(run: Path) -> list[Path]:
    """The specs a run delivered: those with a published plate of the same name (see grade.py)."""
    built = {p.stem for p in run.rglob("*.png") if "_work" not in p.parts}
    specs = []
    for p in sorted(run.rglob("*.y*ml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) if p.stem in built else None
        if isinstance(doc, dict) and "panels" in doc:
            specs.append(p)
    return specs


def lint(job: tuple[str, bool]) -> tuple[str, list[dict]]:
    run, spec_only = job
    findings = []
    with tempfile.TemporaryDirectory() as tmp:
        for spec in delivered(Path(run)):
            if spec_only:
                found = pipeline.grouped(pipeline.prepare(spec, None, "")[2])
            else:
                found = pipeline.build(spec, tmp, deliver=False)
            findings += [{**f, "spec": spec.name} for f in found["errors"] + found["warnings"]]
    return run, findings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", type=Path)
    ap.add_argument("--show", metavar="CHECK", help="list every finding of this check beside the judge's defects of its kind")
    ap.add_argument("--spec-only", action="store_true", help="only the checks that need no browser")
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    runs = sorted(p.parent for p in args.runs.rglob("judge.json"))
    with ProcessPoolExecutor(args.jobs) as pool:
        linted = dict(pool.map(lint, [(str(r), args.spec_only) for r in runs]))
    judged = {str(r): judged_kinds(json.loads((r / "judge.json").read_text(encoding="utf-8"))) for r in runs}

    fires = collections.defaultdict(lambda: collections.defaultdict(list))  # check -> run -> findings
    for run, findings in linted.items():
        for f in findings:
            fires[f["check"]][run].append(f)
    print(f"{len(runs)} judged runs under {args.runs}")
    print(f"{'check':16} {'level':8} {'plates':>6} {'findings':>8}   judged for the same kind")
    for check in sorted(fires, key=lambda c: -len(fires[c])):
        on = fires[check]
        level = "error" if any(f["level"] == "error" for fs in on.values() for f in fs) else "warning"
        about = ABOUT.get(check)
        line = f"{check:16} {level:8} {len(on):6} {sum(map(len, on.values())):8}   "
        if about:
            faulted = {r for r in judged if judged[r].get(about)}
            line += f"{len(faulted & set(on))} of those; {len(faulted)} plates have a {about} defect"
        print(line)
    if args.show:
        about = ABOUT.get(args.show)
        for run in sorted(fires.get(args.show, {})):
            print(f"\n{Path(run).relative_to(args.runs)}")
            for f in fires[args.show][run]:
                print(f"  lint   {f['id']}: {f['detail']}")
            for d in judged[run].get(about, []) if about else []:
                print(f"  judge  {d}")
        if about:
            quiet = sorted(r for r in judged if judged[r].get(about) and r not in fires.get(args.show, {}))
            print(f"\n{len(quiet)} plates with a {about} defect where {args.show} is quiet:")
            for run in quiet:
                print(f"\n{Path(run).relative_to(args.runs)}")
                for d in judged[run][about]:
                    print(f"  judge  {d}")


if __name__ == "__main__":
    main()
