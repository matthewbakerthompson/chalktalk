"""
Defensive assignments: alignment is eleven dots until somebody has a job.
"""
import inspect

import pytest

from chalktalk.catalog import passing, running
from chalktalk.models import Play, Playbook
from chalktalk.models import situation as S
from chalktalk.models.defense import (
    DefensiveAssignment, DefensiveRole, Zone, zone_landmark, zone_size,
)
from chalktalk.models.field import HS, NCAA, NFL
from chalktalk.templates import coverages as C, defense as D, formations as F

ALL_DEFENSES = [fn for name, fn in inspect.getmembers(D, inspect.isfunction)
                if name.isupper()]


def _calls(defense) -> dict[str, str]:
    return {p.label: p.assignment.describe()
            for p in defense.players if p.assignment}


def _deep(defense) -> list[str]:
    return [p.label for p in defense.players
            if p.assignment and p.assignment.zone and p.assignment.zone.is_deep]


# ── Alignment ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fn", ALL_DEFENSES, ids=lambda f: f.__name__)
def test_defenders_have_unique_labels(fn):
    """Assignments are keyed by label, so two ends called 'DE' lose one call."""
    labels = [p.label for p in fn().players]
    assert len(set(labels)) == len(labels) == 11, labels


def test_duplicate_labels_get_a_side_prefix():
    labels = [p.label for p in D.NICKEL_425().players]
    assert "LDE" in labels and "RDE" in labels
    assert "LCB" in labels and "RCB" in labels
    assert "DE" not in labels


def test_the_prefix_follows_alignment():
    look = D.FOUR_THREE_OVER()
    left = look.player("LDE")
    right = look.player("RDE")
    assert left.x < right.x


# ── Zones ─────────────────────────────────────────────────────────────────────

def test_deep_zones_are_deeper_than_underneath_zones():
    assert zone_landmark(Zone.DEEP_THIRD)[1] > zone_landmark(Zone.CURL_FLAT)[1]
    assert zone_landmark(Zone.CURL_FLAT)[1] > zone_landmark(Zone.FLAT)[1]


def test_side_multiplier_places_the_inside_quarters():
    outside = zone_landmark(Zone.DEEP_QUARTER, 1.0)[0]
    inside = zone_landmark(Zone.DEEP_QUARTER, 0.38)[0]
    assert 0 < inside < outside


def test_zones_move_with_the_ball():
    middle = zone_landmark(Zone.FLAT, 1.0, NFL, ball_x=0.0)[0]
    on_left_hash = zone_landmark(Zone.FLAT, 1.0, NFL, ball_x=-3.08)[0]
    assert on_left_hash < middle


def test_zones_stay_inbounds():
    for field in (NFL, NCAA, HS):
        x, _ = zone_landmark(Zone.FLAT, 1.0, field, ball_x=field.hash_from_center)
        assert abs(x) < field.sideline


def test_zone_areas_have_a_size():
    for z in Zone:
        w, h = zone_size(z)
        assert w > 0 and h > 0


def test_deep_flag():
    assert Zone.DEEP_THIRD.is_deep and Zone.DEEP_MIDDLE.is_deep
    assert not Zone.FLAT.is_deep and not Zone.HOOK.is_deep


def test_zone_display_names_read_like_a_coach_says_them():
    assert Zone.CURL_FLAT.display == "Curl/Flat"
    assert Zone.MIDDLE_THIRD.display == "Middle Third"


# ── Assignments ───────────────────────────────────────────────────────────────

def test_assignment_describes_itself():
    assert C.zone(Zone.DEEP_HALF).describe() == "Deep Half"
    assert C.man("X").describe() == "Man X"
    assert C.blitz(D.NICKEL_425().player("W"), "B").describe() == "Blitz B"


def test_pressure_and_coverage_roles_are_distinct():
    assert C.rush(D.FOUR_THREE_OVER().player("LDE")).is_pressure
    assert C.zone(Zone.HOOK).is_coverage
    assert not C.zone(Zone.HOOK).is_pressure


