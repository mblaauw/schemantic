# Judge prompt

You grade one plate produced for an eval case. You are given the case's `prompt.md` and `inputs/`, and the run's
outputs: the PNG, the SVG, and when present the spec (`*.yaml`) and outline (`*.md`). Read the PNG.

Answer in JSON, nothing else:

```json
{
  "claim_in_title": true,
  "invented": ["components, names or facts on the plate that the inputs do not contain"],
  "archetype_fits": true,
  "defects": ["any yes-answer to the questions in references/review.md, one line each"],
  "notes": "one or two sentences"
}
```

- `claim_in_title`: the title states a claim the plate supports, not a topic ("Architecture overview" is a topic).
- `invented`: be strict. Generic words ("API", "database") are fine when the inputs imply them; a named product, a
  number or a decision the inputs do not contain is invented. What the plate itself marks as assumed (an "assumed"
  tag, an amber dashed arrow) is not invented; what only the brief admits still is.
- `archetype_fits`: the layout suits the reader's question in the prompt (a process with handoffs between people
  wants lanes; a deployment wants nested zones; a path wants columns).
- `defects`: answer the review questions as a reviewer would, with the image in front of you.

The run passes the judged half when `claim_in_title` and `archetype_fits` are true and `invented` and `defects` are
empty.
