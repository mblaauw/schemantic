#!/usr/bin/env python3
"""Correction evals: a delivered plate, one sentence from the user, and whether exactly that changed. Graded by code,
so no judge: the sentence was carried out, nothing else in the spec changed, the plate still builds clean, and how many
parts changed or moved.

Usage:
  python evals/corrections.py prepare <runs> --skill <dir> [--models sonnet haiku] [--repeats 2]
      builds each case's plate into <runs>/<model>/<case>/<n>/ and writes <runs>/prompts.json: one agent per prompt.
  python evals/corrections.py grade <runs>
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from schemantic import pipeline  # noqa: E402
from schemantic.review import changed_parts, moved_parts  # noqa: E402

EVENTS, INVOICES = "orderplatform-eventbus", "invoicing-before-after"


def panel(spec: dict, pid: str) -> dict:
    return next(p for p in spec["panels"] if p["id"] == pid)


def names(spec: dict, pid: str) -> list[str]:
    return [c["name"] for c in panel(spec, pid).get("cards", [])]


def joined(spec: dict, a: str, b: str) -> bool:
    """A flow from a to b, either the panel or a card in it."""
    def ends(pid):
        return {pid} | {c["id"] for c in panel(spec, pid).get("cards", []) if c.get("id")} | {
            f"{pid}.card{i}" for i in range(len(panel(spec, pid).get("cards", [])))}
    return any(f["from"] in ends(a) and f["to"] in ends(b) for f in spec.get("flows", []))


def status_of(spec: dict, pid: str, name: str) -> str | None:
    return next((c.get("status") for c in panel(spec, pid)["cards"] if c["name"] == name), None)


# Each case: the plate, what the user says, the paths that may change (regexes on flat()), and whether it was done.
CASES = {
    "rename": (EVENTS, "Rename the Search index card to Product search index.", [r"panels/search/cards/"],
               lambda s: "Product search index" in names(s, "search") and "Search index" not in names(s, "search")),
    "move-arrow": (EVENTS, "Notifications no longer reads the bus. Drop that arrow and connect Shipping to Notifications instead.",
                   [r"flows/", r"panels/(shipping|notify|bus)/cards/.*/id$"],
                   lambda s: not joined(s, "bus", "notify") and joined(s, "shipping", "notify")),
    "drop-card": (EVENTS, "Drop the Capacity card from Operations.", [r"panels/ops/cards/Capacity"],
                  lambda s: "Capacity" not in names(s, "ops")),
    "settled": (EVENTS, "The retention question is settled: 14 days is enough. Take it off the plate.",
                [r"panels/bus/chips", r"footer/open_questions"],
                lambda s: "14 days of retention" not in json.dumps(s.get("footer", {})) + json.dumps(panel(s, "bus").get("chips", []))),
    "status": (INVOICES, "The Payments API is not live yet. Mark it as planned.",
               [r"panels/bankapi/cards/Payments API/(status|status_ref|refs|assumed)"],
               lambda s: status_of(s, "bankapi", "Payments API") == "planned"),
    "add-card": (INVOICES, "Add an Audit trail card to Reconciliation: it keeps every match for seven years.",
                 [r"panels/recon/cards/Audit trail"],
                 lambda s: "Audit trail" in names(s, "recon")),
}
PROMPT = """You are working in the folder {folder}. It holds a plate you delivered earlier: the spec plates/{name}.yaml, built \
into plates/out.

The user says:

{ask}

