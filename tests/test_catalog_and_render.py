"""Every stock asset should build, validate, and draw."""
import inspect

import pytest

from chalktalk.callsheet import CallSheet, Wristband
from chalktalk.catalog import passing, running, redzone, series as SR
from chalktalk.models import Playbook
from chalktalk.models.player import OL_POSITIONS
from chalktalk.renderer.sheets import (
    call_sheet_html, playbook_html, practice_html, script_html, series_html,
    wristband_html,
)
from chalktalk.script import PracticeScript
from chalktalk.templates import formations as F, defense as D, routes as R


def _catalog_functions(module):
    return [fn for name, fn in inspect.getmembers(module, inspect.isfunction)
            if not name.startswith("_") and fn.__module__ == module.__name__]


ALL_PLAY_FNS = (_catalog_functions(passing) + _catalog_functions(running)
                + _catalog_functions(redzone))
ALL_FORMATIONS = [fn for name, fn in inspect.getmembers(F, inspect.isfunction)
                  if name.isupper()]
ALL_DEFENSES = [fn for name, fn in inspect.getmembers(D, inspect.isfunction)
                if name.isupper()]
ALL_ROUTES = [fn for name, fn in inspect.getmembers(R, inspect.isfunction)
              if name.isupper()]


@pytest.mark.parametrize("fn", ALL_FORMATIONS, ids=lambda f: f.__name__)
def test_formation_has_eleven_players_with_five_linemen(fn):
    formation = fn()
    labels = [p.label for p in formation.players]
    assert len(formation.players) == 11, labels
    assert len(set(labels)) == 11, labels
    assert sum(1 for p in formation.players if p.position in OL_POSITIONS) == 5


@pytest.mark.parametrize("fn", ALL_DEFENSES, ids=lambda f: f.__name__)
def test_defense_has_eleven_players_on_the_defensive_side(fn):
    defense = fn()
    assert len(defense.players) == 11
    assert all(p.y >= 0 for p in defense.players)


@pytest.mark.parametrize("fn", ALL_ROUTES, ids=lambda f: f.__name__)
def test_route_has_waypoints_and_mirrors_cleanly(fn):
    route = fn()
    assert len(route.waypoints) >= 2
    mirrored = route.mirror()
    assert [p.x for p in mirrored.waypoints] == [-p.x for p in route.waypoints]
    assert [p.y for p in mirrored.waypoints] == [p.y for p in route.waypoints]


@pytest.mark.parametrize("fn", ALL_PLAY_FNS, ids=lambda f: f.__name__)
def test_every_catalog_play_is_complete(fn):
    play = fn()
    assert len(play.assignments) == 11, play.name
    assert play.formation.personnel
    # every player either has an assignment or is explicitly unassigned
    assert all(a.player.label for a in play.assignments)
    # linemen block
    for a in play.assignments:
        if a.player.is_ol:
            assert a.route is not None, f"{play.name}: {a.player.label} has no assignment"


@pytest.mark.parametrize("fn", ALL_PLAY_FNS, ids=lambda f: f.__name__)
def test_every_catalog_play_renders_to_svg(fn):
    svg = fn().render().render()
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")


def test_run_plays_have_a_ball_carrier():
    for fn in _catalog_functions(running):
        play = fn()
        assert play.ball_carrier is not None, play.name


def test_svg_draws_motion_only_when_present():
    from chalktalk import adjustments as A
    plain = passing.mesh_concept().render().render()
    moved = passing.mesh_concept().adjust(A.MOTION("Z", "jet")).render().render()
    assert 'marker-end="url(#arr-motion)"' not in plain
    assert 'marker-end="url(#arr-motion)"' in moved
    assert "JET" in moved


def test_svg_includes_defense_when_attached():
    defense = D.NICKEL_425()
    plain = passing.mesh_concept().render().render()
    with_d = passing.mesh_concept().vs(defense).render().render()
    # defenders are drawn as squares so they read differently from the offense
    assert with_d.count("<rect") == plain.count("<rect") + len(defense.players)


def test_playbook_pdf_export(tmp_path):
    book = SR.mesh_series().to_playbook()
    path = tmp_path / "book.pdf"
    book.save_pdf(str(path), plays_per_page=2)
    assert path.exists() and path.stat().st_size > 1000


@pytest.mark.parametrize("renderer,builder", [
    (playbook_html, lambda: SR.mesh_series().to_playbook()),
    (series_html, SR.inside_zone_series),
    (script_html, lambda: SR.mesh_series().to_script()),
    (call_sheet_html,
     lambda: CallSheet.from_playbook(SR.red_zone_series().to_playbook()).number()),
    (wristband_html,
     lambda: Wristband.from_call_sheet(
         CallSheet.from_playbook(SR.red_zone_series().to_playbook()))),
    (practice_html,
     lambda: PracticeScript(name="T").add_period("Team",
                                                 SR.mesh_series().to_script())),
])
def test_html_renderers_produce_a_full_document(renderer, builder):
    html = renderer(builder())
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")
    assert "<title>" in html


def test_html_escapes_user_text():
    book = Playbook(name="<script>alert(1)</script>").add(passing.mesh_concept())
    html = playbook_html(book)
    assert "<script>alert(1)</script>" not in html.split("<style>")[0]
    assert "&lt;script&gt;" in html
