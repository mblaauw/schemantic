"""Every lint check, what it means, and how to fix it. Findings carry the first fix as `hint`, and
references/lint-fixes.md is generated from this table (`schemantic docs`), so code and docs cannot drift."""
from __future__ import annotations

from dataclasses import dataclass

from .config import ROOT


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
    "schema": Check("spec", "a field is missing, misspelled, too long or of the wrong type",
                    "the `id` is the path to the field; shorten text or correct the key",
                    "Correct the field at the path in `id`; shorten text that is too long."),
    "id": Check("spec", "two panels share an id, two cards share an id, or a card id equals a panel id or a card's "
                "automatic id", "rename one; the detail names both places", "Rename one of the two elements in the detail."),
    "archetype": Check("spec", "the archetype is planned but not built",
                       "pick a built one (`archetypes.md`, \"Not built yet\")",
                       "Pick a built archetype; references/archetypes.md lists workarounds."),
    "layout": Check("spec", "layout keys do not fit the archetype, a panel is placed twice or not at all, an area is "
                    "not a rectangle, widths/heights do not match the grid, or `footer.columns` does not match the "
                    "footer panels", "follow the detail; every panel id appears in the layout exactly once",
                    "Place every panel id exactly once in the layout, using the keys of this archetype."),
    "budget": Check("spec", "more than 5 columns", "split the plate or merge panels", "Split the plate into a series, or merge panels."),
    "pattern": Check("spec", "a matrix row has the wrong number of cells", "one cell per column", "Give every matrix row one cell per column."),
    "flow": Check("spec", "a flow names an id that does not exist, connects an element to itself, or connects a card "
                  "to its own panel", "use a panel id, or give the card an `id`; connect two different boxes",
                  "Point the flow at an existing panel or card id, and at two different boxes."),
    "canvas": Check("spec", "`part` without `of` (or the reverse), `part` larger than `of`, or a theme file that does not exist",
                    "give both, with `1 ≤ part ≤ of`; check the theme path (relative to the spec)",
                    "Give both canvas.part and canvas.of, with part no larger than of."),
    "role": Check("spec", "a panel role is neither built in nor defined by the theme, or the theme gives it no legend label in "
                  "the plate's language", "use platform, data, external or actor, or define the role and its label in the theme",
                  "Use a built-in role (platform, data, external, actor), or define it with a legend label in the theme."),
    "deprecated": Check("spec", "an old name that still works for one release (warning)", "use the new name in the detail",
                        "Use the new name given in the detail."),
    "chip-mirror": Check("spec", "a warning chip is not under open questions", "`open_questions: {from_chips: true}`",
                         "Set footer.open_questions.from_chips to true."),
    "icon": Check("spec", "unknown icon", "pick from the list in `spec-guide.md`", "Pick an icon from the list in references/spec-guide.md."),
    "language": Check("spec", "a translated technical term in an `nl` plate", "use the English term (the id of the finding)",
                      "Use the English term named in `id`."),
    "text-overflow": Check("layout", "a word or line runs outside its box",
                           "shorten the text; avoid one long word in a narrow tile; fewer `card_columns`; more `weights` "
                           "for that block", "Shorten the text, or give its block more width."),
    "containment": Check("layout", "a block is taller or wider than its panel",
                         "fewer cards or bullets; move a card to another panel; `row_heights: auto` for that row; split "
                         "the plate", "Cut cards or bullets in that panel, or move one to another panel."),
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
                           "connect the panels instead of cards; move the target card to the side of its panel nearest "
                           "the source; place the two panels next to each other",
                           "Connect the two panels instead of their cards, or move one panel next to the other."),
    "arrow-label": Check("layout", "no room for a label, or it touches a box",
                         "shorten the label, drop it, or explain the flow in a card note",
                         "Shorten or drop the label, or explain the flow in a card note."),
    "chip-length": Check("layout", "a chip runs to three lines", "shorten it to one clear sentence",
                         "Shorten the chip to one sentence of about 50 characters."),
    "density": Check("layout", "a panel's content fills under 60% of it",
                     "add real content (bullets, a pattern, an info chip), merge it with a neighbour, give it less room "
                     "(`row_heights`, a different layout); never filler",
                     "Add real content to the panel, or merge it with a neighbour; never filler."),
    "svg-parity": Check("layout", "the SVG differs from the measured layout",
                        "a renderer problem, not a spec problem: report it with the `detail` and the files in `out/_work/`",
                        "Report it with the detail and the files in out/_work/; it is not a spec problem."),
    "internal": Check("layout", "Schemantic itself failed", "not a spec problem: report the detail and the spec",
                      "Report the detail and the spec; it is not a spec problem."),
}


def with_hint(finding: dict) -> dict:
    check = CHECKS.get(finding["check"])
    return {**finding, "hint": check.hint} if check else finding


LINT_FIXES = ROOT / "references" / "lint-fixes.md"


def lint_fixes_md() -> str:
    """references/lint-fixes.md, generated from CHECKS."""
    parts = ["# Lint findings and their fixes", "",
             "Generated from `schemantic/findings.py` by `python -m schemantic docs`; edit the table there.", "",
             "Every finding names an element id (`gateway`, `services.card2`, `flows/3`, `footer.open_questions`) and "
             "carries a `hint`, the first fix to try. Fix it in the spec. Errors block delivery; warnings are judgement "
             "calls that usually mean \"add substance\"."]
    for stage, title in (("spec", "Spec checks (no browser)"), ("layout", "Layout checks (measured in Chromium)")):
        parts += ["", f"## {title}", "", "| check | means | fix |", "| --- | --- | --- |"]
        parts += [f"| `{name}` | {c.means} | {c.fix} |" for name, c in CHECKS.items() if c.stage == stage]
    return "\n".join(parts) + "\n"
