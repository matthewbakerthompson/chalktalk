"""
The quarterback: what he does, and the order he looks at people.
"""
import inspect

import pytest

from chalktalk.catalog import passing, redzone, running
from chalktalk.models import Play, Playbook
from chalktalk.models.qb import QBAction, QBPlan
from chalktalk.templates import formations as F, qb as Q, routes as R

ALL_PLAYS = []
for _mod in (passing, running, redzone):
    for _name, _fn in inspect.getmembers(_mod, inspect.isfunction):
        if not _name.startswith("_") and _fn.__module__ == _mod.__name__:
            ALL_PLAYS.append((_name, _fn))

UNDER_CENTER = ("I_FORM_PRO_RIGHT", "I_FORM_STRONG_RIGHT", "PRO_SET",
                "SINGLE_BACK_ACE", "SINGLE_BACK_PRO_RIGHT", "WISHBONE",
                "GOAL_LINE", "GOAL_LINE_HEAVY", "JUMBO_TIGHT")


# ── Where he lines up ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", UNDER_CENTER)
def test_under_center_quarterbacks_are_under_center(name):
    """He takes the snap with his hands on the center, not five yards deep."""
    qb = next(p for p in getattr(F, name)().players if p.label == "QB")
    assert -3.0 < qb.y < 0.0, f"{name} has the QB at {qb.y}"


@pytest.mark.parametrize("name", UNDER_CENTER)
def test_the_backfield_sits_behind_him_not_on_top_of_him(name):
    formation = getattr(F, name)()
    qb = next(p for p in formation.players if p.label == "QB")
    backs = [p for p in formation.players
             if p.position.value in ("RB", "FB", "HB")]
    for back in backs:
        assert back.y < qb.y, f"{name}: {back.label} is not behind the QB"
        assert back.y > -8.0, f"{name}: {back.label} is {abs(back.y)} yards deep"


def test_shotgun_quarterbacks_are_still_in_the_gun():
    for name in ("SHOTGUN_TRIPS_RIGHT", "GUN_DOUBLES", "SHOTGUN_ACE"):
        qb = next(p for p in getattr(F, name)().players if p.label == "QB")
        assert qb.y <= -4.0


# ── The plan ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", sorted(Q.ACTIONS))
def test_every_action_draws_something(name):
    plan = Q.ACTIONS[name]()
    assert len(plan.path) >= 2, name
    assert plan.path[0].x == 0 and plan.path[0].y == 0, "paths start on the player"


def test_deeper_drops_go_deeper():
    assert Q.DROPBACK(3).depth < Q.DROPBACK(5).depth < Q.DROPBACK(7).depth
    assert Q.GUN(1).depth < Q.GUN(3).depth < Q.GUN(5).depth


def test_a_drop_from_the_gun_is_shorter_than_one_from_under_center():
    assert Q.GUN(3).depth < Q.DROPBACK(3).depth


def test_run_actions_have_a_mesh_point_and_drops_do_not():
    for plan in (Q.HANDOFF(1), Q.MESH(1), Q.PLAY_ACTION(1), Q.OPTION(1),
                 Q.DRAW(1), Q.PITCH(1)):
        assert plan.mesh_point is not None, plan.action
    for plan in (Q.DROPBACK(5), Q.GUN(3), Q.SNEAK()):
        assert plan.mesh_point is None, plan.action


def test_direction_flips_the_footwork():
    right, left = Q.BOOT(1), Q.BOOT(-1)
    assert [p.x for p in right.path] == [-p.x for p in left.path]
    assert [p.y for p in right.path] == [p.y for p in left.path]


def test_mirroring_flips_path_mesh_and_direction():
    plan = Q.PLAY_ACTION(1, back="RB")
    flipped = plan.mirrored()
    assert flipped.direction == -plan.direction
    assert [p.x for p in flipped.path] == [-p.x for p in plan.path]
    assert flipped.mesh_at.x == -plan.mesh_at.x
    assert flipped.mesh_at.y == plan.mesh_at.y


def test_mirroring_twice_is_a_round_trip():
    plan = Q.OPTION(1)
    assert plan.mirrored().mirrored().path == plan.path


def test_read_order_is_one_based():
    plan = Q.GUN(3, reads=["Z", "H", "RB"])
    assert plan.read_order("Z") == 1
    assert plan.read_order("RB") == 3
    assert plan.read_order("Y") is None


def test_progression_replaces_the_reads():
    plan = Q.GUN(3, reads=["Z"]).progression("Y", "H")
    assert plan.reads == ["Y", "H"]


def test_plan_describes_itself():
    assert Q.GUN(3, reads=["Z", "H"]).describe() == "3-step Dropback (Z > H)"
    assert "read the end" in Q.OPTION(1, key="the end").describe()


def test_pass_actions_know_they_are_passes():
    assert Q.DROPBACK(5).is_pass and Q.BOOT(1).is_pass
    assert not Q.HANDOFF(1).is_pass
    assert QBAction.SNEAK.carries_the_ball
    assert not QBAction.HANDOFF.carries_the_ball


# ── On a play ─────────────────────────────────────────────────────────────────

def test_with_qb_and_the_qb_property():
    play = passing.mesh_concept().with_qb(Q.GUN(5, reads=["X"]))
    assert play.qb.steps == 5
    assert play.qb.reads == ["X"]


def test_progression_needs_a_plan_first():
    bare = passing.mesh_concept().with_qb(None)
    with pytest.raises(ValueError):
        bare.progression("X")