def test_mirroring_flips_the_side_and_the_path():
    call = C.blitz(D.NICKEL_425().player("W"), "B")
    flipped = call.mirrored()
    assert [p.x for p in flipped.path] == [-p.x for p in call.path]
    assert C.zone(Zone.FLAT, 1.0).mirrored().side == -1.0


def test_mirroring_a_look_mirrors_every_assignment():
    look = C.cover_3(D.NICKEL_425())
    flipped = look.mirror()
    for before, after in zip(look.players, flipped.players):
        assert after.x == -before.x
        if before.assignment and before.assignment.zone:
            assert after.assignment.side == -before.assignment.side


# ── Coverages ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", sorted(C.COVERAGES))
@pytest.mark.parametrize("fn", ALL_DEFENSES, ids=lambda f: f.__name__)
def test_every_coverage_gives_every_defender_a_job(fn, name):
    look = C.COVERAGES[name](fn(), F.SHOTGUN_TRIPS_RIGHT())
    unassigned = [p.label for p in look.players if p.assignment is None]
    assert not unassigned, f"{name} leaves {unassigned} standing around"


def test_cover_3_is_three_deep_four_under():
    look = C.cover_3(D.NICKEL_425())
    assert len(_deep(look)) == 3
    assert look.coverage == "Cover 3"


def test_cover_2_is_two_deep():
    look = C.cover_2(D.NICKEL_425())
    assert len(_deep(look)) == 2
    assert _calls(look)["LCB"] == "Flat"


def test_quarters_is_four_deep():
    assert len(_deep(C.cover_4(D.NICKEL_425()))) == 4


def test_tampa_2_sends_the_mike_to_the_deep_middle():
    assert _calls(C.tampa_2(D.NICKEL_425()))["M"] == "Deep Middle"


def test_cover_6_splits_the_field():
    calls = _calls(C.cover_6(D.NICKEL_425(), strength=1))
    assert "Quarter" in calls["RCB"]
    assert calls["LCB"] == "Flat"


def test_fire_zone_drops_a_lineman_and_still_plays_three_deep():
    look = C.fire_zone(D.FOUR_THREE_OVER())
    dropped = [p.label for p in look.dl
               if p.assignment and p.assignment.is_coverage]
    assert len(dropped) == 1, "a fire zone drops exactly one lineman"
    assert len(_deep(look)) == 3
    assert look.pressure.startswith("Fire Zone")


def test_fire_zone_flips_with_strength():
    right = C.fire_zone(D.FOUR_THREE_OVER(), strength=1)
    left = C.fire_zone(D.FOUR_THREE_OVER(), strength=-1)
    assert right.pressure.endswith("Rt") and left.pressure.endswith("Lt")


def test_zero_blitz_has_no_deep_help():
    look = C.zero_blitz(D.NICKEL_425(), F.SHOTGUN_TRIPS_RIGHT())
    assert not _deep(look)
    assert look.pressure == "Zero"


def test_line_game_is_a_front_that_layers_over_a_coverage():
    look = C.line_game(C.cover_3(D.FOUR_THREE_OVER()))
    assert any(p.assignment.role is DefensiveRole.STUNT
               for p in look.dl if p.assignment)
    # the back seven keep the coverage they were already playing
    assert len(_deep(look)) == 3
    assert all(p.assignment for p in look.players)


# ── Man match-ups ─────────────────────────────────────────────────────────────

def test_man_coverage_covers_every_receiver_once():
    offense = F.SHOTGUN_TRIPS_RIGHT()
    look = C.cover_1(D.NICKEL_425(), offense)
    covered = [p.assignment.covers for p in look.players
               if p.assignment and p.assignment.role is DefensiveRole.MAN]
    assert len(covered) == len(set(covered)), "somebody is double-covered"
    eligible = {p.label for p in C.eligible_receivers(offense)}
    assert set(covered) <= eligible
    assert None not in covered, "a man defender with nobody to cover"


