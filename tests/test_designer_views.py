"""
The designer's panels draw what Python works out (chalktalk/designer/views.py).
Each view has to say exactly what `planner`, `difficulty` and `scout` say when
a Python user calls them on the same book.
"""
import json

import pytest

from chalktalk import difficulty as D
from chalktalk import planner as P
from chalktalk import scout
from chalktalk.catalog import passing, running
from chalktalk.designer import server, views
from chalktalk.models import DriveScript, DriveState, GamePlan, Outcome, Playbook, Role, Snap
from chalktalk.models import situation as S


def tag(play, **kw):
    return play.model_copy(update=kw)


def _book(**plan) -> Playbook:
    plan = {"starters": ["power-right", "stick"], **plan}
    book = Playbook(name="Wk 3", game_plan=GamePlan(**plan), plays=[
        tag(running.inside_zone(), series="Zone", role=Role.BASE, situation=S.Situation(label="Openers")),
        tag(passing.mesh_concept(), situation=S.Situation(label="Openers")),
        tag(running.speed_sweep(), series="Zone", role=Role.CONSTRAINT, tell="Backside LB flowing hard"),
        tag(passing.y_cross(), series="Zone", role=Role.PLAY_ACTION),
        tag(running.power_right(), situation=S.Situation(down=3, distance=2)),
        tag(passing.four_verticals(), series="Zone", role=Role.SHOT, difficulty=3,
            situation=S.Situation(down=3, distance=9)),
        tag(passing.stick(), favorite=True, situation=S.Situation(down=3, distance=5, yard_line=15)),
        tag(passing.smash(), series="Zone", role=Role.TRICK),
    ]).with_ids()
    script = P.fill_script(book, DriveScript(name="Opening drive"))
    return book.model_copy(update={"game_plan": book.game_plan.model_copy(update={"drives": [script]})})


def _logged(book: Playbook, results) -> Playbook:
    state, log = DriveState(), []
    for pid, outcome, gain in results:
        p = next(q for q in book.plays if q.id == pid)
        log.append(Snap(before=state, play=pid, call=p.call, outcome=outcome, gain=gain))
        state = P.advance(state, outcome, gain)
    return book.model_copy(update={"game_plan": book.game_plan.model_copy(update={"log": log})}), state


# ── the plan builder ──────────────────────────────────────────────────────────

def test_the_plan_view_says_what_the_planner_says():
    book = _book()
    view = views.plan_view(book, script=0)
    assert view["openers"] == P.openers(book) and view["starters"] == P.starters(book)
    assert view["check"] == P.check(book)
    numbers = P.numbers(book)
    assert [numbers[pid] for pid in view["order"]] == sorted(numbers.values())
    assert [(s["section"]["title"], s["ids"]) for s in view["sections"]] == \
           [(s.title, ids) for s, ids in P.sections(book)]
    assert [s["base"] for s in view["sections"]].count(True) == 1
    assert view["thresholds"] == list(P.plan_of(book).thresholds)
    for p in book.plays:
        d = D.difficulty(p)
        assert view["difficulty"][p.id] == {"score": d.score, "tier": d.tier,
                                            "tier_name": D.TIER_NAMES[d.tier], "reasons": d.reasons}


def test_the_script_tree_ranks_each_slot_the_way_it_will_be_called():
    book = _book()
    script = P.plan_of(book).drives[0]
    tree = views.plan_view(book, script=0)["tree"]
    assert [s["path"] for s in tree] == views.SCRIPT_PATHS
    for slot in tree:
        path = slot["path"]
        state = P.script_state(script, path)
        node = P.script_node(script, path)
        assert slot["pick"] == (node.play if node else None)
        if slot["reset"]:
            assert slot["ranked"] == [] and slot["label"] == "A first down"
            continue
        assert slot["label"] == state.label()
        expected = P.suggest(book, state, P.script_log(book, script, path), k=len(book.plays),
                             branches=False)
        assert [(r["play"], r["points"]) for r in slot["ranked"]] == [(s.play, s.points) for s in expected]


def test_the_drive_so_far_above_a_slot_is_the_calls_the_script_makes():
    book = _book()
    script = P.plan_of(book).drives[0]
    assert P.script_log(book, script, []) == []
    log = P.script_log(book, script, ["on", "off"])
    assert [s.play for s in log] == [script.first.play, script.first.on.play]
    assert log[1].before == P.script_state(script, ["on"])


def test_no_script_chosen_means_no_tree():
    view = views.plan_view(_book(), script=None)
    assert view["tree"] is None and view["scripts"][0]["name"] == "Opening drive"
    assert views.plan_view(_book(), script=7)["tree"] is None


# ── the Game panel ────────────────────────────────────────────────────────────

def test_the_game_view_ranks_the_way_suggest_does():
    book, state = _logged(_book(), [("inside-zone", Outcome.GAIN, 3)])
    view = views.game_view(book, state)
    picks = P.suggest(book, state, list(P.plan_of(book).log), k=3)
    assert view["suggestions"] == [s.model_dump(mode="json") for s in picks]
    assert view["label"] == state.label() == "2nd & 7, Own 28"
    assert view["check"] == P.check(book)


