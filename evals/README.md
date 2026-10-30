# Skill evals

Eight cases test the skill's real job: from sources to a truthful plate. Each case in `cases/` has a `prompt.md`
(what the user asks), `inputs/` (fictional sources) and a `rubric.yaml` (what a good plate must have).

| Case | Source | What it tests |
| --- | --- | --- |
| 1-notes-nl | Dutch meeting notes | inventory from notes, decisions as principles, the open point as a question, `lang: nl` |
| 2-repo-en | compose file, Terraform, README | inventory from a repository, the TODO as an open question |
| 3-series | a 40-component inventory | the series rule: two or more plates |
| 4-open-choices | a proposal with two undecided choices | both choices visible as warnings and open questions |
| 5-process-swimlane | a process with handoffs | lanes per actor, numbered steps |
| 6-deployment-zones | environments, clusters, namespaces | nested zones |
| 7-phase-change | today versus phase 2 | change status tags (new, removed, planned) |
| 8-language-follows-user | a Dutch note, an English request | the plate's language follows the user, not the source |

## Running

Each run gives an agent the case prompt and inputs in an empty working folder, and nothing else. **With the skill**
the agent is also given `SKILL.md`'s path; **without** it is not, and may produce the plate any way it can. Collect
everything it writes into `runs/<model>/<with|without>/<case>/`, then grade:

```bash
python evals/grade.py evals/cases/<case> runs/<model>/<with|without>/<case>   # the automated half
```

and have a separate agent apply `judge.md` to the same folder (the judged half). A run passes when both halves pass.
`run_all.py` grades every run folder and prints the automated columns of the tables below.

## Latest results

The newest run per model, eight cases with the skill, one run each, judged blind. A case passes when the automated
grade passes and the judge finds no invented content and no defect; the judge fails a plate on any single defect.

| Model | Run | Automated | Judged | Nothing invented | Defects per plate |
| --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 29 October, second rerun | 8/8 | 2/8 | 7/8 | 2.1 |
| Haiku 5.5 | 29 October, third run | 8/8 | 0/8 | 8/8 | 2.5 |

Without the skill neither model builds a spec, a lint-clean plate or traceable cards (26 October: 0/8 automated on
both); that has not been rerun since.

