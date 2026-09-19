"""
What the quarterback does.

Every other player on the field had an assignment before this: a route, a block,
a coverage responsibility. The quarterback had a dot. But the play *is* what he
does — the drop sets the timing, the mesh point sets the read, and the
progression is the difference between a picture of five routes and a play
somebody can be coached to run.

Two pieces:

- the **action**: drop back, ride the mesh, boot away from it, hand it off;
- the **progression**: the receivers in the order he works them.

Like blocks and defensive assignments — and unlike routes — the path is stored
in absolute directions and is never mirrored for a left-handed version of the
play. `mirrored()` flips it explicitly.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from .core import Point


class QBAction(str, Enum):
    DROPBACK    = "dropback"      # straight drop from under center or gun
    PLAY_ACTION = "play_action"   # sell the run, then set up
    BOOT        = "boot"          # fake one way, get to the edge the other
    SPRINT      = "sprint"        # get to the edge on purpose, no fake
    MESH        = "mesh"          # ride the back and read a defender
    HANDOFF     = "handoff"       # give it and carry out the fake
    PITCH       = "pitch"         # toss it wide
    OPTION      = "option"        # attack down the line, keep or pitch
    KEEP        = "keep"          # designed quarterback run
    SNEAK       = "sneak"         # behind the center
    SCREEN      = "screen"        # retreat and deliver it late

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def is_pass(self) -> bool:
        return self in {QBAction.DROPBACK, QBAction.PLAY_ACTION, QBAction.BOOT,
                        QBAction.SPRINT, QBAction.SCREEN}

    @property
    def carries_the_ball(self) -> bool:
        return self in {QBAction.KEEP, QBAction.SNEAK, QBAction.OPTION}


class QBPlan(BaseModel):
    """The quarterback's job on one play."""
    action: QBAction
    steps: Optional[int] = None        # 3, 5, 7 — how the drop is called
    depth: float = 5.0                 # yards behind the line at the top of it
    direction: int = 1                 # +1 right, -1 left, for anything moving
    mesh_with: Optional[str] = None    # the back he rides, hands to, or fakes to
    reads: list[str] = []              # receiver labels, in the order he works them
    # The order changes with the look: vs Cover 2 he may work the hole shot
    # first, vs Cover 3 the flat. A coverage without its own order uses `reads`.
    reads_vs: dict[str, list[str]] = {}
    key: Optional[str] = None          # the defender he is reading (RPO, option)
    rule: Optional[str] = None         # "high-low the flat defender"
    path: list[Point] = []             # relative waypoints, never mirrored
    mesh_at: Optional[Point] = None    # where he meets the back, relative

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_pass(self) -> bool:
        return self.action.is_pass

    @property
    def mesh_point(self) -> Optional[Point]:
        """Where he meets the back — the moment the play is decided."""
        return self.mesh_at

    def absolute_path(self, x: float, y: float) -> list[tuple[float, float]]:
        return [(x + p.x, y + p.y) for p in self.path]

    def reads_against(self, coverage: Optional[str] = None) -> list[str]:
        """The progression against a coverage ("Cover 3"), or the base one."""
        want = (coverage or "").strip().lower()
        for name, order in self.reads_vs.items():
            if want and name.strip().lower() == want and order:
                return list(order)
        return list(self.reads)

    def read_order(self, label: str, coverage: Optional[str] = None) -> Optional[int]:
        """1-based position in the progression, or None if he is not in it."""
        try:
            return self.reads_against(coverage).index(label) + 1
        except ValueError:
            return None

    def describe(self) -> str:
        bits = [self.action.display]
        if self.steps:
            bits.insert(0, f"{self.steps}-step")
        if self.mesh_with:
            bits.append(f"w/ {self.mesh_with}")
        if self.key:
            bits.append(f"read {self.key}")
        if self.reads:
            bits.append("(" + " > ".join(self.reads) + ")")
        return " ".join(bits)

    def mirrored(self) -> "QBPlan":
        return self.model_copy(update={
            "direction": -self.direction,
            "path": [Point(x=-p.x, y=p.y) for p in self.path],
            "mesh_at": (None if self.mesh_at is None
                        else Point(x=-self.mesh_at.x, y=self.mesh_at.y)),
        })

    def progression(self, *labels: str, vs: Optional[str] = None) -> "QBPlan":
        """Set the read order: .progression('Z', 'H', 'RB'), or against one
        coverage: .progression('H', 'Z', vs='Cover 2')"""
        if vs:
            return self.model_copy(update={"reads_vs": {**self.reads_vs, vs: list(labels)}})
        return self.model_copy(update={"reads": list(labels)})


__all__ = ["QBAction", "QBPlan"]
