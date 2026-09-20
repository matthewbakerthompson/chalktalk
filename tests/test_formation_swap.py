"""
Running a play from a new formation. Every job goes across by label (route,
block, the quarterback's plan, ball carrier, motion, note), and nothing is left
pointing at a player the new formation doesn't have.
"""
import pytest

from chalktalk import adjustments as A
from chalktalk import catalog as _catalog
from chalktalk.catalog import passing, running
from chalktalk.models import Play, Playbook
from chalktalk.templates import formations as F

from test_designer_paper import NODE, _js

ALL_PLAYS = sorted(_catalog.play_builders().items())

# Between them these drop H, RB, FB and TE from somebody, and move most of the
# rest to new spots or the other side of the ball.
SWAPS = ("I_FORM_PRO_RIGHT", "PRO_SET", "GUN_SPREAD_4WR", "SHOTGUN_TRIPS_LEFT")


def _jobs(play: Play, field: str) -> dict:
    return {a.player.label: getattr(a, field) for a in play.assignments
            if getattr(a, field) is not None}


def _spot(formation, label):
    p = formation.player(label)
    return (p.x, p.y)


# ── Blocks ────────────────────────────────────────────────────────────────────

def test_blocks_and_the_quarterback_survive_a_formation_swap():
    """The reported bug: nine blocks and a QB plan before, none after."""
    play = running.power_right()
    moved = play.with_formation(F.I_FORM_PRO_RIGHT())
    assert len(_jobs(play, "block")) == 9
    assert _jobs(moved, "block") == _jobs(play, "block")
    assert moved.qb == play.qb
    assert moved.ball_carrier.player.label == "RB"
    assert play == running.power_right(), "the original play was changed"


def test_the_formation_adjustment_keeps_them_too():
    play = running.power_right().adjust(A.FORMATION(F.I_FORM_PRO_RIGHT()))
    assert len(_jobs(play, "block")) == 9
    assert play.qb.mesh_with == "RB"


def test_a_block_path_is_not_mirrored_when_the_blocker_changes_sides():
    """The fullback kicks out to the right from either side of the ball."""
    play = running.power_right()
    moved = play.with_formation(F.I_FORM_STRONG_LEFT())
    fb = moved.assignment("FB")
    assert play.assignment("FB").player.x > 1.0 and fb.player.x < -1.0
    assert fb.block.path == play.assignment("FB").block.path
    xs = [x for x, _ in fb.block.absolute_path(fb.player.x, fb.player.y)]
    assert xs[-1] > xs[0]


def test_a_route_goes_across_as_authored_and_is_mirrored_when_drawn():
    play = passing.mesh_concept()                     # Z on the right
    moved = play.with_formation(F.SHOTGUN_TRIPS_LEFT())
    before, after = play.assignment("Z"), moved.assignment("Z")
    assert before.player.x > 1.0 and after.player.x < -1.0
    assert after.route == before.route

    def relative(a):
        return [(x - a.player.x, y - a.player.y) for x, y in a.absolute_waypoints()]
    assert relative(after) == pytest.approx([(-dx, dy) for dx, dy in relative(before)])


# ── The quarterback ───────────────────────────────────────────────────────────

def test_the_mesh_point_comes_along():
    play = running.power_right()
    moved = play.with_formation(F.I_FORM_STRONG_LEFT())
    assert play.qb.mesh_at is not None
    assert moved.qb.mesh_at == play.qb.mesh_at
    assert moved.qb.mesh_with == "RB"
    assert moved.qb.path == play.qb.path


def test_reads_on_players_still_on_the_field_come_along_in_order():
    play = passing.mesh_concept()
    moved = play.with_formation(F.SHOTGUN_EMPTY_TRIPS_RIGHT())
    assert moved.qb.reads == play.qb.reads == ["Y", "H", "Z", "RB"]
    for label in moved.qb.reads:
        assert moved.assignment(label).route == play.assignment(label).route


def test_reads_on_players_the_new_formation_lacks_are_dropped():
    play = passing.mesh_concept()
    moved = play.with_formation(F.I_FORM_PRO_RIGHT())       # no H
    assert moved.qb.reads == ["Y", "Z", "RB"]
    assert moved.read_order("Z") == 2


