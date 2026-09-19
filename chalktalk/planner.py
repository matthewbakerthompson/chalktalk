"""
chalktalk.planner — the drive planner.

Given a playbook with its game plan, the situation, and the plays already
called, suggest the next calls in order and say why. The coach decides;
chalktalk explains. Suggestions come only from the book, follow named rules
that each add whole points, and are deterministic: the same inputs give the
same ranking here and in the browser designer, which carries a twin of every
function in this module (a test holds the two together).

    from chalktalk.planner import suggest, advance
    from chalktalk.models import DriveState, Outcome, Snap

    state = DriveState(down=1, distance=10, yard_line=75)
    for s in suggest(book, state):
        print(s.points, s.call)
        for r in s.reasons:
            print("   ", r.points, r.text)

The rules, in the order their reasons are listed:

    situation   the play is in a section that fits the down, distance and spot
    script      the next opener leads until the script is used or a special
                situation (3rd down, red zone, two-minute) takes over
    series      constraints, play-action and shots wait for their base; the
                play whose tell the defense just showed is lifted
    same look   a pass from a formation the defense has seen run
    tendency    breaking a formation's all-run or all-pass habit
    freshness   the same call twice in a row is marked down; a play that
                worked earlier is marked up
    yardage     short yardage favours runs, long yardage passes and screens
    clock       two-minute and four-minute
    hash        the play was planned from this hash
    difficulty  a point off for every point a play scores above the team's level
"""
from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel

from .difficulty import TIER_NAMES, difficulty, over_level
from .models.gameplan import (DEFAULT_SECTIONS, HELD_ROLES, MODE_LABELS, OPENERS_LABEL,
                              ZONES_WITH_DOWNS, CallMethod, DriveState, GamePlan, Mode,
                              Outcome, PlanSection, Role, Snap)
from .models.play import Play, Playbook, PlayType

KIND_POINTS = {"mode": 4, "down": 3, "zone": 3, "base": 0}
_ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}


class Reason(BaseModel):
    points: int
    text: str


class Branch(BaseModel):
    when: str            # "2nd & 4"
    play: str
    call: str
    why: str = ""


class Suggestion(BaseModel):
    play: str
    name: str
    call: str
    points: int
    reasons: list[Reason] = []
    branches: list[Branch] = []


# ── the plan, read from the book ─────────────────────────────────────────────

def plan_of(book: Playbook) -> GamePlan:
    return book.game_plan or GamePlan()


def _series_key(p: Play) -> str:
    return (p.series or "").strip().lower()


def _in_section(p: Play, section: PlanSection) -> bool:
    """Where a play's own situation places it, in a plan built from the book."""
    sit = p.situation
    if sit is None:
        return False
    when, kind = section.when, section.when.kind
    if kind == "mode":
        return MODE_LABELS.get(sit.label or "") == when.mode
    if kind == "down":
        if sit.down is None or sit.down not in when.downs:
            return False
        return sit.distance is None or when.distance is None or \
            when.distance[0] <= sit.distance <= when.distance[1]
    if kind == "zone":
        if sit.yard_line is None or not when.yard_line[0] <= sit.yard_line <= when.yard_line[1]:
            return False
        return sit.down is None or section.title in ZONES_WITH_DOWNS
    return False


def sections(book: Playbook) -> list[tuple[PlanSection, list[str]]]:
    """Every section of the plan with the ids of its plays, in book order."""
    plan = plan_of(book)
    ids = [p.id for p in book.plays]
    if plan.sections:
        return [(s, [i for i in s.plays if i in ids]) for s in plan.sections]
    out: list[tuple[PlanSection, list[str]]] = []
    placed: set[str] = set()
    for section in DEFAULT_SECTIONS:
        if section.when.kind == "base":
            continue
        hits = [p.id for p in book.plays if _in_section(p, section)]
        placed.update(hits)
        out.append((section, hits))
    base = next(s for s in DEFAULT_SECTIONS if s.when.kind == "base")
    out.append((base, [p.id for p in book.plays if p.id not in placed]))
    return out


