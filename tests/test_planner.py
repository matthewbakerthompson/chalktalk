"""
The drive planner: the arithmetic of a drive, where plays sit in the plan, the
rules behind every suggestion, and the coded wristband.
"""
import json
from collections import Counter

import pytest

from chalktalk import codes as K
from chalktalk import planner as P
from chalktalk.catalog import all_plays, passing, running
from chalktalk.difficulty import difficulty
from chalktalk.models import (CallSystem, DriveState, GamePlan, Mode, Outcome, Playbook,
                              Role, Snap)
from chalktalk.models import situation as S
from chalktalk.models.field import Level
from chalktalk.models.situation import Hash


def tag(play, **kw):
    return play.model_copy(update=kw)


def book(**plan) -> Playbook:
    return Playbook(name="Wk 3", game_plan=GamePlan(**plan) if plan else None, plays=[
        tag(running.inside_zone(), series="Zone", role=Role.BASE,
            situation=S.Situation(label="Openers")),
        tag(passing.mesh_concept(), situation=S.Situation(label="Openers")),
        tag(running.speed_sweep(), series="Zone", role=Role.CONSTRAINT,
            tell="Backside LB flowing hard"),
        tag(passing.y_cross(), series="Zone", role=Role.PLAY_ACTION),
        tag(running.power_right(), situation=S.Situation(down=3, distance=2)),
        tag(passing.four_verticals(), series="Zone", role=Role.SHOT,
            situation=S.Situation(down=3, distance=9)),
        tag(passing.stick(), situation=S.Situation(down=3, distance=5, yard_line=15)),
    ]).with_ids()


def snap(state, play_id, gain=0, outcome=Outcome.GAIN, tells=()):
    return Snap(before=state, play=play_id, call=play_id, outcome=outcome, gain=gain,
                tells=list(tells))


# ── the arithmetic ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("start,outcome,gain,expect", [
    (dict(), Outcome.GAIN, 4, dict(down=2, distance=6, yard_line=71)),
    (dict(), Outcome.GAIN, 12, dict(down=1, distance=10, yard_line=63)),
    (dict(yard_line=15), Outcome.GAIN, 10, dict(down=1, distance=5, yard_line=5)),      # goal to go
    (dict(yard_line=6), Outcome.GAIN, 6, dict(over="touchdown")),
    (dict(yard_line=97), Outcome.SACK, 5, dict(over="safety")),
    (dict(down=4, distance=2), Outcome.GAIN, 1, dict(over="downs")),
    (dict(), Outcome.INCOMPLETE, 0, dict(down=2, distance=10, yard_line=75)),
    (dict(), Outcome.SACK, 7, dict(down=2, distance=17, yard_line=82)),
    (dict(), Outcome.PENALTY_US, 5, dict(down=1, distance=15, yard_line=80)),
    (dict(down=2, distance=4), Outcome.PENALTY_THEM, 5, dict(down=1, distance=10, yard_line=70)),
    (dict(down=3, distance=8), Outcome.PENALTY_THEM, 5, dict(down=3, distance=3, yard_line=70)),
    (dict(), Outcome.TURNOVER, 0, dict(over="turnover")),
])
def test_advance(start, outcome, gain, expect):
    after = P.advance(DriveState(**start), outcome, gain)
    for key, value in expect.items():
        assert getattr(after, key) == value, (key, after)
    assert after.snap == 1


def test_a_finished_drive_stays_finished():
    over = P.advance(DriveState(yard_line=3), Outcome.GAIN, 5)
    assert P.advance(over, Outcome.GAIN, 5) == over


