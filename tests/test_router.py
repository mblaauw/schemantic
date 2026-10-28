"""B4: router unit tests on hand-made boxes in a blank page; no template, no spec."""
import pytest
from conftest import ROOT, browser
from playwright.sync_api import sync_playwright

TOKENS = (ROOT / "templates" / "tokens.css").read_text(encoding="utf-8")


def page_with(boxes: dict[str, tuple], cards: dict[str, tuple[str, tuple]] | None = None) -> str:
    """A plate with absolutely placed panels {id: (l, t, w, h)} and cards {id: (panel id, (l, t, w, h))}."""
    def div(kind, id_, box, inner=""):
        left, top, w, h = box
        return (f'<div data-kind="{kind}" data-id="{id_}" style="position:absolute;left:{left}px;top:{top}px;'
                f'width:{w}px;height:{h}px">{inner}</div>')
    cards = cards or {}
    panels = "".join(div("panel", pid, box, "".join(div("card", cid, cbox) for cid, (owner, cbox) in cards.items()
                                                     if owner == pid)) for pid, box in boxes.items())
    return (f"<html><head><style>{TOKENS} body{{margin:0}} #plate{{position:relative;width:1000px;height:700px}}"
            f"</style></head><body><div id=\"plate\"><main id=\"body\">{panels}</main></div></body></html>")


@pytest.fixture(scope="module")
def route():
    with sync_playwright() as p:
        chromium = browser.launch(p)

        def run(html: str, flows: list[dict]) -> dict:
            page = chromium.new_page(viewport={"width": 1000, "height": 700})
            page.set_content(html)
            page.add_script_tag(content=browser.page_scripts())
            out = browser.call(page, "route", flows)
            page.close()
            return out
        yield run
        chromium.close()


def test_neighbours_get_a_straight_arrow(route):
    out = route(page_with({"a": (0, 100, 200, 300), "b": (248, 100, 200, 300)}), [{"from": "a", "to": "b"}])
    assert out["problems"] == []
    assert out["segs"][0]["points"] == [[207, 250], [241, 250]]  # centred on the shared span, 7 px off each box


def test_offset_cards_turn_through_the_gutter(route):
    html = page_with({"a": (0, 0, 200, 600), "b": (248, 0, 200, 600)},
                     {"top": ("a", (12, 20, 176, 60)), "under": ("a", (12, 88, 176, 500)),
                      "over": ("b", (12, 20, 176, 470)), "low": ("b", (12, 500, 176, 60))})
    out = route(html, [{"from": "top", "to": "low"}])
    pts = out["segs"][0]["points"]
    assert out["problems"] == [] and len(pts) == 4 and pts[1][0] == pts[2][0] == 224  # Z along the gutter centre


def test_a_box_in_the_way_blocks_the_route(route):
    html = page_with({"a": (0, 0, 200, 600), "wall": (248, 0, 200, 600), "b": (496, 0, 200, 600)},
                     {"x": ("a", (12, 20, 176, 60)), "y": ("b", (12, 20, 176, 60))})
    out = route(html, [{"from": "x", "to": "y"}])
    assert [p["kind"] for p in out["problems"]] == ["route"]


def test_second_flow_in_a_gutter_takes_another_lane(route):
    html = page_with({"a": (0, 0, 200, 600), "b": (248, 0, 200, 600)},
                     {"a1": ("a", (12, 20, 176, 60)), "a2": ("a", (12, 120, 176, 60)),
                      "b1": ("b", (12, 420, 176, 60)), "b2": ("b", (12, 520, 176, 60))})
    out = route(html, [{"from": "a1", "to": "b1"}, {"from": "a2", "to": "b2"}])
    xs = [s["points"][1][0] for s in out["segs"]]
    assert out["problems"] == [] and len(set(xs)) == 2 and abs(xs[0] - xs[1]) >= 10


# F04: crossing another arrow costs as much as two bends, so a slightly longer route that crosses nothing wins
def test_a_route_that_crosses_nothing_beats_a_shorter_one_that_crosses(route):
    html = page_with({"top": (0, 0, 700, 64), "a": (0, 160, 200, 200), "m": (248, 160, 200, 200),
                      "b": (496, 160, 200, 200), "low": (0, 424, 700, 100)})
    alone = route(html, [{"from": "a", "to": "b"}])["segs"][0]["points"]
    assert min(y for _, y in alone) >= 360  # on its own, a -> b takes the closer gutter below
    out = route(html, [{"from": "m", "to": "low"}, {"from": "a", "to": "b"}])
    down, around = (s["points"] for s in out["segs"])
    assert out["problems"] == []
    assert max(y for _, y in around) <= 160  # with m -> low in that gutter, the wider one above instead
    assert down[0][0] == down[-1][0] == 348  # m -> low stays a straight drop
