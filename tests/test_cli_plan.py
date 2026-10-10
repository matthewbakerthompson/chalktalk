"""
The planner, the scout and every sheet, from the command line: the same
answers the designer shows, for a coach who'd rather type.
"""
import pytest

from chalktalk import cli, paper, planner
from chalktalk.catalog import passing, running, screens
from chalktalk.models import CallSystem, DriveState, Outcome, Playbook, Snap
from chalktalk.models import situation as S

KEY = "K7QM-2XRA-9FPD-HW4C"


def _book(methods=("wristband", "words"), log=False) -> Playbook:
    plays = [running.inside_zone(), running.power_right(), passing.mesh_concept(),
             passing.stick(), screens.rb_slip(), running.speed_sweep()]
    plays[2] = plays[2].at(S.Situation(down=3, distance=8))
    book = planner.draft(Playbook(name="Week 3", team="Owls", plays=plays)).book
    plan = book.game_plan.model_copy(update={"name": "Wk 3 vs Central",
                                              "calls": CallSystem(methods=list(methods))})
    if log:
        state, snaps = DriveState(), []
        for i, (outcome, gain) in enumerate([(Outcome.GAIN, 6), (Outcome.INCOMPLETE, 0), (Outcome.GAIN, 9)]):
            p = book.plays[i]
            snaps.append(Snap(before=state, play=p.id, call=p.call, outcome=outcome, gain=gain))
            state = planner.advance(state, outcome, gain)
        plan = plan.model_copy(update={"log": snaps})
    return book.model_copy(update={"game_plan": plan})


@pytest.fixture
def saved(tmp_path):
    def save(book, name="week3.json"):
        path = tmp_path / name
        book.save(str(path))
        return path
    return save


def _run(capsys, *argv) -> str:
    assert cli.main([str(a) for a in argv]) == 0
    out = capsys.readouterr().out
    assert out.isascii(), "terminal output stays ASCII"
    return out


def test_next_reads_like_the_game_panel(saved, capsys):
    book = _book()
    path = saved(book)
    out = _run(capsys, "next", path, "--down", 3, "--distance", 8, "--at", "opp 40")
    state = DriveState(down=3, distance=8, yard_line=40)
    picks = planner.suggest(book, state, k=3)
    lines = out.splitlines()
    assert lines[0] == state.label() == "3rd & 8, Opp 40"
    assert lines[1].startswith(f" 1. {picks[0].call}  ({picks[0].points:+d})")
    for r in picks[0].reasons:
        assert f"{r.points:+d}  {r.text}" in out


def test_next_can_leave_the_game_log_out(saved, capsys):
    book = _book(log=True)
    path = saved(book)
    fresh = _run(capsys, "next", path, "--fresh", "-k", 5)
    picks = planner.suggest(book, DriveState(), [], k=5)
    assert [line.split(". ", 1)[1].rsplit("  (", 1)[0] for line in fresh.splitlines()
            if line[:3].strip().rstrip(".").isdigit()] == [s.call for s in picks]


@pytest.mark.parametrize("spot,yards", [("own 25", 75), ("opp 32", 32), ("OWN 50", 50), ("8", 8), ("opp 1", 1)])
def test_the_spot_reads_like_a_coach_says_it(spot, yards):
    assert cli._spot(spot) == yards


@pytest.mark.parametrize("spot", ["midfield", "own 60", "0", "opp", "100"])
def test_a_spot_that_isnt_one_is_refused(spot):
    with pytest.raises(SystemExit, match="--at takes"):
        cli._spot(spot)


def test_scout_says_the_half(saved, capsys):
    path = saved(_book(log=True))
    out = _run(capsys, "scout", path)
    assert out.startswith("Wk 3 vs Central: 2 of 3 on schedule")
    assert "\nBy down\n  1st down   1 of 1 on schedule, 6 a call\n" in out
    assert "\nLeft on the sheet\n" in out
    empty = _run(capsys, "scout", saved(_book(), "empty.json"))
    assert "nothing logged yet" in empty


def test_check_says_what_a_coordinator_would(saved, capsys):
    book = _book()
    out = _run(capsys, "check", saved(book))
    notes = planner.check(book)
    assert out.splitlines()[0] == (f"Week 3: {len(notes)} to look at" if notes else "Week 3: nothing to flag")
    for note in notes:
        assert f"  - {note}" in out


def test_draft_shows_its_work_and_saves_only_when_told(saved, capsys, tmp_path):
    bare = Playbook(name="Bare", plays=[running.inside_zone(), running.speed_sweep(), passing.mesh_concept()])
    path = saved(bare, "bare.json")
    out = _run(capsys, "draft", path)
    assert "not saved" in out and Playbook.load(str(path)).plays[0].series is None
    target = tmp_path / "drafted.json"
    out = _run(capsys, "draft", path, "-o", target)
    assert Playbook.load(str(target)).plays[0].series == planner.draft(bare).book.plays[0].series


def test_book_prints_any_sheet(saved, capsys, tmp_path):
    path = saved(_book())
    out = _run(capsys, "book", path, "--sheet", "callsheet", "--columns", 3)
    page = (tmp_path / "week3-callsheet.html").read_text(encoding="utf-8")
    assert "column-count:3" in page and out.startswith("Saved: ")
    target = tmp_path / "band.html"
    _run(capsys, "book", path, "--sheet", "wristband", "--size", "teen", "--copies", 2, "-o", target)
    assert "Teen 5 x 2.75 in" in target.read_text(encoding="utf-8")


def test_coded_sheets_take_the_key_and_never_print_it(saved, capsys, tmp_path, monkeypatch):
    path = saved(_book())
    with pytest.raises(SystemExit, match="Set a key first. Pass --key, or set CHALKTALK_KEY."):
        cli.main(["book", str(path), "--sheet", "qbcard"])
    _run(capsys, "book", path, "--sheet", "qbcard", "--key", KEY, "--size", "teen")
    page = (tmp_path / "week3-qbcard.html").read_text(encoding="utf-8")
    fingerprint = paper.info("qbcard", _book(), key=KEY)[0].split("fingerprint ")[1]
    assert f"Fingerprint {fingerprint}" in page and KEY not in page
    monkeypatch.setenv("CHALKTALK_KEY", KEY)
    out = _run(capsys, "book", path, "--sheet", "gameplan")
    assert f"fingerprint {fingerprint}" in out


def test_a_file_that_isnt_a_book_says_so(tmp_path):
    bad = tmp_path / "notes.json"
    bad.write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(SystemExit, match="isn't a play or a playbook"):
        cli.main(["check", str(bad)])
    with pytest.raises(SystemExit, match="no such file"):
        cli.main(["scout", str(tmp_path / "missing.json")])