def test_play_read_order_reads_through_to_the_plan():
    play = passing.mesh_concept().progression("Z", "Y")
    assert play.read_order("Z") == 1
    assert play.read_order("Y") == 2
    assert play.read_order("H") is None


def test_mirroring_a_play_mirrors_the_quarterback():
    play = running.power_right()
    flipped = play.mirror()
    assert flipped.qb.direction == -play.qb.direction
    assert flipped.qb.mesh_at.x == -play.qb.mesh_at.x


def test_the_plan_survives_a_json_round_trip():
    play = passing.mesh_concept()
    assert Play.from_json(play.to_json()) == play


def test_describe_mentions_the_quarterback():
    text = passing.mesh_concept().describe()
    assert "Dropback" in text


# ── The catalog ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,fn", ALL_PLAYS, ids=[n for n, _ in ALL_PLAYS])
def test_every_play_tells_the_quarterback_what_to_do(name, fn):
    assert fn().qb is not None, f"{name} leaves the quarterback standing there"


@pytest.mark.parametrize("name,fn", ALL_PLAYS, ids=[n for n, _ in ALL_PLAYS])
def test_reads_point_at_receivers_who_are_actually_running_routes(name, fn):
    play = fn()
    for label in play.qb.reads:
        a = play.assignment(label)
        assert a is not None, f"{name} reads {label}, who is not on the field"
        assert a.route is not None, f"{name} reads {label}, who is blocking"


@pytest.mark.parametrize("name,fn", ALL_PLAYS, ids=[n for n, _ in ALL_PLAYS])
def test_the_back_he_meshes_with_is_on_the_field(name, fn):
    play = fn()
    if play.qb.mesh_with:
        assert play.assignment(play.qb.mesh_with) is not None, name


def test_pass_concepts_have_a_progression():
    for name, fn in ALL_PLAYS:
        play = fn()
        if play.qb.is_pass:
            assert play.qb.reads, f"{name} is a pass with nobody to throw to"
            assert len(play.qb.reads) >= 2, f"{name} has a one-man progression"


def test_run_plays_hand_it_to_the_ball_carrier():
    for name in ("inside_zone", "power_right", "counter_trey", "trap"):
        play = getattr(running, name)()
        assert play.qb.action is QBAction.HANDOFF
        assert play.qb.mesh_with == play.ball_carrier.player.label, name


def test_the_zone_read_reads_somebody():
    assert running.veer_read().qb.key
    assert passing.rpo_bubble().qb.key


def test_the_sneak_keeps_it():
    assert redzone.qb_sneak().qb.action is QBAction.SNEAK


def test_reads_do_not_repeat():
    for name, fn in ALL_PLAYS:
        reads = fn().qb.reads
        assert len(reads) == len(set(reads)), name


# ── Rendering ─────────────────────────────────────────────────────────────────

def test_the_drop_is_drawn():
    svg = passing.mesh_concept().render().render()
    assert 'marker-end="url(#arr-qb)"' in svg


def test_the_mesh_point_is_marked_on_run_action():
    """The exchange gets a ring; a straight drop has nothing to mark."""
    import re
    # the ring is hollow; the read numerals are filled discs
    rings = lambda svg: len(re.findall(
        r'<circle[^>]*fill="none"[^>]*stroke="#fbbf24"', svg))
    assert rings(running.power_right().render().render()) == 1
    assert rings(passing.mesh_concept().render().render()) == 0


def test_one_numeral_per_read():
    play = passing.mesh_concept()
    svg = play.render().render()
    assert svg.count('fill="#fde68a"') == len(play.qb.reads)


def test_changing_the_progression_changes_the_diagram():
    play = passing.mesh_concept()
    assert play.render().render() != play.progression("Z").render().render()


def test_a_play_with_no_reads_draws_no_numerals():
    play = running.inside_zone()
    assert 'fill="#fde68a"' not in play.render().render()


def test_the_qb_arrowhead_is_defined():
    import re
    svg = passing.mesh_concept().render().render()
    defined = set(re.findall(r'<marker id="([\w-]+)"', svg))
    used = set(re.findall(r'marker-end="url\(#([\w-]+)\)"', svg))
    assert "arr-qb" in defined
    assert used <= defined


def test_pdf_draws_the_quarterback(tmp_path):
    path = tmp_path / "qb.pdf"
    Playbook(name="QB", plays=[passing.mesh_concept(),
                               running.power_right()]).save_pdf(str(path))
    assert path.stat().st_size > 1500


# ── Designer parity ───────────────────────────────────────────────────────────

def test_the_designer_ships_every_action():
    from chalktalk import designer
    actions = designer.catalog()["qb_actions"]
    assert set(actions) == set(Q.ACTIONS)
    assert all("1" in v and "-1" in v for v in actions.values())


def test_the_designer_draws_the_same_things():
    from chalktalk import designer
    with open(designer._TEMPLATE, encoding="utf-8") as fh:
        src = fh.read()
    assert "drawQB" in src and "drawReads" in src
    assert 'QB_COLOR="#fbbf24"' in src
    assert 'READ_TEXT="#fde68a"' in src


def test_compacting_the_catalog_does_not_break_it():
    """Nulls are stripped on the way into the browser; defaults fill back in."""
    import json

    from chalktalk import designer
    raw = designer._json_for_script(designer.catalog()["plays"])
    plays = json.loads(raw.replace("\\u003c", "<").replace("\\u003e", ">"))
    for name, data in plays.items():
        Play.model_validate(data), name
