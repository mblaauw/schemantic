#!/usr/bin/env python3
"""Deprecated shim for `python -m schemantic render`, kept so 0.1 skill installs keep working for one release."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemantic.cli import main  # noqa: E402

sys.exit(main(["render", *sys.argv[1:]]))