def test_corners_take_the_widest_receivers_on_their_own_side():
    offense = F.SHOTGUN_TRIPS_RIGHT()
    look = C.cover_1(D.NICKEL_425(), offense)
    assert look.player("LCB").assignment.covers == "X"     # split end, left
    assert look.player("RCB").assignment.covers == "Z"     # flanker, right


def test_cover_1_keeps_a_free_safety_deep():
    look = C.cover_1(D.NICKEL_425(), F.SHOTGUN_TRIPS_RIGHT())
    assert look.player("FS").assignment.zone is Zone.DEEP_MIDDLE


def test_the_spare_defender_becomes_a_rat():
    look = C.cover_1(D.NICKEL_425(), F.SHOTGUN_TRIPS_RIGHT())
    rats = [p.label for p in look.players
            if p.assignment and p.assignment.role is DefensiveRole.ROBOT]
    assert len(rats) == 1


def test_man_coverage_without_an_offense_still_assigns_roles():
    look = C.cover_1(D.NICKEL_425())
    assert all(p.assignment for p in look.players)


def test_cover_2_man_keeps_two_deep():
    look = C.cover_2_man(D.NICKEL_425(), F.SHOTGUN_TRIPS_RIGHT())
    assert len(_deep(look)) == 2


@pytest.mark.parametrize("name", sorted(C.COVERAGES))
@pytest.mark.parametrize("fn", ALL_DEFENSES, ids=lambda f: f.__name__)
def test_zone_defenders_never_share_a_landmark(fn, name):
    """Two defenders dropping to the same spot is a bust, not a coverage."""
    look = C.COVERAGES[name](fn(), F.SHOTGUN_TRIPS_RIGHT())
    spots: dict[tuple, str] = {}
    for p in look.players:
        a = p.assignment
        if not (a and a.zone):
            continue
        key = (a.zone, zone_landmark(a.zone, a.side))
        assert key not in spots, \
            f"{name}: {p.label} and {spots[key]} both drop to {a.zone.display}"
        spots[key] = p.label


def test_cover_3_has_a_curl_flat_player_on_each_side():
    look = C.cover_3(D.FOUR_THREE_OVER())
    sides = sorted(p.assignment.side for p in look.players
                   if p.assignment and p.assignment.zone is Zone.CURL_FLAT)
    assert sides == [-1.0, 1.0]


@pytest.mark.parametrize("fn", ALL_DEFENSES, ids=lambda f: f.__name__)
def test_two_deep_safeties_split_the_field(fn):
    look = C.cover_2(fn())
    halves = sorted(p.assignment.side for p in look.players
                    if p.assignment and p.assignment.zone is Zone.DEEP_HALF)
    if len(look.safeties) >= 2:
        assert halves == [-1.0, 1.0]


# ── Attaching to a play ───────────────────────────────────────────────────────

def test_vs_accepts_a_coverage():
    play = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_3)
    assert play.defense.coverage == "Cover 3"
    assert play.defense.has_assignments


def test_with_coverage_needs_a_defense_first():
    with pytest.raises(ValueError):
        passing.mesh_concept().with_coverage(C.cover_3)


def test_with_coverage_uses_the_plays_own_receivers():
    play = passing.mesh_concept().vs(D.NICKEL_425()).with_coverage(C.cover_1)
    labels = {a.player.label for a in play.assignments}
    for p in play.defense.players:
        if p.assignment and p.assignment.covers:
            assert p.assignment.covers in labels


def test_flipping_a_play_flips_the_coverage():
    play = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_3)
    flipped = play.mirror()
    before = play.defense.player("LCB")
    after = flipped.defense.player("LCB")
    assert after.x == -before.x
    assert after.assignment.side == -before.assignment.side


def test_assignments_survive_a_json_round_trip():
    play = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_1)
    assert Play.from_json(play.to_json()) == play


def test_describe_lists_the_call():
    text = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_3).defense.describe()
    assert "Cover 3" in text
    assert "Deep Third" in text


