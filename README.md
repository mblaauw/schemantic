# Schemantic

**From meaning to structure to pixels.**

Schemantic turns an idea into an architecture plate. You describe the system as a
small YAML spec — panels, cards, flows, principles, open questions — and it renders
a finished, print-grade overview plate as **SVG and PNG**.

There are no coordinates in the spec. Chromium does the layout with CSS Grid; a
script measures every box, line and text run, then writes native SVG
(`rect`, `path`, `text`, `line`). The PNG is a raster of that same SVG.

> Status: proof of concept. One body archetype (`column-flow`) and its component
> set are built end to end; the remaining archetypes are not yet implemented.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 scripts/render.py examples/orderplatform-toegang.yaml --out out
python3 scripts/lint.py   examples/orderplatform-toegang.yaml --out out
```

`render.py` writes `out/<name>.svg` and `out/<name>.png` (intermediate HTML lands in
`out/_work/` for debugging only). `lint.py` emits a JSON report and exits `1` on errors.

Needs Python 3.10+, `playwright` (with Chromium: `playwright install chromium`),
`pyyaml`, `jsonschema`, `jinja2`, `pillow`, `fonttools` with `brotli`, and `pytest`.

Only `column-flow` is built. The schema lists the other archetypes as the planned contract,
but render and lint refuse them with an `archetype` error until their template exists.

## Tests

```bash
python3 -m pytest -q                  # spec checks, lint, and renders against tests/golden/
python3 -m pytest -q --update-golden  # after an intended visual change; review and commit the PNGs
```

Every example in `examples/` is rendered and compared with `tests/golden/<name>.png`, using
the same blurred comparison lint uses for SVG parity: sub-pixel noise passes, while a
reworded note already fails. Golden images are made on macOS with the pinned Playwright
Chromium, and CI runs on macOS for that reason.

Fonts are bundled in `assets/fonts/` (Inter, and DejaVu Sans Mono for paths), so nothing
needs to be installed and every machine lays the plate out the same way. The HTML loads
the full files through `@font-face`; the SVG embeds a WOFF2 subset of the glyphs it draws,
so it renders the same in any browser. Tools that ignore `@font-face` in SVG (Inkscape,
Cairo) still need Inter installed.

## Why it is built this way

HTML-to-SVG converters in the Satori style have no CSS Grid. Measuring in a real
browser and emitting SVG from the measured geometry works, and the result renders
identically in Cairo (Inkscape's renderer) and Chromium.

## What is built

| Part | Status |
| --- | --- |
| Canvas frame: title block, part badge, footer (context, principles, open questions, legend) | Built |
| Body archetype: column flow, with spanning areas over several rows | Built |
| Components: panel (role colours), card, bullets, warning and info chips | Built |
| Panel patterns: tier strip, tree, matrix | Built |
| Flow arrows in gutters, labels on vertical arrows | Built |
| Locales `nl` (default, English technical terms) and `en` | Built |
| Lint: schema, built archetype, areas, flow endpoints, chip mirror, icons, never-translate terms (substring, for Dutch compounds), text overflow, containment, overlap, canvas fit, type floor, contrast, arrow routing, arrow labels, chip length, density, SVG parity | Built |
| Other eight body archetypes; process strip, mini sequence, lifecycle loop | Not yet |
| Elbow connectors, connectors from cards, text-as-outlines SVG | Not yet |
| `SKILL.md`, `references/` | Not yet |

## Layout of the folder

```text
SKILL.md (not yet)       references/ (not yet)
schema/plate.schema.json spec contract
locales/                 fixed labels per language, never-translate list
templates/               plate.html.j2, tokens.css (theme, override per project), components.css
assets/icons/            58 Tabler outline icons (MIT, see LICENSE-tabler-icons.txt)
assets/fonts/            Inter 4.1 (400–800) and DejaVu Sans Mono 2.37, with their licences
scripts/                 platelib.py (shared), render.py, lint.py
examples/                fictional plates (spec only; renders go to out/)
tests/                   pytest suite; golden/ holds the reference render of each example
```

## Spec in one look

```yaml
canvas:  {size: landscape-4x3, lang: nl, series: orderplatform, part: 2, of: 3}
title:   "Orderplatform na fase 2 — toegang en data flow"
archetype: column-flow
layout:
  areas:
    - "clients identity gateway services"
    - "data    data     data    data"
panels:
  - id: clients
    title: "Clients en gebruikers"
    role: external                     # platform | storage | external
    cards:
      - {icon: browser, name: "Webshop frontend", note: "leest de product catalog"}
flows:
  - {from: clients, to: identity, label: "OIDC"}
footer:
  principles: ["Eén identity provider", "Data blijft bij de bron"]
```

The full contract lives in [`schema/plate.schema.json`](schema/plate.schema.json).

## Example output

![Rendered plate: order platform access and data flow](assets/example-orderplatform.png)

Rendered from [`examples/orderplatform-toegang.yaml`](examples/orderplatform-toegang.yaml)
(`landscape-4x3`, `nl`, part 2 of 3).


## Findings from building it

- Satori-style HTML-to-SVG converters lack CSS Grid; measuring in Chromium and emitting SVG works and
  renders the same in Cairo (Inkscape's renderer) as in Chromium.
- Pixel-exact parity is the wrong test: Chromium snaps HTML text to whole pixels, SVG keeps fractions
  (0.9 % of pixels differ with no visible change). After a 1.5 px blur a correct plate scores 0 and a
  plate with one card deleted scores about 4,600 pixels, so the check is structural.
- Density below 0.6 matched the one panel that looked empty on review; the fix was content, not layout.
- A long Dutch word ("gestandaardiseerd") overflowed a tier tile; lint caught it, block weights fixed it.

## Icons

The outline icon set in `assets/icons/` is [Tabler Icons](https://tabler.io/icons), MIT licensed —
see `assets/icons/LICENSE-tabler-icons.txt`.

## Fonts

`assets/fonts/` holds [Inter](https://rsms.me/inter/) 4.1 (SIL Open Font License, see
`assets/fonts/LICENSE-inter.txt`) and [DejaVu Sans Mono](https://dejavu-fonts.github.io/) 2.37
(free licence, see `assets/fonts/LICENSE-dejavu.txt`), taken unmodified from their official
releases; DejaVu was converted from TTF to WOFF2.