@pytest.mark.parametrize("level,down,distance,gain,ok", [
    (Level.NFL, 1, 10, 4, False),     # 45% of 10 needs 5 whole yards
    (Level.NFL, 1, 10, 5, True),
    (Level.NCAA, 1, 10, 4, False),    # 50%
    (Level.NCAA, 2, 10, 6, False),    # 70%
    (Level.NCAA, 2, 10, 7, True),
    (Level.HS, 1, 10, 4, True),       # 4 yards on 1st & 10
    (Level.HS, 2, 6, 3, True),        # half the distance on 2nd
    (Level.HS, 2, 6, 2, False),
    (Level.HS, 3, 5, 4, False),       # all of it on third down
    (Level.HS, 3, 5, 5, True),
])
def test_success_scales_with_level(level, down, distance, gain, ok):
    plan = GamePlan(level=level)
    before = DriveState(down=down, distance=distance)
    assert P.is_success(before, Outcome.GAIN, gain, plan.thresholds) is ok


def test_success_edge_cases():
    t = GamePlan().thresholds
    assert P.is_success(DriveState(yard_line=3), Outcome.GAIN, 3, t) is True    # touchdown
    assert P.is_success(DriveState(), Outcome.SACK, 5, t) is False
    assert P.is_success(DriveState(), Outcome.PENALTY_THEM, 5, t) is None


# ── the plan, read from the book ─────────────────────────────────────────────

def test_plays_land_in_the_sections_their_situation_says():
    placed = {section.title: ids for section, ids in P.sections(book())}
    assert placed["3rd & 1-3"] == ["power-right"]
    assert placed["3rd & 7+"] == ["four-verticals"]
    assert placed["3rd & 4-6"] == ["stick"] and "stick" in placed["Red zone"]  # both
    assert set(placed["Base"]) == {"inside-zone", "mesh-concept", "speed-sweep", "y-cross"}
    assert P.openers(book()) == ["inside-zone", "mesh-concept"]


def test_every_play_gets_one_number():
    nums = P.numbers(book())
    assert sorted(nums.values()) == list(range(1, len(book().plays) + 1))
    assert list(nums)[:2] == ["inside-zone", "mesh-concept"]      # openers first


def test_a_plan_can_carry_its_own_sections():
    from chalktalk.models import PlanSection, When
    custom = book(sections=[PlanSection(title="Shots", when=When(downs=[1]),
                                         plays=["four-verticals", "missing"])])
    assert P.sections(custom) == [(custom.game_plan.sections[0], ["four-verticals"])]


def test_check_points_out_what_a_coordinator_would():
    b = book(execution=1)
    b = b.model_copy(update={"plays": b.plays + [
        tag(passing.smash(), id="smash", role=Role.CONSTRAINT),
        tag(running.counter_trey(), id="counter", series="Gap", role=Role.PLAY_ACTION),
    ]})
    notes = " ".join(P.check(b))
    assert "belongs to no series" in notes
    assert "\"Gap\", but that series has no base play" in notes
    lone = Playbook(name="x", plays=[passing.mesh_concept()]).with_ids()
    assert any("opening script" in n for n in P.check(lone))


# ── suggestions ──────────────────────────────────────────────────────────────

def test_the_script_leads_until_a_special_situation():
    first = P.suggest(book(), DriveState())
    assert first[0].play == "inside-zone"
    assert "Next on the opening script (1 of 2)" in [r.text for r in first[0].reasons]
    third = P.suggest(book(), DriveState(down=3, distance=2))
    assert all("opening script" not in r.text for s in third for r in s.reasons)


def test_a_constraint_waits_for_its_base_and_rises_on_its_tell():
    start = DriveState()
    held = next(s for s in P.suggest(book(), DriveState(), k=10) if s.play == "speed-sweep")
    assert held.points < 0 and "Hold" in held.reasons[0].text
    log = [snap(start, "inside-zone", 4, tells=["Backside LB flowing hard"])]
    after = P.advance(start, Outcome.GAIN, 4)
    lifted = next(s for s in P.suggest(book(), after, log, k=10) if s.play == "speed-sweep")
    texts = [r.text for r in lifted.reasons]
    assert "Inside Zone shown 1x; this is its constraint" in texts
    assert any(t.startswith("They showed it: Backside LB flowing hard") for t in texts)


