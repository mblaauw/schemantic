// Set the canvas height before anything is measured. fit: the plate takes its content height, rounded up to 8 px
// (a slide keeps at least `minHeight`, handled as fixed). fixed: the preset height; the surplus goes evenly to the
// row gutters and the gap above the footer, capped per gap, and what is left stays under the footer, never inside a
// panel.
const EVEN_ROW_PX = 36;

schemantic.fit = ({ mode, height, gaps, cap, minHeight, even }) => {
  const plate = schemantic.plate();
  // A last row that does not fill the grid leaves a hole beside its last card: that card takes the rest of the row. Cards
  // a layout places itself (a column, a row) stay where they are, and so do grids whose rows must line up.
  for (const grid of plate.querySelectorAll(".blk.cards:not([data-keep])")) {
    const cards = [...grid.children].filter((el) => el.classList.contains("card"));
    if (cards.some((c) => c.style.gridColumn || c.style.gridRow)) continue;
    const columns = getComputedStyle(grid)
      .gridTemplateColumns.split(/\s+/)
      .filter((w) => parseFloat(w) > 0).length;
    const over = cards.length % columns;
    if (over) cards[cards.length - 1].style.gridColumn = `span ${columns - over + 1}`;
  }
  // A panel a little shorter than the tallest beside it ends in a hole of its own: its cards take up the difference, when
  // that adds little to each row. A much shorter panel stays as it is, and lint says so.
  const rowmates = [...plate.querySelectorAll("#body > .panel:not(.spread), .spoke-row > .panel")];
  const box = (el) => el.getBoundingClientRect();
  const tallest = rowmates.map((p) =>
    Math.max(
      ...rowmates
        .filter((o) => o.parentElement === p.parentElement && Math.abs(box(o).top - box(p).top) < 2)
        .map((o) => box(o).bottom),
    ),
  );
  rowmates.forEach((p, i) => {
    if (!even) return;
    const grid = p.querySelector(":scope > .pb > .blocks > .cards");
    if (!grid || p.querySelector(".chips-bottom")) return;
    const rows = getComputedStyle(grid).gridTemplateRows.split(/\s+/).length;
    if (tallest[i] - box(p).bottom <= EVEN_ROW_PX * rows) p.classList.add("evened");
  });
  plate.style.height = "auto";
  const natural = plate.getBoundingClientRect().height;
  if (mode === "fit" && natural >= minHeight) {
    const h = Math.ceil(natural / 8) * 8;
    plate.style.height = `${h}px`;
    return h;
  }
  if (mode === "fit") height = minHeight;
  const surplus = height - natural;
  if (surplus > 0 && gaps > 0) plate.style.setProperty("--gap-extra", `${Math.min(surplus / gaps, cap)}px`);
  plate.style.height = `${height}px`;
  return height;
};