def test_the_log_reads_like_a_sideline_chart():
    book, state = _logged(_book(), [
        ("inside-zone", Outcome.GAIN, 6), ("mesh-concept", Outcome.INCOMPLETE, 0),
        ("stick", Outcome.SACK, 7), ("power-right", Outcome.PENALTY_THEM, 5)])
    view = views.game_view(book, state)
    t = P.plan_of(book).thresholds
    log = P.plan_of(book).log
    assert [r["ok"] for r in view["log"]] == [P.is_success(s.before, s.outcome, s.gain, t) for s in log]
    assert [r["what"] for r in view["log"]] == ["+6", "incomplete", "sack -7", "flag on them +5"]
    assert [r["name"] for r in view["log"]] == ["Inside Zone", "Mesh Concept", "Stick", "Power Right"]
    assert view["log"][0]["sit"] == "1&10 -25"
    counted = [r for r in view["log"] if r["ok"] is not None]
    assert view["summary"] == f"{sum(r['ok'] for r in counted)} of {len(counted)} on schedule"
    assert view["warning"] == P.alternation_warning(book, list(log))


def test_the_half_so_far_matches_the_scout():
    book, state = _logged(_book(), [("inside-zone", Outcome.GAIN, 6), ("speed-sweep", Outcome.GAIN, 13)])
    r = scout.report(book)
    half = views.game_view(book, state)["scout"]
    assert (half["snaps"], half["on"], half["notes"]) == (r.snaps, r.on, r.notes)
    assert [(s["label"], s["calls"]) for s in half["by_down"]] == [(s.label, s.calls) for s in r.by_down]


def test_the_script_is_followed_from_the_log():
    book = _book()
    script = P.plan_of(book).drives[0]
    view = views.game_view(book, DriveState(), script=0)
    assert view["scripted"]["play"] == script.first.play
    assert view["scripted"]["words"] == "the first call" and view["scripted"]["name"] == "Opening drive"
    book, state = _logged(book, [(script.first.play, Outcome.GAIN, 1)])      # off schedule
    path, node = P.follow(book, script, state, list(P.plan_of(book).log))
    view = views.game_view(book, state, script=0)
    assert view["scripted"]["path"] == path == ["off"]
    assert view["scripted"]["play"] == (node.play if node else None)
    assert view["scripted"]["words"] == "off schedule"


def test_a_finished_drive_offers_nothing():
    over = P.advance(DriveState(yard_line=5), Outcome.GAIN, 5)
    view = views.game_view(_book(), over, script=0)
    assert view["over"] and view["label"] == "Touchdown"
    assert view["suggestions"] == [] and view["scripted"] is None


# ── actions and the play sheet ────────────────────────────────────────────────

def test_advancing_is_the_planners_arithmetic():
    state = DriveState(down=2, distance=6, yard_line=60)
    got = views.advance(state, "gain", 4)["state"]
    assert DriveState.model_validate(got) == P.advance(state, Outcome.GAIN, 4)
    with pytest.raises(ValueError):
        views.advance(state, "fumble-ish", 0)


def test_drafting_and_filling_come_back_as_data_the_page_keeps():
    bare = Playbook(name="Bare", plays=[running.inside_zone(), running.speed_sweep(), passing.mesh_concept()])
    got = views.draft(bare)
    assert got["notes"] and Playbook.model_validate(got["book"]) == P.draft(bare).book
    book = _book()
    empty = DriveScript(name="Two minute", start=DriveState(yard_line=70))
    filled = DriveScript.model_validate(views.fill_script(book, empty)["script"])
    assert filled == P.fill_script(book, empty)


def test_the_play_sheet_shows_the_score_before_the_coachs_tier():
    p = tag(passing.four_verticals(), difficulty=1)
    auto = views.play_view(p)["auto"]
    d = D.difficulty(p.model_copy(update={"difficulty": None}))
    assert (auto["score"], auto["tier"], auto["reasons"]) == (d.score, d.tier, d.reasons)


# ── through the server ────────────────────────────────────────────────────────

def test_the_server_answers_for_each_panel_and_reads_a_book_once(tmp_path):
    session = server.Session(str(tmp_path))
    book = json.loads(_book().model_dump_json())
    state = DriveState().model_dump(mode="json")
    plan = server.ROUTES["plan_view"](session, {"book": book, "script": 0})
    game = server.ROUTES["game_view"](session, {"book": book, "state": state, "script": 0})
    assert plan["tree"] and game["scripted"]["play"]
    assert server._book({"book": book}) is server._book({"book": json.loads(json.dumps(book))})
    assert server.ROUTES["advance"](session, {"state": state, "outcome": "gain", "gain": 12})["state"]["down"] == 1
    assert server.ROUTES["play_view"](session, {"play": book["plays"][0]})["auto"]["tier_name"]
    # a flag in the script index can't pick a script
    assert server.ROUTES["plan_view"](session, {"book": book, "script": True})["tree"] is None
