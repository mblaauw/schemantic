"""Every lint check, what it means, and how to fix it. Findings carry the first fix as `hint`, and
references/lint-fixes.md is generated from this table (`schemantic docs`), so code and docs cannot drift."""
from __future__ import annotations

from dataclasses import dataclass

from .config import ROOT


def finding(check: str, id_: str, detail: str, level: str = "error", **extra) -> dict:
    """A lint finding: which check, the element it is about (an id or a path in the spec), and what is wrong. `extra`
    carries a finding's own `hint` when it knows a better first fix than the table's."""
    return {"level": level, "check": check, "id": id_, "detail": detail, **extra}


@dataclass(frozen=True)
class Check:
    stage: str      # "spec" (no browser) or "layout" (measured in Chromium)
    means: str
    fix: str
    hint: str       # one sentence: the first fix to try


CHECKS: dict[str, Check] = {
    "yaml": Check("spec", "the file is missing, is not valid YAML (the detail gives line and column) or holds no mapping",
                  "fix the file; quote strings that contain `: ` or start with a special character",
                  "Fix the YAML at the line and column in the detail."),
    "placeholder": Check("spec", "text a starter left (`schemantic new`): a string with TODO in it",
                         "write what the sources say in its place, or drop the field or element; the id is its path",
                         "Replace the TODO at the path in `id` with what the sources say, or drop it."),
    "schema": Check("spec", "a field is missing, misspelled, too long or of the wrong type",
                    "the `id` is the path to the field; shorten text or correct the key",
                    "Correct the field at the path in `id`; shorten text that is too long."),
    "id": Check("spec", "two panels share an id, two cards share an id, or a card id equals a panel id or a card's "
                "automatic id", "rename one; the detail names both places", "Rename one of the two elements in the detail."),
    "archetype": Check("spec", "`schemantic new` names an archetype there is no starter for",
                       "use one of the names in the detail; `references/archetypes.md` says when to use each",
                       "Use one of the archetypes named in the detail."),
    "layout": Check("spec", "layout keys do not fit the archetype, a panel is placed twice or not at all, an area is "
                    "not a rectangle, widths/heights do not match the grid, or `footer.columns` does not match the "
                    "footer panels", "follow the detail; every panel id appears in the layout exactly once",
                    "Place every panel id exactly once in the layout, using the keys of this archetype."),
    "budget": Check("spec", "more than 5 columns", "split the plate or merge panels", "Split the plate into a series, or merge panels."),
    "pattern": Check("spec", "a matrix row has the wrong number of cells", "one cell per column", "Give every matrix row one cell per column."),
    "flow": Check("spec", "a flow names an id that does not exist, connects an element to itself, or connects a card "
                  "to its own panel", "use a panel id, or give the card an `id`; connect two different boxes",
                  "Point the flow at an existing panel or card id, and at two different boxes."),
    "orphan": Check("spec", "no flow reaches a panel or any of its cards on a plate whose other panels connect (warning; "
                    "roadmap lanes and layer-cake rails are exempt)",
                    "add the flow the sources describe or imply (an implied one goes in the brief's assumptions); with no "
                    "basis at all, never invent one to clear this: leave the "
                    "warning and say why in the brief's assumptions, make the relation an open question, or drop the "
                    "panel if it does not serve the message",
                    "Add the flow the sources name or imply; with no basis at all, leave the warning and say why, never invent one."),
    "story": Check("spec", "a story names an id that does not exist, or no flow runs from one of its steps to the next",
                   "add the flow between the two steps the detail names, card to card when the route goes through cards "
                   "(give both cards an id); if the sources name no such step, the story claims too much",
                   "Add a flow from the first named step to the second, card to card."),
    "route-end": Check("spec", "a route stops short of what it is about: a story through a panel that holds cards, an arrow labelled "
                       "with a card's name that ends on the panel around it, or a card the title or subtitle names that no arrow "
                       "reaches (warning)",
                       "give the cards ids and run the arrow to the card it is about; if the sources speak of the whole panel, say "
                       "so in the label without a card's name",
                       "Run the arrow to the card, not the panel around it, and put that card in the story."),
    "series": Check("spec", "parts of one series disagree: numbering, `of`, language, what arrows mean, or one thing drawn in "
                    "two colours (people in one part, a platform component in another)",
                    "make the parts agree: one language, and the same role for a thing wherever it appears (a panel's role, or "
                    "the role of the panel a card sits in); arrows may mean different things per part when that is true, "
                    "said in each subtitle",
                    "Give the thing the same role in every part, and the parts one language and one flows_mean."),
    "canvas": Check("spec", "`part` without `of` (or the reverse), `part` larger than `of`, or a theme file that does not exist",
                    "give both, with `1 ≤ part ≤ of`; check the theme path (relative to the spec)",
                    "Give both canvas.part and canvas.of, with part no larger than of."),
    "role": Check("spec", "a panel role is neither built in nor defined by the theme, or the theme gives it no legend label in "
                  "the plate's language", "use platform, data, external or actor, or define the role and its label in the theme",
                  "Use a built-in role (platform, data, external, actor), or define it with a legend label in the theme."),
    "slide-budget": Check("spec", "a slide (canvas.profile: slide) holds more than 5 panels or 18 cards (warning)",
                          "make it two slides, each with its own message, or cut the cards the message does not need",
                          "Split it into two slides, or cut the cards the message does not need."),
    "role-fit": Check("spec", "a panel's colour says people but its cards look like systems, or the reverse, or it mixes both (warning)",
                      "give the panel the role of what it holds (actor for people and teams, platform, data or "
                      "external for systems), or split people and systems into two panels",
                      "Give the panel the role of what its cards are, or split people and systems apart."),
    "focus": Check("spec", "more than one panel or card has `focus: true`", "keep focus on the one element the title is about",
                   "Keep focus on the one element the title is about."),
    "flows-mean": Check("spec", "the plate has flows but no `flows_mean` (warning)", "say what an arrow means: data, request, "
                        "dependency, control or sequence", "Add flows_mean: data, request, dependency, control or sequence."),
    "timeline": Check("spec", "on a roadmap, an arrow ends at an item that starts before the item it comes from, so it reads "
                      "back in time (warning)", "point each arrow from what comes first to what builds on it, and say "
                      "`flows_mean: sequence`", "Reverse the arrow so it runs forward in time, with flows_mean: sequence."),
    "traceability": Check("spec", "the spec declares `sources`, and a card, arrow, status or warning has no source and is not "
                          "marked `assumed`; a ref names an undeclared source; a ref's quote is not in the file a source's `path` "
                          "names; or more than a third of the cards and arrows are assumed (warning)",
                          "add `refs: [\"<source id>: <path or quote>\"]` from the inventory (`status_ref` for a status); what the "
                          "sources do not say gets `assumed: <why>`, which the plate shows, or becomes an open question",
                          "Add refs quoting the source; what it does not say gets `assumed: <why>`, or drop it."),
    "chip-mirror": Check("spec", "a warning chip or warning flag is not under open questions", "`open_questions: {from_chips: true}`",
                         "Set footer.open_questions.from_chips to true."),
    "icon": Check("spec", "unknown icon", "use one of the closest names in the hint, or search: `schemantic icons <word>`",
                  "Search the icons with: schemantic icons <word>."),
    "language": Check("spec", "a translated technical term in an `nl` plate", "use the English term (the id of the finding)",
                      "Use the English term named in `id`."),
    "card-width": Check("layout", "a wide panel stacks its cards in one column, and their text fills less than half of each "
                        "(warning)", "drop `card_columns` so cards flow into columns of 280 px, or raise it; or give the "
                        "panel less width", "Drop card_columns so the cards flow into columns, or raise it."),
    "text-overflow": Check("layout", "a word or line runs outside its box",
                           "shorten the text; avoid one long word in a narrow tile; fewer `card_columns`; more `weights` "
                           "for that block", "Shorten the text, or give its block more width."),
    "containment": Check("layout", "a block is taller or wider than its panel",
                         "fewer cards or bullets; move a card to another panel; split the plate",
                         "Cut cards or bullets in that panel, or move one to another panel."),
    "canvas-fit": Check("layout", "something extends past the canvas margin",
                        "cut content; a shorter footer (fewer principles); `landscape-4x3` instead of 16x9",
                        "Cut content, or use the taller landscape-4x3 canvas."),
    "overlap": Check("layout", "two boxes overlap", "usually follows from containment; fix that first",
                     "Fix any containment finding first; overlap usually follows from it."),
    "type-floor": Check("layout", "text below 11 px", "only from theme overrides; restore the type ramp in `tokens.css`",
                        "Restore the type sizes in the theme to 11 px or more."),
    "contrast": Check("layout", "text colour too close to its background", "only from theme overrides; fix the token pair",
                      "Fix the colour pair in the theme so text reaches 4.5:1."),
    "arrow-routing": Check("layout", "no clear route, or a route crosses a panel or card",
                           "move the card to the side of its panel nearest the other end; place the two panels next to each "
                           "other; only then join the panels, and name the cards the route means in the brief",
                           "Move the card nearer the other end, or the two panels next to each other, before joining panels."),
    "arrow-label": Check("layout", "no room for a label, or it touches a box",
                         "shorten the label, drop it, or explain the flow in a card note",
                         "Shorten or drop the label, or explain the flow in a card note."),
    "arrow-crossing": Check("layout", "an arrow crosses another arrow at a right angle",
                            "connect a card instead of its panel, or the other way round; swap the two panels so the "
                            "arrows run side by side; drop a flow the message does not need",
                            "Swap the two panels, or connect panels instead of cards, so the arrows no longer cross."),
    "print-size": Check("layout", "on paper the plate is scaled down to fit the sheet, and its smallest text would print below 6 pt",
                        "print on a3-landscape, or cut content so the plate is shorter; a4-landscape suits a plate of a "
                        "few panels",
                        "Print on a3-landscape, or cut content so the plate is shorter."),
    "rail-layer": Check("layout", "a rail card cannot sit level with the layer it names (warning)",
                        "fewer or shorter cards above it in the rail, a later layer for one of them, or no layer for "
                        "cards that concern every layer",
                        "Shorten the rail cards above it, or drop `layer` from a card that concerns every layer."),
    "footer-share": Check("layout", "the footer takes more than an eighth (12.5%) of the plate's height, and more than two lines "
                          "over the legend (warning)",
                          "fewer principles (three that a team could check), shorter open questions, no context panel "
                          "unless the roles matter to the message; the footer is context for the body",
                          "Cut the footer: keep three principles, shorten the questions, or drop the context panel."),
    "widow": Check("layout", "the topic, title or subtitle ends with a single word on a line of its own",
                   "cut a few words, or rephrase so the line breaks between phrases; a headline reads best on one line",
                   "Shorten the title by a few words so its last line is not a single word."),
    "chip-length": Check("layout", "a chip runs to three lines", "shorten it to one clear sentence",
                         "Shorten the chip to one sentence of about 50 characters."),
    "void": Check("layout", "a run of empty space inside a body panel (warning over 96 px, error over 160 px), below a short "
                  "panel next to taller ones in its row, inside a zone frame, in an empty cell of `layout.areas`, or as a "
                  "blank band under the footer or around a plate on paper (warning over 96 px); or cards a row-spanning "
                  "panel spreads apart by most of a card's height",
                  "add real content (bullets, a pattern, an info chip); move the panel next to one of its height; merge it "
                  "with a neighbour; let a panel span an empty cell; give a spread panel fewer rows; in nested zones, put "
                  "short panels in a row under the zones (`outside_at: bottom`); on paper or a fixed "
                  "height, let the plate grow taller (fewer `card_columns`, another row) or use `height: fit`; never "
                  "filler", "Add real content to the panel, or place it next to a panel of its height."),
    "svg-parity": Check("layout", "the SVG differs from the measured layout",
                        "a renderer problem, not a spec problem: report it with the `detail` and the files in `out/_work/`",
                        "Report it with the detail and the files in out/_work/; it is not a spec problem."),
    "paint": Check("layout", "a theme uses CSS the SVG cannot draw (shadows, gradients, transforms, opacity, text-transform, "
                   "letter-spacing, decoration, italics, outlines, non-solid borders, ::before/::after content)",
                   "remove it from the theme: the plate's styles are backgrounds, solid borders, radii, text (family, "
                   "size, weight, colour) and icons, so the SVG matches the page",
                   "Remove that property from the theme; plates draw only backgrounds, solid borders, text and icons."),
    "font": Check("layout", "text uses a font family that is not bundled, or characters the bundled fonts lack (CJK, emoji, "
                  "some symbols)",
                  "use Inter (or DejaVu Sans Mono for code) and write the word instead of the symbol or emoji; the SVG "
                  "embeds only bundled fonts, so anything else looks different on another machine",
                  "Write the word instead of the symbol, or use a bundled font (Inter, DejaVu Sans Mono)."),
    "network": Check("layout", "the plate tried to load something from the network (a theme with a remote font or image)",
                     "put the file next to the theme and use a relative path, or drop it: a plate loads nothing from the "
                     "network, so it builds the same on a machine without one",
                     "Bundle the font or image with the theme, or drop it; plates load nothing from the network."),
    "internal": Check("layout", "Schemantic itself failed", "not a spec problem: report the detail and the spec",
                      "Report the detail and the spec; it is not a spec problem."),
}


