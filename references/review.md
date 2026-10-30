# Review: defect questions

Answer each question with the review crops in front of you (`build --review`), yes or no. A "yes" is a defect:
change the spec and build again. Stop after three rounds and report what is left.

The first round lists the whole plate and a crop of every part. Later rounds list the whole plate and the parts that
changed since; `review_unchanged` lists the others, whose crops are still there, so read those too if you rebuilt
before reading them. Ask the whole-plate questions (1, 2, 5) of the overview each round, and the others of the crops
you have not read yet. `--review all` lists every part again.

Lint has already measured what it can, so a clean build answers part of these; each question says which part is
left to you.

1. **Message.** With the subtitle covered, does the picture fail to support the title's claim? (No check can.)
2. **Path.** Is there a jump where a reader cannot follow the route the title or subtitle names, from its first
   card to its last? Lint (`story`) checks that a flow joins every step of a story; you check that every route the
   title names has a story, drawn (`draw: true`), and that no step lives only in a card note.
3. **Arrows.** Does any arrow point against what `flows_mean` says arrows mean (data where requests are meant)?
   Lint catches a roadmap arrow back in time (`timeline`); every other direction is yours.
4. **Colour.** Does any panel have a role whose legend label is wrong for it? Lint (`role-fit`) judges a panel by
   its cards' icons; you judge the panels whose icons do not say (a team drawn with system icons).
5. **Holes.** Is any part of the plate visibly empty: a panel emptier than its neighbours, cards floating apart, a
   blank band? Lint (`void`) warns at 96 px; a smaller hole you can see is still a defect.
6. **Footer.** Does the footer draw the eye before the body? Its size is lint's (`footer-share`).
7. **Words.** Is any name a term the reader would not know, or any note true of every system rather than this one?
   (No check can.)
8. **Truth.** Is any card, flow or principle not supported by the sources (the brief's assumptions aside)? Lint
   (`traceability`) checks that every card cites a source; you check that the source says it.
9. **Open ends.** Is any warning a question the sources already settle, or any principle a slogan nobody could
   check? (No check can.)
10. **Series.** If this is one part of a series, does anything carry a different name than on the other parts?
    `plate.py series` checks the language, the arrows' meaning and one colour per thing.