def openers(book: Playbook) -> list[str]:
    plan = plan_of(book)
    ids = {p.id for p in book.plays}
    if plan.openers:
        return [i for i in plan.openers if i in ids]
    return [p.id for p in book.plays
            if p.situation is not None and p.situation.label == OPENERS_LABEL]


def numbers(book: Playbook) -> dict[str, int]:
    """One call number per play: the openers first, then section by section."""
    out: dict[str, int] = {}
    for pid in openers(book) + [i for _, ids in sections(book) for i in ids]:
        if pid not in out:
            out[pid] = len(out) + 1
    return out


def check(book: Playbook) -> list[str]:
    """What a coordinator would want pointed out before the week's install."""
    plan = plan_of(book)
    notes: list[str] = []
    bases: dict[str, list[Play]] = {}
    for p in book.plays:
        if p.role is Role.BASE and _series_key(p):
            bases.setdefault(_series_key(p), []).append(p)
    for p in book.plays:
        if p.role is not None and not _series_key(p):
            notes.append(f"{p.name} is a {p.role.display.lower()} but belongs to no series.")
        elif p.role in HELD_ROLES and _series_key(p) not in bases:
            notes.append(f"{p.name} is a {p.role.display.lower()} in \"{p.series}\", "
                         f"but that series has no base play.")
        tier = difficulty(p).tier
        if tier > plan.execution:
            notes.append(f"{p.name} is {TIER_NAMES[tier]}; the team is set to "
                         f"{TIER_NAMES[plan.execution]}.")
    if not openers(book):
        notes.append("No opening script: label plays \"Openers\" in the play sheet.")
    by_id = {p.id: p for p in book.plays}
    for section, ids in sections(book):
        if section.title == "3rd & 1-3" and ids and not any(
                by_id[i].play_type is PlayType.RUN for i in ids):
            notes.append("3rd & 1-3 has no run.")
        if section.title == "3rd & 7+" and ids and not any(
                by_id[i].play_type in (PlayType.PASS, PlayType.SCREEN) for i in ids):
            notes.append("3rd & 7+ has no pass or screen.")
    calls = plan.calls
    if CallMethod.BOARDS in calls.methods:
        from .codes import BOARD_MEMORY, board_units
        units, keep = len(board_units(book)), BOARD_MEMORY[plan.level.value]
        if units > keep:
            notes.append(f"{units} board symbols to learn this game; players keep about "
                         f"{keep} at this level. Use a symbol per series, or fewer calls.")
        if units and calls.dummy_boards * 2 < units:
            notes.append(f"{calls.dummy_boards} dummy boards for {units} live ones: "
                         f"use at least {math.ceil(units / 2)}.")
    return notes


# ── the football arithmetic ──────────────────────────────────────────────────

def advance(state: DriveState, outcome: Outcome, gain: float = 0) -> DriveState:
    """The next down, distance and spot. The only place yards are counted."""
    if state.over:
        return state
    s = state.model_copy(update={"snap": state.snap + 1})
    if outcome is Outcome.TURNOVER:
        return s.model_copy(update={"over": "turnover"})
    if outcome is Outcome.PENALTY_US:
        spot = min(99, state.yard_line + abs(gain))
        return s.model_copy(update={"yard_line": spot,
                                    "distance": state.distance + (spot - state.yard_line)})
    if outcome is Outcome.PENALTY_THEM:
        spot = max(1, state.yard_line - abs(gain))
        moved = state.yard_line - spot
        if moved >= state.distance:
            return s.model_copy(update={"yard_line": spot, "down": 1,
                                        "distance": min(10, spot)})
        return s.model_copy(update={"yard_line": spot, "distance": state.distance - moved})
    g = 0 if outcome is Outcome.INCOMPLETE else (-abs(gain) if outcome is Outcome.SACK else gain)
    spot = state.yard_line - g
    if spot <= 0:
        return s.model_copy(update={"yard_line": 1, "over": "touchdown"})
    if spot >= 100:
        return s.model_copy(update={"yard_line": 99, "over": "safety"})
    if g >= state.distance:
        return s.model_copy(update={"yard_line": spot, "down": 1, "distance": min(10, spot)})
    if state.down == 4:
        return s.model_copy(update={"yard_line": spot, "over": "downs"})
    return s.model_copy(update={"yard_line": spot, "down": state.down + 1,
                                "distance": state.distance - g})