The most frequent defect left is **paths**: arrows that end on a panel where the title names a card, and steps that
live only in a card note (7 of Haiku's last 20 defects, 16 of 45 across both models the run before).

**Not yet measured:** everything since these runs. Stories (a route named in the title, checked by lint and drawn as
numbered steps), starters (`schemantic new`), review crops (`build --review`, only of what changed after the first
round), grouped findings, the skill's reordered steps and worked examples that draw their
routes, the `sequence` flows and `now` column, and slate arrows. One run per case is noisy; the next rerun should
take three per case.

## History

Each run below names what changed before it and what it found; the targets it names are what the following runs
went after.

### First run (26 October 2026)

Eight cases, with and without the skill, on Sonnet 5.5 and Haiku 5.5, one run each. A case passes when the automated grade passes and the judge finds no invented content and no defect.

| Model | Skill | Automated | Judged | Claim title | Nothing invented | Layout fits | Defects per plate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | without | 0/8 | 0/8 | 0/8 | 7/8 | 8/8 | 2.9 |
| Sonnet 5.5 | with | 8/8 | 0/8 | 8/8 | 8/8 | 8/8 | 2.8 |
| Haiku 5.5 | without | 0/8 | 0/8 | 0/8 | 5/8 | 7/8 | 3.8 |
| Haiku 5.5 | with | 8/8 | 2/8 | 8/8 | 8/8 | 8/8 | 2.0 |

Without the skill neither model produces a spec, a lint-clean build or traceable cards, so the automated half fails
every case; the judge then sees hand-drawn SVG or HTML. With the skill every plate builds clean, every title is a
claim and nothing is invented. Haiku gains the most: fewer invented items and half the defects.

The judge fails a plate on any one defect, which is strict on purpose. What it still found on the 16 plates made
with the skill, most frequent first:

- **Holes** (9 plates): a panel visibly emptier than its neighbours, often under the 96 px void threshold, or a
  short panel beside a tall one. Haiku's case 6 was judged on a render from before the nested-zones fix in this
  release, which removes its worst holes.
- **Footer over an eighth** (5): principles, open questions and a legend on two lines take about a fifth.
- **Paths drawn panel to panel** (4): the title promises a path through named cards that the arrows do not show.
- **Role colour** (4): systems in a people panel, or one colour for everything.
- **Open questions the sources settle** (4).

These are the next targets for lint and the review questions.

### Rerun of 29 October 2026 (with the skill only)

The same eight cases with the skill as it stands after the design tiers (claim titles with a topic line, question
labels, panels that end with their content, footer and widow lint, series checks, before-after, rails by layer,
quieter neighbours around the focus, role-fit, the slide profile, roadmap). Without the skill nothing changed, so it
was not rerun. One run per case; the judge saw the runs under neutral names.

| Model | Automated | Judged | Claim title | Nothing invented | Layout fits | Defects per plate (26 Oct) |
| --- | --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 8/8 | 0/8 | 8/8 | 8/8 | 8/8 | 2.2 (2.8) |
| Haiku 5.5 | 8/8 | 0/8 | 8/8 | 7/8 | 8/8 | 1.6 (2.0) |

Defects fell by about a fifth on both models; the judged pass rate did not move (Haiku passed 2 of 8 before, 0
now), since the judge fails a plate on any single defect and one run per case is noisy. By kind:

- Footer over an eighth: 5 plates before, none now (`footer-share`).
- Role colour: 4 before, 2 now (`role-fit` caught and fixed two more during the runs, by the agents' reports).
- Holes are still first (12): with panels ending at their content, the judge now names the space beside a short
  panel ("ends 135 px above the panel beside it"), and an empty area inside a zone frame, which no check measures.
- Paths (6): the arrows join panels where the title names a route through cards, and two swimlane runs could not
  draw an arrow from the bottom lane back to the top one, so the agents left a step out.

The next targets: a hole check for rows and zones, card-to-card routes when the message names a path, and the
router's long upward arrows in a swimlane.

### Rerun of 29 October 2026, second (after the hole, router and path fixes)

The same eight cases with the skill, after the hole check for rows and zones, the second outer lane and the rule
that a route named in the title is traced card by card. The review questions gained the finger test, so the judge
reads paths more strictly than before; to measure that, the first rerun's Haiku plates were judged again, blind,
with the current questions.

| Model | Automated | Judged | Claim title | Nothing invented | Layout fits | Defects per plate |
| --- | --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 8/8 | 2/8 | 8/8 | 7/8 | 8/8 | 2.1 |
| Haiku 5.5 | 8/8 | 0/8 | 8/8 | 6/8 | 8/8 | 3.5 |
| Haiku 5.5, first rerun's plates judged again | | 0/8 | 8/8 | 5/8 | 8/8 | 2.25 (1.6 then) |

- Sonnet passes the judged half for the first time (the swimlane and the deployment zones) and holds its defect
  rate under the stricter judge.
- The stricter judge alone adds about 0.6 defects per Haiku plate (1.6 to 2.25 on the same plates). Today's Haiku
  plates are worse than that, at 3.5: holes on 6 plates against 3. The holes are of kinds no check measures: an
  empty grid cell left by `areas`, cards spread apart inside a panel, and a blank band on a fixed or paper canvas.
  Two Haiku agents saw a hole and left it, because lint was clean.
- Paths are the most frequent defect on both models (16 of 45): arrows that end on a panel where the title names
  a card, and routes in the subtitle with no arrow at all.
- Two Haiku plates added small facts in card notes ("the decision becomes final"); one Sonnet series called a
  read optional by drawing it dotted.

Next targets: the three kinds of hole above as lint, a warning when a flow named in the subtitle ends on a panel
that holds the named card, and keeping the dotted style for what the legend says it means.

### Haiku after the hole checks (29 October, third run)

Haiku only, with the skill at the hole checks (empty grid cells, spread cards, blank bands; before zone frames
ended with their content). Judged blind with the same review questions as the second run and its control, so the
three Haiku rows compare directly.

| Haiku 5.5 plates | Judged | Nothing invented | Plates with holes | Defects per plate |
| --- | --- | --- | --- | --- |
| first rerun's, judged again | 0/8 | 5/8 | 3 | 2.25 |
| second rerun | 0/8 | 6/8 | 6 | 3.5 |
| after the hole checks | 0/8 | 8/8 | 2 | 2.5 |

- Holes fell from 6 plates to 2: one is two account frames half empty beside a tall one (zone frames now end with
  their content), the other a gap under 96 px.
- Nothing was invented on any plate, for the first time on Haiku.
- Paths are now most of what is left (7 of 20 defects): arrows that end on a panel, and steps that live only in a
  card note. Colour is next (3): people in a platform panel.

