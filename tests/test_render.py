"""End-to-end: the real CLIs in Chromium. Renders are compared with tests/golden/ the same way lint compares
the SVG with the HTML, so sub-pixel noise passes and a moved, dropped or rewrapped element fails."""
import json
import shutil
import subprocess
import sys

import pytest
import yaml

from conftest import EXAMPLES, ROOT, pl

GOLDEN = ROOT / "tests" / "golden"


def run(script: str, *args) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                          capture_output=True, text=True, cwd=ROOT)
    return proc.returncode, json.loads(proc.stdout)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_render_matches_golden(path, tmp_path, update_golden):
    code, report = run("render.py", path, "--out", tmp_path, "--scale", 1)
    assert code == 0, report
    fresh, golden = tmp_path / f"{path.stem}.png", GOLDEN / f"{path.stem}.png"
    if update_golden or not golden.exists():
        GOLDEN.mkdir(exist_ok=True)
        shutil.copyfile(fresh, golden)
        pytest.skip(f"wrote {golden.relative_to(ROOT)}; review it and commit")
    diff = pl.image_diff(golden, fresh, tmp_path / "golden-diff.png")
    assert diff["share"] <= pl.PARITY_ERROR_SHARE, (
        f"{diff['detail']}. Mask: {tmp_path / 'golden-diff.png'}, render: {fresh}. "
        "If the change is intended, run pytest --update-golden and commit the new image.")


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_lint_is_clean(path, tmp_path):
    code, report = run("lint.py", path, "--out", tmp_path)
    assert (code, report["errors"]) == (0, [])


def test_render_refuses_unbuilt_archetype(example, tmp_path):
    example["archetype"] = "roadmap"
    spec = tmp_path / "roadmap.yaml"
    spec.write_text(yaml.safe_dump(example, allow_unicode=True), encoding="utf-8")
    code, report = run("render.py", spec, "--out", tmp_path)
    assert code == 1 and report["rendered"] is False
    assert [e["check"] for e in report["errors"]] == ["archetype"]
    assert not (tmp_path / "roadmap.svg").exists()
