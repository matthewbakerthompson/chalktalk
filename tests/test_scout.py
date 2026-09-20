"""
The self-scout: reading the game log back. What the numbers say, what a scout
on the other sideline sees, and what the staff has not used yet.
"""
from chalktalk import planner as P
from chalktalk.catalog import passing, running
from chalktalk.models import DriveState, GamePlan, Outcome, Playbook, Role, Snap
from chalktalk.scout import EXPLOSIVE, report


def tag(play, **kw):
    return play.model_copy(update=kw)


def book(**plan) -> Playbook:
    return Playbook(name="Owls", game_plan=GamePlan(**plan), plays=[
        tag(running.inside_zone(), series="Zone", role=Role.BASE),
        tag(running.speed_sweep(), series="Zone", role=Role.CONSTRAINT),
        tag(passing.mesh_concept(), favorite=True),
        tag(passing.stick(), id="stick"),
    ])


def play(book, pid, outcome=Outcome.GAIN, gain=0, state=None):
    return Snap(before=state or DriveState(), play=pid, call=pid, outcome=outcome, gain=gain)


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
    log = [play(b, "inside-zone", gain=3) for _ in range(4)]
    r = report(b, log)
    tend = r.tendencies[0]
    assert (tend.look, tend.calls, tend.runs, tend.passes) == ("I-Form Pro Right", 4, 4, 0)
    assert any("you have run 4 of 4: a scout sees it" in n for n in r.notes)
    # Three calls from a look is not a tendency worth saying.
    assert not report(b, log[:3]).tendencies


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