def test_a_trick_is_once_a_game():
    b = book()
    b = b.model_copy(update={"plays": b.plays + [
        tag(passing.smash(), id="trick", series="Zone", role=Role.TRICK)]})
    start = DriveState()
    log = [snap(start, "inside-zone", 3), snap(start, "inside-zone", 3), snap(start, "trick", 20)]
    assert "trick" not in [s.play for s in P.suggest(b, DriveState(yard_line=40), log, k=20)]


def test_the_same_call_twice_is_marked_down_and_a_winner_comes_back():
    start = DriveState()
    just = P.suggest(book(), DriveState(yard_line=40), [snap(start, "mesh-concept", 12)], k=10)
    mesh = next(s for s in just if s.play == "mesh-concept")
    assert any(r.text == "Just called" for r in mesh.reasons)
    log = [snap(start, "mesh-concept", 12), snap(start, "inside-zone", 3),
           snap(start, "inside-zone", 3)]
    later = next(s for s in P.suggest(book(), DriveState(yard_line=40), log, k=10)
                 if s.play == "mesh-concept")
    assert any(r.text.startswith("Worked earlier: +12") for r in later.reasons)


def test_plays_above_the_teams_level_are_marked_down():
    hard = tag(passing.mesh_concept(), id="hard", difficulty=3)
    b = Playbook(name="x", plays=[hard, tag(running.inside_zone(), id="iz")],
                 game_plan=GamePlan(execution=1))
    ranked = P.suggest(b, DriveState(), k=2)
    assert ranked[-1].play == "hard"
    assert any("above your team's level" in r.text for r in ranked[-1].reasons)


def test_a_book_saved_without_ids_gets_them_on_load(tmp_path):
    old = book().model_dump(mode="json")
    for p in old["plays"]:
        p.pop("id")                                   # as saved before ids existed
    path = tmp_path / "old.json"
    path.write_text(json.dumps(old), encoding="utf-8")
    loaded = Playbook.load(str(path))
    assert all(p.id for p in loaded.plays)
    assert [p.id for p in loaded.plays] == [p.id for p in book().plays]
    top = P.suggest(loaded, DriveState(), k=1)[0]
    assert loaded.play(top.play) is not None
    assert K.wristband(loaded, "key", "g").plays == list(P.numbers(loaded))


def test_a_point_off_for_every_point_above_the_level():
    from chalktalk import adjustments as A
    orbit = running.speed_sweep().model_copy()      # jet named in the tags only
    rpo = next(p for n, p in all_plays().items() if n == "bubble").adjust(A.MOTION("RB", "orbit"))
    d = difficulty(rpo)
    assert (d.score, d.name) == (8, "Advanced")
    assert d.reasons[0] == "RB orbit motion (3)"
    for execution, off in ((1, 5), (2, 1), (3, 0)):
        b = Playbook(name="x", plays=[tag(rpo, id="rpo")], game_plan=GamePlan(execution=execution))
        penalty = [r for r in P.suggest(b, DriveState(), k=1)[0].reasons
                   if "above your team's level" in r.text]
        assert sum(r.points for r in penalty) == -off
    assert difficulty(orbit).reasons[0] == "jet motion (3)"


def test_a_tier_the_coach_sets_counts_as_repped():
    from chalktalk.difficulty import over_level
    hard = difficulty(tag(passing.mesh_concept(), difficulty=2))
    assert hard.coached and over_level(hard, 2) == 0
    assert over_level(hard, 1) >= 1


def test_the_catalog_is_mostly_basic_with_reads_and_motion_standard():
    from collections import Counter
    tiers = Counter(difficulty(p).name for p in all_plays().values())
    assert tiers["Advanced"] == 0 and tiers["Basic"] > tiers["Standard"] > 0
    assert difficulty(running.inside_zone()).name == "Basic"
    assert difficulty(running.speed_sweep()).name == "Standard"


def test_branches_follow_a_gain_and_no_gain():
    top = P.suggest(book(), DriveState())[0]
    assert [b.when for b in top.branches] == ["2nd & 4", "2nd & 10"]


