import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from schemantic import archetypes, browser, html, images, route  # noqa: E402,F401
from schemantic import spec as sp  # noqa: E402

EXAMPLES = sorted((ROOT / "examples").glob("*.yaml"))


def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true",
                     help="overwrite tests/golden/ with fresh renders instead of comparing against them")


@pytest.fixture
def update_golden(request) -> bool:
    return request.config.getoption("--update-golden")


@pytest.fixture
def example() -> dict:
    """A fresh copy of the reference spec, safe to break in a test."""
    return copy.deepcopy(sp.load_spec(ROOT / "examples" / "orderplatform-toegang.yaml"))