You have a skill for this: read {skill}/SKILL.md and follow it. Treat {skill} as read-only. Do not ask questions. When \
done, reply with what changed and the paths of the plate."""
FREE = ("sources", "brief")  # a correction may cite the user as a source


def flat(spec: dict) -> dict[str, object]:
    """Every value by a path that does not depend on order: panels by id, cards by name, flows by their ends."""
    out: dict[str, object] = {}

    def walk(v, where):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{where}/{k}")
        elif isinstance(v, list) and all(isinstance(x, dict) and ("id" in x or "name" in x or "from" in x) for x in v) and v:
            for x in v:
                key = x.get("name") if where.endswith("cards") else x.get("id") or x.get("name") or f"{x['from']}->{x['to']}"
                walk(x, f"{where}/{key}")
        else:
            out[where.lstrip("/")] = v
    walk({k: v for k, v in spec.items() if k not in FREE}, "")
    return out


def stray(before: dict, after: dict, allowed: list[str]) -> list[str]:
    a, b = flat(before), flat(after)
    return sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k) and not any(re.search(r, k) for r in allowed))


def prepare(runs: Path, skill: Path, models: list[str], repeats: int) -> list[dict]:
    out = []
    for model in models:
        for case, (name, ask, _, _) in CASES.items():
            for n in range(1, repeats + 1):
                folder = runs / model / case / str(n)
                (folder / "plates").mkdir(parents=True)
                shutil.copy(ROOT / "examples" / f"{name}.yaml", folder / "plates" / f"{name}.yaml")
                report = pipeline.build(folder / "plates" / f"{name}.yaml", folder / "plates" / "out")
                assert not report["errors"], report["errors"]
                out.append({"model": model, "case": case, "n": n, "folder": str(folder.resolve()),
                            "prompt": PROMPT.format(folder=folder.resolve(), name=name, ask=ask, skill=skill.resolve())})
    (runs / "prompts.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def grade_run(case: str, folder: Path) -> dict:
    name, _, allowed, done = CASES[case]
    path = folder / "plates" / f"{name}.yaml"
    before = yaml.safe_load((ROOT / "examples" / f"{name}.yaml").read_text(encoding="utf-8"))
    after = yaml.safe_load(path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        first = pipeline.build(ROOT / "examples" / f"{name}.yaml", tmp, deliver=False)
        base = json.loads(Path(first["snapshot"]).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        report = pipeline.build(path, tmp, deliver=False)
        snap = json.loads(Path(report["snapshot"]).read_text(encoding="utf-8")) if report["snapshot"] else None
    others = stray(before, after, allowed)
    result = {"done": bool(done(after)), "stray": others, "lint_clean": not report["errors"],
              "used_baseline": (folder / "plates" / "out" / "_work" / "baseline").exists(),
              "parts": len(after["panels"]) + 2,
              "changed": changed_parts(base, snap, after) if snap else None, "moved": moved_parts(base, snap, after) if snap else None}
    result["pass"] = result["done"] and not others and result["lint_clean"]
    return result


def grade(runs: Path) -> list[dict]:
    rows = []
    for model in sorted(p for p in runs.iterdir() if p.is_dir()):
        for case in CASES:
            for run in sorted((model / case).glob("*")):
                rows.append({"model": model.name, "case": case, "n": run.name, **grade_run(case, run)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("runs", type=Path)
    p.add_argument("--skill", type=Path, required=True)
    p.add_argument("--models", nargs="+", default=["sonnet", "haiku"])
    p.add_argument("--repeats", type=int, default=2)
    g = sub.add_parser("grade")
    g.add_argument("runs", type=Path)
    a = ap.parse_args()
    if a.cmd == "prepare":
        print(f"{len(prepare(a.runs, a.skill, a.models, a.repeats))} runs; prompts in {a.runs / 'prompts.json'}")
        return
    rows = grade(a.runs)
    for r in rows:
        print(f"{r['model']:7s} {r['case']:11s} {r['n']} {'pass' if r['pass'] else 'FAIL'} done={r['done']} lint={r['lint_clean']} "
              f"baseline={r['used_baseline']} changed={r['changed']} moved={len(r['moved'] or [])} stray={r['stray']}")
    print(f"{sum(r['pass'] for r in rows)}/{len(rows)} pass")


if __name__ == "__main__":
    main()
