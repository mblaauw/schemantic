"""Docs that cannot drift: every YAML block marked <!-- lint --> (or <!-- lint: <example> -->) in the README and
the references is merged into an example spec and must lint without errors."""
import re

import pytest
import yaml
from conftest import ROOT, sp
from test_render import run, write

BLOCK = re.compile(r"<!-- lint(?::\s*(\S+))? -->\s*```yaml\n(.*?)```", re.S)
DOCS = [ROOT / "README.md", *sorted((ROOT / "references").glob("*.md"))]


def merge(base, over):
    """Overlay a snippet on a full spec: mappings merge, panels merge by id, other lists are replaced."""
    if isinstance(base, dict) and isinstance(over, dict):
        return {**base, **{k: merge(base[k], v) if k in base else v for k, v in over.items()}}
    if isinstance(base, list) and isinstance(over, list) and all(isinstance(x, dict) and "id" in x for x in base + over):
        ids = {x["id"]: x for x in over}
        return [merge(x, ids.pop(x["id"])) if x["id"] in ids else x for x in base] + list(ids.values())
    return over


def blocks():
    for doc in DOCS:
        for n, m in enumerate(BLOCK.finditer(doc.read_text(encoding="utf-8"))):
            yield pytest.param(m.group(1) or "examples/orderplatform-toegang.yaml", m.group(2), id=f"{doc.name}-{n}")


def test_docs_have_linted_samples():
    assert len(list(blocks())) >= 4


@pytest.mark.parametrize("example, snippet", list(blocks()))
def test_doc_sample_lints(example, snippet, tmp_path):
    spec = merge(sp.load_spec(ROOT / example), yaml.safe_load(snippet))
    code, report = run("lint", write(tmp_path, spec, "sample"), "--out", tmp_path)
    assert report["errors"] == [] and code == 0
