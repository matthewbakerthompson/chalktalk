"""
chalktalk.scout — what the first half says about you.

The Game panel logs every snap: where it was, what was called, what happened.
This reads that log back and says what a scout on the other sideline would
see, and what the staff has left. Nothing here is an opinion about football;
it is counting, with the thresholds the plan already uses.

    from chalktalk.scout import report

    r = report(book)
    r.on, r.snaps                      # on schedule, of the snaps that counted
    [n for n in r.notes]               # "From I-Form Pro Right, you have run 6 of 6"

A scout breaks the half down the way the defense sees it before the snap: the
formation, the personnel, the down and distance, the hash, where the ball is,
and any two of those together. A look is said out loud only when nothing
broader already says the same thing: 6 of 6 from I-Form is the note, not also
6 of 6 in 21 personnel when I-Form is the only 21 look.
"""
from __future__ import annotations

from pydantic import BaseModel

from .models.gameplan import DEFAULT_SECTIONS, GamePlan, Outcome, Snap
from .models.play import Play, Playbook, PlayType
from .planner import advance, is_success, openers, plan_of, starters

# A gain that changes a drive, by the level's own yardstick: the numbers high
# school staffs chart, and the ones the planner already calls on schedule.
EXPLOSIVE = {"run": 12, "pass": 16}
# How many calls from one look before a tendency is worth saying out loud,
# and the share that makes it one.
TENDENCY_CALLS = 4
TENDENCY_SHARE = 0.8
# What a scout breaks the half down by, in the order the sheet lists them. A
# formation carries its personnel, so those two are never paired.
DIMENSIONS = ("formation", "personnel", "down", "hash", "field")
HASHES = {"L": "Left hash", "M": "Middle", "R": "Right hash"}
# Where the ball is, when the plan has no section of its own for the spot: the
# zones of `situation.zone_for`, named the way the call sheet names them.
FIELD = [(90, "Backed up"), (60, "Coming out"), (41, "Midfield"), (21, "Fringe"),
         (11, "Red zone"), (4, "Low red"), (1, "Goal line")]
# How a scout says each part of the field before "you have run 6 of 6".
FIELD_WORDS = {"Backed up": "backed up", "Coming out": "coming out",
               "Midfield": "around midfield", "Fringe": "on the fringe",
               "Red zone": "in the red zone", "Low red": "in the low red",
               "Goal line": "on the goal line"}
_ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}


class Split(BaseModel):
    """One row of counting: calls, how many stayed on schedule, and the yards."""
    label: str
    calls: int = 0
    on: int = 0
    yards: float = 0

    @property
    def rate(self) -> int:
        return round(100 * self.on / self.calls) if self.calls else 0


class Tendency(BaseModel):
    """Run against pass from one look: a formation, a personnel group, a down
    and distance, a hash, a part of the field, or two of them at once."""
    look: str                      # "I-Form Pro Right"; two at once: "2nd & 7+, Left hash"
    by: str = "formation"          # a dimension, two joined ("down+hash"), or "overall"
    calls: int
    runs: int
    passes: int
    on: int = 0                    # how many stayed on schedule


class PlayLine(BaseModel):
    play: str
    call: str
    calls: int
    yards: float
    on: int


class Report(BaseModel):
    game: str = ""
    snaps: int = 0                 # snaps that counted (penalties don't)
    on: int = 0
    yards: float = 0
    by_down: list[Split] = []
    by_look: list[Split] = []      # how the half went against each coverage
    thirds: Split = Split(label="3rd down")
    explosives: list[PlayLine] = []
    best: list[PlayLine] = []
    tendencies: list[Tendency] = []   # every look called often enough to read, by dimension
    leans: list[Tendency] = []        # the ones a scout picks out, in the order of the notes
    ready: list[str] = []          # a series whose base has been shown
    unused: list[str] = []         # the script, the starters and the favorites left
    notes: list[str] = []

    @property
    def rate(self) -> int:
        return round(100 * self.on / self.snaps) if self.snaps else 0


def _kind(p: Play) -> str:
    return "run" if p.play_type in (PlayType.RUN, PlayType.RPO) else "pass"


def _line(p: Play, pid: str) -> PlayLine:
    return PlayLine(play=pid, call=p.call if p else pid, calls=0, yards=0, on=0)


