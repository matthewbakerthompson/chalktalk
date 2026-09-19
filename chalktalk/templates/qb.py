"""
Quarterback actions, with the footwork already drawn.

Every helper returns a `QBPlan` whose path is relative to where the quarterback
lines up and already points the right way, so the scheme functions never rely on
the renderer to flip anything.

    from chalktalk.templates import qb as Q

    Q.GUN(3, reads=["Z", "H", "RB"])
    Q.PLAY_ACTION(+1, back="RB", steps=5)
    Q.MESH(+1, back="RB", key="backside end")
"""
from __future__ import annotations
from typing import Optional, Sequence

from ..models.core import Point
from ..models.qb import QBAction, QBPlan


def _pts(*pairs: tuple[float, float]) -> list[Point]:
    return [Point(x=x, y=y) for x, y in pairs]


def _reads(reads: Optional[Sequence[str]]) -> list[str]:
    return list(reads) if reads else []


def _d(direction: int) -> int:
    return 1 if direction >= 0 else -1


# ── Dropping back ─────────────────────────────────────────────────────────────

def DROPBACK(steps: int = 5, reads: Optional[Sequence[str]] = None,
             rule: Optional[str] = None) -> QBPlan:
    """
    A drop from under center. Three steps is quick game, five is the standard
    rhythm throw, seven is a deep concept that needs time.
    """
    depth = {3: 4.0, 5: 6.0, 7: 8.0}.get(steps, 6.0)
    return QBPlan(
        action=QBAction.DROPBACK, steps=steps, depth=depth,
        reads=_reads(reads), rule=rule,
        path=_pts((0, 0), (0, -depth * 0.55), (0, -depth)),
    )


def GUN(steps: int = 3, reads: Optional[Sequence[str]] = None,
        rule: Optional[str] = None) -> QBPlan:
    """
    A drop from the gun. He is already at depth, so this is a hitch or a short
    slide rather than a true drop.
    """
    depth = {0: 0.5, 1: 1.2, 3: 2.4, 5: 3.4}.get(steps, 2.4)
    return QBPlan(
        action=QBAction.DROPBACK, steps=steps, depth=depth,
        reads=_reads(reads), rule=rule,
        path=_pts((0, 0), (0, -depth * 0.6), (0, -depth)),
    )


def SCREEN(direction: int = 1, back: str = "RB",
           reads: Optional[Sequence[str]] = None,
           rule: Optional[str] = None) -> QBPlan:
    """Retreat, invite the rush, and deliver it late."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.SCREEN, depth=5.0, direction=d, mesh_with=back,
        reads=_reads(reads) or [back],
        rule=rule or "Sell the drop, let them come, throw over the rush",
        path=_pts((0, 0), (-d * 0.8, -2.6), (-d * 1.4, -5.0)),
    )


# ── Run action ────────────────────────────────────────────────────────────────

def PLAY_ACTION(direction: int = 1, back: str = "RB", steps: int = 5,
                reads: Optional[Sequence[str]] = None,
                rule: Optional[str] = None) -> QBPlan:
    """Open to the back, sell the handoff, then get to your depth away from it."""
    d = _d(direction)
    depth = {3: 4.0, 5: 6.5, 7: 8.5}.get(steps, 6.5)
    return QBPlan(
        action=QBAction.PLAY_ACTION, steps=steps, depth=depth, direction=d,
        mesh_with=back, reads=_reads(reads),
        rule=rule or "Eyes on the fake, then find the read",
        path=_pts((0, 0), (d * 1.6, -1.2), (d * 0.6, -depth * 0.7), (0, -depth)),
        mesh_at=Point(x=d * 1.6, y=-1.2),
    )


def BOOT(direction: int = 1, back: str = "RB",
         reads: Optional[Sequence[str]] = None,
         rule: Optional[str] = None) -> QBPlan:
    """Fake the run one way and take the ball out on the edge the other way."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.BOOT, depth=5.0, direction=d, mesh_with=back,
        reads=_reads(reads), rule=rule or "Flat to the edge, high-low the corner",
        path=_pts((0, 0), (-d * 1.5, -1.2), (d * 2.0, -3.2), (d * 7.0, -3.6)),
        mesh_at=Point(x=-d * 1.5, y=-1.2),
    )


