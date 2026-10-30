#!/usr/bin/env python3
"""Set up an eval run, blind it for the judge, and bring the verdicts back. The agents themselves are started by
whoever runs the eval (one agent per prompt, given nothing but its prompt).

Usage:
  python evals/harness.py prepare <runs> --skill <dir> [--models sonnet haiku] [--repeats 3] [--cases 2-repo-en ...]
      copies each case's inputs to <runs>/<model>/with/<case>/<n>/ and writes <runs>/prompts.json: one entry per
      run with its folder and the prompt to give the agent. <dir> is a read-only copy of the skill.
  python evals/harness.py blind <runs> <judge dir> [--yardstick <dir>]
      copies every finished run to <judge dir>/r<random>/ with a case.txt, so the judge cannot tell model or run
      apart; the key goes to <runs>/blind.json, outside the judge's folder. <runs>/judges.json holds one prompt per
      four runs, from judge_prompt.md: start one agent per prompt, with nothing else. Change that wording and the
      numbers stop comparing (one word, "strict", added 25% to the defects on the same plates). <dir> holds a frozen
      judge.md and review.md; by default, the current ones.
  python evals/harness.py unblind <runs>
      copies each judge.json back into its run folder.

Then: python evals/run_all.py <runs>
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

EVALS = Path(__file__).resolve().parent
CASES = EVALS / "cases"
PER_JUDGE = 4
PROMPT = """You are working in the folder {folder} (the "run folder"). Its inputs/ subfolder holds the sources.

The user asks:

{ask}

You have a skill for this: read {skill}/SKILL.md and follow it step by step. Treat {skill} as read-only: never \
write into it. Write every file you make (specs, builds) inside the run folder, for example in plates/. Do not ask \
questions; decide as the skill says. When done, reply with the paths of the plates you delivered, their one \
message, and their open questions."""


def prepare(runs: Path, skill: Path, models: list[str], repeats: int, cases: list[str] | None = None) -> list[dict]:
    out = []
    for model in models:
        for case in sorted(p for p in CASES.iterdir() if p.is_dir() and (not cases or p.name in cases)):
            for n in range(1, repeats + 1):
                folder = runs / model / "with" / case.name / str(n)
                if folder.exists():
                    raise SystemExit(f"{folder} exists; prepare a new runs folder")
                shutil.copytree(case / "inputs", folder / "inputs")
                ask = (case / "prompt.md").read_text(encoding="utf-8").strip()
                out.append({"model": model, "case": case.name, "n": n, "folder": str(folder.resolve()),
                            "prompt": PROMPT.format(folder=folder.resolve(), ask=ask, skill=skill.resolve())})
    (runs / "prompts.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def finished(runs: Path) -> list[Path]:
    return sorted(p.parent for p in runs.glob("*/with/*/*/inputs") if any(p.parent.rglob("*.png")))


def judge_prompts(judge: Path, names: list[str], yardstick: Path | None = None) -> list[str]:
    """One prompt per PER_JUDGE runs, in a random order, so no judge sees one case or model only."""
    judge_md = (yardstick or EVALS) / "judge.md"
    review_md = yardstick / "review.md" if yardstick else EVALS.parent / "references" / "review.md"
    text = (EVALS / "judge_prompt.md").read_text(encoding="utf-8")
    names = random.sample(names, len(names))
    return [text.format(judge_dir=judge.resolve(), folders=", ".join(names[i:i + PER_JUDGE]), cases=CASES,
                        judge_md=judge_md.resolve(), review_md=review_md.resolve()) for i in range(0, len(names), PER_JUDGE)]


def blind(runs: Path, judge: Path, yardstick: Path | None = None) -> dict:
    names = random.sample(range(100000, 1000000), len(finished(runs)))
    key = {}
    for run, name in zip(finished(runs), names, strict=True):
        dest = judge / f"r{name}"
        shutil.copytree(run, dest, ignore=shutil.ignore_patterns("_work", "inputs", "*.json", "*.sh", "*.py"))
        (dest / "case.txt").write_text(run.parent.name + "\n", encoding="utf-8")
        key[dest.name] = str(run)
    (runs / "blind.json").write_text(json.dumps({"judge": str(judge), "key": key}, indent=1) + "\n", encoding="utf-8")
    prompts = judge_prompts(judge, list(key), yardstick)
    (runs / "judges.json").write_text(json.dumps(prompts, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return key


def unblind(runs: Path) -> list[str]:
    blind_key = json.loads((runs / "blind.json").read_text(encoding="utf-8"))
    missing = []
    for name, run in blind_key["key"].items():
        verdict = Path(blind_key["judge"]) / name / "judge.json"
        if verdict.exists():
            shutil.copy(verdict, Path(run) / "judge.json")
        else:
            missing.append(name)
    return missing


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("runs", type=Path)
    p.add_argument("--skill", type=Path, required=True)
    p.add_argument("--models", nargs="+", default=["sonnet", "haiku"])
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--cases", nargs="+", help="only these cases (default: all)")
    b = sub.add_parser("blind")
    b.add_argument("runs", type=Path)
    b.add_argument("judge", type=Path)
    b.add_argument("--yardstick", type=Path, help="a folder with a frozen judge.md and review.md")
    u = sub.add_parser("unblind")
    u.add_argument("runs", type=Path)
    a = ap.parse_args()
    if a.cmd == "prepare":
        print(f"{len(prepare(a.runs, a.skill, a.models, a.repeats, a.cases))} runs; prompts in {a.runs / 'prompts.json'}")
    elif a.cmd == "blind":
        print(f"{len(blind(a.runs, a.judge, a.yardstick))} runs blinded into {a.judge}; judge prompts in {a.runs / 'judges.json'}")
    else:
        missing = unblind(a.runs)
        print("all verdicts back" if not missing else f"no verdict yet for {', '.join(missing)}")


if __name__ == "__main__":
    main()