def _looks(plan: GamePlan, snap: Snap, p: Play) -> list[tuple[str, str]]:
    """Every look one snap was called from, in `DIMENSIONS` order. The down and
    the spot are named by the plan's own sections, so a tendency points at the
    part of the call sheet that breaks it."""
    st = snap.before
    hash_ = st.hash_mark.value if st.hash_mark else None
    mode = st.mode.value if st.mode else None
    sections = plan.sections or DEFAULT_SECTIONS

    def section(kind: str):
        return next((s.title for s in sections if s.when.kind == kind and
                     s.when.matches(st.down, st.distance, st.yard_line, hash_, mode)), None)

    bucket = "1-3" if st.distance <= 3 else "4-6" if st.distance <= 6 else "7+"
    out = [("formation", p.formation.name)]
    if p.formation.personnel:
        out.append(("personnel", f"{p.formation.personnel} personnel"))
    out.append(("down", section("down") or f"{_ORD[st.down]} & {bucket}"))
    if hash_:
        out.append(("hash", HASHES[hash_]))
    out.append(("field", section("zone") or next(n for line, n in FIELD if st.yard_line >= line)))
    return out


def _say(parts: list[tuple[str, str]]) -> str:
    """A look the way a scout puts it: "From Trips Right, on 3rd & 7+"."""
    words = {"formation": "from {}", "personnel": "in {}", "down": "on {}"}
    said = []
    for by, look in parts:
        if by == "hash":
            said.append(f"from the {look.lower()}")
        elif by == "field":
            said.append(FIELD_WORDS.get(look, f"in {look}"))
        else:
            said.append(words[by].format(look))
    text = ", ".join(said) or "overall"
    return text[0].upper() + text[1:]


def _lean(t: Tendency) -> tuple[str, int] | None:
    """Which way a look leans, and how many calls say so, once it is a tendency."""
    what, n = ("thrown", t.passes) if t.passes > t.runs else ("run", t.runs)
    return (what, n) if t.calls >= TENDENCY_CALLS and n / t.calls >= TENDENCY_SHARE else None


