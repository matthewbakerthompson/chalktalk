"""
The designer draws in the browser; Python renders the result. These tests pin
the contract between the two — anything that drifts here puts a drawn route in
a different place than the coach put it.
"""
import json
import os
import re

import pytest

from chalktalk import designer
from chalktalk.catalog import passing
from chalktalk.models import Play
from chalktalk.models.assignment import Assignment
from chalktalk.models.core import Point
from chalktalk.models.field import HS, NCAA, NFL, Level, field_for
from chalktalk.models.player import Player, Position
from chalktalk.models.route import Route, RouteType
from chalktalk.models.situation import Hash


# ── Field levels ──────────────────────────────────────────────────────────────

def test_hash_separation_matches_the_rulebooks():
    # NFL 18'6", NCAA 40'0", NFHS 53'4" — converted to yards
    assert NFL.hash_separation == pytest.approx(6.167, abs=0.01)
    assert NCAA.hash_separation == pytest.approx(13.333, abs=0.01)
    assert HS.hash_separation == pytest.approx(17.778, abs=0.01)


def test_hashes_get_wider_as_the_level_drops():
    assert NFL.hash_from_center < NCAA.hash_from_center < HS.hash_from_center


def test_every_level_is_the_same_width():
    for spec in (NFL, NCAA, HS):
        assert spec.width == pytest.approx(53.33, abs=0.01)


def test_boundary_and_field_split_on_a_hash():
    # On a high school hash the field side is twice the boundary; in the NFL
    # the two sides are nearly even. That is the whole point of the setting.
    assert HS.field_width(Hash.LEFT) / HS.boundary_width(Hash.LEFT) == \
        pytest.approx(2.0, abs=0.05)
    assert NFL.field_width(Hash.LEFT) / NFL.boundary_width(Hash.LEFT) == \
        pytest.approx(1.26, abs=0.05)
    for spec in (NFL, NCAA, HS):
        assert spec.boundary_width(Hash.LEFT) + spec.field_width(Hash.LEFT) == \
            pytest.approx(spec.width)


def test_middle_of_field_is_symmetric():
    assert NCAA.hash_x(Hash.MIDDLE) == 0.0
    assert NCAA.hash_x(None) == 0.0
    assert NCAA.hash_x(Hash.LEFT) == -NCAA.hash_x(Hash.RIGHT)


@pytest.mark.parametrize("value,expected", [
    ("nfl", NFL), ("ncaa", NCAA), ("hs", HS),
    (Level.HS, HS), (None, NFL), (NCAA, NCAA),
])
def test_field_for_accepts_any_spelling(value, expected):
    assert field_for(value) is expected


def test_renderer_moves_the_hashes_with_the_level():
    play = passing.mesh_concept()
    marks = {}
    for level in ("nfl", "ncaa", "hs"):
        svg = play.render(level=level).render()
        # hash ticks are the only 1.5-width lines drawn in the hash colour
        xs = re.findall(r'x1="([\d.]+)" y1="[\d.]+" x2="[\d.]+" y2="[\d.]+" '
                        r'stroke="rgba\(255,255,255,0\.20\)"', svg)
        marks[level] = min(float(x) for x in xs)
    # a wider hash separation puts the left hash further left on the page
    assert marks["hs"] < marks["ncaa"] < marks["nfl"]


def test_ball_spot_is_drawn_only_when_a_hash_is_known():
    from chalktalk.models import situation as S
    play = passing.mesh_concept()
    assert "#c2703a" not in play.render().render()
    on_hash = play.at(S.Situation(down=1, distance=10, hash_mark=Hash.LEFT))
    assert "#c2703a" in on_hash.render().render()


# ── The mirroring convention ──────────────────────────────────────────────────

def _assignment(x: float, waypoints: list[tuple[float, float]]) -> Assignment:
    return Assignment(
        player=Player(label="X", position=Position.X, x=x, y=0.0),
        route=Route(route_type=RouteType.CUSTOM,
                    waypoints=[Point(x=wx, y=wy) for wx, wy in waypoints]),
    )


def test_right_side_routes_are_stored_as_drawn():
    a = _assignment(20.0, [(0, 0), (0, 10), (6, 14)])
    assert a.absolute_waypoints() == [(20.0, 0.0), (20.0, 10.0), (26.0, 14.0)]


def test_left_side_routes_are_mirrored_on_the_way_out():
    # This is exactly what the browser stores when a coach drags a point on a
    # left-side receiver to (-18, 12) and (-4, 14).
    a = _assignment(-22.0, [(0, 0), (-4, 12), (-18, 14)])
    assert a.absolute_waypoints() == [(-22.0, 0.0), (-18.0, 12.0), (-4.0, 14.0)]


