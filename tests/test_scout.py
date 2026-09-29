"""
The self-scout: reading the game log back. What the numbers say, what a scout
on the other sideline sees, and what the staff has not used yet.
"""
from chalktalk import planner as P
from chalktalk.catalog import passing, running
from chalktalk.models import (DriveState, GamePlan, Outcome, PlanSection, Playbook, Role, Snap,
                              When)
from chalktalk.models.situation import Hash
from chalktalk.scout import EXPLOSIVE, report


def tag(play, **kw):
    return play.model_copy(update=kw)


def book(**plan) -> Playbook:
    return Playbook(name="Owls", game_plan=GamePlan(**plan), plays=[
        tag(running.inside_zone(), series="Zone", role=Role.BASE),
        tag(running.speed_sweep(), series="Zone", role=Role.CONSTRAINT),
        tag(passing.mesh_concept(), favorite=True),
        tag(passing.stick(), id="stick"),
        passing.y_cross(),
        passing.four_verticals(),
        running.power_right(),
    ])


def play(book, pid, outcome=Outcome.GAIN, gain=0, state=None):
    return Snap(before=state or DriveState(), play=pid, call=pid, outcome=outcome, gain=gain)


def at(down=1, distance=10, yard_line=75, hash_mark=None):
    return DriveState(down=down, distance=distance, yard_line=yard_line,
                      hash_mark=Hash(hash_mark) if hash_mark else None)


def test_it_counts_only_the_snaps_that_were_plays():
    b = book()
    log = [play(b, "inside-zone", gain=4),                       # on schedule at 40%
           play(b, "inside-zone", Outcome.PENALTY_US, 5),        # a flag is not a play
           play(b, "mesh-concept", Outcome.INCOMPLETE),
           play(b, "stick", Outcome.SACK, 6)]
    r = report(b, log)
    assert (r.snaps, r.on, r.rate) == (3, 1, 33)
    assert r.yards == 4 + 0 - 6
    assert [d.label for d in r.by_down] == ["1st down"]


def test_third_downs_count_conversions_not_yards():
    b = book()
    third = DriveState(down=3, distance=5, yard_line=40)
    log = [play(b, "stick", gain=9, state=third),                # a first down
           play(b, "stick", gain=2, state=third)]                # short of it
    r = report(b, log)
    assert (r.thirds.calls, r.thirds.on) == (2, 1)
    assert "1 of 2 on third down" in r.notes


def test_a_scout_sees_a_formation_that_only_runs():
    b = book()
    runs = [play(b, "inside-zone", gain=3) for _ in range(4)]
    log = runs + [play(b, "y-cross", gain=6) for _ in range(4)]
    r = report(b, log)
    tend = r.tendencies[0]
    assert (tend.by, tend.look, tend.calls, tend.runs, tend.passes) == (
        "formation", "I-Form Pro Right", 4, 4, 0)
    assert "From I-Form Pro Right, you have run 4 of 4: a scout sees it" in r.notes
    # Three calls from a look is not a tendency worth saying.
    assert not report(b, runs[:3]).tendencies


def test_the_half_is_split_every_way_a_scout_splits_it():
    b = book()
    log = [play(b, "inside-zone", gain=3, state=at(1, 10, 95, "L")) for _ in range(4)]
    r = report(b, log)
    assert [(t.by, t.look) for t in r.tendencies] == [
        ("formation", "I-Form Pro Right"), ("personnel", "21 personnel"),
        ("down", "1st & 10"), ("hash", "Left hash"), ("field", "Backed up")]
    assert all((t.calls, t.runs, t.on) == (4, 4, 0) for t in r.tendencies)


def test_a_look_is_said_only_when_nothing_broader_says_it():
    b = book()
    log = [play(b, "inside-zone", gain=4) for _ in range(4)] + [play(b, "power-right", gain=4)] \
        + [play(b, "mesh-concept", gain=6) for _ in range(5)]
    r = report(b, log)
    # Four runs from I-Form and a power from I-Form Strong: every 21 personnel
    # snap is a run, so the personnel is the note, not the formation inside it.
    assert "In 21 personnel, you have run 5 of 5: a scout sees it" in r.notes
    assert not any(n.startswith("From I-Form Pro Right") for n in r.notes)
    # Trips Right is all of 11 personnel: the same snaps, and the formation is said.
    assert "From Shotgun Trips Right, you have thrown 5 of 5: a scout sees it" in r.notes
    assert not any(n.startswith("In 11 personnel") for n in r.notes)
    assert [t.by for t in r.leans] == ["formation", "personnel"]


