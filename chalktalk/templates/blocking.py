"""
Named block constructors.

Every helper takes a `direction` (+1 = the play is going to the offense's
right, -1 = left) and returns a `Block` whose path already points the right way.
Block paths are never mirrored by the renderer, so what you build here is what
gets drawn.

    from chalktalk.templates import blocking as B

    B.DOWN(-1, target="3T")      # step down to the inside
    B.WRAP(+1, target="M")       # pull right and wrap to the Mike
    B.COMBO("RT", +1, "S")       # double with the right tackle, climb to Sam
"""
from __future__ import annotations
from typing import Optional

from ..models.block import Block, BlockKind
from ..models.core import Point


def _pts(*pairs: tuple[float, float]) -> list[Point]:
    return [Point(x=x, y=y) for x, y in pairs]


# ── At the line ───────────────────────────────────────────────────────────────

def BASE(target: Optional[str] = None) -> Block:
    """Drive the defender aligned over you."""
    return Block(kind=BlockKind.BASE, target=target,
                 path=_pts((0, 0), (0, 1.3)))


def DOWN(direction: int = -1, target: Optional[str] = None) -> Block:
    """
    Block down — step toward the inside gap and take the man there.
    `direction` is the way the blocker steps, which for a down block is the
    opposite of the way the play is going.
    """
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.DOWN, target=target,
                 path=_pts((0, 0), (d * 0.5, 0.5), (d * 1.1, 1.1)))


def REACH(direction: int = 1, target: Optional[str] = None) -> Block:
    """Zone step playside and get your helmet across."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.REACH, target=target,
                 path=_pts((0, 0), (d * 0.8, 0.35), (d * 1.7, 1.0)))


def SCOOP(direction: int = 1, target: Optional[str] = None) -> Block:
    """Backside cut-off — flat step playside to wall off pursuit."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.SCOOP, target=target,
                 path=_pts((0, 0), (d * 1.1, 0.2), (d * 2.1, 0.7)))


def CUT(direction: int = 1, target: Optional[str] = None) -> Block:
    """Cut block — go at the near knee."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.CUT, target=target,
                 path=_pts((0, 0), (d * 1.2, 0.7)))


def CLIMB(direction: int = 0, target: Optional[str] = None) -> Block:
    """Release clean to the second level."""
    d = 0 if direction == 0 else (1 if direction > 0 else -1)
    return Block(kind=BlockKind.CLIMB, target=target, climbs=True,
                 path=_pts((0, 0), (d * 0.3, 1.4), (d * 1.0, 3.6)))


def COMBO(partner: str, direction: int = 1, target: Optional[str] = None,
          climb: bool = True) -> Block:
    """
    Double team with `partner`. Put this on both blockers — the renderer
    brackets the pair — and give `climb=True` to whichever one comes off the
    double to take the linebacker.
    """
    d = 1 if direction >= 0 else -1
    path = (_pts((0, 0), (d * 0.4, 1.2), (d * 1.1, 3.4)) if climb
            else _pts((0, 0), (d * 0.4, 1.3)))
    return Block(kind=BlockKind.COMBO, target=target, combo_with=partner,
                 climbs=climb, path=path)


# ── Pullers ───────────────────────────────────────────────────────────────────

def KICK(direction: int = 1, target: Optional[str] = None,
         depth: float = 1.1) -> Block:
    """Pull flat and kick out the edge defender."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.KICK, target=target,
                 path=_pts((0, 0), (d * 1.2, -depth), (d * 3.6, -depth * 0.8),
                           (d * 5.2, 0.6)))


def WRAP(direction: int = 1, target: Optional[str] = None,
         depth: float = 1.3) -> Block:
    """Pull and wrap up through the hole to a linebacker."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.WRAP, target=target, climbs=True,
                 path=_pts((0, 0), (d * 1.4, -depth), (d * 3.4, -depth * 0.7),
                           (d * 4.2, 1.4), (d * 4.6, 3.4)))


def TRAP(direction: int = 1, target: Optional[str] = None) -> Block:
    """Pull flat and trap the first defender past the center."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.TRAP, target=target,
                 path=_pts((0, 0), (d * 1.3, -0.9), (d * 2.8, -0.6), (d * 3.6, 0.5)))


def PULL(direction: int = 1, target: Optional[str] = None,
         width: float = 4.0) -> Block:
    """Generic pull with no specified finish."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.PULL, target=target,
                 path=_pts((0, 0), (d * 1.3, -1.1), (d * width, -0.8)))


# ── Protection ────────────────────────────────────────────────────────────────

def PASS_SET(direction: int = 0, target: Optional[str] = None) -> Block:
    """Vertical set — the default look for a man protection."""
    d = 0 if direction == 0 else (1 if direction > 0 else -1)
    return Block(kind=BlockKind.PASS_SET, target=target,
                 path=_pts((0, 0), (d * 0.5, -1.2)))


def SLIDE(direction: int = 1, target: Optional[str] = None) -> Block:
    """Slide protection — you own the gap to one side."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.SLIDE, target=target,
                 path=_pts((0, 0), (d * 1.0, -0.5), (d * 1.5, -1.0)))


def FAN(direction: int = 1, target: Optional[str] = None) -> Block:
    """Turn out on the edge rusher."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.FAN, target=target,
                 path=_pts((0, 0), (d * 1.3, -0.6), (d * 2.0, -0.2)))


def HINGE(direction: int = -1, target: Optional[str] = None) -> Block:
    """Backside protection — set, then hinge back to wall the edge."""
    d = 1 if direction >= 0 else -1
    return Block(kind=BlockKind.HINGE, target=target,
                 path=_pts((0, 0), (d * 0.4, -1.0), (d * 1.4, -1.7)))


__all__ = [
    "BASE", "DOWN", "REACH", "SCOOP", "CUT", "CLIMB", "COMBO",
    "KICK", "WRAP", "TRAP", "PULL",
    "PASS_SET", "SLIDE", "FAN", "HINGE",
]