def test_the_convention_survives_a_flip():
    from chalktalk import adjustments as A
    play = Play(name="t", formation=passing.mesh_concept().formation,
                play_type="pass", assignments=[_assignment(-22.0, [(0, 0), (-4, 12)])])
    flipped = play.adjust(A.FLIP())
    assert flipped.assignments[0].absolute_waypoints() == [(22.0, 0.0), (18.0, 12.0)]


def test_no_route_means_no_waypoints():
    a = Assignment(player=Player(label="QB", position=Position.QB, x=0, y=-5))
    assert a.absolute_waypoints() == []


# ── Designer build ────────────────────────────────────────────────────────────

def test_catalog_carries_everything_the_browser_needs():
    cat = designer.catalog()
    for key in ("fields", "routes", "formations", "defenses", "plays",
                "motions", "default_formation"):
        assert key in cat, key
    assert set(cat["fields"]) == {"nfl", "ncaa", "hs"}
    assert cat["default_formation"] in cat["formations"]
    assert len(cat["plays"]) >= 30
    assert "BLOCK" in cat["routes"]


def test_catalog_is_json_serializable():
    json.dumps(designer.catalog())


def test_catalog_plays_round_trip_back_into_python():
    for name, raw in designer.catalog()["plays"].items():
        Play.model_validate(raw), name


def test_build_inlines_the_catalog_and_leaves_no_placeholder():
    html = designer.build()
    assert "/*__CATALOG__*/{}" not in html
    assert html.lstrip().startswith("<!doctype html>")
    assert '"formations"' in html


def test_build_can_preload_a_play():
    play = passing.mesh_concept()
    html = designer.build(play=play)
    assert "/*__PLAY__*/null" not in html
    assert "Mesh Concept" in html


def test_build_honours_the_level():
    assert 'let level = "hs";' in designer.build(level="hs")
    assert 'let level = "nfl";' in designer.build()


def test_inlined_json_cannot_break_out_of_the_script_tag():
    play = passing.mesh_concept().rename("</script><script>alert(1)</script>")
    html = designer.build(play=play)
    assert "</script><script>alert(1)" not in html
    assert html.count("</script>") == 1


def test_designer_is_self_contained():
    # The SVG namespace is an identifier, not something the page fetches, and
    # the licence notice at the top names URLs without loading them.
    html = designer.build().replace("http://www.w3.org/2000/svg", "")
    notice = html[:html.index("-->") + 3]
    assert "Required Notice:" in notice and "PolyForm Noncommercial" in notice
    html = html[len(notice):]
    assert "http://" not in html
    assert "https://" not in html
    assert "<script src=" not in html
    assert "<link rel=" not in html
    # the one thing it asks for is its own `chalk design` server, by a relative path
    assert re.findall(r"fetch\(([^,)]*)", html) == ['"api/" + name']


def test_app_template_keeps_its_placeholders():
    with open(designer._TEMPLATE, encoding="utf-8") as fh:
        src = fh.read()
    assert src.count("/*__CATALOG__*/{}") == 1
    assert src.count("/*__PLAY__*/null") == 1
    assert src.count("/*__BOOK__*/null") == 1
    assert src.count("/*__SERVER__*/null") == 1


def test_designer_mirrors_the_python_motion_geometry():
    """The JS copy of _motion_geometry must stay in step with the Python one."""
    from chalktalk.adjustments import _MOTION_PRESETS, _motion_geometry
    with open(designer._TEMPLATE, encoding="utf-8") as fh:
        src = fh.read()
    for kind in _MOTION_PRESETS:
        assert f'case "{kind}"' in src or kind == "short", kind
    # spot-check the numbers the JS hard-codes against the Python source
    assert _motion_geometry("jet", 20.0, -1.0) == ((20.0, -1.0), (-2.0, -1.5))
    assert _motion_geometry("orbit", 12.0, -1.0) == ((12.0, -1.0), (-5.0, -5.0))
    assert 'cl(-side*2.0), y-0.5' in src
    assert 'cl(-side*5.0), y-4.0' in src


# ── Themes and layers ─────────────────────────────────────────────────────────

def test_the_two_themes_draw_the_same_play_in_different_ink():
    from chalktalk.renderer.theme import PAPER, TURF
    play = passing.mesh_concept()
    turf = play.render().render()
    paper = play.render(theme="paper").render()
    assert f'fill="{TURF.field}"' in turf
    assert f'fill="{PAPER.field}"' in paper
    assert TURF.field not in paper
    assert turf.count("<circle") == paper.count("<circle")


