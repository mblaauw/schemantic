# Review: defect questions

Answer each question with the rendered PNG in front of you, yes or no. A "yes" is a defect: change the spec and
build again. Lint has already checked geometry; these check whether the plate works. Stop after three rounds and
report what is left.

1. **Message.** With the subtitle covered, does the picture fail to support the title's claim?
2. **Path.** Is there a jump where a reader cannot follow the arrows from where the story starts to where it ends?
   Test it: for each route the title or subtitle describes ("webshop via Kafka to Bronze"), put a finger on its first
   card and follow arrows to its last. An arrow that ends on a panel instead of the card the route goes through is a
   jump; so is a step that only a card note mentions.
3. **Arrows.** Does any arrow point against what `flows_mean` says arrows mean (data where requests are meant)?
4. **Colour.** Does any panel have a role whose legend label is wrong for it (people marked as a system)?
5. **Holes.** Is any part of the plate visibly empty: a panel emptier than its neighbours, an empty cell in the
   grid, cards floating apart in a tall panel, or a blank band above or below? (Lint warns at 96 px; a hole you can
   see is a defect even when lint is clean.)
6. **Footer.** Does the footer draw the eye before the body, or take more than about an eighth of the plate?
7. **Words.** Is any name a term the reader would not know, or any note true of every system rather than this one?
8. **Truth.** Is any card, flow or principle not traceable to the sources (the brief's assumptions aside)?
9. **Open ends.** Is any warning a question that is already settled, or any principle a slogan nobody could check?
10. **Series.** If this is one part of a series, does anything carry a different name or colour than on the other
    parts?