def is_success(before: DriveState, outcome: Outcome, gain: float,
               thresholds: tuple[int, int, int]) -> Optional[bool]:
    """
    Whether a play stayed on schedule: enough of the yards to go for its down
    (the level's thresholds), a touchdown, or a first down. Penalties don't
    count either way; sacks, incompletions and turnovers fail.
    """
    if outcome in (Outcome.PENALTY_US, Outcome.PENALTY_THEM):
        return None
    if outcome in (Outcome.TURNOVER, Outcome.SACK, Outcome.INCOMPLETE):
        return False
    if gain >= before.yard_line:
        return True
    pct = thresholds[min(before.down, 3) - 1]
    return gain >= before.distance * pct / 100


def down_label(down: int, distance: float, yard_line: Optional[int] = None) -> str:
    goal = yard_line is not None and distance >= yard_line
    return f"{_ORD[down]} & {'Goal' if goal else format(distance, 'g')}"


# ── suggestions ──────────────────────────────────────────────────────────────

def _kind(p: Play) -> str:
    if p.play_type is PlayType.RUN:
        return "run"
    if p.play_type in (PlayType.PASS, PlayType.SCREEN):
        return "pass"
    return "other"


def _snap_gain(s: Snap) -> float:
    if s.outcome is Outcome.INCOMPLETE:
        return 0
    if s.outcome is Outcome.SACK:
        return -abs(s.gain)
    return s.gain