def test_two_minute_marks_runs_down():
    ranked = P.suggest(book(), DriveState(yard_line=70, mode=Mode.TWO_MINUTE), k=10)
    zone = next(s for s in ranked if s.play == "inside-zone")
    assert any(r.text.startswith("Two-minute") for r in zone.reasons)


def test_suggestions_are_deterministic_and_json():
    a = P.suggest(book(), DriveState(hash_mark=Hash.LEFT))
    b = P.suggest(book(), DriveState(hash_mark=Hash.LEFT))
    assert a == b
    json.dumps([s.model_dump(mode="json") for s in a])


def test_drive_cards_cover_the_usual_starts():
    cards = P.drive_cards(book())
    assert [t for t, _, _ in cards][0] == "Drive starter · own 25"
    assert all(len(s) <= 3 for _, _, s in cards)


def test_the_alternation_warning():
    start = DriveState()
    log = []
    for i in range(4):
        log.append(snap(start, "inside-zone" if i % 2 == 0 else "mesh-concept", 0,
                        Outcome.GAIN if i % 2 == 0 else Outcome.INCOMPLETE))
    assert P.alternation_warning(book(), log)
    assert P.alternation_warning(book(), log[:2]) is None


def test_a_book_with_its_plan_round_trips():
    b = book(opponent="Central", calls=CallSystem(rotate="quarter"))
    again = Playbook.model_validate_json(b.model_dump_json())
    assert again == b and again.game_plan.calls.rotate == "quarter"
    assert again.plays[2].role is Role.CONSTRAINT


# ── the coded wristband ──────────────────────────────────────────────────────

def test_a_wristband_is_reproducible_from_the_key():
    b = book(calls=CallSystem(rotate="quarter"))
    one = K.wristband(b, "k7qm-2xra 9fpd-hw4c", "Wk 3 Central")
    two = K.wristband(b, "K7QM2XRA9FPDHW4C", "Wk 3 Central")
    assert one == two and len(one.cards) == 4
    assert one != K.wristband(b, "K7QM2XRA9FPDHW4D", "Wk 3 Central")
    assert one.fingerprint != K.wristband(b, "k7qm-2xra 9fpd-hw4c", "Wk 4 North").fingerprint


def test_every_play_has_a_code_and_the_top_calls_have_more():
    b = book(calls=CallSystem(top_calls=2, extra_codes=2, dead_codes=5))
    card = K.wristband(b, "key", "g").cards[0]
    counts = Counter(card.codes.values())
    assert set(counts) == {p.id for p in b.plays}
    assert counts["inside-zone"] == counts["mesh-concept"] == 3      # the two openers
    assert len(card.dead) == 5 and not set(card.dead) & set(card.codes)


def test_no_code_keeps_its_play_into_the_next_period():
    b = book(calls=CallSystem(rotate="quarter", top_calls=7, extra_codes=4, dead_codes=20))
    cards = K.wristband(b, "key", "g").cards
    for a, c in zip(cards, cards[1:]):
        assert not [code for code in c.codes if a.codes.get(code) == c.codes[code]]


def test_too_many_codes_for_two_digits_says_how_to_fix_it():
    many = Playbook(name="x", plays=[tag(passing.mesh_concept(), id=f"p{i}") for i in range(80)],
                    game_plan=GamePlan(calls=CallSystem(dead_codes=20)))
    with pytest.raises(ValueError, match="use 3 digits"):
        K.wristband(many, "key", "g")
    three = many.model_copy(update={"game_plan": GamePlan(calls=CallSystem(digits=3))})
    assert len(K.wristband(three, "key", "g").cards[0].codes) >= 80


def test_new_keys_are_random_and_readable():
    a, b = K.new_key(), K.new_key()
    assert a != b and len(a) == 19 and a.count("-") == 3
    assert set(a.replace("-", "")) <= set(K.KEY_ALPHABET)


def test_the_key_never_lands_in_the_book():
    b = book()
    K.wristband(b, "SECRETKEY123", "g")
    assert "SECRETKEY123" not in b.model_dump_json()


# ── line calls ───────────────────────────────────────────────────────────────

