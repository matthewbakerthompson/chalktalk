"""
Series sets: several series treated as one offense.
"""
import pytest

from chalktalk.callsheet import CallSheet
from chalktalk.catalog import series as SR, systems
from chalktalk.models import Playbook
from chalktalk.script import PracticeScript, Script
from chalktalk.series import Role, Series, SeriesSet, series, series_set
from chalktalk.templates import defense as D


def _small_set() -> SeriesSet:
    return (
        series_set("Test System", "two families")
        .add(SR.inside_zone_series(), install_week=1, priority=0)
        .add(SR.mesh_series(), install_week=2, priority=0)
        .team("Test HS", 2026)
        .build()
    )


# ── Building ──────────────────────────────────────────────────────────────────

def test_a_set_holds_its_series():
    s = _small_set()
    assert len(s) == 2
    assert [x.name for x in s.series] == ["Inside Zone Series", "Mesh Series"]
    assert s.team == "Test HS" and s.season == 2026


def test_plays_roll_up_from_every_series():
    s = _small_set()
    assert len(s.plays) == len(SR.inside_zone_series()) + len(SR.mesh_series())


def test_bases_are_the_base_play_of_each_series():
    names = [p.name for p in _small_set().bases]
    assert names == ["Inside Zone", "Mesh Concept"]


def test_get_finds_a_series_by_name_or_substring():
    s = _small_set()
    assert s.get("Mesh Series") is not None
    assert s.get("mesh") is not None
    assert s.get("nonexistent") is None


def test_ordering_respects_week_then_priority():
    s = (series_set("S")
         .add(SR.mesh_series(), install_week=2, priority=0)
         .add(SR.red_zone_series(), install_week=1, priority=1)
         .add(SR.inside_zone_series(), install_week=1, priority=0)
         .build())
    assert [e.series.name for e in s.ordered()] == [
        "Inside Zone Series", "Red Zone Series", "Mesh Series"]


def test_by_week_groups_them():
    weeks = _small_set().by_week()
    assert set(weeks) == {1, 2}
    assert weeks[1][0].name == "Inside Zone Series"


# ── Installing ────────────────────────────────────────────────────────────────

def test_install_puts_every_base_before_any_constraint():
    """A constraint installed before the play it constrains teaches nothing."""
    s = (series_set("S")
         .add(SR.inside_zone_series(), install_week=1)
         .add(SR.mesh_series(), install_week=1)
         .build())
    week_one = s.install()[1]
    bases = {p.name for p in s.bases}
    first_two = {p.name for p in week_one[:2]}
    assert first_two == bases


def test_install_stamps_the_week_on_each_play():
    for week, plays in _small_set().install().items():
        assert all(p.install_day == week for p in plays)


def test_install_covers_every_play_once():
    s = _small_set()
    planned = [p.name for plays in s.install().values() for p in plays]
    assert len(planned) == len(s.plays)


def test_asking_for_more_weeks_gives_empty_ones_to_fill():
    plan = _small_set().install(weeks=5)
    assert set(plan) == {1, 2, 3, 4, 5}
    assert plan[4] == [] and plan[5] == []


# ── Repping ───────────────────────────────────────────────────────────────────

def test_the_script_covers_the_whole_set_and_renumbers():
    s = _small_set()
    script = s.to_script()
    assert isinstance(script, Script)
    assert len(script) == len(s.plays)
    assert [e.number for e in script] == list(range(1, len(s.plays) + 1))


def test_a_script_can_be_limited_to_one_week():
    s = _small_set()
    assert len(s.to_script(week=1)) == len(SR.inside_zone_series())


def test_reps_multiply_the_script():
    s = _small_set()
    assert len(s.to_script(reps=2)) == len(s.plays) * 2


def test_practice_gets_one_period_per_series():
    practice = _small_set().to_practice(minutes=10)
    assert isinstance(practice, PracticeScript)
    assert [p.name for p in practice.periods] == [
        "Inside Zone Series", "Mesh Series"]
    assert practice.total_minutes == 20


def test_scout_looks_carry_into_the_set_script():
    looks = [D.NICKEL_425(), D.FOUR_THREE_OVER()]
    script = _small_set().to_script(looks=looks)
    assert all(e.look is not None for e in script)


# ── Printing ──────────────────────────────────────────────────────────────────

def test_the_playbook_carries_the_teams_details():
    book = _small_set().to_playbook()
    assert isinstance(book, Playbook)
    assert book.team == "Test HS" and book.season == 2026
    assert len(book) == len(_small_set().plays)


