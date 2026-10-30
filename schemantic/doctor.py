"""Find a Python that can run Schemantic, and prove Chromium starts. Prints JSON; exits 1 if nothing works.

Usage: python3 scripts/doctor.py [--no-install]   (or: python -m schemantic doctor)

Order: the interpreter running this script; an existing cache venv; a new cache venv. The cache lives in
${SCHEMANTIC_HOME:-${XDG_CACHE_HOME:-~/.cache}/schemantic}; an offline kit installs its venv and Chromium there.
Nothing is ever written into the skill folder, which is read-only once installed. Chromium is launched once; only
if that fails does it try `playwright install chromium`, which needs network access. Uses the standard library only,
so any python3 can run it.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import LAUNCH_ARGS, ROOT  # config is standard library only, as this module must be

MIN_PYTHON = (3, 10)
# Checks each requirement's installed version, not only that it imports, so a venv an older release built is
# refreshed when a requirement moves.
PROBE = r"""
import importlib.metadata, json, operator, re, sys
if sys.version_info < (3, 10):
    print(json.dumps({"deps": False, "old": "{}.{}".format(*sys.version_info[:2])})); sys.exit()
OPS = {">=": operator.ge, "<=": operator.le, "==": operator.eq, ">": operator.gt, "<": operator.lt}
key = lambda v: tuple(int(re.match(r"\d*", part).group() or 0) for part in (v.split(".") + ["0", "0"])[:3])
missing = []
for req in %r:
    name, specs = re.match(r"([A-Za-z0-9_.-]+)(.*)", req).groups()
    try:
        have = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        missing.append(name); continue
    for op, want in (re.match(r"(>=|<=|==|>|<)(.+)", s.strip()).groups() for s in specs.split(",") if s.strip()):
        if not OPS[op](key(have), key(want)):
            missing.append(f"{name} {have} (needs {op}{want})")
if missing:
    print(json.dumps({"deps": False, "missing": missing})); sys.exit()
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=%r); v = b.version; b.close()
    print(json.dumps({"deps": True, "chromium": v}))
except Exception as e:
    print(json.dumps({"deps": True, "chromium": None, "error": str(e).splitlines()[0][:300]}))
"""


def home() -> Path:
    if os.environ.get("SCHEMANTIC_HOME"):
        return Path(os.environ["SCHEMANTIC_HOME"]).expanduser()
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache").expanduser() / "schemantic"


def use_kit_browsers() -> None:
    """An offline kit installs Chromium into <home>/browsers; point Playwright there unless told otherwise. Must run
    before Playwright starts, which reads the variable once."""
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and (home() / "browsers").is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(home() / "browsers")


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def requirements() -> list[str]:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def probe(python: Path) -> dict:
    try:
        out = subprocess.run([str(python), "-c", PROBE % (requirements(), LAUNCH_ARGS)], capture_output=True, text=True, timeout=180)
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception as e:  # a broken interpreter is just another candidate that does not work
        return {"deps": False, "error": f"{type(e).__name__}: {e}"}


def run(cmd: list[str], steps: list[str], what: str) -> bool:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    steps.append(f"{what}: {'ok' if proc.returncode == 0 else 'failed'}")
    if proc.returncode:
        steps.append((proc.stderr or proc.stdout).strip().splitlines()[-1][:300] if (proc.stderr or proc.stdout).strip() else "no output")
    return proc.returncode == 0


def base_python() -> str | None:
    """A Python to build the venv from: this one if it is new enough, else the newest python3.x on PATH."""
    if sys.version_info >= MIN_PYTHON:
        return sys.executable
    for minor in range(20, MIN_PYTHON[1] - 1, -1):
        if shutil.which(f"python3.{minor}"):
            return shutil.which(f"python3.{minor}")
    return None


def diagnose(install: bool = True) -> dict:
    use_kit_browsers()  # the probes run in child processes, which inherit it
    steps: list[str] = []
    venv = home() / "venv"
    candidates = [Path(sys.executable)] + ([venv_python(venv)] if venv_python(venv).exists() else [])
    found = None
    for py in candidates:
        r = probe(py)
        steps.append(f"{py}: " + (f"Python {r['old']}, older than 3.10" if r.get("old") else
                                  "needs installing: " + (", ".join(r.get("missing", [])) or r.get("error", "?")) if not r.get("deps")
                                  else f"Chromium {r['chromium']}" if r.get("chromium") else f"Chromium did not start ({r.get('error')})"))
        if r.get("deps"):
            found = (py, r)
            if r.get("chromium"):
                break

    base = base_python()
    if not found and install and base:
        py = venv_python(venv)
        if not py.exists() or probe(py).get("old"):  # none yet, or one an older doctor built from an old Python
            # (an existing venv with missing or outdated requirements is updated in place by the install below)
            venv.parent.mkdir(parents=True, exist_ok=True)
            run([base, "-m", "venv", "--clear", str(venv)], steps, f"create venv {venv} with {base}")
        if py.exists() and run([str(py), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")], steps, "install requirements"):
            r = probe(py)
            found = (py, r) if r.get("deps") else None

    if found and not found[1].get("chromium") and install:
        py = found[0]
        if run([str(py), "-m", "playwright", "install", "chromium"], steps, "playwright install chromium"):
            found = (py, probe(py))

    ok = bool(found and found[1].get("chromium"))
    report = {"ok": ok, "python": str(found[0]) if ok else None, "chromium": found[1].get("chromium") if found else None,
              "cache": str(home()), "steps": steps}
    if not ok:
        report["problem"] = ("Schemantic needs Python 3.10 or later, and none was found (python3 is older). Install a "
                             "newer Python (python.org or the system's package manager) and run the doctor again."
                             if not found and not base else
                             "No Python with the dependencies was found and none could be installed (no network?). "
                             "Install them with: python3 -m pip install -r requirements.txt" if not found else
                             "The dependencies are there, but Chromium does not start and could not be downloaded. "
                             "Run `python3 -m playwright install chromium` where there is network access, or set "
                             "PLAYWRIGHT_BROWSERS_PATH to a folder that holds a matching Chromium.")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-install", action="store_true", help="only look; never create a venv or download Chromium")
    report = diagnose(install=not ap.parse_args().no_install)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1
