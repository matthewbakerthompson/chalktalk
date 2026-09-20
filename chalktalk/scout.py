"""
chalktalk.scout — what the first half says about you.

The Game panel logs every snap: where it was, what was called, what happened.
This reads that log back and says what a scout on the other sideline would
see, and what the staff has left. Nothing here is an opinion about football;
it is counting, with the thresholds the plan already uses.

    from chalktalk.scout import report

    r = report(book)
    r.on, r.snaps                      # on schedule, of the snaps that counted
    [n for n in r.notes]               # "From I-Form Pro Right you have run 6 of 6"

The browser carries a twin, and a test holds the two together.
"""
from __future__ import annotations

from pydantic import BaseModel

from .models.gameplan import Outcome, Snap
from .models.play import Play, Playbook, PlayType
from .planner import advance, is_success, openers, plan_of, starters

# A gain that changes a drive, by the level's own yardstick: the numbers high
# school staffs chart, and the ones the planner already calls on schedule.
EXPLOSIVE = {"run": 12, "pass": 16}
# How many calls from one look before a tendency is worth saying out loud,
# and the share that makes it one.
TENDENCY_CALLS = 4
TENDENCY_SHARE = 0.8


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
    look: str
    calls: int
    runs: int
    passes: int


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
    thirds: Split = Split(label="3rd down")
    explosives: list[PlayLine] = []
    best: list[PlayLine] = []
    tendencies: list[Tendency] = []
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


def report(book: Playbook, log: list[Snap] | None = None) -> Report:
    """Read the log back: the numbers, the tendencies, and what is left."""
    plan = plan_of(book)
    log = list(plan.log if log is None else log)
    by_id = {p.id: p for p in book.plays}
    t = plan.thresholds
    out = Report(game=plan.name)

    downs: dict[int, Split] = {}
    looks: dict[str, Tendency] = {}
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
        if snap.before.down == 3:
            after = advance(snap.before, snap.outcome, snap.gain)
            out.thirds.calls += 1
            out.thirds.on += 1 if (after.down == 1 or after.over == "touchdown") else 0
        if p is not None:
            look = p.formation.name
            tend = looks.setdefault(look, Tendency(look=look, calls=0, runs=0, passes=0))
            tend.calls += 1
            if _kind(p) == "run":
                tend.runs += 1
            else:
                tend.passes += 1
            line = plays.setdefault(snap.play, _line(p, snap.play))
            line.calls += 1
            line.yards += gain
            line.on += 1 if ok else 0
            if gain >= EXPLOSIVE[_kind(p)]:
                out.explosives.append(PlayLine(play=snap.play, call=p.call, calls=1, yards=gain, on=1))

    ordinal = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
    out.by_down = [Split(label=f"{ordinal.get(d, d)} down", calls=s.calls, on=s.on, yards=s.yards)
                   for d, s in sorted(downs.items())]
    out.best = sorted([l for l in plays.values() if l.calls >= 2],
                      key=lambda l: (-(l.yards / l.calls), l.play))[:5]
    out.tendencies = [t for t in sorted(looks.values(), key=lambda x: (-x.calls, x.look))
                      if t.calls >= TENDENCY_CALLS]

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
    for tend in out.tendencies:
        share, what, n = (tend.runs / tend.calls, "run", tend.runs)
        if tend.passes > tend.runs:
            share, what, n = (tend.passes / tend.calls, "thrown", tend.passes)
        if share >= TENDENCY_SHARE:
            out.notes.append(f"From {tend.look} you have {what} {n} of {tend.calls}: "
                             f"a scout sees it")
    if out.explosives:
        out.notes.append(f"{len(out.explosives)} explosive "
                         f"{'play' if len(out.explosives) == 1 else 'plays'}: "
                         + ", ".join(f"{e.call} {int(e.yards)}" for e in out.explosives[:3]))
    return out


__all__ = ["EXPLOSIVE", "TENDENCY_CALLS", "TENDENCY_SHARE", "Split", "Tendency",
           "PlayLine", "Report", "report"]