# ── Rendering ─────────────────────────────────────────────────────────────────

def test_zone_drops_draw_areas_and_arrows():
    from chalktalk.renderer.theme import TURF
    svg = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_3).render().render()
    assert svg.count(f'fill="{TURF.zone_fill}"') == 7        # every zone dropper
    assert "url(#arr-def)" in svg


def test_zone_shading_can_be_turned_off():
    play = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_3)
    from chalktalk.renderer.theme import TURF
    assert f'fill="{TURF.zone_fill}"' in play.render().render()
    assert f'fill="{TURF.zone_fill}"' not in play.render(zones=False).render()
    assert "url(#arr-def)" in play.render(zones=False).render()


def test_the_arrowheads_the_renderer_asks_for_actually_exist():
    """Every marker-end reference needs a matching marker in <defs>."""
    import re
    svg = (passing.mesh_concept()
           .vs(D.NICKEL_425(), C.cover_1)
           .render().render())
    defined = set(re.findall(r'<marker id="([\w-]+)"', svg))
    used = set(re.findall(r'marker-end="url\(#([\w-]+)\)"', svg))
    assert used <= defined, f"undefined markers: {used - defined}"


def test_press_coverage_still_shows_the_matchup():
    """A corner standing on his receiver must not draw a zero-length arrow."""
    import re
    from chalktalk.renderer.theme import TURF
    play = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_1)
    svg = play.render().render()
    lengths = [
        ((float(x2) - float(x1)) ** 2 + (float(y2) - float(y1)) ** 2) ** 0.5
        for x1, y1, x2, y2 in re.findall(
            r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" '
            r'stroke="' + TURF.def_assign + '"', svg)
    ]
    assert lengths and min(lengths) > 8.0


def test_a_play_without_a_defense_draws_no_defensive_ink():
    svg = passing.mesh_concept().render().render()
    assert "url(#arr-def)" not in svg      # the marker is defined, never used


def test_zones_shift_with_the_hash():
    base = passing.mesh_concept().vs(D.NICKEL_425(), C.cover_2)
    middle = base.render().render()
    left = base.at(S.Situation(down=1, distance=10, hash_mark="L")).render().render()
    assert middle != left


def test_pdf_draws_the_defense(tmp_path):
    path = tmp_path / "d.pdf"
    Playbook(name="D", plays=[
        passing.mesh_concept().vs(D.NICKEL_425(), C.cover_3),
        running.inside_zone().vs(D.FOUR_THREE_OVER(), C.cover_1),
    ]).save_pdf(str(path), plays_per_page=2)
    assert path.stat().st_size > 1500


# ── Designer parity ───────────────────────────────────────────────────────────

def test_designer_ships_a_call_for_every_look():
    from chalktalk import designer
    calls = designer.catalog()["coverage_calls"]
    for fn in ALL_DEFENSES:
        look = fn()
        assert look.name in calls, look.name
        assert set(calls[look.name]) >= set(C.COVERAGES) | set(C.FRONTS)


def test_designer_keeps_stunt_paths_but_drops_the_formulaic_ones():
    from chalktalk import designer
    calls = designer.catalog()["coverage_calls"]["4-3 Over"]
    assert all("path" not in a for a in calls["cover_3"].values()
               if isinstance(a, dict) and a.get("role") != "stunt")
    stunts = [a for a in calls["line_game"].values()
              if isinstance(a, dict) and a.get("role") == "stunt"]
    assert stunts and all(a["path"] for a in stunts)


def test_designer_mirrors_the_rush_formulas():
    from chalktalk import designer
    with open(designer._TEMPLATE, encoding="utf-8") as fh:
        src = fh.read()
    # the JS rebuilds paths the renderer never shipped — keep the numbers in step
    assert "-0.18*d.x" in src        # rush lean
    assert "-0.3*d.x" in src         # blitz lean
    assert "s*1.4,-1.2" in src       # contain
    assert C.rush(D.FOUR_THREE_OVER().player("LDE")).path[-1].y == -3.6
