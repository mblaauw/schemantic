"""Find a Python that can run Schemantic, and prove Chromium starts. Prints JSON; exits 1 if nothing works.

Usage: python3 scripts/doctor.py [--no-install]   (or: python -m schemantic doctor)

Order: the interpreter running this script; an existing cache venv; a new cache venv. The cache lives in
${SCHEMANTIC_HOME:-${XDG_CACHE_HOME:-~/.cache}/schemantic}. Nothing is ever written into the skill folder, which
is read-only once installed. Chromium is launched once; only if that fails does it try `playwright install
chromium`, which needs network access. Uses the standard library only, so any python3 can run it.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCH_ARGS = ["--font-render-hinting=none", "--disable-lcd-text"]  # as schemantic.browser; this module stays stdlib-only
PROBE = r"""
import importlib.util, json, sys
missing = [m for m in ("yaml", "jsonschema", "jinja2", "PIL", "fontTools", "brotli", "playwright") if importlib.util.find_spec(m) is None]
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


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def probe(python: Path) -> dict:
    try:
        out = subprocess.run([str(python), "-c", PROBE % (LAUNCH_ARGS,)], capture_output=True, text=True, timeout=180)
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception as e:  # a broken interpreter is just another candidate that does not work
        return {"deps": False, "error": f"{type(e).__name__}: {e}"}


def run(cmd: list[str], steps: list[str], what: str) -> bool:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    steps.append(f"{what}: {'ok' if proc.returncode == 0 else 'failed'}")
    if proc.returncode:
        steps.append((proc.stderr or proc.stdout).strip().splitlines()[-1][:300] if (proc.stderr or proc.stdout).strip() else "no output")
    return proc.returncode == 0


def diagnose(install: bool = True) -> dict:
    steps: list[str] = []
    venv = home() / "venv"
    candidates = [Path(sys.executable)] + ([venv_python(venv)] if venv_python(venv).exists() else [])
    found = None
    for py in candidates:
        r = probe(py)
        steps.append(f"{py}: " + ("dependencies missing: " + (", ".join(r.get("missing", [])) or r.get("error", "?")) if not r.get("deps")
                                  else f"Chromium {r['chromium']}" if r.get("chromium") else f"Chromium did not start ({r.get('error')})"))
        if r.get("deps"):
            found = (py, r)
            if r.get("chromium"):
                break

    if not found and install:
        py = venv_python(venv)
        if not py.exists():
            venv.parent.mkdir(parents=True, exist_ok=True)
            run([sys.executable, "-m", "venv", str(venv)], steps, f"create venv {venv}")
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
        report["problem"] = ("No Python with the dependencies was found and none could be installed (no network?). "
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
