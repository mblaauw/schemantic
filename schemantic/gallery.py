"""`schemantic gallery`: build every example and write the README's images to assets/gallery/ as WebP at 1.5x,
with a manifest of each example's structural snapshot, so a test can tell when the gallery is out of date."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from PIL import Image

from .config import ROOT

GALLERY = ROOT / "assets" / "gallery"
SCALE = 1.5


def digest(snapshot: dict) -> str:
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:16]


def build_gallery() -> dict:
    from .pipeline import build
    GALLERY.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with tempfile.TemporaryDirectory() as tmp:
        for spec in sorted((ROOT / "examples").glob("*.yaml")):
            report = build(spec, tmp, scale=SCALE)
            if report["errors"]:
                raise RuntimeError(f"{spec.name} does not lint clean: {report['errors'][:3]}")
            with Image.open(report["png"]) as im:
                im.convert("RGB").save(GALLERY / f"{spec.stem}.webp", "WEBP", quality=88, method=6)
            snap = json.loads(Path(report["snapshot"]).read_text(encoding="utf-8"))
            manifest[spec.stem] = digest(snap)
    (GALLERY / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return {"gallery": str(GALLERY), "images": sorted(manifest)}
