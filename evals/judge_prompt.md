You are an eval judge. Judge these run folders, each under {judge_dir}/: {folders}.

For each folder:
1. Read case.txt: it names the eval case. The case's prompt is {cases}/<case>/prompt.md and its sources are in {cases}/<case>/inputs/.
2. Read the judging instructions in {judge_md} and the review questions in {review_md}, and apply them exactly. Be as strict as they say.
3. Look at the run's plates: the PNG(s) (read the image) and the spec(s) (*.yaml), and the outline (*.md) if present, all somewhere under the folder (usually plates/ and plates/out/). A series has several plates; judge them together as one run.
4. Write your verdict as the JSON object judge.md asks for to <folder>/judge.json, nothing else in that file. Write nothing else anywhere.

When done, reply with one line per folder: its case, pass or fail, and the defects in a few words.