def suggest(book: Playbook, state: DriveState, log: Optional[list[Snap]] = None,
            k: int = 3, branches: bool = True) -> list[Suggestion]:
    """The next `k` calls for `state`, best first, each with its reasons."""
    plan = plan_of(book)
    log = list(plan.log if log is None else log)
    if state.over:
        return []
    by_id = {p.id: p for p in book.plays}
    order = {p.id: i for i, p in enumerate(book.plays)}
    mode = state.mode.value if state.mode else None
    hash_ = state.hash_mark.value if state.hash_mark else None

    # sections that fit this state, and the best one for each play
    fit: dict[str, list[PlanSection]] = {}
    for section, ids in sections(book):
        if section.when.matches(state.down, state.distance, state.yard_line, hash_, mode):
            for pid in ids:
                fit.setdefault(pid, []).append(section)

    script = openers(book)
    called = [s.play for s in log]
    special = state.down >= 3 or state.yard_line <= 20 or state.mode is not None
    remaining = [pid for pid in script if pid not in called]
    next_opener = remaining[0] if remaining and not special else None

    candidates = [p for p in book.plays if p.id in fit or p.id == next_opener]
    seen_tells: dict[str, int] = {}
    for n, s in enumerate(log, 1):
        for t in s.tells:
            seen_tells.setdefault(t.strip().lower(), n)

    out: list[Suggestion] = []
    for p in candidates:
        reasons: list[Reason] = []
        add = lambda pts, text: reasons.append(Reason(points=pts, text=text))  # noqa: E731

        # situation
        matched = [s for s in fit.get(p.id, []) if s.when.kind != "base"]
        if matched:
            best = max(matched, key=lambda s: KIND_POINTS[s.when.kind])
            add(KIND_POINTS[best.when.kind], f"In your {best.title} calls")
            if len(matched) > 1:
                add(1, "Also fits " + ", ".join(s.title for s in matched if s is not best))

        # script
        if p.id == next_opener:
            add(6, f"Next on the opening script ({script.index(p.id) + 1} of {len(script)})")

        # series and tells
        key = _series_key(p)
        if key and p.role is not None:
            base_calls = [n for n, s in enumerate(log, 1)
                          if s.play in by_id and _series_key(by_id[s.play]) == key
                          and by_id[s.play].role is Role.BASE]
            base_names = sorted({q.name for q in book.plays
                                 if _series_key(q) == key and q.role is Role.BASE})
            base_name = base_names[0] if base_names else "its base"
            shown = len(base_calls)
            if p.role is Role.TRICK and p.id in called:
                continue                                   # once a game
            if p.role in HELD_ROLES:
                if shown == 0:
                    add(-4, f"Hold: {base_name} hasn't been shown yet")
                elif p.role is Role.TRICK and shown < 2:
                    add(-2, f"Hold the trick until {base_name} has been shown twice")
                else:
                    add(2, f"{base_name} shown {shown}x; this is its {p.role.display.lower()}")
            elif p.role is Role.BASE and shown == 0:
                add(1, f"Establishes the {p.series.strip()} series")
            elif p.role in (Role.COMPLEMENT, Role.ANSWER) and shown:
                add(1, f"Same picture as {base_name}")
        if p.tell and p.tell.strip().lower() in seen_tells:
            add(4, f"They showed it: {p.tell.strip()} (snap {seen_tells[p.tell.strip().lower()]})")

        # same look, and tendency
        kind = _kind(p)
        formation = p.formation.name
        from_here = [(n, s) for n, s in enumerate(log, 1)
                     if s.play in by_id and by_id[s.play].formation.name == formation]
        if kind == "pass":
            runs = [(n, s) for n, s in from_here if _kind(by_id[s.play]) == "run"]
            if runs:
                n, s = runs[-1]
                add(2, f"Same look as {s.call} (snap {n})")
        kinds_here = [_kind(by_id[s.play]) for _, s in from_here]
        if len(kinds_here) >= 3 and len(set(kinds_here)) == 1 and kinds_here[0] in ("run", "pass") \
                and kind in ("run", "pass") and kind != kinds_here[0]:
            add(2, f"Breaks a tendency: {formation} has been a {kinds_here[0]} "
                   f"{len(kinds_here)} of {len(kinds_here)}")

        # freshness
        mine = [(n, s) for n, s in enumerate(log, 1) if s.play == p.id]
        if mine:
            last_n, last = mine[-1]
            ago = len(log) - last_n + 1
            if ago <= 2:
                add(-3, "Just called" if ago == 1 else "Called 2 snaps ago")
            else:
                add(-min(len(mine), 2), f"Called {len(mine)}x already")
                if is_success(last.before, last.outcome, last.gain, plan.thresholds):
                    add(2, f"Worked earlier: {format(_snap_gain(last), '+g')} on snap {last_n}")

        # yardage
        if state.down >= 3 and state.distance >= 7:
            if kind == "pass":
                add(2, "Long yardage: a pass or screen")
            elif kind == "run":
                add(-2, "Long yardage for a run")
        elif state.down >= 2 and state.distance <= 2 and kind == "run":
            add(2, "Short yardage: a run")
        prev = [s for s in log if s.before.drive == state.drive]
        if prev and _snap_gain(prev[-1]) < 0 and state.distance >= 11 and \
                p.play_type is PlayType.SCREEN:
            add(2, "After a loss: a screen earns yards back")

        # clock
        in_mode = any(s.when.kind == "mode" for s in matched)
        if state.mode is Mode.TWO_MINUTE and kind == "run" and not in_mode:
            add(-2, "Two-minute: a run keeps the clock moving")
        if state.mode is Mode.FOUR_MINUTE and not in_mode:
            if kind == "run":
                add(2, "Four-minute: keep the clock running")
            elif kind == "pass":
                add(-1, "Four-minute: an incompletion stops the clock")

        # hash
        if hash_ and p.situation is not None and p.situation.hash_mark is not None \
                and p.situation.hash_mark.value == hash_:
            add(1, f"Planned from the {hash_} hash")

        # difficulty
        d = difficulty(p)
        over = over_level(d, plan.execution)
        if over:
            why = ", ".join(r for r in d.reasons if r != "set by the coach")
            add(-over, f"{TIER_NAMES[d.tier]} {d.score}: above your team's level"
                + (f" ({why})" if why else ""))

        out.append(Suggestion(play=p.id, name=p.name, call=p.call,
                              points=sum(r.points for r in reasons), reasons=reasons))

    out.sort(key=lambda s: (-s.points, order[s.play]))
    top = out[:k]
    if branches:
        for s in top:
            s.branches = _branches(book, state, log, s)
    return top