def test_line_calls_give_every_play_a_word_and_a_live_colour_each_period():
    b = book(calls=CallSystem(methods=["words"], rotate="quarter", dummy_words=5))
    sheet = K.line_calls(b, "key", "Wk 3")
    assert sorted(sheet.words.values()) == sorted(P.numbers(b))
    assert len(sheet.dead) == 5 and not set(sheet.dead) & set(sheet.words)
    assert list(sheet.live) == K.PERIODS["quarter"]
    colours = list(sheet.live.values())
    assert all(c in K.LIVE_COLORS for c in colours)
    assert all(a != c for a, c in zip(colours, colours[1:]))     # never live twice running
    assert K.line_calls(b, "key", "Wk 3") == sheet
    assert K.line_calls(b, "key", "Wk 4").words != sheet.words     # fresh words each game


def test_a_word_the_coach_sets_stays_and_burned_words_become_dummies():
    plays = [tag(p, word="Ranger") if p.id == "mesh-concept" else p for p in book().plays]
    b = Playbook(name="x", plays=plays, game_plan=GamePlan(calls=CallSystem(
        methods=["words"], dummy_words=0, burned_words=["Tiger", " rocket ", "ranger"])))
    sheet = K.line_calls(b, "key", "g")
    assert sheet.words["Ranger"] == "mesh-concept"
    assert "Tiger" not in sheet.words and "Rocket" not in sheet.words
    assert sheet.dead == ["rocket", "Tiger"]        # burned, and "ranger" is still in use


FOOTBALL_WORDS = {  # calls a team already says at the line, or a defense already names
    "mesh", "smash", "stick", "snag", "flood", "levels", "sail", "spacing", "curl", "drive",
    "cross", "dagger", "glance", "arrow", "bubble", "pop", "slant", "jet", "orbit", "veer",
    "power", "counter", "trap", "toss", "draw", "iso", "zone", "sweep", "boot", "naked",
    "waggle", "tunnel", "post", "corner", "fade", "wheel", "seam", "hitch", "screen",
    "tampa", "nickel", "dime", "cover", "blitz", "fire", "mike", "will", "sam", "omaha",
    "hut", "set", "go", "hike", "ready", "kill", "can", "check", "alert", "helmet"}


def test_word_lists_are_distinct_and_shoutable():
    everyone = [w for name, words in K.WORD_LISTS.items() if name != "mix" for w in words]
    assert len(everyone) == len({w.lower() for w in everyone}) == len(K.WORDS) == 144
    signals = {w.lower() for ws in K.LIVE_SIGNALS.values() for w in ws}
    for w in everyone:
        assert w.isascii() and w.isalpha(), w
        assert w.lower() not in signals | FOOTBALL_WORDS, w


# ── the format of a signal ───────────────────────────────────────────────────

def test_letter_codes_and_a_dummy_digit_each_period():
    b = book(calls=CallSystem(methods=["wristband"], code_style="letter", dummy_digit="key",
                              signals=3, rotate="quarter"))
    sheet = K.wristband(b, "key", "Wk 3")
    assert sheet.style == "letter"
    for card in sheet.cards:
        assert all(c[0] in K.LETTERS and c[1:].isdigit() for c in [*card.codes, *card.dead])
        assert list(card.codes) == sorted(card.codes)
    dummies = [c.dummy for c in sheet.cards]
    lives = [c.live for c in sheet.cards]
    assert set(dummies) <= {"first", "middle", "last"} and set(lives) <= {1, 2, 3}
    assert all(a != c for a, c in zip(dummies, dummies[1:]))    # never the same twice running
    assert all(a != c for a, c in zip(lives, lives[1:]))


def test_the_key_picks_the_code_style_per_game():
    b = book(calls=CallSystem(methods=["wristband"], code_style="key"))
    styles = {K.wristband(b, "key", f"Wk {n}").style for n in range(1, 13)}
    assert styles == {"number", "letter"}
    plain = K.wristband(book(), "key", "Wk 3").cards[0]
    assert plain.dummy is None and plain.live is None