def SPRINT(direction: int = 1, reads: Optional[Sequence[str]] = None,
           rule: Optional[str] = None) -> QBPlan:
    """Get to the edge on purpose — no fake, half the field, throw on the move."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.SPRINT, depth=4.0, direction=d, reads=_reads(reads),
        rule=rule or "Run to throw; take off if nobody is open",
        path=_pts((0, 0), (d * 2.5, -1.6), (d * 6.5, -2.6)),
    )


def MESH(direction: int = 1, back: str = "RB", key: Optional[str] = None,
         reads: Optional[Sequence[str]] = None,
         rule: Optional[str] = None) -> QBPlan:
    """
    Ride the back and read a defender — a zone read, or the conflict defender
    on an RPO. The mesh point is where the play is actually decided.
    """
    d = _d(direction)
    return QBPlan(
        action=QBAction.MESH, depth=2.0, direction=d, mesh_with=back,
        key=key, reads=_reads(reads),
        rule=rule or (f"Ride and read the {key}" if key else "Ride and read"),
        path=_pts((0, 0), (d * 1.5, -0.6), (d * 2.6, -1.4)),
        mesh_at=Point(x=d * 1.5, y=-0.6),
    )


def HANDOFF(direction: int = 1, back: str = "RB",
            rule: Optional[str] = None) -> QBPlan:
    """Open, give it, and carry out the fake away from the ball."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.HANDOFF, depth=2.0, direction=d, mesh_with=back,
        rule=rule or "Give and carry out the fake",
        path=_pts((0, 0), (d * 1.4, -0.5), (-d * 1.0, -2.6), (-d * 3.0, -3.4)),
        mesh_at=Point(x=d * 1.4, y=-0.5),
    )


def DRAW(direction: int = 1, back: str = "RB") -> QBPlan:
    """Show the drop, let the rush come upfield, then give it underneath."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.HANDOFF, depth=3.0, direction=d, mesh_with=back,
        rule="Show pass, invite the rush, then give it",
        path=_pts((0, 0), (0, -1.8), (d * 1.2, -2.9)),
        mesh_at=Point(x=d * 1.2, y=-2.9),
    )


def PITCH(direction: int = 1, back: str = "RB") -> QBPlan:
    """Reverse out and toss it wide."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.PITCH, depth=3.0, direction=d, mesh_with=back,
        rule="Get depth, lead him with the pitch",
        path=_pts((0, 0), (-d * 0.8, -1.6), (d * 1.2, -3.0)),
        mesh_at=Point(x=d * 1.2, y=-3.0),
    )


def OPTION(direction: int = 1, back: str = "RB",
           key: str = "the end") -> QBPlan:
    """Attack down the line: keep it or pitch it off the unblocked man."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.OPTION, depth=1.5, direction=d, mesh_with=back, key=key,
        rule=f"Attack the inside shoulder of {key}; keep or pitch",
        path=_pts((0, 0), (d * 2.0, -0.4), (d * 4.5, 0.3), (d * 6.0, 1.6)),
        mesh_at=Point(x=d * 2.0, y=-0.4),
    )


# ── Keeping it ────────────────────────────────────────────────────────────────

def KEEP(direction: int = 1, depth: float = 6.0,
         rule: Optional[str] = None) -> QBPlan:
    """A designed quarterback run."""
    d = _d(direction)
    return QBPlan(
        action=QBAction.KEEP, direction=d, depth=depth, rule=rule,
        path=_pts((0, 0), (d * 1.6, 0.6), (d * 2.6, depth * 0.6),
                  (d * 3.0, depth)),
    )


def SNEAK() -> QBPlan:
    """Behind the center, forward."""
    return QBPlan(
        action=QBAction.SNEAK, depth=2.0,
        rule="Follow the center's surge; ball high and tight",
        path=_pts((0, 0), (0, 1.0), (0, 2.2)),
    )


#: Everything above, addressable by name (used by the CLI and the designer).
ACTIONS = {
    "dropback": DROPBACK, "gun": GUN, "screen": SCREEN,
    "play_action": PLAY_ACTION, "boot": BOOT, "sprint": SPRINT,
    "mesh": MESH, "handoff": HANDOFF, "draw": DRAW, "pitch": PITCH,
    "option": OPTION,
    "keep": KEEP, "sneak": SNEAK,
}


__all__ = [
    "DROPBACK", "GUN", "SCREEN", "PLAY_ACTION", "BOOT", "SPRINT", "MESH",
    "HANDOFF", "DRAW", "PITCH", "OPTION", "KEEP", "SNEAK", "ACTIONS",
]