def with_hint(finding: dict) -> dict:
    """The finding with its check's hint, unless the finding brings a more specific one (an icon's closest names)."""
    check = CHECKS.get(finding["check"])
    return {**finding, "hint": finding.get("hint") or check.hint} if check else finding


def grouped(issues: list[dict]) -> dict:
    """The report's findings: errors, warnings, and a summary of one line per check (errors first, in the order they
    were found, so the first line is the one to fix first) with its count and hint. A hint repeated by the same
    check (a fresh starter has dozens of TODOs) is given once, on that check's first finding and in the summary."""
    ordered = [with_hint(i) for i in issues if i["level"] == "error"] + [with_hint(i) for i in issues if i["level"] == "warning"]
    summary: dict[tuple[str, str], dict] = {}
    seen: set[tuple[str, str | None]] = set()
    out: dict[str, list] = {"error": [], "warning": []}
    for f in ordered:
        line = summary.setdefault((f["level"], f["check"]), {"check": f["check"], "level": f["level"], "count": 0, "hint": f.get("hint")})
        line["count"] += 1
        key = (f["check"], f.get("hint"))
        out[f["level"]].append(f if key not in seen else {k: v for k, v in f.items() if k != "hint"})
        seen.add(key)
    return {"errors": out["error"], "warnings": out["warning"], "summary": list(summary.values())}


LINT_FIXES = ROOT / "references" / "lint-fixes.md"


def lint_fixes_md() -> str:
    """references/lint-fixes.md, generated from CHECKS."""
    parts = ["# Lint findings and their fixes", "",
             "Generated from `schemantic/findings.py` by `python -m schemantic docs`; edit the table there.", "",
             "Every finding names an element id (`gateway`, `services.card2`, `flows/3`, `footer.open_questions`). "
             "A check's `hint`, the first fix to try, comes with its first finding and in the report's `summary`, one "
             "line per check with its count, errors first. Fix it in the spec. Errors block delivery; warnings are "
             "judgement calls that usually mean \"add substance\"."]
    for stage, title in (("spec", "Spec checks (no browser)"), ("layout", "Layout checks (measured in Chromium)")):
        parts += ["", f"## {title}", "", "| check | means | fix |", "| --- | --- | --- |"]
        parts += [f"| `{name}` | {c.means} | {c.fix} |" for name, c in CHECKS.items() if c.stage == stage]
    return "\n".join(parts) + "\n"
