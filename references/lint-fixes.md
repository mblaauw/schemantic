# Lint findings and their fixes

Generated from `schemantic/findings.py` by `python -m schemantic docs`; edit the table there.

Every finding names an element id (`gateway`, `services.card2`, `flows/3`, `footer.open_questions`) and carries a `hint`, the first fix to try. Fix it in the spec. Errors block delivery; warnings are judgement calls that usually mean "add substance".

## Spec checks (no browser)

| check | means | fix |
| --- | --- | --- |
| `yaml` | the file is missing, is not valid YAML (the detail gives line and column) or holds no mapping | fix the file; quote strings that contain `: ` or start with a special character |
| `schema` | a field is missing, misspelled, too long or of the wrong type | the `id` is the path to the field; shorten text or correct the key |
| `id` | two panels share an id, two cards share an id, or a card id equals a panel id or a card's automatic id | rename one; the detail names both places |
| `archetype` | the archetype is planned but not built | pick a built one (`archetypes.md`, "Not built yet") |
| `layout` | layout keys do not fit the archetype, a panel is placed twice or not at all, an area is not a rectangle, widths/heights do not match the grid, or `footer.columns` does not match the footer panels | follow the detail; every panel id appears in the layout exactly once |
| `budget` | more than 5 columns | split the plate or merge panels |
| `pattern` | a matrix row has the wrong number of cells | one cell per column |
| `flow` | a flow names an id that does not exist, connects an element to itself, or connects a card to its own panel | use a panel id, or give the card an `id`; connect two different boxes |
| `canvas` | `part` without `of` (or the reverse), `part` larger than `of`, or a theme file that does not exist | give both, with `1 ≤ part ≤ of`; check the theme path (relative to the spec) |
| `role` | a panel role is neither built in nor defined by the theme, or the theme gives it no legend label in the plate's language | use platform, data, external or actor, or define the role and its label in the theme |
| `deprecated` | an old name that still works for one release (warning) | use the new name in the detail |
| `focus` | more than one panel or card has `focus: true` | keep focus on the one element the title is about |
| `flows-mean` | the plate has flows but no `flows_mean` (warning) | say what an arrow means: data, request, dependency or control |
| `traceability` | the spec declares `sources`, and a card has no `refs` or names an undeclared source (warning) | add `refs: ["<source id>: <path or quote>"]` from the inventory; a card you cannot trace is an assumption or an open question, not a fact |
| `chip-mirror` | a warning chip or warning flag is not under open questions | `open_questions: {from_chips: true}` |
| `icon` | unknown icon | use one of the closest names in the hint, or search: `schemantic icons <word>` |
| `language` | a translated technical term in an `nl` plate | use the English term (the id of the finding) |

## Layout checks (measured in Chromium)

| check | means | fix |
| --- | --- | --- |
| `text-overflow` | a word or line runs outside its box | shorten the text; avoid one long word in a narrow tile; fewer `card_columns`; more `weights` for that block |
| `containment` | a block is taller or wider than its panel | fewer cards or bullets; move a card to another panel; `row_heights: auto` for that row; split the plate |
| `canvas-fit` | something extends past the canvas margin | cut content; a shorter footer (fewer principles); `landscape-4x3` instead of 16x9 |
| `overlap` | two boxes overlap | usually follows from containment; fix that first |
| `type-floor` | text below 11 px | only from theme overrides; restore the type ramp in `tokens.css` |
| `contrast` | text colour too close to its background | only from theme overrides; fix the token pair |
| `arrow-routing` | no clear route, or a route crosses a panel or card | connect the panels instead of cards; move the target card to the side of its panel nearest the source; place the two panels next to each other |
| `arrow-label` | no room for a label, or it touches a box | shorten the label, drop it, or explain the flow in a card note |
| `arrow-crossing` | an arrow crosses another arrow at a right angle | connect a card instead of its panel, or the other way round; swap the two panels so the arrows run side by side; drop a flow the message does not need |
| `chip-length` | a chip runs to three lines | shorten it to one clear sentence |
| `void` | a run of empty space inside a body panel: warning over 96 px, error over 160 px | add real content (bullets, a pattern, an info chip); move the panel next to one of its height; merge it with a neighbour; never filler |
| `svg-parity` | the SVG differs from the measured layout | a renderer problem, not a spec problem: report it with the `detail` and the files in `out/_work/` |
| `network` | the plate tried to load something from the network (a theme with a remote font or image) | put the file next to the theme and use a relative path, or drop it: a plate loads nothing from the network, so it builds the same on a machine without one |
| `internal` | Schemantic itself failed | not a spec problem: report the detail and the spec |
