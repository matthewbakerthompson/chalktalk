"""
What each panel of the designer shows, worked out in Python.

The page asks `chalk design` for a panel's view and draws what comes back.
Everything that takes football judgement (the planner's ranking and reasons,
the difficulty score, the self-scout, the plan check, drafting a plan, filling
a drive script, moving the chains) happens here, from the book the page sends,
so there is one implementation: the same `planner`, `difficulty` and `scout`
a Python user calls.
"""
from __future__ import annotations

from typing import Optional

from .. import difficulty as D
from .. import planner as P
from .. import scout as SC
from ..models import DriveScript, DriveState, Outcome, Playbook
from ..models.play import Play
from ..models.situation import Situation
from ..renderer.plan_sheets import _path_words as path_words

#: The slots of a drive script the builder shows: 1st down, 2nd on and off
#: schedule, and 3rd down under each.
SCRIPT_PATHS: list[list[str]] = [[], ["on"], ["off"], ["on", "on"], ["on", "off"],
                                 ["off", "on"], ["off", "off"]]


def _difficulty(play: Play) -> dict:
    d = D.difficulty(play)
    return {"score": d.score, "tier": d.tier, "tier_name": D.TIER_NAMES[d.tier],
            "reasons": list(d.reasons)}


def play_view(play: Play) -> dict:
    """The play sheet: the play's own difficulty, before any tier the coach sets."""
    return {"auto": _difficulty(play.model_copy(update={"difficulty": None}))}


def script_tree(book: Playbook, script: DriveScript) -> list[dict]:
    """Every slot of a script: where it is called, and the book ranked for it."""
    out = []
    for path in SCRIPT_PATHS:
        state = P.script_state(script, path)
        reset = bool(state.over) or (bool(path) and state.down == 1)
        node = P.script_node(script, path)
        slot = {"path": path, "label": "A first down" if reset else state.label(),
                "words": path_words(path), "reset": reset,
                "pick": node.play if node is not None else None, "ranked": []}
        if not reset:
            ranked = P.suggest(book, state, P.script_log(book, script, path),
                               k=len(book.plays), branches=False)
            slot["ranked"] = [{"play": s.play, "points": s.points} for s in ranked]
        out.append(slot)
    return out


def plan_view(book: Playbook, script: Optional[int] = None) -> dict:
    """The plan builder: difficulty, the call sheet, the scripts, and the check."""
    plan = P.plan_of(book)
    numbers = P.numbers(book)
    drives = plan.drives
    chosen = drives[script] if script is not None and 0 <= script < len(drives) else None
    return {
        "difficulty": {p.id: _difficulty(p) for p in book.plays},
        "sections": [{"section": s.model_dump(mode="json"), "ids": ids, "base": s.when.kind == "base"}
                     for s, ids in P.sections(book)],
        "openers": P.openers(book),
        "starters": P.starters(book),
        "order": sorted(numbers, key=numbers.get),
        "check": P.check(book),
        "thresholds": list(plan.thresholds),
        "scripts": [{"name": d.name, "from": d.start.label()} for d in drives],
        "tree": script_tree(book, chosen) if chosen is not None else None,
    }


def _signed(gain: float) -> str:
    return ("+" if gain >= 0 else "") + format(gain, "g")


def _what(outcome: str, gain: float) -> str:
    """A logged result the way the log reads it: "+6", "sack -7", "flag on them +5"."""
    return {"gain": _signed(gain), "incomplete": "incomplete", "sack": f"sack {_signed(-abs(gain))}",
            "penalty_us": f"flag on us {_signed(-abs(gain))}",
            "penalty_them": f"flag on them {_signed(abs(gain))}",
            "turnover": "turnover"}.get(outcome, outcome)


def _short(state: DriveState) -> str:
    return Situation(down=state.down, distance=state.distance, yard_line=state.yard_line,
                     hash_mark=state.hash_mark).short()


def game_view(book: Playbook, state: DriveState, script: Optional[int] = None) -> dict:
    """The Game panel: the script's call, the planner's picks, the log and the half so far."""
    plan = P.plan_of(book)
    log = list(plan.log)
    by_id = {p.id: p for p in book.plays}
    t = plan.thresholds

    scripted = None
    drives = plan.drives
    if script is not None and 0 <= script < len(drives) and not state.over:
        path, node = P.follow(book, drives[script], state, log)
        play = by_id.get(node.play) if node is not None and node.play else None
        scripted = {"name": drives[script].name, "words": path_words(path), "path": path,
                    "play": play.id if play else None, "call": play.call if play else None}

    rows = []
    for snap in log:
        ok = P.is_success(snap.before, snap.outcome, snap.gain, t)
        p = by_id.get(snap.play)
        rows.append({"sit": _short(snap.before), "name": p.name if p else snap.call,
                     "what": _what(snap.outcome.value, snap.gain), "ok": ok})
    counted = [r for r in rows if r["ok"] is not None]

    r = SC.report(book, log)
    return {
        "label": state.label(),
        "over": bool(state.over),
        "scripted": scripted,
        "suggestions": [] if state.over else [s.model_dump(mode="json") for s in P.suggest(book, state, log, k=3)],
        "log": rows,
        "summary": f"{sum(1 for r_ in counted if r_['ok'])} of {len(counted)} on schedule" if rows else "",
        "warning": P.alternation_warning(book, log),
        "scout": {"snaps": r.snaps, "on": r.on, "notes": r.notes,
                  "by_down": [{"label": s.label, "on": s.on, "calls": s.calls,
                               "per_call": round(s.yards / s.calls * 10) / 10 if s.calls else 0}
                              for s in r.by_down],
                  "ready": r.ready[:1], "unused": r.unused[:1]},
        "check": P.check(book),
    }


def draft(book: Playbook) -> dict:
    """Fill what the coach left blank, and say every decision made."""
    d = P.draft(book)
    return {"book": d.book.model_dump(mode="json"), "notes": d.notes}


def fill_script(book: Playbook, script: DriveScript) -> dict:
    return {"script": P.fill_script(book, script).model_dump(mode="json")}


def advance(state: DriveState, outcome: str, gain: float) -> dict:
    """The next snap's down, distance and spot, or how the drive ended."""
    return {"state": P.advance(state, Outcome(outcome), gain).model_dump(mode="json")}


__all__ = ["play_view", "plan_view", "game_view", "script_tree", "draft", "fill_script",
           "advance", "SCRIPT_PATHS"]
