// Set the canvas height before anything is measured. fit: the plate takes its content height, rounded up to 8 px
// (a slide keeps at least `minHeight`, handled as fixed). fixed: the preset height; the surplus goes evenly to the
// row gutters and the gap above the footer, capped per gap, and what is left stays under the footer, never inside a
// panel.
schemantic.fit = ({ mode, height, gaps, cap, minHeight }) => {
  const plate = schemantic.plate();
  if (mode === "legacy") return height; // row_heights given: rows share the preset height as in 0.1
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
