"""Repository rules that would otherwise drift: dependencies, design tokens, and the JS/Python boundary."""

import re

from conftest import ROOT


def test_requirements_follow_pyproject():
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    deps = re.findall(r'^\s*"([^"]+)",?$', py.split("dependencies = [")[1].split("]")[0], re.M)
    reqs = [line for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    assert reqs == deps


def test_colours_live_in_tokens_only():
    hexes = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    files = [
        ROOT / "schemantic" / "templates" / "components.css",
        ROOT / "schemantic" / "templates" / "plate.html.j2",
        *(ROOT / "schemantic").rglob("*.py"),
        *(ROOT / "schemantic" / "js").glob("*.js"),
    ]
    found = {str(f.relative_to(ROOT)): hexes.findall(f.read_text(encoding="utf-8")) for f in files}
    assert {k: v for k, v in found.items() if v} == {}


def test_no_javascript_inside_python():
    js = re.compile(r"=>|document\.|getComputedStyle|querySelector")
    for f in [*(ROOT / "schemantic").rglob("*.py"), *(ROOT / "scripts").glob("*.py")]:
        assert not js.search(f.read_text(encoding="utf-8")), f


def test_skill_md_stays_small_and_complete():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    description = re.search(r"^description: (.*)$", skill, re.M).group(1)
    assert len(skill.splitlines()) < 500
    assert len(description) < 1024 and description.startswith("Turns ")
    for word in ("architecture plate", "C4", "architectuurplaat", "overzichtsplaat"):
        assert word in description
    # References are one level deep from SKILL.md, and every one it names exists.
    for ref in set(re.findall(r"references/[\w-]+\.md", skill)):
        assert (ROOT / ref).exists(), ref
    assert set(re.findall(r"references/[\w-]+\.md", skill)) >= {f"references/{p.name}" for p in (ROOT / "references").glob("*.md")}


def test_licence_is_declared_and_present():
    """F1: the code is MIT, and every bundled asset keeps its own notice."""
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = "MIT"' in py and 'license-files = ["LICENSE"]' in py
    licence = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert licence.startswith("MIT License") and "Permission is hereby granted" in licence
    assert "Copyright (c) 2026" in licence
    assert "**Code:** MIT, see [`LICENSE`](LICENSE)." in (ROOT / "README.md").read_text(encoding="utf-8")
    for notice in ("schemantic/icons/LICENSE-tabler-icons.txt", "schemantic/fonts/LICENSE-inter.txt", "schemantic/fonts/LICENSE-dejavu.txt"):
        assert (ROOT / notice).exists(), notice


def test_gallery_is_current():
    """F5: the README images were built from the examples as they are (compared through the structural snapshots)."""
    import json

    from schemantic.gallery import GALLERY, digest

    manifest = json.loads((GALLERY / "manifest.json").read_text(encoding="utf-8"))
    examples = sorted(p.stem for p in (ROOT / "examples").glob("*.yaml"))
    assert sorted(manifest) == examples, "run: python -m schemantic gallery"
    for name in examples:
        snap = json.loads((ROOT / "tests" / "snapshots" / f"{name}.json").read_text(encoding="utf-8"))
        assert manifest[name] == digest(snap), f"{name}: run python -m schemantic gallery"
    for plate in (ROOT / "docs" / "plates").glob("*.yaml"):  # rebuilt by the same command, shown in the docs
        assert (ROOT / "docs" / "img" / f"{plate.stem}.webp").exists(), f"{plate.stem}: run python -m schemantic gallery"


def test_docs_list_what_is_built():
    """F7: README, SKILL.md, the archetypes reference and the layouts page name the built archetypes and patterns."""
    import json

    from schemantic import archetypes

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    reference = (ROOT / "references" / "archetypes.md").read_text(encoding="utf-8")
    built_cell = next(line for line in readme.splitlines() if line.startswith("| Archetypes:")).split("|")[1]
    for name in archetypes.BUILT:
        assert name in built_cell and f"`{name}`" in skill and f"## {name}" in reference, name
    assert sorted(line[3:] for line in reference.splitlines() if line.startswith("## ")) == archetypes.BUILT
    layouts = (ROOT / "docs" / "layouts.md").read_text(encoding="utf-8")
    for name in archetypes.BUILT:
        assert f"## {name}" in layouts and (ROOT / "docs" / "img" / "layouts" / f"{name}.svg").exists(), name
    patterns = json.loads((ROOT / "schemantic" / "schema" / "plate.schema.json").read_text())["$defs"]["pattern"]["properties"]["type"]["enum"]
    pattern_row = next(line for line in readme.splitlines() if line.startswith("| Patterns:"))
    for p in patterns:
        assert p.replace("-", " ") in pattern_row.split("|")[1], p
        assert f"`{p}`" in layouts and (ROOT / "docs" / "img" / "layouts" / f"pattern-{p}.svg").exists(), p


def test_the_wheel_carries_every_file_a_render_reads():
    """An installed wheel has only what package-data names; every non-Python file in the package must match it."""
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    globs = re.findall(r'"([^"]+)"', py.split("[tool.setuptools.package-data]")[1].split("]")[0])
    pkg = ROOT / "schemantic"
    data = [p for p in pkg.rglob("*") if p.is_file() and p.suffix not in (".py", ".pyc") and "__pycache__" not in p.parts]
    assert data and [p for p in data if not any(p.relative_to(pkg).match(g) for g in globs)] == []


def test_the_doctor_imports_only_the_standard_library():
    """It runs on any python3 to find one with the dependencies, so it may share config but nothing that needs them."""
    import subprocess
    import sys
    code = "import sys, schemantic.doctor; print(sorted({m.split('.')[0] for m in sys.modules}))"
    loaded = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True).stdout
    for dep in ("yaml", "jsonschema", "jinja2", "PIL", "fontTools", "playwright"):
        assert f"'{dep}'" not in loaded, dep


def test_the_doctor_refreshes_an_outdated_requirement(monkeypatch):
    """A venv an older release built has every module but not the versions a newer release needs: the probe says
    which, so the doctor installs again instead of a build failing later."""
    import sys
    from pathlib import Path

    from schemantic import doctor
    monkeypatch.setattr(doctor, "requirements", lambda: ["pyyaml>=999", "jinja2>=3.1,<999", "no-such-package-here>=1"])
    r = doctor.probe(Path(sys.executable))
    assert r["deps"] is False
    assert r["missing"][0].startswith("pyyaml ") and r["missing"][0].endswith("(needs >=999)")
    assert r["missing"][1:] == ["no-such-package-here"]