def test_line_calls_from_the_teams_own_words_and_live_words():
    own = ["Ranger", "Hawk", "Maple", "Onyx", "Quartz", "Sierra", "Tundra", "Umber", "Vortex", "Willow"]
    b = book(calls=CallSystem(methods=["words"], word_list="own", own_words=own + [" hawk "],
                              live_signal="own", own_live=["Alpha", "Bravo", "Charlie"], dummy_words=1))
    sheet = K.line_calls(b, "key", "g")
    assert set(sheet.words) <= set(own) and len(sheet.dead) == 1
    assert set(sheet.live.values()) <= {"Alpha", "Bravo", "Charlie"}
    assert sheet.signals == ["Alpha", "Bravo", "Charlie"] and not sheet.order
    short = book(calls=CallSystem(methods=["words"], word_list="own", own_words=own[:3]))
    with pytest.raises(ValueError, match="Not enough words"):
        K.line_calls(short, "key", "g")
    with pytest.raises(ValueError, match="two live words"):
        K.line_calls(book(calls=CallSystem(methods=["words"], live_signal="own", own_live=["Alpha"])), "key", "g")


def test_line_calls_by_order_say_which_call_counts():
    b = book(calls=CallSystem(methods=["words"], live_signal="order", signals=3, rotate="quarter",
                              word_list="animals"))
    sheet = K.line_calls(b, "key", "g")
    assert not sheet.live and sheet.calls == 3 and list(sheet.order) == K.PERIODS["quarter"]
    turns = list(sheet.order.values())
    assert set(turns) <= {1, 2, 3} and all(a != c for a, c in zip(turns, turns[1:]))
    assert set(sheet.words) <= set(K.WORD_LISTS["animals"])
    numbers = K.line_calls(book(calls=CallSystem(methods=["words"], live_signal="numbers")), "key", "g")
    assert set(numbers.live.values()) <= set(K.LIVE_SIGNALS["numbers"])


def test_the_key_picks_two_or_four_cells_per_game():
    b = book(calls=CallSystem(methods=["boards"], board_cells="key"))
    assert {K.boards(b, "key", f"Wk {n}").cells for n in range(1, 13)} == {2, 4}


# ── the draft ────────────────────────────────────────────────────────────────

def test_the_draft_fills_only_blanks_and_says_why():
    plain = Playbook(name="x", plays=[running.inside_zone(), running.speed_sweep(),
                                      all_plays()["pa_boot"], passing.mesh_concept(),
                                      running.power_right()])
    d = P.draft(plain)
    by = {p.id: p for p in d.book.plays}
    assert (by["inside-zone"].series, by["inside-zone"].role) == ("Inside Zone", Role.BASE)
    assert by["speed-sweep"].role is Role.CONSTRAINT and by["speed-sweep"].series == "Inside Zone"
    assert by["mesh-concept"].series is None and by["mesh-concept"].role is None
    assert (by["power-right"].series, by["power-right"].role) == ("Power", Role.BASE)
    assert any(n.startswith("Speed Sweep: constraint in Inside Zone") for n in d.notes)
    sections = dict((s.title, ids) for s, ids in P.sections(d.book))
    assert "inside-zone" in sections["1st & 10"] and "mesh-concept" in sections["2nd & 7+"]
    assert by["pa-boot-left"].role is Role.PLAY_ACTION and by["pa-boot-left"].series == "Inside Zone"
    script = P.openers(d.book)                   # base runs first, run and pass in turn
    assert script == ["inside-zone", "pa-boot-left", "power-right", "mesh-concept", "speed-sweep"]
    again = P.draft(d.book)                      # nothing left to fill
    assert again.book.plays == d.book.plays and not again.notes


def test_the_draft_keeps_what_the_coach_set():
    b = book()                                   # tagged, with openers and situations
    d = P.draft(b)
    for mine, drafted in zip(b.plays, d.book.plays):
        if mine.series or mine.role:
            assert (drafted.series, drafted.role) == (mine.series, mine.role)
    assert P.openers(d.book) == P.openers(b)


# ── favorites and drive starters ─────────────────────────────────────────────

