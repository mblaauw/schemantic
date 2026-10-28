"""An offline kit: everything Schemantic needs on a machine without a network, in one folder.

`schemantic offline <dir>` writes, for this operating system, CPU and Python version:

    schemantic/        the runtime: code, templates, schema, locales, fonts, icons, references, examples, docs
    wheels/            the Python packages at the versions installed here, where the suite passes; wheels only
    requirements.lock  those versions with their SHA-256 hashes; pip installs nothing else and checks every hash
    browsers/          the Chromium build this Playwright drives (its headless shell)
    manifest.json      versions, platform, the Chromium revision and the layout digest the smoke test must reproduce
    install.sh         a venv from the wheels (no package index), the browser, a checksum check, the smoke test
    SHA256SUMS         a checksum for every file above

Build it where there is network access, on the same OS, CPU and Python minor version as the target. Nothing in
it needs a network, Node.js (Playwright carries its own driver), an API or a daemon. Standard library only at import,
so `verify` runs before any package is installed.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from datetime import date
from importlib import metadata
from pathlib import Path

from . import __version__
from .config import ROOT

RUNTIME = ["SKILL.md", "README.md", "LICENSE", "CHANGELOG.md", "pyproject.toml", "requirements.txt", "schemantic",
           "scripts", "templates", "schema", "locales", "assets/fonts", "assets/icons", "references", "examples", "docs"]
SMOKE_SPEC = "examples/orderplatform-toegang.yaml"
SUMS = "SHA256SUMS"
SKIP = ("__pycache__", ".DS_Store")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def files(root: Path) -> list[Path]:
    """Every file under root, sorted, without caches; symbolic links count as the files they are."""
    return sorted(p for p in root.rglob("*") if p.is_file() and not any(s in p.parts for s in SKIP))


def runtime_dependencies() -> list[str]:
    """The [project] dependencies in pyproject.toml (no tomllib: it is not in Python 3.10)."""
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.findall(r'^\s*"([^"]+)",?$', py.split("dependencies = [")[1].split("]")[0], re.M)


def installed_versions() -> str:
    """Constraints pinning every installed distribution to its installed version."""
    pins = {d.metadata["Name"]: d.version for d in metadata.distributions() if d.metadata["Name"]}
    return "\n".join(f"{n}=={v}" for n, v in sorted(pins.items()) if n.lower() != "schemantic") + "\n"


def download_wheels(wheels: Path) -> list[dict]:
    """Download the runtime dependencies as wheels, at the versions installed here, and return them hashed."""
    wheels.mkdir(parents=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as c:
        c.write(installed_versions())
    try:
        subprocess.run([sys.executable, "-m", "pip", "download", "--quiet", "--disable-pip-version-check",
                        "--only-binary=:all:", "-d", str(wheels), "-c", c.name, *runtime_dependencies()], check=True)
    finally:
        os.unlink(c.name)
    out = []
    for whl in sorted(wheels.glob("*.whl")):
        name, version = whl.name.split("-")[:2]
        out.append({"file": whl.name, "name": name, "version": version, "sha256": sha256(whl)})
    return out


def playwright_browsers() -> Path:
    """Where Playwright keeps its browsers on this machine."""
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"]).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ms-playwright"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "ms-playwright"


def chromium_build() -> dict:
    """The headless shell this Playwright drives: its revision and Chromium version, from Playwright's own list."""
    import playwright
    listed = json.loads((Path(playwright.__file__).parent / "driver" / "package" / "browsers.json").read_text())
    shell = next(b for b in listed["browsers"] if b["name"] == "chromium-headless-shell")
    return {"revision": shell["revision"], "version": shell.get("browserVersion"),
            "folder": f"chromium_headless_shell-{shell['revision']}"}


def copy_browser(dest: Path, build: dict) -> str:
    """Copy the headless shell from Playwright's cache, or have Playwright download it into the kit."""
    src = playwright_browsers() / build["folder"]
    if (src / "INSTALLATION_COMPLETE").exists():
        shutil.copytree(src, dest / build["folder"], symlinks=True)
        return f"copied from {src}"
    env = {**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(dest)}
    subprocess.run([sys.executable, "-m", "playwright", "install", "--only-shell", "chromium"], check=True, env=env)
    return "downloaded by playwright install --only-shell chromium"


def linux_packages() -> str | None:
    """On Linux, the system packages Chromium needs; the target must have them, since the kit cannot install them."""
    if not sys.platform.startswith("linux"):
        return None
    proc = subprocess.run([sys.executable, "-m", "playwright", "install-deps", "--dry-run", "chromium"],
                          capture_output=True, text=True)
    return proc.stdout.strip() or None


def smoke(expect: str | None = None) -> dict:
    """Build the reference plate and digest its structure (every box, text line and connector, rounded to 2 px).
    The digest is the same wherever Chromium lays the plate out the same, so it proves the target matches."""
    from .pipeline import build
    with tempfile.TemporaryDirectory() as tmp:
        report = build(ROOT / SMOKE_SPEC, tmp, deliver=False)
        snapshot = json.loads(Path(report["snapshot"]).read_text(encoding="utf-8")) if report["snapshot"] else None
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest() if snapshot else None
    out = {"spec": SMOKE_SPEC, "errors": report["errors"], "parity": report["parity"], "digest": digest,
           "chromium": (report.get("build") or {}).get("chromium")}
    out["ok"] = not report["errors"] and digest is not None and (expect is None or digest == expect)
    if expect and digest != expect:
        out["problem"] = "the plate lays out differently here than where the kit was built"
    return out


