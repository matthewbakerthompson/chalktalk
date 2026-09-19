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
    starters    on a drive's first snap, the staff's drive starters come up
    favorites   the coach's go-to calls, wherever they fit
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
                              ZONES_WITH_DOWNS, CallMethod, DriveScript, DriveState, GamePlan,
                              Mode, Outcome, PlanSection, Role, ScriptCall, Snap)
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
        # A staff's own sections; a play added since lands in Base, not nowhere.
        listed = {i for s in plan.sections if s.when.kind != "base" for i in s.plays}
        own: list[tuple[PlanSection, list[str]]] = []
        for s in plan.sections:
            hits = [i for i in s.plays if i in ids]
            if s.when.kind == "base":
                hits += [i for i in ids if i not in listed and i not in hits]
            own.append((s, hits))
        return own
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


def starters(book: Playbook) -> list[str]:
    """The staff's go-to first calls of a drive, once the opening script is done."""
    ids = {p.id for p in book.plays}
    return [i for i in plan_of(book).starters if i in ids]


def numbers(book: Playbook) -> dict[str, int]:
    """One call number per play: the openers first, then section by section."""
    out: dict[str, int] = {}
    for pid in openers(book) + [i for _, ids in sections(book) for i in ids]:
        if pid not in out:
            out[pid] = len(out) + 1
    return out


# ── a first draft of the plan ────────────────────────────────────────────────
# Tagging every play by hand is the slow part of a game plan. The draft fills
# only what is blank, from what the plays already say about themselves (their
# type, their scheme tags, the quarterback's action), and says why for each
# decision, so a staff edits a plan instead of starting one.

RUN_SCHEMES = [("inside-zone", "Inside Zone"), ("outside-zone", "Outside Zone"),
               ("power", "Power"), ("counter", "Counter"), ("iso", "Iso"), ("trap", "Trap")]
DRAFT_TAGS = {
    "perimeter": ["sweep", "jet", "toss", "perimeter"],
    "short": ["goal-line", "short-yardage"],
    "red": ["red-zone", "end-zone"],
    "play_action": ["play-action"],
    "shot": ["shot", "shot-play", "explosive"],
    "quick": ["quick-game", "quick"],
}
SCRIPT_LENGTH = 10


class Draft(BaseModel):
    book: Playbook
    notes: list[str] = []


def _has(p: Play, group: str) -> bool:
    return any(t in p.tags for t in DRAFT_TAGS[group])


def _draft_role(p: Play) -> Optional[Role]:
    """The job a play's own data gives it, for anything but a base-scheme run."""
    action = p.qb.action.value if p.qb else None
    if p.play_type is PlayType.SPECIAL:
        return Role.TRICK
    if p.play_type is PlayType.SCREEN:
        return Role.CONSTRAINT
    if p.play_type is PlayType.RPO:
        return Role.ANSWER
    if p.play_type is PlayType.RUN and _has(p, "perimeter"):
        return Role.CONSTRAINT
    if p.play_type is PlayType.PASS and (_has(p, "play_action") or action in ("play_action", "boot")):
        return Role.SHOT if _has(p, "shot") else Role.PLAY_ACTION
    return None


def _spots(p: Play) -> list[str]:
    """The call-sheet sections a play's own data points it at."""
    if _has(p, "short"):
        return ["3rd & 1-3", "4th & short", "Goal line"]
    if _has(p, "red"):
        return ["Red zone", "Low red"]
    if p.play_type is PlayType.RUN:
        if _has(p, "perimeter"):
            return ["1st & 10", "2nd & 4-6"]
        if "draw" in p.tags:
            return ["2nd & 7+", "3rd & 7+"]
        return ["1st & 10", "2nd & 1-3", "3rd & 1-3", "Backed up", "Four minute"]
    if p.play_type is PlayType.RPO:
        return ["1st & 10", "2nd & 4-6"]
    if p.play_type is PlayType.SCREEN:
        return ["2nd & 7+", "3rd & 7+"]
    if p.play_type is PlayType.SPECIAL:
        return ["1st & 10"]
    if _has(p, "play_action") or _has(p, "shot") or p.role in (Role.PLAY_ACTION, Role.SHOT):
        return ["1st & 10", "2nd & 1-3"]
    if _has(p, "quick"):
        return ["2nd & 4-6", "3rd & 4-6", "Two minute"]
    return ["2nd & 7+", "3rd & 7+", "Two minute"]


