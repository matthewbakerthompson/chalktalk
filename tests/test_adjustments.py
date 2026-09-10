import pytest

from chalktalk import adjustments as A
from chalktalk.catalog import passing, running
from chalktalk.models import Play, PlayType
from chalktalk.models.situation import Tempo
from chalktalk.templates import routes as R, formations as F


def test_tag_swaps_one_route_and_names_itself():
    play = passing.mesh_concept().adjust(A.TAG("Y", R.CORNER()))
    assert play.assignment("Y").route.route_type.value == "corner"
    assert "Y Corner" in play.adjustments


def test_motion_records_origin_and_type():
    play = passing.mesh_concept().adjust(A.MOTION("Z", "jet"))
    z = play.assignment("Z")
    assert z.motion_type == "jet"
    assert z.motion_from is not None
    assert z.in_motion


def test_full_speed_motion_moves_the_snap_position():
    base = passing.mesh_concept()
    moved = base.adjust(A.MOTION("Z", "jet"))
    assert moved.assignment("Z").player.x != base.assignment("Z").player.x
    # the origin is where the player used to line up
    assert moved.assignment("Z").motion_from[0] == pytest.approx(
        base.assignment("Z").player.x)


def test_motion_keeps_players_on_the_field():
    for kind in ("jet", "orbit", "across", "return", "short", "out", "in"):
        play = passing.mesh_concept().adjust(A.MOTION("Z", kind))
        z = play.assignment("Z")
        assert abs(z.motion_from[0]) <= 26.0
        assert abs(z.player.x) <= 26.0


def test_motion_stays_in_sync_with_the_formation():
    play = passing.mesh_concept().adjust(A.MOTION("Z", "jet"))
    z_assign = play.assignment("Z").player
    z_form = next(p for p in play.formation.players if p.label == "Z")
    assert (z_assign.x, z_assign.y) == (z_form.x, z_form.y)


def test_unknown_motion_raises():
    with pytest.raises(ValueError):
        A.MOTION("Z", "teleport")


def test_shift_moves_player_and_leaves_a_trail():
    base = passing.mesh_concept()
    play = base.adjust(A.SHIFT("Y", -7.0, 0.0))
    assert play.assignment("Y").player.x == -7.0
    assert play.assignment("Y").motion_from == (base.assignment("Y").player.x,
                                                base.assignment("Y").player.y)


def test_flip_mirrors_geometry_and_the_name():
    play = running.power_right().adjust(A.FLIP())
    assert "Left" in play.formation.name or "Lt" in play.formation.name
    assert play.assignment("RB") is not None


def test_flip_mirrors_motion_trails():
    play = passing.mesh_concept().adjust(A.MOTION("Z", "jet"), A.FLIP())
    z = play.assignment("Z")
    assert z.motion_from[0] == pytest.approx(-20.0)


def test_protection_sets_field_not_suffix():
    play = passing.mesh_concept().adjust(A.PROTECTION("Slide Rt"))
    assert play.protection == "Slide Rt"
    assert "Slide Rt" not in play.adjustments


def test_max_protect_puts_the_back_in_to_block():
    play = passing.mesh_concept().adjust(A.MAX_PROTECT("RB"))
    assert play.assignment("RB").route.route_type.value == "block"
    assert "Max" in (play.protection or "")


def test_release_sends_the_back_out():
    play = (passing.mesh_concept()
            .adjust(A.MAX_PROTECT("RB"))
            .adjust(A.RELEASE("RB", R.WHEEL())))
    assert play.assignment("RB").route.route_type.value == "wheel"


def test_alert_and_tempo():
    play = passing.mesh_concept().adjust(A.ALERT("Alert Fade vs press"),
                                         A.TEMPO("no_huddle"))
    assert play.alerts == ["Alert Fade vs press"]
    assert play.tempo is Tempo.NO_HUDDLE


def test_play_action_forces_a_pass_with_protection():
    play = running.inside_zone().adjust(A.PLAY_ACTION("RB"))
    assert play.play_type is PlayType.PASS
    assert play.protection
    assert not play.assignment("RB").is_ball_carrier


def test_formation_adjustment_moves_the_concept():
    play = passing.mesh_concept().adjust(A.FORMATION(F.GUN_DOUBLES()))
    assert play.formation.name == F.GUN_DOUBLES().name


def test_adjustments_are_serializable():
    adj = A.TAG("Y", R.CORNER())
    assert A.Adjustment.model_validate_json(adj.model_dump_json()) == adj


def test_adjusted_play_round_trips_through_json():
    play = passing.mesh_concept().adjust(
        A.MOTION("Z", "jet"), A.TAG("Y", R.CORNER()), A.PROTECTION("Slide Rt"))
    assert Play.from_json(play.to_json()) == play


def test_concept_is_preserved_across_alts():
    play = passing.mesh_concept().adjust(A.TAG("Y", R.CORNER()), A.MOTION("Z", "jet"))
    assert play.base_concept == "Mesh Concept"


def test_variants_produce_independent_plays():
    base = passing.mesh_concept()
    out = A.variants(base, A.FLIP(), A.MOTION("Z", "jet"), include_base=True)
    assert len(out) == 3
    assert out[0] is base
    assert len({p.call for p in out}) == 3


def test_matrix_is_a_cartesian_product():
    base = passing.mesh_concept()
    out = A.matrix(base, [A.PROTECTION("Slide Rt"), A.PROTECTION("Half Slide")],
                   [A.MOTION("Z", "jet"), A.MOTION("H", "orbit")])
    assert len(out) == 4
    assert len({p.call for p in out}) == 4


def test_adjustments_do_not_mutate_the_base():
    base = passing.mesh_concept()
    before = base.model_dump()
    base.adjust(A.MOTION("Z", "jet"), A.TAG("Y", R.CORNER()), A.FLIP())
    assert base.model_dump() == before