def test_layers_can_be_left_out():
    from chalktalk.templates import defense as D
    play = passing.mesh_concept().vs(D.NICKEL_425())
    full = play.render().render()
    bare = play.render(hide=["defense", "title", "routes"]).render()
    assert full.count("<rect") > bare.count("<rect")
    assert play.name in full and play.name not in bare
    assert "url(#arr-route)" in full and "url(#arr-route)" not in bare
    with pytest.raises(ValueError):
        play.render(hide=["defence"])


def test_unknown_theme_is_refused():
    with pytest.raises(ValueError):
        passing.mesh_concept().render(theme="chalkboard")


def test_yard_numbers_and_the_end_zone_appear_once_the_ball_is_spotted():
    from chalktalk.models import situation as S
    from chalktalk.renderer.theme import TURF
    play = passing.mesh_concept()
    plain = play.render().render()
    spotted = play.at(S.Situation(down=1, distance=10, yard_line=12)).render().render()
    assert f'fill="{TURF.endzone}"' not in plain
    assert f'fill="{TURF.endzone}"' in spotted          # goal line 12 yards away
    assert ">10<" in spotted and ">10<" not in plain    # the ten-yard line is labelled


def test_designer_receives_the_theme_table():
    cat = designer.catalog()
    assert set(cat["themes"]) == {"turf", "paper"}
    assert cat["themes"]["turf"]["qb"] == "#fbbf24"
    assert "defense" in cat["layers"]


def test_designer_only_uses_ink_the_theme_defines():
    """Every `t.key` / `T().key` the browser draws with must be a Theme field."""
    from chalktalk.renderer.theme import theme_keys
    with open(designer._TEMPLATE, encoding="utf-8") as fh:
        src = fh.read()
    used = set(re.findall(r"\bT\(\)\.([a-z_]+)", src)) | set(re.findall(r"\bt\.([a-z_]+)", src))
    used -= {"text", "class", "dataset", "_t"}   # `t` is also a DOM node in the toast and pointer code
    unknown = used - set(theme_keys())
    assert not unknown, unknown
    assert "CATALOG.themes" in src


def test_designer_script_parses():
    """The suite pins strings in the JS; make sure the JS is at least JavaScript."""
    import shutil, subprocess, tempfile
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    with open(designer._TEMPLATE, encoding="utf-8") as fh:
        src = fh.read()
    script = src[src.index("<script>") + len("<script>"):src.rindex("</script>")]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "designer.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(script)
        result = subprocess.run([node, "--check", path], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# ── Playbooks ─────────────────────────────────────────────────────────────────

def _book():
    from chalktalk.catalog import running
    from chalktalk.models import Playbook
    return Playbook(name="Week 3", team="Owls", season=2026,
                    plays=[passing.mesh_concept(), running.power_right()])


def test_build_can_open_a_whole_playbook():
    html = designer.build(playbook=_book())
    assert "/*__BOOK__*/null" not in html
    assert "/*__PLAY__*/null" in html              # the single-play slot stays empty
    assert "Week 3" in html and "Power Right" in html
    assert html.count("</script>") == 1


def test_a_designer_book_is_a_python_playbook(tmp_path):
    """The file the designer saves is `Playbook` JSON, nothing more."""
    from chalktalk.models import Playbook
    path = tmp_path / "book.json"
    _book().save(str(path))
    again = Playbook.load(str(path))
    assert [p.name for p in again.plays] == ["Mesh Concept", "Power Right"]
    assert again.team == "Owls" and again.season == 2026


def test_cli_prints_a_playbook(tmp_path):
    from chalktalk import cli
    book = tmp_path / "book.json"
    _book().save(str(book))
    assert cli.main(["book", str(book), "-o", str(tmp_path / "book.pdf")]) == 0
    assert (tmp_path / "book.pdf").stat().st_size > 1500
    assert cli.main(["book", str(book), "-o", str(tmp_path / "book.html")]) == 0
    page = (tmp_path / "book.html").read_text(encoding="utf-8")
    assert "Week 3" in page and page.count("<svg") == 2


def test_the_start_screen_and_the_preview_stay_out_of_exports():
    """Both are interface: neither may leak into an exported SVG or the printed book."""
    with open(designer._TEMPLATE, encoding="utf-8") as fh:
        src = fh.read()
    assert 'id="welcome"' in src and "showWelcome" in src
    assert 'id="fileInput"' in src
    # every place that strips the UI layer strips the preview layer too
    assert src.count('svg.querySelector("#ui").remove()') == \
        src.count('svg.querySelector("#preview").remove()') == 2