def test_the_call_sheet_is_numbered_and_bucketed():
    sheet = _small_set().to_call_sheet()
    assert isinstance(sheet, CallSheet)
    assert len(sheet) == len(_small_set().plays)
    assert all(p.call_number for p in sheet.plays)


def test_render_all_writes_a_folder_per_series(tmp_path):
    paths = _small_set().render_all(str(tmp_path))
    assert len(paths) == len(_small_set().plays)
    assert len({p.rsplit("\\", 1)[0].rsplit("/", 1)[0] for p in paths}) >= 2


def test_the_install_book_is_a_full_document():
    html = _small_set().to_html()
    assert html.startswith("<!doctype html>")
    assert "Week 1" in html and "Inside Zone Series" in html


def test_a_set_round_trips_through_json(tmp_path):
    s = _small_set()
    path = tmp_path / "system.json"
    s.save(str(path))
    assert SeriesSet.load(str(path)) == s


# ── Checking it ───────────────────────────────────────────────────────────────

def test_balance_counts_the_whole_set():
    b = _small_set().balance()
    assert b["series"] == 2
    assert b["plays"] == len(_small_set().plays)
    assert b["run_pct"] + b["pass_pct"] <= 100
    assert b["roles"]["base"] == 2


def test_answers_per_base_counts_the_constraints():
    b = _small_set().balance()
    assert b["answers_per_base"]["Inside Zone Series"] == \
        len(SR.inside_zone_series()) - 1


def test_gaps_flags_a_base_with_no_answers():
    thin = (series_set("Thin")
            .add(series("Lonely").base(SR.inside_zone_series().base).build())
            .build())
    notes = thin.gaps()
    assert any("only 0 answer" in n for n in notes)


def test_gaps_flags_a_series_with_nothing_over_the_top():
    only_runs = (series_set("Ground")
                 .add(series("Grind")
                      .base(SR.inside_zone_series().base)
                      .constraint(SR.inside_zone_series().plays[1])
                      .constraint(SR.inside_zone_series().plays[2])
                      .build())
                 .build())
    assert any("over the top" in n for n in only_runs.gaps())


def test_gaps_flags_a_one_sided_set():
    notes = SeriesSet(
        name="All Pass",
        entries=[{"series": SR.mesh_series()}, {"series": SR.two_minute_series()}],
    ).gaps()
    assert any("% run" in n for n in notes)


def test_a_healthy_series_does_not_get_flagged_for_shots():
    healthy = series_set("Healthy").add(SR.inside_zone_series()).build()
    assert not any("over the top" in n for n in healthy.gaps())


def test_describe_shows_weeks_and_gaps():
    text = _small_set().describe()
    assert "Week 1" in text and "Week 2" in text
    assert "series" in text


# ── Stock systems ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", sorted(systems.ALL_SYSTEMS))
def test_every_stock_system_builds(name):
    s = systems.ALL_SYSTEMS[name]()
    assert len(s) >= 4
    assert s.plays
    assert s.describe()


@pytest.mark.parametrize("name", sorted(systems.ALL_SYSTEMS))
def test_every_stock_system_installs_bases_first(name):
    s = systems.ALL_SYSTEMS[name]()
    for week, plays in s.install().items():
        week_series = s.by_week()[week]
        bases = {x.base.name for x in week_series if x.base}
        assert {p.name for p in plays[:len(bases)]} == bases, (name, week)


@pytest.mark.parametrize("name", sorted(systems.ALL_SYSTEMS))
def test_every_stock_system_can_be_repped_and_printed(name):
    s = systems.ALL_SYSTEMS[name]()
    assert len(s.to_script()) == len(s.plays)
    assert s.to_practice().periods
    assert s.to_call_sheet().plays
    assert s.to_html().startswith("<!doctype html>")


def test_the_systems_are_not_all_the_same():
    signatures = {name: tuple(sorted(x.name for x in fn().series))
                  for name, fn in systems.ALL_SYSTEMS.items()}
    assert len(set(signatures.values())) == len(signatures)


def test_a_pro_style_offense_runs_the_ball_more_than_a_spread():
    assert (systems.pro_style().balance()["run_pct"]
            > systems.spread_offense().balance()["run_pct"])


def test_the_cli_sees_every_system():
    from chalktalk.cli import _system_by_key
    for name in systems.ALL_SYSTEMS:
        assert _system_by_key(name) is not None
    with pytest.raises(SystemExit):
        _system_by_key("no_such_system")
