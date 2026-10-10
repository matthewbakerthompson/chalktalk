"""
Every sheet a staff prints comes from `chalktalk.paper`, for Python users and
for the designer alike (it asks `chalk design` for them).
"""
import pytest

from chalktalk import paper, planner
from chalktalk.callsheet import CallSheet, Wristband
from chalktalk.catalog import passing, running, screens
from chalktalk.models import CallSystem, DriveState, Outcome, Playbook, Snap
from chalktalk.models import situation as S
from chalktalk.script import Script

KEY = "K7QM-2XRA-9FPD-HW4C"


def _book(methods=("wristband", "words", "boards"), log=True) -> Playbook:
    plays = [running.inside_zone(), running.power_right(), passing.mesh_concept(),
             passing.four_verticals(), screens.rb_slip(), running.buck_sweep()]
    plays[0] = plays[0].at(S.Situation(down=1, distance=10, yard_line=75))
    plays[2] = plays[2].at(S.Situation(down=3, distance=8, yard_line=40))
    plays[1] = plays[1].model_copy(update={"install_day": 1, "favorite": True})
    plays[3] = plays[3].model_copy(update={"install_day": 2, "alerts": ["Alert fade vs press"]})
    book = planner.draft(Playbook(name="Week 3", team="Owls", season=2026, plays=plays)).book
    plan = book.game_plan.model_copy(update={"name": "Wk 3 vs Central",
                                              "calls": CallSystem(methods=list(methods))})
    if log:
        state, snaps = DriveState(), []
        for i, outcome in enumerate([Outcome.GAIN, Outcome.INCOMPLETE, Outcome.GAIN, Outcome.GAIN]):
            p = plays[i]
            snaps.append(Snap(before=state, play=book.plays[i].id, call=p.call, outcome=outcome,
                              gain=6 if outcome == Outcome.GAIN else 0))
            state = planner.advance(state, outcome, snaps[-1].gain)
        plan = plan.model_copy(update={"log": snaps})
    return book.model_copy(update={"game_plan": plan})


@pytest.mark.parametrize("kind", list(paper.KINDS))
def test_every_kind_prints_a_whole_page(kind):
    html = paper.render(kind, _book(), key=KEY)
    assert html.startswith("<!doctype html>") and html.rstrip().endswith("</html>")
    assert "generated with chalktalk" in html
    assert KEY not in html and KEY.replace("-", "") not in html


def test_the_call_sheet_numbers_in_its_own_order():
    book = _book()
    sheet = paper.call_sheet(book)
    numbers = [p.call_number for p in sheet.plays]
    assert numbers == list(range(1, len(book.plays) + 1))
    assert [p.id for p in sheet.plays] == paper.call_order(book)


def test_numbers_the_book_already_has_are_kept():
    book = _book()
    plays = list(book.plays)
    plays[0], plays[3] = plays[0].numbered(40), plays[3].numbered(7)
    book = book.model_copy(update={"plays": plays})
    sheet = paper.call_sheet(book)
    assert {p.name: p.call_number for p in sheet.plays}[plays[0].name] == 40
    html = paper.render("callsheet", book)
    assert '<span class="num">40</span>' in html and '<span class="num">•</span>' in html


def test_the_wristband_carries_the_call_sheets_numbers():
    book = _book()
    band = Wristband.from_call_sheet(paper.call_sheet(book))
    html = paper.render("wristband", book, size="teen", copies=2)
    assert "Teen 5 x 2.75 in" in html
    inserts = html.count('class="insert"')
    assert inserts > 0 and inserts % 2 == 0          # two copies of every insert
    assert [e.number for e in band.entries] == list(range(1, len(book.plays) + 1))


def test_the_script_says_its_balance():
    book = _book()
    b = Script(name=book.name).add_all(book.plays, reps=2).balance()
    summary, hint = paper.info("script", book, reps=2)
    assert summary == f"{b['total_reps']} reps · {b['run_pct']}% run · {b['pass_pct']}% pass"
    assert hint == ""


def test_the_install_book_goes_day_by_day():
    html = paper.render("install", _book())
    assert html.index("Day 1") < html.index("Day 2") < html.index("Not scheduled")
    assert paper.info("install", _book())[0] == "2 days · 4 not scheduled"


def test_the_playbook_follows_the_layers_and_the_hashes():
    book = _book()
    assert "url(#arr-route)" in paper.render("playbook", book)
    assert "url(#arr-route)" not in paper.render("playbook", book, hide=["routes"])
    assert paper.render("playbook", book, level="hs") != paper.render("playbook", book, level="nfl")


def test_coded_sheets_print_the_fingerprint_not_the_key():
    book = _book()
    summary, _ = paper.info("gameplan", book, key=KEY)
    fingerprint = summary.split("fingerprint ")[1]
    for kind in ("gameplan", "qbcard", "boards"):
        assert f"Fingerprint {fingerprint}" in paper.render(kind, book, key=KEY)


def test_coded_sheets_say_what_they_are_missing():
    with pytest.raises(ValueError, match="Set a key first"):
        paper.render("qbcard", _book())
    with pytest.raises(ValueError, match="Turn on sign boards first"):
        paper.render("boards", _book(methods=("wristband",)), key=KEY)
    with pytest.raises(ValueError, match="Choose wristband numbers or line calls first"):
        paper.render("qbcard", _book(methods=("boards",)), key=KEY)
    assert "Set a key" in paper.info("gameplan", _book())[1]
    assert "Turn on sign boards" in paper.info("boards", _book(methods=("words",)))[1]


def test_the_hints_point_at_what_to_set():
    bare = Playbook(name="Bare", plays=[passing.mesh_concept(), running.inside_zone()])
    assert "every call lands in Base" in paper.info("callsheet", bare)[1]
    assert "No play has an install day" in paper.info("install", bare)[1]
    assert paper.info("scout", bare) == ("nothing logged yet",
                                         "Log a drive in the Game panel and the halftime sheet fills itself.")
    assert paper.info("scout", _book())[0] == "3 of 4 snaps on schedule"


def test_an_unknown_sheet_is_refused():
    with pytest.raises(ValueError, match="Nothing called"):
        paper.render("menu", _book())


def test_the_sheets_python_already_printed_are_unchanged():
    """Call sheet and script through `paper` are the same pages their own renderers make."""
    from chalktalk.renderer import sheets
    book = _book()
    assert paper.render("callsheet", book, columns=3) == sheets.call_sheet_html(
        CallSheet.from_playbook(book).number(), columns=3)
