# Offline use

Rendering a plate needs no network: no LLM, no API, no daemon, no Node.js to install. Fonts are embedded and
icons, templates and the schema are files in the repository. What does need the network is setup: Python packages
and Chromium are downloaded. The offline kit does that download once, on a machine that has a network, and carries
everything to one that does not.

## Build a kit

On a machine with network access and the **same operating system, CPU and Python minor version** as the target,
in an environment where the test suite passes:

```bash
python -m schemantic offline dist/schemantic-kit
```

The kit is a folder of about 275 MB:

| Path | What |
| --- | --- |
| `schemantic/` | the runtime: code, templates, schema, locales, fonts, icons, references, examples, docs, SKILL.md |
| `wheels/` | every Python package, as wheels, at the versions installed where the kit was built |
| `requirements.lock` | those exact versions with their SHA-256 hashes |
| `browsers/` | the Chromium build (headless shell) this Playwright version drives |
| `manifest.json` | Schemantic, Python, platform, Playwright and Chromium versions; the smoke test's layout digest; on Linux, the system packages Chromium needs |
| `install.sh` | the installer |
| `SHA256SUMS` | a checksum for every file in the kit |

Building the kit runs the smoke test first and refuses to write a kit from a machine where it fails.

## Install it

Copy the folder to the target and run:

```bash
sh schemantic-kit/install.sh
```

It never contacts a package index or any other host. In order, it:

1. checks that `python3` (or `$PYTHON`) is the Python version the kit was built for;
2. checks every file against `SHA256SUMS`, and stops if anything is missing or changed;
3. creates a venv in `${SCHEMANTIC_HOME:-~/.cache/schemantic}` with `pip install --no-index --require-hashes`;
4. copies Chromium to `${SCHEMANTIC_HOME:-~/.cache/schemantic}/browsers`, where Schemantic and its doctor find it
   without any environment variable;
5. runs the smoke test: it builds the reference plate and compares its layout digest (every box, text line and
   connector, rounded to 2 px) with the one recorded where the kit was built. A match means the target lays plates
   out exactly as the builder did.

Then build plates with the venv's Python, or use `schemantic-kit/schemantic` as the skill folder: its doctor finds
the venv and the browser.

The target needs:

- `python3` of the kit's version, with `venv` (on Debian and Ubuntu, the `python3-venv` package);
- on Linux, Chromium's system libraries, which a kit cannot install: `manifest.json` lists them under
  `linux_system_packages` (install them from your distribution's offline mirror).

## Check a kit or an install

```bash
python3 schemantic-kit/schemantic/scripts/plate.py verify schemantic-kit   # checksums; standard library only
~/.cache/schemantic/venv/bin/python schemantic-kit/schemantic/scripts/plate.py smoke --expect <digest>
```

## At runtime

Every build runs Chromium with the network refused: page requests for `http`, `https`, `ws` or `ftp` are aborted,
and anything else goes to a proxy that does not exist, so not even a DNS lookup leaves the machine. A theme that
points at a remote font or image fails the build with a `network` finding instead of quietly rendering with another
font, because the result must be the same with or without a network.

Playwright's Python package drives Chromium through a small driver program that ships inside its wheel (it is
built on Node.js, but nothing needs to be installed for it).

## Proof

CI builds a kit on Ubuntu and on macOS and installs it with the network cut off (an empty network namespace on
Linux, a sandbox on macOS), after checking that the network is in fact unreachable. The install must pass its
checksums and reproduce the builder's layout digest.
