# Lint findings and their fixes

Generated from `schemantic/findings.py` by `python -m schemantic docs`; edit the table there.

Every finding names an element id (`gateway`, `services.card2`, `flows/3`, `footer.open_questions`). A check's `hint`, the first fix to try, comes with its first finding and in the report's `summary`, one line per check with its count, errors first. Fix it in the spec. Errors block delivery; warnings are judgement calls that usually mean "add substance".

## Spec checks (no browser)

| check | means | fix |
| --- | --- | --- |
| `yaml` | the file is missing, is not valid YAML (the detail gives line and column) or holds no mapping | fix the file; quote strings that contain `: ` or start with a special character |
| `placeholder` | text a starter left (`schemantic new`): a string with TODO in it | write what the sources say in its place, or drop the field or element; the id is its path |
| `schema` | a field is missing, misspelled, too long or of the wrong type | the `id` is the path to the field; shorten text or correct the key |
| `id` | two panels share an id, two cards share an id, or a card id equals a panel id or a card's automatic id | rename one; the detail names both places |
| `archetype` | `schemantic new` names an archetype there is no starter for | use one of the names in the detail; `references/archetypes.md` says when to use each |
| `layout` | layout keys do not fit the archetype, a panel is placed twice or not at all, an area is not a rectangle, widths/heights do not match the grid, or `footer.columns` does not match the footer panels | follow the detail; every panel id appears in the layout exactly once |
| `budget` | more than 5 columns | split the plate or merge panels |
| `pattern` | a matrix row has the wrong number of cells | one cell per column |
| `flow` | a flow names an id that does not exist, connects an element to itself, or connects a card to its own panel | use a panel id, or give the card an `id`; connect two different boxes |
| `orphan` | no flow reaches a panel or any of its cards on a plate whose other panels connect (warning; roadmap lanes and layer-cake rails are exempt) | add the flow the sources describe or imply (an implied one goes in the brief's assumptions); with no basis at all, never invent one to clear this: leave the warning and say why in the brief's assumptions, make the relation an open question, or drop the panel if it does not serve the message |
| `story` | a story names an id that does not exist, or no flow runs from one of its steps to the next | add the flow between the two steps the detail names, card to card when the route goes through cards (give both cards an id); if the sources name no such step, the story claims too much |
| `series` | parts of one series disagree: numbering, `of`, language, what arrows mean, or one thing drawn in two colours (people in one part, a platform component in another) | make the parts agree: one language, and the same role for a thing wherever it appears (a panel's role, or the role of the panel a card sits in); arrows may mean different things per part when that is true, said in each subtitle |
| `canvas` | `part` without `of` (or the reverse), `part` larger than `of`, or a theme file that does not exist | give both, with `1 ≤ part ≤ of`; check the theme path (relative to the spec) |
| `role` | a panel role is neither built in nor defined by the theme, or the theme gives it no legend label in the plate's language | use platform, data, external or actor, or define the role and its label in the theme |
| `slide-budget` | a slide (canvas.profile: slide) holds more than 5 panels or 18 cards (warning) | make it two slides, each with its own message, or cut the cards the message does not need |
| `role-fit` | a panel's colour says people but its cards look like systems, or the reverse, or it mixes both (warning) | give the panel the role of what it holds (actor for people and teams, platform, data or external for systems), or split people and systems into two panels |
| `focus` | more than one panel or card has `focus: true` | keep focus on the one element the title is about |
| `flows-mean` | the plate has flows but no `flows_mean` (warning) | say what an arrow means: data, request, dependency, control or sequence |
| `timeline` | on a roadmap, an arrow ends at an item that starts before the item it comes from, so it reads back in time (warning) | point each arrow from what comes first to what builds on it, and say `flows_mean: sequence` |
| `traceability` | the spec declares `sources`, and a card has no `refs` or names an undeclared source (warning) | add `refs: ["<source id>: <path or quote>"]` from the inventory; a card you cannot trace is an assumption or an open question, not a fact |
| `chip-mirror` | a warning chip or warning flag is not under open questions | `open_questions: {from_chips: true}` |
| `icon` | unknown icon | use one of the closest names in the hint, or search: `schemantic icons <word>` |
| `language` | a translated technical term in an `nl` plate | use the English term (the id of the finding) |

## Layout checks (measured in Chromium)

| check | means | fix |
| --- | --- | --- |
| `card-width` | a wide panel stacks its cards in one column, and their text fills less than half of each (warning) | drop `card_columns` so cards flow into columns of 280 px, or raise it; or give the panel less width |
| `text-overflow` | a word or line runs outside its box | shorten the text; avoid one long word in a narrow tile; fewer `card_columns`; more `weights` for that block |
| `containment` | a block is taller or wider than its panel | fewer cards or bullets; move a card to another panel; split the plate |
| `canvas-fit` | something extends past the canvas margin | cut content; a shorter footer (fewer principles); `landscape-4x3` instead of 16x9 |
| `overlap` | two boxes overlap | usually follows from containment; fix that first |
| `type-floor` | text below 11 px | only from theme overrides; restore the type ramp in `tokens.css` |
| `contrast` | text colour too close to its background | only from theme overrides; fix the token pair |
| `arrow-routing` | no clear route, or a route crosses a panel or card | move the card to the side of its panel nearest the other end; place the two panels next to each other; only then join the panels, and name the cards the route means in the brief |
| `arrow-label` | no room for a label, or it touches a box | shorten the label, drop it, or explain the flow in a card note |
| `arrow-crossing` | an arrow crosses another arrow at a right angle | connect a card instead of its panel, or the other way round; swap the two panels so the arrows run side by side; drop a flow the message does not need |
| `print-size` | on paper the plate is scaled down to fit the sheet, and its smallest text would print below 6 pt | print on a3-landscape, or cut content so the plate is shorter; a4-landscape suits a plate of a few panels |
| `rail-layer` | a rail card cannot sit level with the layer it names (warning) | fewer or shorter cards above it in the rail, a later layer for one of them, or no layer for cards that concern every layer |
| `footer-share` | the footer takes more than an eighth (12.5%) of the plate's height, and more than two lines over the legend (warning) | fewer principles (three that a team could check), shorter open questions, no context panel unless the roles matter to the message; the footer is context for the body |
| `widow` | the topic, title or subtitle ends with a single word on a line of its own | cut a few words, or rephrase so the line breaks between phrases; a headline reads best on one line |
| `chip-length` | a chip runs to three lines | shorten it to one clear sentence |
| `void` | a run of empty space inside a body panel (warning over 96 px, error over 160 px), below a short panel next to taller ones in its row, inside a zone frame, in an empty cell of `layout.areas`, or as a blank band under the footer or around a plate on paper (warning over 96 px); or cards a row-spanning panel spreads apart by most of a card's height | add real content (bullets, a pattern, an info chip); move the panel next to one of its height; merge it with a neighbour; let a panel span an empty cell; give a spread panel fewer rows; in nested zones, put short panels in a row under the zones (`outside_at: bottom`); on paper or a fixed height, let the plate grow taller (fewer `card_columns`, another row) or use `height: fit`; never filler |
| `svg-parity` | the SVG differs from the measured layout | a renderer problem, not a spec problem: report it with the `detail` and the files in `out/_work/` |
| `paint` | a theme uses CSS the SVG cannot draw (shadows, gradients, transforms, opacity, text-transform, letter-spacing, decoration, italics, outlines, non-solid borders, ::before/::after content) | remove it from the theme: the plate's styles are backgrounds, solid borders, radii, text (family, size, weight, colour) and icons, so the SVG matches the page |
| `font` | text uses a font family that is not bundled, or characters the bundled fonts lack (CJK, emoji, some symbols) | use Inter (or DejaVu Sans Mono for code) and write the word instead of the symbol or emoji; the SVG embeds only bundled fonts, so anything else looks different on another machine |
| `network` | the plate tried to load something from the network (a theme with a remote font or image) | put the file next to the theme and use a relative path, or drop it: a plate loads nothing from the network, so it builds the same on a machine without one |
| `internal` | Schemantic itself failed | not a spec problem: report the detail and the spec |