def test_orders_against_a_coverage_lose_the_same_players():
    play = passing.mesh_concept().progression("H", "Z", vs="Cover 2").progression("H", vs="Cover 3")
    moved = play.with_formation(F.I_FORM_PRO_RIGHT())       # no H
    assert moved.qb.reads_vs == {"Cover 2": ["Z"]}          # Cover 3 had only H: it goes
    assert moved.read_order("Z", "Cover 2") == 1


def test_the_mesh_goes_with_a_missing_back_but_the_footwork_stays():
    play = running.power_right()
    moved = play.with_formation(F.PRO_SET())                # HB and FB, no RB
    assert moved.qb.mesh_with is None
    assert moved.qb.mesh_at == play.qb.mesh_at
    assert moved.ball_carrier is None
    assert moved.assignment("FB").block == play.assignment("FB").block


def test_the_quarterback_is_still_drawn_after_a_swap():
    svg = running.power_right().with_formation(F.I_FORM_PRO_RIGHT()).render().render()
    assert 'marker-end="url(#arr-qb)"' in svg


@pytest.mark.parametrize("formation", SWAPS)
@pytest.mark.parametrize("name,fn", ALL_PLAYS, ids=[n for n, _ in ALL_PLAYS])
def test_every_play_passes_the_read_checks_after_a_swap(name, fn, formation):
    """The same rules test_qb.py holds the catalog to, from any formation."""
    original = fn()
    play = original.with_formation(getattr(F, formation)())
    for a in play.assignments:
        assert not (a.route and a.block), f"{name}: {a.player.label} blocks and runs a route"
    holder = next(a for a in original.assignments if a.qb is not None).player.label
    if play.assignment(holder) is None:          # the new formation has no such player
        return
    plan = play.assignment(holder).qb
    assert plan is not None, f"{name} lost the quarterback's plan"
    for label in plan.reads:
        a = play.assignment(label)
        assert a is not None, f"{name} reads {label}, who is not on the field"
        assert a.route is not None, f"{name} reads {label}, who is blocking"
    if plan.mesh_with:
        assert play.assignment(plan.mesh_with) is not None, name


# ── Notes ─────────────────────────────────────────────────────────────────────

def test_notes_come_along():
    play = running.inside_zone().adjust(A.PLAY_ACTION("RB"))
    play = play.model_copy(update={"assignments": [
        a.model_copy(update={"note": a.note or f"{a.player.label} coaching point"})
        for a in play.assignments
    ]})
    moved = play.with_formation(F.GUN_DOUBLES())
    for a in moved.assignments:
        before = play.assignment(a.player.label)
        assert a.note == (before.note if before else None), a.player.label
    assert moved.assignment("RB").note.startswith("Sell the fake")
    assert moved.assignment("H").note is None               # new to the play


# ── Motion ────────────────────────────────────────────────────────────────────

def test_preset_motion_is_run_again_from_the_new_alignment():
    """Jet then a new formation lands exactly where the new formation then jet does."""
    one = passing.mesh_concept().adjust(A.MOTION("H", "jet"), A.FORMATION(F.GUN_DOUBLES()))
    two = passing.mesh_concept().adjust(A.FORMATION(F.GUN_DOUBLES()), A.MOTION("H", "jet"))
    assert one.assignment("H") == two.assignment("H")
    assert one.formation.players == two.formation.players
    # H starts from his Doubles spot on the left, not his Trips spot on the right
    assert one.assignment("H").motion_from == _spot(F.GUN_DOUBLES(), "H")


def test_motion_on_the_same_spot_is_kept_as_it_was():
    play = passing.mesh_concept().adjust(A.SHIFT("Z", 18.5, -1.0))
    moved = play.with_formation(F.GUN_TREY_RIGHT())         # Z already at 18.5
    z = moved.assignment("Z")
    assert z.motion_from == play.assignment("Z").motion_from == (20.0, -1.0)
    assert z.motion_type == "shift"


def test_other_motion_is_dropped_when_the_player_moves():
    play = passing.mesh_concept().adjust(A.SHIFT("Z", 18.5, -1.0))
    moved = play.with_formation(F.GUN_DOUBLES())            # Z back out at 20
    z = moved.assignment("Z")
    assert z.motion_from is None and z.motion_type is None
    assert (z.player.x, z.player.y) == _spot(F.GUN_DOUBLES(), "Z")


