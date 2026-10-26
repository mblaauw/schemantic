"""Repository rules that would otherwise drift: dependencies, design tokens, and the JS/Python boundary."""
import re

from conftest import ROOT


def test_requirements_follow_pyproject():
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    deps = re.findall(r'^\s*"([^"]+)",?$', py.split("dependencies = [")[1].split("]")[0], re.M)
    deps += re.findall(r'"(pytest[^"]*)"', py.split("[project.optional-dependencies]")[1].split("\n\n")[0])
    reqs = [line for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]
    assert reqs == deps


def test_colours_live_in_tokens_only():
    hexes = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    files = [ROOT / "templates" / "components.css", ROOT / "templates" / "plate.html.j2",
             *(ROOT / "schemantic").rglob("*.py"), *(ROOT / "schemantic" / "js").glob("*.js")]
    found = {str(f.relative_to(ROOT)): hexes.findall(f.read_text(encoding="utf-8")) for f in files}
    assert {k: v for k, v in found.items() if v} == {}


def test_no_javascript_inside_python():
    js = re.compile(r"=>|document\.|getComputedStyle|querySelector")
    for f in [*(ROOT / "schemantic").rglob("*.py"), *(ROOT / "scripts").glob("*.py")]:
        assert not js.search(f.read_text(encoding="utf-8")), f
