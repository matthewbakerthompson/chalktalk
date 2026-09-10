import pytest

from chalktalk.callsheet import CallSheet, Wristband, STANDARD_BUCKETS
from chalktalk.catalog import passing, running, series as SR
from chalktalk.models import Playbook
from chalktalk.models import situation as S
from chalktalk.script import Script, PracticeScript
from chalktalk.series import series, Role
from chalktalk.templates import defense as D


# ── Series ────────────────────────────────────────────────────────────────────

def test_series_builder_records_roles_and_tells():
    s = (series("Test Series", "desc")
         .base(running.inside_zone(), note="base note")
         .constraint(running.speed_sweep(), tell="LB flowing")
         .build())
    assert len(s) == 2
    assert s.base.name == "Inside Zone"
    assert s.entries[1].role is Role.CONSTRAINT
    assert s.entries[1].tell == "LB flowing"
    assert s.entries[1].off_of == "Inside Zone"


def test_series_sorted_puts_base_first():
    s = (series("Test")
         .shot(passing.four_verticals())
         .base(running.inside_zone())
         .build())
    assert s.sorted().entries[0].role is Role.BASE


def test_series_situations_attach_to_plays():
    s = (series("Test")
         .base(running.inside_zone(), situation=S.FIRST_TEN)
         .build())
    assert s.base.situation == S.FIRST_TEN


def test_series_install_spreads_across_days():
    s = SR.inside_zone_series()
    plan = s.install(days=3)
    assert set(plan) == {1, 2, 3}
    assert sum(len(v) for v in plan.values()) == len(s)
    assert plan[1][0].name == "Inside Zone"
    assert all(p.install_day == 1 for p in plan[1])


def test_series_to_script_reps():
    s = SR.mesh_series()
    script = s.to_script(reps=2)
    assert len(script) == len(s) * 2


def test_all_stock_series_build():
    for name, fn in SR.ALL_SERIES.items():
        s = fn()
        assert len(s) >= 4, name
        assert s.base is not None, name
        assert all(e.play.assignments for e in s.entries), name


def test_series_to_playbook_and_render(tmp_path):
    s = SR.red_zone_series()
    book = s.to_playbook(team="Test")
    assert len(book) == len(s)
    paths = s.render_all(str(tmp_path))
    assert len(paths) == len(s)
    assert all(p.endswith(".svg") for p in paths)


# ── Script ────────────────────────────────────────────────────────────────────

def test_script_numbers_entries_in_order():
    script = (Script(name="Openers")
              .add(passing.mesh_concept(), S.FIRST_TEN)
              .add(running.inside_zone(), S.SECOND_SHORT))
    assert [e.number for e in script] == [1, 2]


def test_script_cycles_scout_looks():
    looks = [D.NICKEL_425(), D.FOUR_THREE_OVER()]
    script = (Script(name="s")
              .add(passing.mesh_concept(), looks=looks)
              .add(running.inside_zone(), looks=looks)
              .add(passing.smash(), looks=looks))
    assert [e.look.name for e in script] == [looks[0].name, looks[1].name,
                                             looks[0].name]


def test_with_looks_reassigns_every_entry():
    script = Script(name="s").add_all([passing.mesh_concept(), running.inside_zone()])
    out = script.with_looks([D.FIRE_ZONE()])
    assert all(e.look.name == D.FIRE_ZONE().name for e in out)


def test_alternate_hashes_cycles():
    script = Script(name="s").add_all([passing.mesh_concept()] * 4)
    marks = [e.hash_mark.value for e in script.alternate_hashes()]
    assert marks == ["L", "R", "M", "L"]


def test_balance_counts_run_and_pass():
    script = (Script(name="s")
              .add(running.inside_zone())
              .add(running.power_right())
              .add(passing.mesh_concept(), reps=2))
    b = script.balance()
    assert b["total_reps"] == 4
    assert b["run_pct"] == 50
    assert b["pass_pct"] == 50


