#!/usr/bin/env python3
"""Grade one eval run: the automated half of the rubric. Prints JSON.

Usage: python evals/grade.py <case dir> <run dir>

The run dir holds what the agent produced: one or more spec YAML files (skill runs) and the SVG/PNG images. The
checks: an image exists; every spec builds without lint errors; the archetype, language and series match the
rubric; required components appear; enough open questions, warnings, principles, statuses and steps; and no card is
invented (its name's words, or a quoted ref, must be found in the inputs). The judged half (the title is a claim,
the review questions find no defect) comes from evals/judge.md.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from schemantic import pipeline  # noqa: E402
from schemantic import spec as sp  # noqa: E402

STOP = set("the and for with from into that this then than are was were its our your their een het de van voor met "
           "naar die dat zijn wordt worden per via plus".split())
DUTCH = set("de het een en van voor met naar die dat niet ook wordt zijn bij als door".split())
ENGLISH = set("the and of for with to that not also is are by as from".split())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP}


def stem(w: str) -> str:
    return w[:5]


def traced(text: str, stems: set[str], share: float = 1.0) -> bool:
    """At least `share` of the text's words appear in the sources, compared by their first five letters."""
    ws = words(text)
    return sum(stem(w) in stems for w in ws) >= share * len(ws) if ws else False


def svg_text(path: Path) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", t) for t in re.findall(r"<text[^>]*>.*?</text>", path.read_text(encoding="utf-8")))


def language(text: str) -> str:
    tokens = re.findall(r"[a-z]+", text.lower())
    return "nl" if sum(t in DUTCH for t in tokens) > sum(t in ENGLISH for t in tokens) else "en"


def grade(case: Path, run: Path) -> dict:
    rubric = yaml.safe_load((case / "rubric.yaml").read_text(encoding="utf-8"))
    inputs = " ".join(p.read_text(encoding="utf-8") for p in (case / "inputs").rglob("*") if p.is_file())
    inputs += " " + (case / "prompt.md").read_text(encoding="utf-8")
    in_words = words(inputs)
    svgs = sorted(run.rglob("*.svg"))
    pngs = sorted(run.rglob("*.png"))
    specs = []
    for p in sorted(run.rglob("*.y*ml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "panels" in doc:
            specs.append((p, doc))
    checks: dict[str, object] = {"image": bool(svgs and pngs)}
    text = " ".join(svg_text(p) for p in svgs)

    if specs:
        errors = {}
        with tempfile.TemporaryDirectory() as tmp:
            for p, _ in specs:
                report = pipeline.build(p, tmp, deliver=False)
                if report["errors"]:
                    errors[p.name] = [f"{e['check']} {e['id']}" for e in report["errors"]]
        checks["lint_clean"] = not errors
        checks["lint_errors"] = errors
        checks["archetype"] = all(doc["archetype"] in rubric["archetype"] for _, doc in specs)
        checks["lang"] = all(doc["canvas"]["lang"] == rubric["lang"] for _, doc in specs)
        cards = [c for _, doc in specs for panel in doc["panels"] for c in panel.get("cards", [])]
        in_stems = {stem(w) for w in in_words}
        # A card is traced when its name's words are in the sources, or a ref quotes them (the text after "<source>:").
        refs_of = lambda c: [r.split(":", 1)[-1] for r in c.get("refs", [])]  # noqa: E731
        invented = [c["name"] for c in cards if c["name"].lower() not in inputs.lower()
                    and not traced(c["name"], in_stems) and not any(traced(r, in_stems, 0.6) for r in refs_of(c))]
        # A plate in another language than its sources translates every name; then only the judge can tell.
        checks["invented"] = invented if language(inputs) == rubric["lang"] else []
        checks["invented_checked"] = language(inputs) == rubric["lang"]
        count = lambda f: sum(f(doc) for _, doc in specs)  # noqa: E731
        checks["open_questions"] = count(lambda d: len(sp.open_questions(d)))
        checks["warnings"] = count(lambda d: sum(ch["kind"] == "warning" for p in d["panels"] for ch in p.get("chips", []))
                                   + sum(f["kind"] == "warning" for f in sp.flags(d)))
        checks["principles"] = count(lambda d: len((d.get("footer") or {}).get("principles") or []))
        things = lambda d: [*d["panels"], *(c for p in d["panels"] for c in p.get("cards", []))]  # noqa: E731
        checks["statuses"] = count(lambda d: sum(bool(t.get("status")) for t in things(d)))
        checks["steps"] = count(lambda d: sum(bool(f.get("step")) for f in d.get("flows", [])) + (
            sum(len(p.get("cards", [])) for p in d["panels"]) if d["archetype"] == "swimlane" else 0))
        checks["parts"] = len(specs)
    else:
        checks["lang"] = language(text) == rubric["lang"] if text else False
    found = (text + " " + " ".join(json.dumps(doc) for _, doc in specs)).lower()
    checks["components_missing"] = [c for c in rubric.get("components", []) if c.lower() not in found]

    passed = {"image": checks["image"], "lang": checks["lang"],
              "components": len(checks["components_missing"]) <= len(rubric.get("components", [])) // 4}
    if specs:
        passed |= {"lint_clean": checks["lint_clean"], "archetype": checks["archetype"], "not_invented": not checks["invented"],
                   "open_questions": checks["open_questions"] >= rubric.get("open_questions_min", 0),
                   "warnings": checks["warnings"] >= rubric.get("warnings_min", 0),
                   "principles": checks["principles"] >= rubric.get("principles_min", 0),
                   "statuses": checks["statuses"] >= rubric.get("status_min", 0),
                   "steps": checks["steps"] >= rubric.get("steps_min", 0),
                   "series": checks["parts"] >= rubric.get("series_min_parts", 1)}
    else:
        passed |= {"structured": False}  # without a spec there is no lint, archetype or traceability to check
    return {"case": case.name, "run": str(run), "checks": checks, "passed": passed, "pass": all(passed.values())}


if __name__ == "__main__":
    print(json.dumps(grade(Path(sys.argv[1]), Path(sys.argv[2])), indent=2, ensure_ascii=False))
