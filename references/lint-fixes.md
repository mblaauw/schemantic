# Lint findings and their fixes

Every finding names an element id (`gateway`, `services.card2`, `flows/3`, `footer.open_questions`). Fix it
in the spec. Errors block delivery; warnings are judgement calls that usually mean "add substance".

## Spec checks (no browser)

| check | means | fix |
| --- | --- | --- |
| `schema` | a field is missing, misspelled, too long or of the wrong type | the `id` is the path to the field; shorten text or correct the key |
| `archetype` | the archetype is planned but not built | pick a built one (`archetypes.md`, "Not built yet") |
| `layout` | layout keys do not fit the archetype, a panel is placed twice or not at all, an area is not a rectangle, widths/heights do not match the grid | follow the detail; every panel id appears in the layout exactly once |
| `budget` | more than 5 columns | split the plate or merge panels |
| `pattern` | a matrix row has the wrong number of cells | one cell per column |
| `flow` | a flow names an id that does not exist | use a panel id, or give the card an `id` |
| `chip-mirror` | a warning chip is not under open questions | `open_questions: {from_chips: true}` |
| `icon` | unknown icon | pick from the list in `spec-guide.md` |
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
| `chip-length` | a chip runs to three lines | shorten it to one clear sentence |
| `density` (warning) | a panel's content fills under 60% of it | add real content (bullets, a pattern, an info chip), merge it with a neighbour, give it less room (`row_heights`, a different layout); never filler |
| `svg-parity` | the SVG differs from the measured layout | a renderer problem, not a spec problem: report it with the `detail` and the files in `out/_work/` |