def draft(book: Playbook) -> Draft:
    """
    A first plan from the book, filling only blanks: series and roles for
    untagged plays, the call-sheet sections if the plan has none of its own,
    and an opening script if there isn't one. Every decision is in the notes.
    """
    plays = list(book.plays)
    notes: list[str] = []

    def blank(p: Play) -> bool:
        return not _series_key(p) and p.role is None

    # Runs with a base scheme found their series: the first is its base.
    bases: dict[str, Play] = {}
    for p in plays:
        if p.role is Role.BASE and _series_key(p) and _series_key(p) not in bases:
            bases[_series_key(p)] = p
    for i, p in enumerate(plays):
        if not blank(p) or p.play_type is not PlayType.RUN:
            continue
        name = next((n for tag, n in RUN_SCHEMES if tag in p.tags), None)
        if name is None:
            continue
        role = Role.COMPLEMENT if name.lower() in bases else Role.BASE
        plays[i] = p = p.model_copy(update={"series": name, "role": role})
        if role is Role.BASE:
            bases[name.lower()] = p
        notes.append(f"{p.name}: {role.display.lower()} of the {name} series")

    # Everything else joins the series whose base shares its formation, or the first.
    order: dict[str, Play] = {}
    for p in plays:
        if p.role is Role.BASE and _series_key(p) and _series_key(p) not in order:
            order[_series_key(p)] = p
    for i, p in enumerate(plays):
        role = _draft_role(p) if blank(p) else None
        if role is None or not order:
            continue
        same = next((b for b in order.values() if b.formation.name == p.formation.name), None)
        home = same or next(iter(order.values()))
        plays[i] = p.model_copy(update={"series": home.series, "role": role})
        notes.append(f"{p.name}: {role.display.lower()} in {home.series} "
                     f"({'same formation' if same else 'the first series'})")

    drafted = book.model_copy(update={"plays": plays})
    plan = plan_of(book).model_copy(deep=True)

    if not plan.sections:
        base = next(s for s in DEFAULT_SECTIONS if s.when.kind == "base")
        derived = sections(drafted)
        spots = {s.title: set(ids) for s, ids in derived}
        by_id = {p.id: p for p in plays}
        unplaced = next(ids for s, ids in derived if s.title == base.title)
        for pid in unplaced:
            for title in _spots(by_id[pid]):
                spots[title].add(pid)
        # Base is left empty: it gathers whatever no other section lists.
        plan.sections = [s.model_copy(update={"plays": [] if s.title == base.title else [
            p.id for p in plays if p.id in spots[s.title]]}) for s in DEFAULT_SECTIONS]
        if unplaced:
            notes.append(f"Call sheet: {len(unplaced)} plays placed by their type and tags")

    if not openers(drafted):
        pool = [p for p in plays if p.role is not Role.TRICK
                and not _has(p, "short") and not _has(p, "red")]
        runs = sorted([p for p in pool if p.play_type in (PlayType.RUN, PlayType.RPO)],
                      key=lambda p: p.role is not Role.BASE)
        passes = [p for p in pool if p.play_type in (PlayType.PASS, PlayType.SCREEN)]
        script: list[str] = []
        while (runs or passes) and len(script) < SCRIPT_LENGTH:
            if runs:
                script.append(runs.pop(0).id)
            if passes and len(script) < SCRIPT_LENGTH:
                script.append(passes.pop(0).id)
        plan.openers = script
        if script:
            notes.append(f"Opening script: {len(script)} plays, run and pass in turn")

    return Draft(book=drafted.model_copy(update={"game_plan": plan}), notes=notes)


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
    # A drive's first snap, with no opener leading: the drive starters come up.
    first_snap = state.snap == 0 and state.down == 1 and next_opener is None
    starting = set(starters(book)) if first_snap else set()

    candidates = [p for p in book.plays if p.id in fit or p.id == next_opener or p.id in starting]
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
        if p.id in starting:
            add(4, "A drive starter")
        if p.favorite:
            add(2, "One of your favorites")

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


# ── drive scripts ────────────────────────────────────────────────────────────
# A staff scripts drive patterns in the week (GamePlan.drives): the 1st-down
# call, the 2nd-down call on and off schedule, and 3rd down under each. On
# game day the planner follows a script from each result; when the drive
# leaves it, the suggestions take over.

SCRIPT_DEPTH = 3                 # 1st, 2nd and 3rd down


