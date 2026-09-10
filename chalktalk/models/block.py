"""
Blocking assignments.

A route says where a receiver runs. A block says who a lineman is responsible
for and how he gets there — and the two are not the same shape, which is why
this is its own model. A puller's path goes backwards behind the line before it
goes forwards; a combo is two players on one defender before one of them climbs;
a down block and a reach block start from the same alignment and go opposite
directions.

Coordinate convention
---------------------
`path` waypoints are relative to the blocker, in the same units as everything
else (+x toward the offense's right, +y downfield). Unlike routes, block paths
are **never mirrored** for left-side players: a pull to the right is a pull to
the right whether it is the left guard or the right guard doing it. The scheme
builders in `chalktalk.templates.schemes` work out the direction per player.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from .core import Point


class BlockKind(str, Enum):
    BASE     = "base"      # drive the man over you
    DOWN     = "down"      # step inside and block the man in the next gap
    REACH    = "reach"     # zone step playside for outside leverage
    SCOOP    = "scoop"     # backside cut-off
    COMBO    = "combo"     # two on one, then climb to a linebacker
    CLIMB    = "climb"     # release straight to the second level
    KICK     = "kick"      # kick out the edge defender
    WRAP     = "wrap"      # pull and wrap up through the hole
    PULL     = "pull"      # pull with no specified finish
    TRAP     = "trap"      # pull flat and trap the first man past the center
    CUT      = "cut"       # cut block
    PASS_SET = "pass_set"  # vertical / kick set in protection
    SLIDE    = "slide"     # protection: take the gap to one side
    FAN      = "fan"       # protection: turn out on the edge
    HINGE    = "hinge"     # backside protection: set, then hinge back

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").title()


#: Kinds whose path leaves the line before it arrives — drawn as a curve.
PULLING_KINDS = {BlockKind.KICK, BlockKind.WRAP, BlockKind.PULL, BlockKind.TRAP}

#: Kinds that finish at the second level.
SECOND_LEVEL_KINDS = {BlockKind.CLIMB, BlockKind.WRAP, BlockKind.COMBO}


class Block(BaseModel):
    """One blocker's assignment."""
    kind: BlockKind
    target: Optional[str] = None       # defender label ("M", "W") or gap ("A", "B")
    path: list[Point] = []             # relative waypoints, never mirrored
    combo_with: Optional[str] = None   # partner's label, for a double team
    climbs: bool = False               # comes off the double to the second level
    note: Optional[str] = None

    @property
    def is_pulling(self) -> bool:
        return self.kind in PULLING_KINDS

    @property
    def to_second_level(self) -> bool:
        return self.climbs or self.kind in SECOND_LEVEL_KINDS

    def absolute_path(self, x: float, y: float) -> list[tuple[float, float]]:
        """The block path in field coordinates for a blocker aligned at (x, y)."""
        return [(x + p.x, y + p.y) for p in self.path]

    def describe(self) -> str:
        bits = [self.kind.display]
        if self.combo_with:
            bits.append(f"w/ {self.combo_with}")
        if self.target:
            bits.append(f"-> {self.target}")
        return " ".join(bits)

    def mirrored(self) -> "Block":
        """Flip the block's direction — used when a whole play is mirrored."""
        return self.model_copy(update={
            "path": [Point(x=-p.x, y=p.y) for p in self.path],
            "target": _mirror_label(self.target),
        })


_GAP_FLIP = {"A": "A", "B": "B", "C": "C", "D": "D"}


def _mirror_label(target: Optional[str]) -> Optional[str]:
    """Left/right words inside a target flip with the play; gaps and names don't."""
    if not target:
        return target
    for a, b in (("Rt", "Lt"), ("Right", "Left"), ("playside", "playside")):
        if a in target:
            return target.replace(a, b)
        if b in target:
            return target.replace(b, a)
    return target


__all__ = ["Block", "BlockKind", "PULLING_KINDS", "SECOND_LEVEL_KINDS"]
