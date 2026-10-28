#!/usr/bin/env python3
"""Run the Schemantic CLI from a skill folder: `python scripts/plate.py build spec.yaml --out out` (same as
`python -m schemantic ...` with the skill folder on the path)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemantic.cli import main  # noqa: E402

sys.exit(main(sys.argv[1:]))