def test_a_favorite_is_lifted_wherever_it_fits():
    b = book()
    favs = Playbook(name="x", plays=[tag(p, favorite=True) if p.id == "mesh-concept" else p for p in b.plays],
                    game_plan=b.game_plan)
    state = DriveState(down=2, distance=8, yard_line=60, snap=1)
    before = {s.play: s.points for s in P.suggest(b, state, k=20)}
    after = {s.play: s for s in P.suggest(favs, state, k=20)}
    assert after["mesh-concept"].points == before["mesh-concept"] + 2          # Base fits anywhere
    assert any(r.text == "One of your favorites" for r in after["mesh-concept"].reasons)


def test_drive_starters_come_up_on_a_drives_first_snap():
    b = book()
    plan = (b.game_plan or GamePlan()).model_copy(update={"starters": ["power-right"], "openers": []})
    b = b.model_copy(update={"game_plan": plan,
                             "plays": [tag(p, situation=None) if p.id != "power-right" else tag(p, situation=None)
                                       for p in b.plays]})
    first = {s.play: s for s in P.suggest(b, DriveState(drive=2, yard_line=60), k=20)}
    assert "power-right" in first
    assert any(r.text == "A drive starter" and r.points == 4 for r in first["power-right"].reasons)
    later = {s.play: s for s in P.suggest(b, DriveState(drive=2, down=2, distance=6, yard_line=56, snap=1), k=20)}
    assert not any(r.text == "A drive starter" for s in later.values() for r in s.reasons)
    assert P.starters(b) == ["power-right"]


def test_scripts_can_start_all_over_the_field():
    assert len(P.SCRIPT_STARTS) >= 12
    assert {st.mode for _, st in P.SCRIPT_STARTS} >= {None, Mode.TWO_MINUTE, Mode.FOUR_MINUTE}


# ── drive scripts ────────────────────────────────────────────────────────────

def test_a_script_fills_its_empty_calls_and_keeps_the_coachs():
    from chalktalk.models import DriveScript, ScriptCall
    b = book()
    mine = DriveScript(name="Open", first=ScriptCall(play="power-right"))
    s = P.fill_script(b, mine)
    assert s.first.play == "power-right"                          # the coach's call stays
    for path in (["on"], ["off"], ["on", "on"], ["on", "off"], ["off", "on"], ["off", "off"]):
        node = P.script_node(s, path)
        assert node is not None and node.play in {p.id for p in b.plays}, path
    assert P.script_state(s, ["on"]).label().startswith("2nd & 4")
    assert P.script_state(s, ["off", "off"]).label().startswith("3rd & 10")
    assert P.fill_script(b, s) == s                               # nothing left to fill


def test_the_game_follows_the_script_from_each_result():
    from chalktalk.models import DriveScript, ScriptCall
    b = book()
    s = DriveScript(name="Open", first=ScriptCall(play="inside-zone",
                                                  on=ScriptCall(play="speed-sweep", on=ScriptCall(play="power-right")),
                                                  off=ScriptCall(play="mesh-concept", off=ScriptCall(play="stick"))))
    st0 = DriveState()
    assert P.follow(b, s, st0, [])[1].play == "inside-zone"
    st1 = P.advance(st0, Outcome.GAIN, 2)                       # 2 of 10: off schedule
    log = [Snap(before=st0, play="inside-zone", call="IZ", gain=2)]
    assert P.follow(b, s, st1, log) == (["off"], s.first.off)
    st2 = P.advance(st1, Outcome.INCOMPLETE)
    log.append(Snap(before=st1, play="mesh-concept", call="Mesh", outcome=Outcome.INCOMPLETE))
    assert P.follow(b, s, st2, log)[1].play == "stick"
    flag = P.advance(st2, Outcome.PENALTY_US, 5)                 # a flag doesn't move the script
    log.append(Snap(before=st2, play="stick", call="Stick", outcome=Outcome.PENALTY_US, gain=5))
    assert P.follow(b, s, flag, log)[1].play == "stick"
    first = P.advance(flag, Outcome.GAIN, 20)                    # a first down starts it again
    log.append(Snap(before=flag, play="stick", call="Stick", gain=20))
    assert first.down == 1 and P.follow(b, s, first, log)[1].play == "inside-zone"