def _script_gain(state: DriveState, step: str) -> int:
    """The gain a script plans around: most of the distance on schedule, none off it."""
    return max(1, math.ceil(state.distance * 0.6)) if step == "on" else 0


def script_state(script: DriveScript, path: list[str]) -> DriveState:
    """Where a call in the script is meant to be made."""
    state = script.start
    for step in path:
        state = advance(state, Outcome.GAIN, _script_gain(state, step))
    return state


def script_node(script: DriveScript, path: list[str]) -> Optional[ScriptCall]:
    node: Optional[ScriptCall] = script.first
    for step in path:
        node = getattr(node, step) if node is not None else None
    return node


def follow(book: Playbook, script: DriveScript, state: DriveState,
           log: list[Snap]) -> tuple[list[str], Optional[ScriptCall]]:
    """
    Where a drive stands in a script: the path since this set of downs began
    (each call on or off schedule) and the call the script makes next, if it
    makes one. Penalties don't move it; a first down starts it again.
    """
    if state.down == 1 or state.over:
        return [], (script.first if not state.over else None)
    t = plan_of(book).thresholds
    path: list[str] = []
    for snap in log:
        if snap.before.drive != state.drive:
            continue
        if snap.before.down == 1:
            path = []
        ok = is_success(snap.before, snap.outcome, snap.gain, t)
        if ok is not None:
            path.append("on" if ok else "off")
    if len(path) >= SCRIPT_DEPTH:
        return path, None
    return path, script_node(script, path)


def fill_script(book: Playbook, script: DriveScript) -> DriveScript:
    """
    Fill a script's empty calls with the planner's first pick for where each
    one is meant to be made, reading the calls above it as the drive so far.
    What the coach already picked stays.
    """
    by_id = {p.id: p for p in book.plays}

    def fill(node: Optional[ScriptCall], state: DriveState, log: list[Snap],
             depth: int) -> ScriptCall:
        node = node.model_copy() if node is not None else ScriptCall()
        if not node.play:
            pick = suggest(book, state, log, k=1, branches=False)
            node.play = pick[0].play if pick else None
        if node.play and depth + 1 < SCRIPT_DEPTH:
            for step in ("on", "off"):
                gain = _script_gain(state, step)
                after = advance(state, Outcome.GAIN, gain)
                if after.over or after.down == 1:
                    continue
                p = by_id.get(node.play)
                snap = Snap(before=state, play=node.play, call=p.call if p else node.play,
                            outcome=Outcome.GAIN, gain=gain)
                setattr(node, step, fill(getattr(node, step), after, log + [snap], depth + 1))
        return node

    return script.model_copy(update={"first": fill(script.first, script.start, [], 0)})


# ── drive cards ──────────────────────────────────────────────────────────────

DRIVE_CARD_STARTS: list[tuple[str, DriveState]] = [
    ("Drive starter · own 25", DriveState(yard_line=75)),
    ("Backed up · own 5", DriveState(yard_line=95)),
    ("Midfield", DriveState(yard_line=50)),
    ("Red zone · opp 18", DriveState(yard_line=18)),
    ("Goal to go · opp 7", DriveState(distance=7, yard_line=7)),
    ("Two minute · own 30", DriveState(yard_line=70, mode=Mode.TWO_MINUTE)),
]
# Where a staff can start a scripted drive: the card starts and the rest of
# the field, from coming out of the end zone to first and goal.
SCRIPT_STARTS: list[tuple[str, DriveState]] = [
    ("Drive starter · own 25", DriveState(yard_line=75)),
    ("Backed up · own 3", DriveState(yard_line=97)),
    ("Coming out · own 10", DriveState(yard_line=90)),
    ("Own 40", DriveState(yard_line=60)),
    ("Midfield", DriveState(yard_line=50)),
    ("After a turnover · opp 35", DriveState(yard_line=35)),
    ("Fringe · opp 30", DriveState(yard_line=30)),
    ("Red zone · opp 18", DriveState(yard_line=18)),
    ("Low red · opp 8", DriveState(distance=8, yard_line=8)),
    ("Goal line · opp 2", DriveState(distance=2, yard_line=2)),
    ("Two minute · own 30", DriveState(yard_line=70, mode=Mode.TWO_MINUTE)),
    ("End of half · own 45", DriveState(yard_line=55, mode=Mode.TWO_MINUTE)),
    ("Four minute · opp 45", DriveState(yard_line=45, mode=Mode.FOUR_MINUTE)),
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
