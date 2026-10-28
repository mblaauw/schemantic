"""The SVG writer is a pure function of the layout document: tested on hand-made documents, without Chromium."""
from schemantic.export import num, svg_items

INK = {"color": "#1a2b3c"}


def test_numbers_are_short_and_rounded():
    assert [num(v) for v in (12.0, 12.5, 12.349999999999998, -0.0, 0.004)] == ["12", "12.5", "12.35", "0", "0"]


def test_a_group_nests_its_items_and_carries_its_identity():
    doc = [{"kind": "group", "type": "panel", "id": "data", "label": "panel: Data & storage", "refs": "notes: line 3",
            "items": [{"kind": "rect", "x": 0, "y": 0, "w": 10, "h": 5, "radii": [0, 0, 0, 0], "fill": INK}]}]
    assert svg_items(doc) == [
        '<g id="panel-data" data-id="data" data-refs="notes: line 3" inkscape:label="panel: Data &amp; storage">',
        '<rect x="0" y="0" width="10" height="5" fill="#1a2b3c"/>',
        "</g>"]


def test_equal_radii_make_a_rect_and_unequal_ones_a_path():
    same = {"kind": "rect", "x": 1, "y": 2, "w": 30, "h": 20, "radii": [7, 7, 7, 7], "fill": INK}
    top = dict(same, radii=[7, 7, 0, 0])
    assert svg_items([same]) == ['<rect x="1" y="2" width="30" height="20" rx="7" fill="#1a2b3c"/>']
    assert svg_items([top]) == ['<path d="M8 2H24A7 7 0 0 1 31 9V22H1V9A7 7 0 0 1 8 2Z" fill="#1a2b3c"/>']


def test_a_stroked_rect_without_fill_says_so_and_keeps_opacity():
    rect = {"kind": "rect", "x": 0.5, "y": 0.5, "w": 9, "h": 9, "radii": [0, 0, 0, 0], "fill": None,
            "stroke": {"color": "#000000", "opacity": 0.25}, "strokeWidth": 1}
    assert svg_items([rect]) == [
        '<rect x="0.5" y="0.5" width="9" height="9" fill="none" stroke="#000000" stroke-opacity="0.25" stroke-width="1"/>']


def test_text_is_escaped_and_keeps_preserved_spaces():
    line = {"kind": "text", "x": 4, "y": 16, "text": 'a < b & "c"', "preserve": True, "fill": INK,
            "font": {"family": '"DejaVu Sans Mono", monospace', "size": 12.5, "weight": "400"}}
    assert svg_items([line]) == [
        '<text x="4" y="16" font-family="\'DejaVu Sans Mono\', monospace" font-size="12.5" font-weight="400" '
        'fill="#1a2b3c" xml:space="preserve">a &lt; b &amp; &quot;c&quot;</text>']


def test_an_icon_is_scaled_from_its_24_px_grid():
    icon = {"kind": "icon", "x": 10, "y": 20, "size": 18, "stroke": "#1a2b3c", "strokeWidth": "1.75", "svg": "<path d=\"M1 1\"/>"}
    assert svg_items([icon]) == [
        '<g transform="translate(10 20) scale(0.7500)" fill="none" stroke="#1a2b3c" stroke-width="1.75" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M1 1"/></g>']
