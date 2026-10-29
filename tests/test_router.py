"""B4: router unit tests on hand-made boxes in a blank page; no template, no spec."""
import pytest
from conftest import ROOT, browser
from playwright.sync_api import sync_playwright

TOKENS = (ROOT / "schemantic" / "templates" / "tokens.css").read_text(encoding="utf-8")


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


def crossings(segs: list[dict]) -> int:
    """Right-angle crossings between routes, as schemantic.crossings counts them (ends that touch do not count)."""
    def across(h, w):
        inside = lambda v, x, y: min(x, y) + 2 < v < max(x, y) - 2  # noqa: E731
        return h[0][1] == h[1][1] and w[0][0] == w[1][0] and inside(w[0][0], h[0][0], h[1][0]) \
            and inside(h[0][1], w[0][1], w[1][1])
    runs = [list(zip(s["points"], s["points"][1:], strict=False)) for s in segs]
    return sum(across(p, q) or across(q, p) for i, a in enumerate(runs) for b in runs[i + 1:] for p in a for q in b)


# A route that blocks a later one is taken up, the later one placed, and the first routed again (found by a search
# over random layouts: without the repair, r1 -> l2 has no route here)
def test_a_blocked_flow_is_repaired_by_moving_an_earlier_route(route):
    html = page_with({"top": (20, 20, 180, 160), "left": (20, 224, 180, 160), "right": (248, 224, 180, 160)},
                     {"t1": ("top", (12, 40, 156, 48)), "t2": ("top", (12, 100, 156, 48)),
                      "l1": ("left", (12, 40, 156, 48)), "l2": ("left", (12, 100, 156, 48)),
                      "r1": ("right", (12, 40, 156, 48)), "r2": ("right", (12, 100, 156, 48))})
    flows = [{"from": "l2", "to": "right"}, {"from": "left", "to": "r2"}, {"from": "r1", "to": "l2"},
             {"from": "right", "to": "t1"}]
    out = route(html, flows)
    assert out["problems"] == [] and len(out["segs"]) == 4


# After every flow is placed, a route that crosses arrows is routed once more and kept if it crosses fewer
def test_a_second_pass_removes_a_crossing_the_first_could_not_see(route):
    html = page_with({"a": (20, 20, 180, 160), "b": (248, 20, 180, 160), "c": (20, 204, 180, 160),
                      "d": (248, 204, 180, 160)},
                     {"b1": ("b", (12, 40, 156, 48)), "b2": ("b", (12, 100, 156, 48)),
                      "d1": ("d", (12, 40, 156, 48)), "d2": ("d", (12, 100, 156, 48))})
    flows = [{"from": "b1", "to": "b2"}, {"from": "d1", "to": "b2"}, {"from": "b1", "to": "d"},
             {"from": "d1", "to": "a"}]
    out = route(html, flows)
    assert out["problems"] == [] and crossings(out["segs"]) == 1  # 2 without the second pass
