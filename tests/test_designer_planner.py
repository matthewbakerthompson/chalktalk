"""
The designer carries a twin of the drive planner and the codes. These tests
run the browser's functions in node against planner.py, difficulty.py and
codes.py on the same books, and require the same numbers, the same ranking,
the same reasons word for word, and byte-identical wristband cards.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

from chalktalk import codes as K
from chalktalk import planner as P
from chalktalk.catalog import all_plays, passing, running
from chalktalk.difficulty import difficulty
from chalktalk.models import (CallSystem, DriveState, GamePlan, Mode, Outcome, Playbook,
                              Role, Snap)
from chalktalk.models import situation as S
from chalktalk.models.situation import Hash

from chalktalk import designer

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def tag(play, **kw):
    return play.model_copy(update=kw)


def _book(**plan) -> Playbook:
    return Playbook(name="Wk 3", game_plan=GamePlan(**plan), plays=[
        tag(running.inside_zone(), series="Zone", role=Role.BASE,
            situation=S.Situation(label="Openers")),
        tag(passing.mesh_concept(), situation=S.Situation(label="Openers", hash_mark=Hash.LEFT)),
        tag(running.speed_sweep(), series="Zone", role=Role.CONSTRAINT,
            tell="Backside LB flowing hard"),
        tag(passing.y_cross(), series="Zone", role=Role.PLAY_ACTION),
        tag(running.power_right(), situation=S.Situation(down=3, distance=2)),
        tag(passing.four_verticals(), series="Zone", role=Role.SHOT, difficulty=3,
            situation=S.Situation(down=3, distance=9)),
        tag(passing.stick(), situation=S.Situation(down=3, distance=5, yard_line=15)),
        tag(passing.smash(), series="Zone", role=Role.TRICK),
        tag(passing.mesh_concept(), situation=S.Situation(label="Two Minute")),
    ]).with_ids()


def _js(book, body: str):
    html = designer.build()
    script = html[html.index("<script>") + len("<script>"):html.rindex("</script>")].rstrip()
    assert script.endswith("boot();")
    script = script[:-len("boot();")]
    prelude = ("globalThis.window = globalThis;\n"
               "globalThis.document = {getElementById: () => null, addEventListener() {},"
               " createElement: () => ({})};\n"
               "globalThis.localStorage = {getItem: () => null, setItem() {}, removeItem() {}};\n")
    data = book if isinstance(book, dict) else book.model_dump(mode="json")
    tail = (f"\n;const __book = ensureIds(normalizeBook({json.dumps(data)}));\n"
            f"process.stdout.write(JSON.stringify((function () {{ {body} }})()));\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "designer.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(prelude + script + tail)
        run = subprocess.run([NODE, path], capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def _log(book):
    start = DriveState()
    s1 = P.advance(start, Outcome.GAIN, 4)
    s2 = P.advance(s1, Outcome.INCOMPLETE)
    return [
        Snap(before=start, play="inside-zone", call="IZ", gain=4, tells=["backside lb flowing hard"]),
        Snap(before=s1, play="mesh-concept", call="Mesh", outcome=Outcome.INCOMPLETE),
        Snap(before=s2, play="inside-zone", call="IZ", gain=9),
    ]


STATES = [
    DriveState(),
    DriveState(down=2, distance=6, yard_line=71, hash_mark=Hash.LEFT),
    DriveState(down=3, distance=2, yard_line=45),
    DriveState(down=3, distance=9, yard_line=30),
    DriveState(down=1, distance=10, yard_line=15),
    DriveState(down=2, distance=14, yard_line=60),
    DriveState(yard_line=70, mode=Mode.TWO_MINUTE),
    DriveState(yard_line=50, mode=Mode.FOUR_MINUTE),
]


def test_ids_are_made_the_same_way():
    raw = Playbook(name="x", plays=[passing.mesh_concept(), passing.mesh_concept(),
                                    tag(passing.stick(), id="mesh-concept-2"), running.power_right()])
    # The model fills ids in; hand the browser the book as it was saved, without them.
    data = raw.model_dump(mode="json")
    for p, saved in zip(data["plays"], [None, None, "mesh-concept-2", None]):
        p["id"] = saved
    assert _js(data, "return __book.plays.map(p => p.id);") == [p.id for p in raw.plays]
    assert [p.id for p in raw.plays] == ["mesh-concept", "mesh-concept-3", "mesh-concept-2", "power-right"]


def test_difficulty_matches_python():
    plays = list(all_plays().values())
    book = Playbook(name="all", plays=plays).with_ids()
    js = _js(book, "return __book.plays.map(p => { const d = difficultyOf(p); return [d.score, d.tier, d.reasons]; });")
    assert js == [[d.score, d.tier, d.reasons] for d in map(difficulty, book.plays)]


def test_difficulty_of_adjusted_plays_matches_python():
    # The catalog has little motion, no tags and no alerts; adjusted plays do.
    from chalktalk import adjustments as A
    from chalktalk.models.play import PlayType
    from chalktalk.templates import routes as R
    plays = all_plays()
    adjusted = [
        plays["mesh_concept"].adjust(A.MOTION("Z", "jet")),
        plays["mesh_concept"].adjust(A.MOTION("Z", "jet"), A.TAG("Y", R.CORNER()), A.TEMPO("no_huddle")),
        plays["bubble"].adjust(A.MOTION("RB", "orbit")),
        plays["inside_zone"].adjust(A.TEMPO("check"), A.ALERT("Check to Power vs 5-down"), A.ALERT("Bubble")),
        plays["counter_trey"].adjust(A.MOTION("Z", "short"), A.SHIFT("Y", 4, -1)),
        tag(plays["smash"], difficulty=1), tag(plays["four_verticals"], play_type=PlayType.SPECIAL),
    ]
    book = Playbook(name="adjusted", plays=adjusted).with_ids()
    js = _js(book, "return __book.plays.map(p => { const d = difficultyOf(p); return [d.score, d.tier, d.reasons]; });")
    assert js == [[d.score, d.tier, d.reasons] for d in map(difficulty, book.plays)]


@pytest.mark.parametrize("size", ["youth", "teen", "adult"])
def test_wristband_inserts_lay_out_the_same(size):
    from chalktalk.renderer.sheets import band_layout, short_call
    calls = ["Shotgun Trips Right Mesh Concept", "I-Form Strong Left Power", "Doubles Screen Right"]
    groups = [["1st & 10", [[str(n), short_call(calls[n % 3])] for n in range(1, 18)]],
              ["3rd & short", [[str(n), "Power"] for n in range(18, 20)]],
              ["Red zone", [[str(n), "Fade"] for n in range(20, 75)]]]
    js = _js(_book(), f"return [bandLayout({json.dumps(groups)}, {json.dumps(size)}),"
                      f" {json.dumps(calls)}.map(shortCall)];")
    assert js == [band_layout(groups, size), [short_call(c) for c in calls]]


def test_reads_against_a_coverage_match_python():
    from chalktalk.models.qb import QBAction, QBPlan
    plan = QBPlan(action=QBAction.DROPBACK).progression("Z", "H", "RB").progression("H", "Z", vs="Cover 2")
    covs = [None, "Cover 2", "cover 2 ", "Cover 3", ""]
    js = _js(_book(), f"const plan = {plan.model_dump_json()};"
                      f" return {json.dumps(covs)}.map(c => readsAgainst(plan, c));")
    assert js == [plan.reads_against(c) for c in covs]


@pytest.mark.parametrize("start", [DriveState(), DriveState(yard_line=18), DriveState(down=1, distance=2, yard_line=50)])
def test_filling_and_following_a_script_match_python(start):
    from chalktalk.models import DriveScript, ScriptCall
    book = _book()
    mine = DriveScript(name="Open", start=start, first=ScriptCall(play="power-right", off=ScriptCall(play="stick")))
    py = P.fill_script(book, mine)
    s1 = P.advance(start, Outcome.GAIN, 1)
    log = [Snap(before=start, play=py.first.play or "x", call="x", gain=1)]
    path, node = P.follow(book, py, s1, log)
    payload = json.dumps({"script": mine.model_dump(mode="json"), "state": s1.model_dump(mode="json"),
                          "log": [s.model_dump(mode="json") for s in log]})
    js = _js(book, f"const x = {payload}; const f = fillScript(__book, x.script);"
                   " const [path, node] = followScript(__book, f, x.state, x.log);"
                   " return {first: f.first, path, node: node ? node.play : null};")
    assert js == {"first": py.first.model_dump(mode="json"), "path": path, "node": node.play if node else None}


def _plan_view(book: Playbook, notes: list[str]) -> dict:
    return {"tags": [[p.id, p.series, p.role.value if p.role else None] for p in book.plays],
            "sections": [[s.title, ids] for s, ids in P.sections(book)],
            "openers": P.openers(book), "notes": notes}


@pytest.mark.parametrize("which", ["catalog", "tagged", "few"])
def test_the_draft_matches_python(which):
    book = {"catalog": lambda: Playbook(name="all", plays=list(all_plays().values())),
            "tagged": _book,
            "few": lambda: Playbook(name="few", plays=[running.inside_zone(), running.speed_sweep(),
                                                       all_plays()["pa_boot"], passing.mesh_concept(),
                                                       running.power_right()])}[which]()
    d = P.draft(book)
    js = _js(book, "const d = draftPlan(__book);"
                   " return {tags: d.book.plays.map(p => [p.id, p.series || null, p.role || null]),"
                   " sections: planSections(d.book).map(([s, ids]) => [s.title, ids]),"
                   " openers: planOpeners(d.book), notes: d.notes};")
    assert js == _plan_view(d.book, d.notes)


def test_sections_openers_numbers_and_check_match_python():
    book = _book(execution=2)
    js = _js(book, "return {sections: planSections(__book).map(([s, ids]) => [s.title, ids]),"
                   " openers: planOpeners(__book), order: planCallOrder(__book), check: planCheck(__book)};")
    assert js["sections"] == [[s.title, ids] for s, ids in P.sections(book)]
    assert js["openers"] == P.openers(book)
    assert js["order"] == list(P.numbers(book))
    assert js["check"] == P.check(book)


@pytest.mark.parametrize("state", STATES, ids=lambda s: s.label().replace(" ", ""))
@pytest.mark.parametrize("with_log", [False, True])
def test_suggestions_match_python_word_for_word(state, with_log):
    book = _book()
    log = _log(book) if with_log else []
    py = [s.model_dump(mode="json") for s in P.suggest(book, state, log, k=5)]
    payload = json.dumps({"state": state.model_dump(mode="json"),
                          "log": [s.model_dump(mode="json") for s in log]})
    js = _js(book, f"const x = {payload}; return suggestCalls(__book, x.state, x.log, 5);")
    assert js == py


@pytest.mark.parametrize("start,outcome,gain", [
    (DriveState(), Outcome.GAIN, 4), (DriveState(yard_line=15), Outcome.GAIN, 10),
    (DriveState(yard_line=6), Outcome.GAIN, 6), (DriveState(yard_line=97), Outcome.SACK, 5),
    (DriveState(down=4, distance=2), Outcome.GAIN, 1), (DriveState(), Outcome.PENALTY_US, 5),
    (DriveState(down=2, distance=4), Outcome.PENALTY_THEM, 5), (DriveState(), Outcome.TURNOVER, 0),
    (DriveState(down=3, distance=8), Outcome.PENALTY_THEM, 5), (DriveState(), Outcome.INCOMPLETE, 0),
])
def test_advance_and_success_match_python(start, outcome, gain):
    t = GamePlan().thresholds
    payload = json.dumps(start.model_dump(mode="json"))
    js = _js(_book(), f"const s = {payload}; return [advanceState(s, {json.dumps(outcome.value)}, {gain}),"
                      f" isSuccess(s, {json.dumps(outcome.value)}, {gain}, {json.dumps(list(t))})];")
    assert js[0] == P.advance(start, outcome, gain).model_dump(mode="json")
    assert js[1] == P.is_success(start, outcome, gain, t)


def test_drive_cards_and_the_alternation_warning_match_python():
    book = _book()
    js = _js(book, "return driveCards(__book).map(([t, s, list]) => [t, list.map(x => [x.play, x.points])]);")
    assert js == [[t, [[x.play, x.points] for x in s]] for t, _, s in P.drive_cards(book)]


def test_sha256_hmac_and_key_stretching_match_python():
    import hashlib
    import hmac
    msgs = ["", "abc", "a" * 55, "a" * 56, "a" * 64, "a" * 200, "Wk 3 Central|1st half|wristband|0"]
    js = _js(_book(), f"return {json.dumps(msgs)}.map(m => [hex(sha256(utf8(m))), hex(hmacSha256(utf8('key'), utf8(m)))])"
                      ".concat([[hex(keyBytes('k7qm-2xra 9fpd-hw4c'))]]);")
    for (h, mac), m in zip(js, msgs):
        assert h == hashlib.sha256(m.encode()).hexdigest()
        assert mac == hmac.new(b"key", m.encode(), hashlib.sha256).hexdigest()
    assert js[-1][0] == K.key_bytes("K7QM2XRA9FPDHW4C").hex()


@pytest.mark.parametrize("calls", [
    CallSystem(),
    CallSystem(rotate="quarter", extra_codes=4, top_calls=9, dead_codes=20),
    CallSystem(rotate="game", digits=3, extra_codes=0, dead_codes=0),
    CallSystem(code_style="letter", dummy_digit="key", signals=3, rotate="quarter"),
    CallSystem(code_style="key", digits=3, dummy_digit="middle", signals=2),
])
def test_wristbands_are_identical_in_both(calls):
    book = _book(calls=calls)
    py = K.wristband(book, "k7qm-2xra 9fpd-hw4c", "Wk 3 Central").model_dump(mode="json")
    js = _js(book, "return wristbandCodes(__book, 'k7qm-2xra 9fpd-hw4c', 'Wk 3 Central');")
    assert js == py


@pytest.mark.parametrize("calls", [
    CallSystem(methods=["words"]),
    CallSystem(methods=["words"], rotate="quarter", dummy_words=9, burned_words=["Tiger", "rocket"]),
    CallSystem(methods=["words"], word_list="cities", live_signal="numbers"),
    CallSystem(methods=["words"], word_list="own", live_signal="own", dummy_words=2,
               own_words=["Ranger", "Hawk", "Maple", "Onyx", "Quartz", "Sierra", "Tundra", "Umber",
                          "Vortex", "Willow", " hawk ", "Zinc", "Yarrow"],
               own_live=["Alpha", "Bravo", "alpha", "Charlie"]),
    CallSystem(methods=["words"], word_list="things", live_signal="order", signals=3, rotate="quarter"),
])
def test_line_calls_are_identical_in_both(calls):
    plays = [tag(p, word="Ranger") if p.id == "stick" else p for p in _book().plays]
    book = Playbook(name="Wk 3", plays=plays, game_plan=GamePlan(calls=calls))
    py = K.line_calls(book, "k7qm-2xra 9fpd-hw4c", "Wk 3 Central").model_dump(mode="json")
    js = _js(book, "return lineCalls(__book, 'Wk 3 Central', keyBytes('k7qm-2xra 9fpd-hw4c'));")
    assert js == py


@pytest.mark.parametrize("calls", [
    CallSystem(methods=["boards"]),
    CallSystem(methods=["boards"], board_cells=1),
    CallSystem(methods=["boards"], board_cells=2, rotate="quarter", dummy_boards=6),
    CallSystem(methods=["boards"], rotate="quarter", boards_by="series", dummy_boards=5),
    CallSystem(methods=["boards"], board_cells="key"),
])
def test_boards_are_identical_in_both(calls):
    book = _book(calls=calls)
    py = K.boards(book, "k7qm-2xra 9fpd-hw4c", "Wk 3 Central").model_dump(mode="json")
    js = _js(book, "return boardSymbols(__book, 'Wk 3 Central', keyBytes('k7qm-2xra 9fpd-hw4c'));")
    assert js == py
