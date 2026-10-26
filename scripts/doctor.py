#!/usr/bin/env python3
"""Find a Python that can run Schemantic; see schemantic/doctor.py. Runs on any python3 (standard library only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemantic.doctor import main  # noqa: E402

sys.exit(main())
