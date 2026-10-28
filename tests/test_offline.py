"""The offline kit: checksums, the smoke test, and the manifest fields install.sh reads. The full kit (download,
install with the network cut off) runs in CI's offline job; see .github/workflows/test.yml."""
import json
import subprocess

from conftest import ROOT

from schemantic import offline


def test_verify_names_a_changed_and_a_missing_file(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b", encoding="utf-8")
    offline.write_sums(tmp_path)
    assert offline.verify(tmp_path)["ok"]
    (tmp_path / "a.txt").write_text("changed", encoding="utf-8")
    (tmp_path / "sub" / "b.txt").unlink()
    (tmp_path / "new.txt").write_text("new", encoding="utf-8")
    report = offline.verify(tmp_path)
    assert not report["ok"]
    assert (report["changed"], report["missing"], report["extra"]) == (["a.txt"], ["sub/b.txt"], ["new.txt"])


def test_verify_refuses_a_folder_that_is_not_a_kit(tmp_path):
    assert not offline.verify(tmp_path)["ok"]


def test_smoke_reproduces_its_digest_and_refuses_another():
    first = offline.smoke()
    assert first["ok"] and first["errors"] == [] and first["parity"]["pixels"] == 0
    assert offline.smoke(first["digest"])["ok"]
    wrong = offline.smoke("0" * 64)
    assert not wrong["ok"] and "differently" in wrong["problem"]


def test_install_script_reads_the_manifest_it_is_shipped_with(tmp_path):
    """install.sh reads two fields with sed; the manifest is written by json.dumps(indent=2)."""
    manifest = {"schemantic": "0", "python": "3.12", "smoke_digest": "abc123", "wheels": [{"python": "nested"}]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    field = offline.INSTALL.split("field() { ")[1].split("; }")[0]
    out = subprocess.run(["sh", "-c", f'KIT="{tmp_path}"; {field.replace("$1", "python")}; '
                                      f'{field.replace("$1", "smoke_digest")}'], capture_output=True, text=True)
    assert out.stdout.split() == ["3.12", "abc123"]


def test_kit_ships_what_the_runtime_reads():
    """Every path under the repository that the package reads (`ROOT / "..."`) is in the kit, except the gallery,
    which only `schemantic gallery` writes in a checkout."""
    import re
    read = {"/".join(re.findall(r'"([^"]+)"', m)) for f in (ROOT / "schemantic").glob("*.py")
            for m in re.findall(r'ROOT / "[^"]+"(?: / "[^"]+")?', f.read_text(encoding="utf-8"))}
    shipped = lambda path: any(path == n or path.startswith(n + "/") for n in offline.RUNTIME)  # noqa: E731
    assert {p for p in read if not shipped(p)} == {"assets/gallery"}
