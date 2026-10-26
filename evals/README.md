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
`run_all.py` grades every run folder and prints the table below.

## Results

Run of 26 October 2026: eight cases, with and without the skill, on Sonnet 5.5 and Haiku 5.5, one run each. A
case passes when the automated grade passes and the judge finds no invented content and no defect.

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