def test_the_whole_half_speaks_first():
    b = book()
    r = report(b, [play(b, "inside-zone", gain=3, state=at(hash_mark="R")) for _ in range(4)])
    assert [n for n in r.notes if "a scout sees it" in n] == [
        "Overall, you have run 4 of 4: a scout sees it"]
    assert [t.by for t in r.leans] == ["overall"]


def test_two_looks_together_when_neither_says_it_alone():
    b = book()
    log = [play(b, pid, gain=9, state=at(2, 8, 70, "L"))
           for pid in ("mesh-concept", "y-cross", "four-verticals", "y-cross")] \
        + [play(b, "inside-zone", gain=3, state=at(2, 8, 70, "R")) for _ in range(4)] \
        + [play(b, "inside-zone", gain=3, state=at(1, 10, 70, "L")) for _ in range(4)]
    r = report(b, log)
    # 2nd & 7+ is half and half, and so is the left hash: together, all pass.
    assert "On 2nd & 7+, from the left hash, you have thrown 4 of 4: a scout sees it" in r.notes
    assert (r.leans[-1].by, r.leans[-1].look) == ("down+hash", "2nd & 7+, Left hash")
    # In a half that runs, the one place it throws is still said.
    log += [play(b, "inside-zone", gain=3, state=at(2, 8, 70, "R")) for _ in range(12)]
    r = report(b, log)
    assert [n for n in r.notes if "a scout sees it" in n] == [
        "Overall, you have run 20 of 24: a scout sees it",
        "On 2nd & 7+, from the left hash, you have thrown 4 of 4: a scout sees it"]


def test_downs_and_spots_are_named_by_the_plans_own_sections():
    b = book(sections=[PlanSection(title="3rd & short", when=When(downs=[3], distance=(0, 2))),
                       PlanSection(title="Scoring zone", when=When(yard_line=(1, 25)))])
    log = [play(b, "power-right", gain=3, state=at(3, 2, 20, "M")) for _ in range(4)] \
        + [play(b, "stick", gain=3, state=at(3, 5, 60)) for _ in range(4)]
    r = report(b, log)
    looks = {(t.by, t.look) for t in r.tendencies}
    assert {("down", "3rd & short"), ("field", "Scoring zone"),       # the plan's own
            ("down", "3rd & 4-6"), ("field", "Coming out"),           # nothing in the plan
            ("hash", "Middle")} <= looks
    # And the stock sections by default: 1st & 5 isn't "1st & 10".
    r = report(book(), [play(book(), "stick", state=at(1, 5, 50)) for _ in range(4)])
    assert {("down", "1st & 4-6"), ("field", "Midfield")} <= {(t.by, t.look) for t in r.tendencies}


def test_explosives_use_the_yardstick_for_the_kind_of_play():
    b = book()
    log = [play(b, "inside-zone", gain=EXPLOSIVE["run"]),        # a run that counts
           play(b, "mesh-concept", gain=EXPLOSIVE["run"]),       # the same yards, a pass: not yet
           play(b, "mesh-concept", gain=EXPLOSIVE["pass"])]
    r = report(b, log)
    assert [e.play for e in r.explosives] == ["inside-zone", "mesh-concept"]
    assert [round(e.yards) for e in r.explosives] == [12, 16]


def test_what_is_set_up_and_what_is_left():
    b = book(openers=["stick", "mesh-concept"], starters=["inside-zone"])
    r = report(b, [play(b, "inside-zone", gain=5)])
    assert r.ready == ["Zone has been shown: Speed Sweep hasn't been called"]
    assert r.unused[0].startswith("2 of the opening script left: Stick, Mesh Concept")
    assert any("Favorites not used: Mesh Concept" in u for u in r.unused)
    assert not any("Drive starters" in u for u in r.unused)   # it was called


def test_the_best_calls_are_ranked_by_yards_a_call():
    b = book()
    log = [play(b, "inside-zone", gain=2), play(b, "inside-zone", gain=4),
           play(b, "stick", gain=9), play(b, "stick", gain=11),
           play(b, "mesh-concept", gain=30)]                    # one call: not ranked
    r = report(b, log)
    assert [l.play for l in r.best] == ["stick", "inside-zone"]
    assert r.best[0].yards / r.best[0].calls == 10


def test_an_empty_log_says_nothing():
    r = report(book())
    assert (r.snaps, r.rate, r.notes, r.tendencies) == (0, 0, [], [])