def _branches(book: Playbook, state: DriveState, log: list[Snap],
              first: Suggestion) -> list[Branch]:
    """If the call gets most of the way, and if it gets nothing: what comes next."""
    if state.down > 2 or state.distance < 3:
        return []
    hit = max(1, math.ceil(state.distance * 0.6))
    out: list[Branch] = []
    for gain in (hit, 0):
        snap = Snap(before=state, play=first.play, call=first.call,
                    outcome=Outcome.GAIN, gain=gain)
        after = advance(state, Outcome.GAIN, gain)
        if after.over or after.down == 1:
            continue
        nxt = suggest(book, after, log + [snap], k=1, branches=False)
        if nxt:
            out.append(Branch(when=down_label(after.down, after.distance, after.yard_line),
                              play=nxt[0].play, call=nxt[0].call,
                              why=nxt[0].reasons[0].text if nxt[0].reasons else ""))
    return out


# ── drive cards ──────────────────────────────────────────────────────────────

DRIVE_CARD_STARTS: list[tuple[str, DriveState]] = [
    ("Drive starter · own 25", DriveState(yard_line=75)),
    ("Backed up · own 5", DriveState(yard_line=95)),
    ("Midfield", DriveState(yard_line=50)),
    ("Red zone · opp 18", DriveState(yard_line=18)),
    ("Goal to go · opp 7", DriveState(distance=7, yard_line=7)),
    ("Two minute · own 30", DriveState(yard_line=70, mode=Mode.TWO_MINUTE)),
]


def drive_cards(book: Playbook, k: int = 3) -> list[tuple[str, DriveState, list[Suggestion]]]:
    """The printed drive cards: for each common start, the calls and their branches."""
    return [(title, state, suggest(book, state, [], k=k)) for title, state in DRIVE_CARD_STARTS]


def alternation_warning(book: Playbook, log: Optional[list[Snap]] = None) -> Optional[str]:
    """
    Coaches switch between run and pass after a failed play more than they
    should, and defenses expect it. Say so when the last three failures were
    each followed by a switch.
    """
    plan = plan_of(book)
    log = list(plan.log if log is None else log)
    by_id = {p.id: p for p in book.plays}
    switches = 0
    for a, b in zip(log, log[1:]):
        if a.play not in by_id or b.play not in by_id:
            continue
        if is_success(a.before, a.outcome, a.gain, plan.thresholds) is False:
            ka, kb = _kind(by_id[a.play]), _kind(by_id[b.play])
            if {ka, kb} == {"run", "pass"}:
                switches += 1
            else:
                switches = 0
    if switches >= 3:
        return ("You switched between run and pass after each of the last three failed "
                "plays. Defenses expect that switch.")
    return None


__all__ = ["Reason", "Branch", "Suggestion", "plan_of", "sections", "openers", "numbers",
           "check", "advance", "is_success", "down_label", "suggest", "drive_cards",
           "DRIVE_CARD_STARTS", "alternation_warning"]