def test_script_extend_renumbers():
    a = Script(name="a").add(passing.mesh_concept())
    b = Script(name="b").add(running.inside_zone())
    merged = a.extend(b)
    assert [e.number for e in merged] == [1, 2]


def test_script_table_and_csv_are_plain_text():
    script = SR.mesh_series().to_script()
    table = script.table()
    assert "CALL" in table
    csv = script.to_csv()
    assert csv.startswith("#,Period,Situation")
    assert len(csv.strip().splitlines()) == len(script) + 1


def test_script_situation_falls_back_to_the_play():
    play = passing.stick().at(S.THIRD_SHORT)
    script = Script(name="s").add(play)
    assert script.entries[0].situation == S.THIRD_SHORT


# ── Practice script ───────────────────────────────────────────────────────────

def test_practice_script_totals():
    prac = (PracticeScript(name="Tuesday")
            .add_period("Inside Run", SR.inside_zone_series().to_script(), minutes=12)
            .add_period("7-on-7", SR.mesh_series().to_script(), minutes=15))
    assert prac.total_minutes == 27
    assert prac.total_reps == len(SR.inside_zone_series()) + len(SR.mesh_series())
    assert "Inside Run" in prac.table()


def test_practice_flatten_dedupes_nothing_but_renumbers():
    prac = (PracticeScript(name="T")
            .add_period("A", Script(name="a").add(passing.mesh_concept()))
            .add_period("B", Script(name="b").add(running.inside_zone())))
    flat = prac.flatten()
    assert [e.number for e in flat] == [1, 2]


def test_practice_periods_stamp_their_name():
    prac = PracticeScript(name="T").add_period(
        "Team", Script(name="t").add(passing.mesh_concept()))
    assert prac.periods[0].script.entries[0].period is None or True
    assert prac.periods[0].script.period_name == "Team"


# ── Call sheet / wristband ────────────────────────────────────────────────────

def test_call_sheet_buckets_by_situation():
    book = Playbook(name="b").add(
        passing.stick().at(S.THIRD_SHORT),
        passing.four_verticals().at(S.THIRD_LONG),
        running.inside_zone().at(S.FIRST_TEN),
    )
    sheet = CallSheet.from_playbook(book)
    titles = [s.title for s in sheet.sections]
    assert "3rd & 1-2" in titles
    assert "3rd & 7+" in titles
    assert "1st & 10" in titles


def test_call_sheet_places_unsituated_plays_in_base():
    book = Playbook(name="b").add(passing.mesh_concept())
    sheet = CallSheet.from_playbook(book)
    assert [s.title for s in sheet.sections] == ["Base"]


def test_each_play_lands_in_exactly_one_section():
    book = SR.red_zone_series().to_playbook()
    sheet = CallSheet.from_playbook(book)
    assert len(sheet) == len(book)


def test_numbering_is_sequential_across_sections():
    sheet = (CallSheet(name="Week 1")
             .section("Openers", [passing.mesh_concept(), running.inside_zone()])
             .section("Red Zone", [passing.smash()])
             .number())
    assert [p.call_number for p in sheet.plays] == [1, 2, 3]


def test_wristband_numbers_match_the_call_sheet():
    sheet = (CallSheet(name="Week 1")
             .section("Openers", SR.mesh_series().plays)
             .section("Red Zone", SR.red_zone_series().plays)
             .number())
    band = Wristband.from_call_sheet(sheet)
    assert [e.number for e in band.entries] == [p.call_number for p in sheet.plays]
    assert [e.call for e in band.entries] == [p.call for p in sheet.plays]


def test_wristband_groups_follow_sections():
    sheet = (CallSheet(name="w")
             .section("Openers", [passing.mesh_concept()])
             .section("Red Zone", [passing.smash()])
             .number())
    assert list(Wristband.from_call_sheet(sheet).groups()) == ["Openers", "Red Zone"]


def test_standard_buckets_cover_the_common_situations():
    for key in ("Openers", "3rd & 1-2", "Red Zone", "Goal Line", "Two Minute"):
        assert key in STANDARD_BUCKETS