def test_a_play_added_after_the_plan_lands_in_base():
    d = P.draft(Playbook(name="x", plays=[running.inside_zone()]))
    later = d.book.model_copy(update={"plays": [*d.book.plays, passing.stick().model_copy(update={"id": "stick"})]})
    assert "stick" in dict((s.title, ids) for s, ids in P.sections(later))["Base"]


# ── sign boards ──────────────────────────────────────────────────────────────

def _read(sheet, period, board):
    """What a board means in a period: the unit whose symbol sits in the live cell."""
    sym = sheet.boards[board][sheet.live[period]]
    return next((u for u, s in sheet.symbols.items() if s == sym), None)


@pytest.mark.parametrize("cells", [1, 2, 4])
def test_one_rack_carries_every_call_in_every_period(cells):
    b = book(calls=CallSystem(methods=["boards"], rotate="quarter", dummy_boards=3, board_cells=cells))
    sheet = K.boards(b, "key", "Wk 3")
    assert sheet.units == list(P.numbers(b)) and len(sheet.boards) == len(b.plays) + 3
    assert all(len(row) == cells == len(set(row)) for row in sheet.boards)   # no symbol twice
    for period in sheet.live:
        meant = [_read(sheet, period, i) for i in range(len(sheet.boards))]
        assert sorted(filter(None, meant)) == sorted(sheet.units)             # each call once
        assert meant.count(None) == 3                                         # and the dummies
    lives = list(sheet.live.values())
    if cells > 1:
        assert all(a != c for a, c in zip(lives, lives[1:]))
        # a board never means the same call two periods running
        for a, c in zip(K.PERIODS["quarter"], K.PERIODS["quarter"][1:]):
            assert not [i for i in range(len(sheet.boards))
                        if _read(sheet, a, i) and _read(sheet, a, i) == _read(sheet, c, i)]


def test_decoys_mix_the_symbols_across_boards():
    b = book(calls=CallSystem(methods=["boards"], rotate="half", board_cells=4))
    sheet = K.boards(b, "key", "Wk 3")
    seen = Counter(s for row in sheet.boards for s in row)
    meaning = set(sheet.symbols.values())
    assert sum(1 for s in meaning if seen[s] > 1) >= len(meaning) // 2   # most show up more than once


def test_symbols_are_colour_blind_safe_shapes():
    assert len(K.BOARD_SHAPES) * len(K.BOARD_COLORS) == 40
    assert "hexagon" not in K.BOARD_SHAPES and "octagon" not in K.BOARD_SHAPES
    assert set(K.BOARD_COLORS.values()) == {"#000000", "#0072B2", "#D55E00", "#F0E442", "#56B4E9"}


def test_boards_can_go_by_series():
    b = book(calls=CallSystem(methods=["boards"], boards_by="series"))
    units = K.board_units(b)
    assert "series:Zone" in units and "inside-zone" not in units and "speed-sweep" not in units
    assert "power-right" in units                      # no series: its own symbol


def test_too_many_boards_says_how_to_fix_it():
    many = Playbook(name="x", plays=[tag(passing.mesh_concept(), id=f"p{i}") for i in range(60)],
                    game_plan=GamePlan(calls=CallSystem(methods=["boards"])))
    with pytest.raises(ValueError, match="a symbol per series"):
        K.boards(many, "key", "g")


def test_the_check_counts_what_players_must_remember():
    many = Playbook(name="x", plays=[tag(passing.mesh_concept(), id=f"p{i}") for i in range(14)],
                    game_plan=GamePlan(calls=CallSystem(methods=["boards"], dummy_boards=2)))
    notes = P.check(many)
    assert any("14 board symbols to learn" in n and "about 12" in n for n in notes)
    assert any("2 dummy boards for 14 live ones: use at least 7" in n for n in notes)
