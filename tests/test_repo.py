"""Repository rules that would otherwise drift: dependencies, design tokens, and the JS/Python boundary."""

import re

from conftest import ROOT


def test_requirements_follow_pyproject():
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    deps = re.findall(r'^\s*"([^"]+)",?$', py.split("dependencies = [")[1].split("]")[0], re.M)
    deps += re.findall(r'"(pytest[^"]*)"', py.split("[project.optional-dependencies]")[1].split("\n\n")[0])
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


def test_docs_list_what_is_built():
    """F7: README, SKILL.md and the archetypes reference name exactly the built archetypes and patterns."""
    import json

    from schemantic import archetypes

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    reference = (ROOT / "references" / "archetypes.md").read_text(encoding="utf-8")
    built_cell = next(line for line in readme.splitlines() if line.startswith("| Archetypes:")).split("|")[1]
    for name in archetypes.BUILT:
        assert name in built_cell and f"`{name}`" in skill and f"## {name}" in reference, name
    assert sorted(line[3:] for line in reference.splitlines() if line.startswith("## ")) == archetypes.BUILT
    patterns = json.loads((ROOT / "schemantic" / "schema" / "plate.schema.json").read_text())["$defs"]["pattern"]["properties"]["type"]["enum"]
    pattern_row = next(line for line in readme.splitlines() if line.startswith("| Patterns:"))
    for p in patterns:
        assert p.replace("-", " ") in pattern_row.split("|")[1], p


def test_the_wheel_carries_every_file_a_render_reads():
    """An installed wheel has only what package-data names; every non-Python file in the package must match it."""
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    globs = re.findall(r'"([^"]+)"', py.split("[tool.setuptools.package-data]")[1].split("]")[0])
    pkg = ROOT / "schemantic"
    data = [p for p in pkg.rglob("*") if p.is_file() and p.suffix not in (".py", ".pyc") and "__pycache__" not in p.parts]
    assert data and [p for p in data if not any(p.relative_to(pkg).match(g) for g in globs)] == []