def test_a_hand_placed_start_is_dropped_when_the_player_moves():
    play = passing.mesh_concept()
    play = play.model_copy(update={"assignments": [
        a.model_copy(update={"motion_from": (4.0, -1.0)}) if a.player.label == "H" else a
        for a in play.assignments
    ]})
    moved = play.with_formation(F.GUN_DOUBLES())
    assert not moved.assignment("H").in_motion


@pytest.mark.parametrize("adjust", [
    A.MOTION("H", "jet"), A.MOTION("H", "orbit"), A.MOTION("Z", "across"),
    A.MOTION("Z", "short"), A.SHIFT("Y", 8.0, 0.0),
], ids=str)
def test_the_formation_and_the_assignments_agree_after_a_swap(adjust):
    moved = passing.mesh_concept().adjust(adjust, A.FORMATION(F.GUN_DOUBLES()))
    assert [a.player for a in moved.assignments] == moved.formation.players
    assert Play.from_json(moved.to_json()) == moved


# ── Designer parity ───────────────────────────────────────────────────────────

PARITY = [
    ("power_right", [], "I_FORM_STRONG_LEFT"),
    ("power_right", [], "PRO_SET"),
    ("mesh_concept", [], "I_FORM_PRO_RIGHT"),
    ("mesh_concept", [A.MOTION("H", "jet")], "GUN_DOUBLES"),
    ("mesh_concept", [A.MOTION("Z", "short")], "SHOTGUN_TRIPS_LEFT"),
    ("mesh_concept", [A.SHIFT("Z", 18.5, -1.0)], "GUN_TREY_RIGHT"),
    ("mesh_concept", [A.SHIFT("Z", 18.5, -1.0)], "GUN_DOUBLES"),
]


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("name,adjust,formation", PARITY,
                         ids=["-".join([n, *(str(x).replace(" ", "_") for x in a), f])
                              for n, a, f in PARITY])
def test_the_designer_swaps_formations_the_same_way(name, adjust, formation):
    play = _catalog.play_builders()[name]().adjust(*adjust)
    expected = play.with_formation(getattr(F, formation)())
    got = _js(Playbook(name="Swap", plays=[play]),
              f'return formationSwap(__book.plays[0], CATALOG.formations["{formation}"]);')
    swapped = Play.model_validate({**play.model_dump(mode="json"), **got})
    assert swapped.assignments == expected.assignments
    assert swapped.formation.players == expected.formation.players


# ── Flipping ─────────────────────────────────────────────────────────

FLIPPED = ["power_right", "counter_trey", "buck_sweep", "mesh_concept", "pa_boot",
           "speed_option", "rb_slip", "bubble"]


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("name", FLIPPED)
def test_the_designer_flips_a_play_the_way_python_mirrors_it(name):
    """Flip in the browser and Play.mirror() must agree, blocks and all: a
    pulling guard has to come around the other way."""
    play = _catalog.play_builders()[name]()
    got = _js(Playbook(name="Flip", plays=[play]),
              "renderAll = () => {}; play = normalizePlay(__book.plays[0]); flipPlay();"
              " return {assignments: play.assignments, formation: play.formation};")
    flipped = Play.model_validate({**play.model_dump(mode="json"), **got})
    mirrored = play.mirror()
    assert flipped.assignments == mirrored.assignments
    assert flipped.formation.players == mirrored.formation.players


MOTIONS = [("mesh_concept", "H", "jet"), ("mesh_concept", "Z", "orbit"),
           ("inside_zone", "Z", "across"), ("smash", "H", "short"),
           ("power_right", "Z", "in"), ("mesh_concept", "X", "return")]


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("name,label,kind", MOTIONS, ids=["-".join(m) for m in MOTIONS])
def test_the_designer_puts_a_man_in_motion_the_way_python_does(name, label, kind):
    """Where he starts, where he is at the snap, and what it is called."""
    play = _catalog.play_builders()[name]()
    got = _js(Playbook(name="Motion", plays=[play]),
              f"renderAll = () => {{}}; play = normalizePlay(__book.plays[0]);"
              f" applyMotion({label!r}, {kind!r});"
              " return {assignments: play.assignments, formation: play.formation};")
    moved = Play.model_validate({**play.model_dump(mode="json"), **got})
    expected = play.adjust(A.MOTION(label, kind))
    assert moved.assignment(label) == expected.assignment(label)
    assert moved.formation.player(label) == expected.formation.player(label)
