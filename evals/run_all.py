#!/usr/bin/env python3
"""Grade every run under a runs folder and print a pass-rate table per model and condition.

Usage: python evals/run_all.py <runs dir>      # runs/<model>/<with|without>/<case>/, plus judge.json per run
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import grade  # noqa: E402

CASES = Path(__file__).resolve().parent / "cases"


def main(runs: Path) -> None:
    rows = []
    for model in sorted(p for p in runs.iterdir() if p.is_dir()):
        for cond in ("without", "with"):
            results = []
            for case in sorted(CASES.iterdir()):
                run = model / cond / case.name
                if not run.is_dir():
                    continue
                auto = grade(case, run)
                judge_file = run / "judge.json"
                judge = json.loads(judge_file.read_text()) if judge_file.exists() else {}
                judged = bool(judge) and judge.get("claim_in_title") and judge.get("archetype_fits") \
                    and not judge.get("invented") and not judge.get("defects")
                results.append((case.name, auto["pass"], judged, auto["passed"], judge))
            if results:
                rows.append((model.name, cond, results))
    for model, cond, results in rows:
        both = sum(a and j for _, a, j, _, _ in results)
        print(f"{model} {cond}: {both}/{len(results)} pass (automated {sum(a for _, a, _, _, _ in results)}, "
              f"judged {sum(bool(j) for _, _, j, _, _ in results)})")
        for name, a, j, passed, _ in results:
            failed = [k for k, v in passed.items() if not v]
            print(f"  {name:26} auto={'pass' if a else 'FAIL ' + ','.join(failed)} judge={'pass' if j else 'FAIL'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