def report(book: Playbook, log: list[Snap] | None = None) -> Report:
    """Read the log back: the numbers, the tendencies, and what is left."""
    plan = plan_of(book)
    log = list(plan.log if log is None else log)
    by_id = {p.id: p for p in book.plays}
    t = plan.thresholds
    out = Report(game=plan.name)

    downs: dict[int, Split] = {}
    looks_seen: dict[str, Split] = {}
    looks: dict[str, Tendency] = {}             # keyed "by|look"
    parts: dict[str, list[tuple[str, str]]] = {}
    covers: dict[str, set[int]] = {}            # the snaps each look was called on
    plays: dict[str, PlayLine] = {}
    called: set[str] = set()
    for snap in log:
        p = by_id.get(snap.play)
        called.add(snap.play)
        ok = is_success(snap.before, snap.outcome, snap.gain, t)
        if ok is None:                      # a flag is not a play
            continue
        gain = 0 if snap.outcome in (Outcome.INCOMPLETE, Outcome.TURNOVER) else (
            -abs(snap.gain) if snap.outcome is Outcome.SACK else snap.gain)
        out.snaps += 1
        out.on += 1 if ok else 0
        out.yards += gain
        down = downs.setdefault(snap.before.down, Split(label=f"{snap.before.down} down"))
        down.calls += 1
        down.on += 1 if ok else 0
        down.yards += gain
        if snap.look:
            seen = looks_seen.setdefault(snap.look, Split(label=snap.look))
            seen.calls += 1
            seen.on += 1 if ok else 0
            seen.yards += gain
        if snap.before.down == 3:
            after = advance(snap.before, snap.outcome, snap.gain)
            out.thirds.calls += 1
            out.thirds.on += 1 if (after.down == 1 or after.over == "touchdown") else 0
        if p is not None:
            one = _looks(plan, snap, p)
            every = [[]] + [[x] for x in one] + [
                [a, b] for i, a in enumerate(one) for b in one[i + 1:]
                if (a[0], b[0]) != ("formation", "personnel")]
            for these in every:
                by = "+".join(b for b, _ in these) or "overall"
                look = ", ".join(x for _, x in these) or "Overall"
                key = f"{by}|{look}"
                if key not in looks:
                    looks[key] = Tendency(look=look, by=by, calls=0, runs=0, passes=0)
                    parts[key], covers[key] = these, set()
                tend = looks[key]
                tend.calls += 1
                tend.on += 1 if ok else 0
                if _kind(p) == "run":
                    tend.runs += 1
                else:
                    tend.passes += 1
                covers[key].add(out.snaps)
            line = plays.setdefault(snap.play, _line(p, snap.play))
            line.calls += 1
            line.yards += gain
            line.on += 1 if ok else 0
            if gain >= EXPLOSIVE[_kind(p)]:
                out.explosives.append(PlayLine(play=snap.play, call=p.call, calls=1, yards=gain, on=1))

    out.by_down = [Split(label=f"{_ORD.get(d, d)} down", calls=s.calls, on=s.on, yards=s.yards)
                   for d, s in sorted(downs.items())]
    out.by_look = [s for s in sorted(looks_seen.values(), key=lambda x: (-x.calls, x.label))]
    out.best = sorted([l for l in plays.values() if l.calls >= 2],
                      key=lambda l: (-(l.yards / l.calls), l.play))[:5]
    # The whole half first, then one look at a time in `DIMENSIONS` order, then two.
    order = sorted(looks, key=lambda k: (
        len(parts[k]), "".join(str(DIMENSIONS.index(by)) for by, _ in parts[k]),
        -looks[k].calls, looks[k].look))
    out.tendencies = [looks[k] for k in order
                      if len(parts[k]) == 1 and looks[k].calls >= TENDENCY_CALLS]
    # A look is worth saying only when nothing broader says it already: no look
    # that covers every one of its snaps (or the same snaps, listed first) and
    # leans the same way.
    leaning = [k for k in order if _lean(looks[k])]
    said = [k for i, k in enumerate(leaning) if not any(
        _lean(looks[u])[0] == _lean(looks[k])[0] and covers[u] >= covers[k]
        and (len(covers[u]) > len(covers[k]) or j < i)
        for j, u in enumerate(leaning) if u != k)]
    out.leans = [looks[k] for k in said]

    # What the staff has set up, and what it has not used.
    shown: dict[str, int] = {}
    for pid in called:
        p = by_id.get(pid)
        if p is not None and p.role is not None and p.role.value == "base" and p.series:
            key = p.series.strip()
            shown[key] = shown.get(key, 0) + 1
    for p in book.plays:
        key = (p.series or "").strip()
        if key in shown and p.role is not None and p.role.value != "base" and p.id not in called:
            out.ready.append(f"{key} has been shown: {p.name} hasn't been called")
    left = [i for i in openers(book) if i not in called]
    if left:
        out.unused.append(f"{len(left)} of the opening script left: "
                          + ", ".join(by_id[i].name for i in left[:4]))
    start = [i for i in starters(book) if i not in called]
    if start:
        out.unused.append("Drive starters not used: "
                          + ", ".join(by_id[i].name for i in start[:4]))
    favs = [p for p in book.plays if p.favorite and p.id not in called]
    if favs:
        out.unused.append("Favorites not used: " + ", ".join(p.name for p in favs[:4]))

    # The notes: what a scout sees, in the order a coordinator reads them.
    if out.snaps:
        out.notes.append(f"{out.on} of {out.snaps} snaps on schedule ({out.rate}%), "
                         f"{round(out.yards / out.snaps, 1)} yards a snap")
    if out.thirds.calls:
        out.notes.append(f"{out.thirds.on} of {out.thirds.calls} on third down")
    for k in said:
        what, n = _lean(looks[k])
        out.notes.append(f"{_say(parts[k])}, you have {what} {n} of {looks[k].calls}: "
                         f"a scout sees it")
    for seen in out.by_look:
        if seen.calls >= TENDENCY_CALLS:
            out.notes.append(f"vs {seen.label}: {seen.on} of {seen.calls} on schedule")
    if out.explosives:
        out.notes.append(f"{len(out.explosives)} explosive "
                         f"{'play' if len(out.explosives) == 1 else 'plays'}: "
                         + ", ".join(f"{e.call} {int(e.yards)}" for e in out.explosives[:3]))
    return out


__all__ = ["EXPLOSIVE", "TENDENCY_CALLS", "TENDENCY_SHARE", "DIMENSIONS", "HASHES", "FIELD",
           "FIELD_WORDS", "Split", "Tendency", "PlayLine", "Report", "report"]