def write_sums(kit: Path) -> None:
    lines = [f"{sha256(p)}  {p.relative_to(kit).as_posix()}" for p in files(kit) if p.name != SUMS]
    (kit / SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify(kit: Path) -> dict:
    """Check every file against SHA256SUMS: nothing missing, nothing changed. Extra files are listed, not fatal."""
    kit = Path(kit)
    sums = kit / SUMS
    if not sums.exists():
        return {"ok": False, "problem": f"no {SUMS} in {kit}: not an offline kit"}
    pairs = (line.split("  ", 1) for line in sums.read_text(encoding="utf-8").splitlines() if line)
    listed = {path: digest for digest, path in pairs}
    missing = [p for p in listed if not (kit / p).is_file()]
    changed = [p for p, h in listed.items() if p not in missing and sha256(kit / p) != h]
    extra = [p.relative_to(kit).as_posix() for p in files(kit) if p.name != SUMS
             and p.relative_to(kit).as_posix() not in listed]
    return {"ok": not missing and not changed, "files": len(listed), "missing": missing, "changed": changed,
            "extra": extra}


INSTALL = r"""#!/bin/sh
# Installs Schemantic from this kit on a machine without network access: a venv from the bundled wheels (no package
# index, every hash checked), the bundled Chromium, a checksum check of the kit, and a smoke test that must lay the
# reference plate out exactly as it was laid out where the kit was built.
#
# Usage: sh install.sh     Installs into ${SCHEMANTIC_HOME:-${XDG_CACHE_HOME:-~/.cache}/schemantic}, where the
#                          skill's doctor finds the venv and the browser. Set PYTHON to pick the interpreter.
set -eu
KIT=$(cd "$(dirname "$0")" && pwd)
DEST=${SCHEMANTIC_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/schemantic}
PY=${PYTHON:-python3}
field() { sed -n "s/^  \"$1\": \"\(.*\)\",*$/\1/p" "$KIT/manifest.json"; }
WANT=$(field python)
HAVE=$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
if [ "$WANT" != "$HAVE" ]; then
  echo "This kit is for Python $WANT; $PY is Python $HAVE. Set PYTHON=python$WANT." >&2
  exit 1
fi
"$PY" -B "$KIT/schemantic/scripts/plate.py" verify "$KIT"
mkdir -p "$DEST"
rm -rf "$DEST/venv" "$DEST/browsers"
"$PY" -m venv "$DEST/venv"
"$DEST/venv/bin/python" -m pip install --quiet --disable-pip-version-check --no-index --find-links "$KIT/wheels" \
  --require-hashes -r "$KIT/requirements.lock"
cp -R "$KIT/browsers" "$DEST/browsers"
"$DEST/venv/bin/python" -B "$KIT/schemantic/scripts/plate.py" smoke --expect "$(field smoke_digest)"
echo "Installed in $DEST. Build a plate with:"
echo "  $DEST/venv/bin/python $KIT/schemantic/scripts/plate.py build <spec.yaml> --out <folder>"
"""


def bundle(dest: Path) -> dict:
    """Write the kit to dest (a new folder) and return its manifest."""
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        return {"ok": False, "problem": f"{dest} exists and is not empty; give a new folder"}
    dest.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, dest / "schemantic" / name, ignore=shutil.ignore_patterns(*SKIP))
        elif src.is_file():
            (dest / "schemantic" / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / "schemantic" / name)
    wheels = download_wheels(dest / "wheels")
    (dest / "requirements.lock").write_text(
        "# Exact versions and hashes; install with: pip install --no-index --find-links wheels --require-hashes -r "
        "requirements.lock\n" + "".join(f"{w['name']}=={w['version']} --hash=sha256:{w['sha256']}\n" for w in wheels),
        encoding="utf-8")
    chromium = chromium_build()
    how = copy_browser(dest / "browsers", chromium)
    check = smoke()
    if not check["ok"]:
        return {"ok": False, "problem": "the smoke test fails on this machine; fix that before bundling", "smoke": check}
    manifest = {
        "schemantic": __version__,
        "built": date.today().isoformat(),
        "python": f"{sys.version_info[0]}.{sys.version_info[1]}",
        "implementation": platform.python_implementation().lower(),
        "platform": sysconfig.get_platform(),
        "playwright": metadata.version("playwright"),
        "chromium_revision": chromium["revision"],
        "chromium_version": chromium["version"],
        "chromium_source": how,
        "smoke_spec": SMOKE_SPEC,
        "smoke_digest": check["digest"],
        "linux_system_packages": linux_packages(),
        "wheels": wheels,
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (dest / "install.sh").write_text(INSTALL, encoding="utf-8")
    (dest / "install.sh").chmod(0o755)
    write_sums(dest)
    return {"ok": True, "kit": str(dest), "files": len(files(dest)), **{k: manifest[k] for k in (
        "python", "platform", "playwright", "chromium_version", "smoke_digest")}}
