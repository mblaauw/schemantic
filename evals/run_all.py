#!/usr/bin/env python3
"""Grade every run under a runs folder and print a pass-rate table per model and condition.

Usage: python evals/run_all.py <runs dir>
    runs/<model>/<with|without>/<case>/ holds one run per case; runs/<model>/<with|without>/<case>/<n>/ holds
    repeats (see harness.py). A run's judge.json (evals/judge.md) is its judged half.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import grade  # noqa: E402

CASES = Path(__file__).resolve().parent / "cases"


def runs_of(folder: Path) -> list[Path]:
    """The case folder itself, or its numbered repeats."""
    repeats = sorted((p for p in folder.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name))
    return repeats or [folder]


def main(runs: Path) -> None:
    rows = []
    for model in sorted(p for p in runs.iterdir() if p.is_dir()):
        for cond in ("without", "with"):
            results = []
            for case in sorted(CASES.iterdir()):
                if not (model / cond / case.name).is_dir():
                    continue
                for run in runs_of(model / cond / case.name):
                    auto = grade(case, run)
                    judge_file = run / "judge.json"
                    judge = json.loads(judge_file.read_text()) if judge_file.exists() else {}
                    judged = bool(judge) and judge.get("claim_in_title") and judge.get("archetype_fits") \
                        and not judge.get("invented") and not judge.get("defects")
                    label = case.name if run == model / cond / case.name else f"{case.name}/{run.name}"
                    results.append((label, auto["pass"], judged, auto["passed"], judge))
            if results:
                rows.append((model.name, cond, results))
    for model, cond, results in rows:
        both = sum(a and j for _, a, j, _, _ in results)
        judged = [j for *_, j in results if j]
        defects = sum(len(j.get("defects", [])) for j in judged) / len(judged) if judged else float("nan")
        print(f"{model} {cond}: {both}/{len(results)} pass (automated {sum(a for _, a, _, _, _ in results)}, "
              f"judged {sum(bool(j) for _, _, j, _, _ in results)}, nothing invented "
              f"{sum(not j.get('invented') for j in judged)}/{len(judged)}, {defects:.2f} defects per plate)")
        for name, a, j, passed, _ in results:
            failed = [k for k, v in passed.items() if not v]
            print(f"  {name:28} auto={'pass' if a else 'FAIL ' + ','.join(failed)} judge={'pass' if j else 'FAIL'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
