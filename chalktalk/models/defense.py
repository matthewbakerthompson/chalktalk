"""
The defense: alignment, and what each defender is actually responsible for.

Alignment alone is a picture of eleven dots. A defensive *assignment* says
whether a defender is rushing a gap, matched to a receiver, or dropping to a
spot on the grass — and a zone is a spot on the grass, so where it lands
depends on where the ball is. Landmarks are computed from the field spec and
the hash the play is run from.

Coordinate conventions
----------------------
Defensive players use the same field coordinates as the offense: +x toward the
offense's right, +y downfield (so the defense sits at positive y). Assignment
paths, like block paths and unlike routes, are **never mirrored** — a blitz off
the offense's right edge stays on the right until the whole play is flipped.
"""
from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, model_validator

from .core import Point

if TYPE_CHECKING:
    from .field import FieldSpec


class DefensePosition(str, Enum):
    # D-Line
    DE  = "DE"    # defensive end (generic)
    DT  = "DT"    # defensive tackle
    NT  = "NT"    # nose tackle (0-tech)
    # Linebackers
    WILL = "W"    # weakside LB
    MIKE = "M"    # middle LB / MLB
    SAM  = "S"    # strongside LB
    OLB  = "OLB"  # outside LB (3-4 standup)
    ILB  = "ILB"  # inside LB (3-4)
    LB   = "LB"   # generic LB
    # Defensive backs
    CB   = "CB"   # cornerback
    FS   = "FS"   # free safety
    SS   = "SS"   # strong safety
    NCB  = "N"    # nickel back
    DCB  = "D"    # dime back
    QCB  = "Q"    # quarter back (7th DB)


DL_POSITIONS = {DefensePosition.DE, DefensePosition.DT, DefensePosition.NT}

LB_POSITIONS = {
    DefensePosition.WILL, DefensePosition.MIKE, DefensePosition.SAM,
    DefensePosition.OLB,  DefensePosition.ILB,  DefensePosition.LB,
}

DB_POSITIONS = {
    DefensePosition.CB,  DefensePosition.FS,  DefensePosition.SS,
    DefensePosition.NCB, DefensePosition.DCB, DefensePosition.QCB,
}

SAFETY_POSITIONS = {DefensePosition.FS, DefensePosition.SS}


class DefensiveRole(str, Enum):
    RUSH    = "rush"      # attack a gap from the line
    BLITZ   = "blitz"     # pressure from off the line
    ZONE    = "zone"      # drop to a spot
    MAN     = "man"       # travel with a receiver
    SPY     = "spy"       # mirror the quarterback
    CONTAIN = "contain"   # set the edge, keep everything inside
    TWO_GAP = "two_gap"   # read the blocker, play both gaps
    STUNT   = "stunt"     # loop as part of a line game
    ROBOT   = "robot"     # rat in the hole, read the quarterback

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").title()


#: Roles that finish in the offensive backfield.
PRESSURE_ROLES = {DefensiveRole.RUSH, DefensiveRole.BLITZ, DefensiveRole.STUNT,
                  DefensiveRole.CONTAIN}


class Zone(str, Enum):
    FLAT          = "flat"
    CURL_FLAT     = "curl_flat"
    HOOK_CURL     = "hook_curl"
    HOOK          = "hook"
    SEAM          = "seam"
    HOLE          = "hole"           # low rat / robber
    DEEP_THIRD    = "deep_third"
    MIDDLE_THIRD  = "middle_third"
    DEEP_HALF     = "deep_half"
    DEEP_QUARTER  = "deep_quarter"
    DEEP_MIDDLE   = "deep_middle"

    @property
    def display(self) -> str:
        return _ZONE_NAMES[self]

    @property
    def is_deep(self) -> bool:
        return self in {Zone.DEEP_THIRD, Zone.MIDDLE_THIRD, Zone.DEEP_HALF,
                        Zone.DEEP_QUARTER, Zone.DEEP_MIDDLE}


_ZONE_NAMES: dict["Zone", str] = {}          # filled in below, after the enum


#: Zone landmark: (yards from the ball at side=1.0, depth, half-width, half-height).
_ZONE_GEOMETRY: dict[Zone, tuple[float, float, float, float]] = {
    Zone.FLAT:         (17.0,  4.0,  7.0, 4.0),
    Zone.CURL_FLAT:    (12.0, 11.0,  6.0, 4.5),
    Zone.HOOK_CURL:    ( 7.0, 11.0,  5.5, 4.5),
    Zone.HOOK:         ( 4.0, 10.0,  5.0, 4.5),
    Zone.SEAM:         ( 9.0, 14.0,  5.0, 5.0),
    Zone.HOLE:         ( 3.0,  5.0,  4.0, 3.0),
    Zone.DEEP_THIRD:   (17.0, 20.0,  8.0, 6.0),
    Zone.MIDDLE_THIRD: ( 0.0, 20.0,  8.0, 6.0),
    Zone.DEEP_HALF:    (12.0, 18.0, 11.0, 6.0),
    Zone.DEEP_QUARTER: (17.0, 20.0,  7.0, 6.0),
    Zone.DEEP_MIDDLE:  ( 0.0, 22.0,  7.0, 6.0),
}


_ZONE_NAMES.update({
    Zone.FLAT: "Flat",
    Zone.CURL_FLAT: "Curl/Flat",
    Zone.HOOK_CURL: "Hook/Curl",
    Zone.HOOK: "Hook",
    Zone.SEAM: "Seam",
    Zone.HOLE: "Hole",
    Zone.DEEP_THIRD: "Deep Third",
    Zone.MIDDLE_THIRD: "Middle Third",
    Zone.DEEP_HALF: "Deep Half",
    Zone.DEEP_QUARTER: "Deep Quarter",
    Zone.DEEP_MIDDLE: "Deep Middle",
})


def zone_landmark(zone: Zone, side: float = 1.0,
                  field: Optional["FieldSpec"] = None,
                  ball_x: float = 0.0) -> tuple[float, float]:
    """
    Where a zone sits, in field coordinates.

    `side` is a multiplier, so 1.0 is the outside landmark and something like
    0.35 is the inside one — that is how the two inside quarters differ from
    the two outside quarters. `ball_x` shifts everything toward the hash the
    play is run from, which is why the boundary flat is a smaller area than the
    field flat.
    """
    from .field import NFL
    field = field or NFL
    base_x, depth, _, _ = _ZONE_GEOMETRY[zone]
    x = ball_x + side * base_x
    limit = field.sideline - 1.0
    return (max(-limit, min(limit, x)), depth)


def zone_size(zone: Zone) -> tuple[float, float]:
    """Half-width and half-height of the area, in yards."""
    _, _, w, h = _ZONE_GEOMETRY[zone]
    return (w, h)


class DefensiveAssignment(BaseModel):
    """What one defender is doing."""
    role: DefensiveRole
    zone: Optional[Zone] = None          # for ZONE
    side: float = 1.0                    # which landmark, and how far outside
    covers: Optional[str] = None         # for MAN — the offensive player's label
    gap: Optional[str] = None            # for RUSH / BLITZ — "A", "B", "C", "D"
    path: list[Point] = []               # relative waypoints, never mirrored
    note: Optional[str] = None

    @property
    def is_pressure(self) -> bool:
        return self.role in PRESSURE_ROLES

    @property
    def is_coverage(self) -> bool:
        return self.role in {DefensiveRole.ZONE, DefensiveRole.MAN,
                             DefensiveRole.ROBOT, DefensiveRole.SPY}

    def absolute_path(self, x: float, y: float) -> list[tuple[float, float]]:
        return [(x + p.x, y + p.y) for p in self.path]

    def landmark(self, field: Optional["FieldSpec"] = None,
                 ball_x: float = 0.0) -> Optional[tuple[float, float]]:
        if self.zone is None:
            return None
        return zone_landmark(self.zone, self.side, field, ball_x)

    def describe(self) -> str:
        if self.role is DefensiveRole.ZONE and self.zone:
            return self.zone.display
        if self.role is DefensiveRole.MAN and self.covers:
            return f"Man {self.covers}"
        if self.is_pressure and self.gap:
            return f"{self.role.display} {self.gap}"
        return self.role.display

    def mirrored(self) -> "DefensiveAssignment":
        return self.model_copy(update={
            "side": -self.side,
            "path": [Point(x=-p.x, y=p.y) for p in self.path],
            "gap": _mirror_gap(self.gap),
        })


def _mirror_gap(gap: Optional[str]) -> Optional[str]:
    if not gap:
        return gap
    for a, b in (("Rt", "Lt"), ("Right", "Left"), ("strong", "weak")):
        if a in gap:
            return gap.replace(a, b)
        if b in gap:
            return gap.replace(b, a)
    return gap


class DefensePlayer(BaseModel):
    label: str
    position: DefensePosition
    x: float = 0.0   # yards from center; +x = offense's right
    y: float = 1.0   # yards from LOS; +y = defensive side (away from QB)
    assignment: Optional[DefensiveAssignment] = None

    @property
    def is_dl(self) -> bool:
        return self.position in DL_POSITIONS

    @property
    def is_lb(self) -> bool:
        return self.position in LB_POSITIONS

    @property
    def is_db(self) -> bool:
        return self.position in DB_POSITIONS

    @property
    def is_safety(self) -> bool:
        return self.position in SAFETY_POSITIONS


def _uniquify(players: list["DefensePlayer"]) -> list["DefensePlayer"]:
    """
    Defenses line up two ends, two tackles and two corners, and playbooks draw
    them all with the same letter. Assignments are keyed by label, so repeated
    labels get an L/R prefix by alignment — the way a coach says it out loud.
    """
    counts: dict[str, int] = {}
    for p in players:
        counts[p.label] = counts.get(p.label, 0) + 1
    if all(n == 1 for n in counts.values()):
        return players

    out = list(players)
    for label, n in counts.items():
        if n < 2:
            continue
        group = sorted((i for i, p in enumerate(out) if out[i].label == label),
                       key=lambda i: out[i].x)
        prefixes = ["L", "R"] if n == 2 else ["L", "M", "R"][:n]
        for slot, index in enumerate(group):
            prefix = prefixes[slot] if slot < len(prefixes) else str(slot + 1)
            out[index] = out[index].model_copy(
                update={"label": f"{prefix}{label}"})
    return out


class DefensiveFormation(BaseModel):
    name: str
    front: str          # "4-3", "3-4", "Nickel 4-2-5", etc.
    personnel: str      # "4-3-4" (DL-LB-DB counts)
    players: list[DefensePlayer]
    coverage: Optional[str] = None    # "Cover 2", "Cover 3", etc.
    pressure: Optional[str] = None    # "Fire Zone Rt", "Zero", ...
    description: Optional[str] = None

    @model_validator(mode="after")
    def _ensure_unique_labels(self) -> "DefensiveFormation":
        unique = _uniquify(self.players)
        if unique is not self.players:
            object.__setattr__(self, "players", unique)
        return self

    # ── Access ────────────────────────────────────────────────────────────────

    def player(self, label: str) -> Optional[DefensePlayer]:
        return next((p for p in self.players if p.label == label), None)

    @property
    def dl(self) -> list[DefensePlayer]:
        return [p for p in self.players if p.is_dl]

    @property
    def linebackers(self) -> list[DefensePlayer]:
        return [p for p in self.players if p.is_lb]

    @property
    def dbs(self) -> list[DefensePlayer]:
        return [p for p in self.players if p.is_db]

    @property
    def safeties(self) -> list[DefensePlayer]:
        return [p for p in self.players if p.is_safety]

    @property
    def corners(self) -> list[DefensePlayer]:
        return [p for p in self.players if p.position is DefensePosition.CB]

    @property
    def has_assignments(self) -> bool:
        return any(p.assignment is not None for p in self.players)

    @property
    def rushers(self) -> list[DefensePlayer]:
        return [p for p in self.players
                if p.assignment is not None and p.assignment.is_pressure]

    # ── Building ──────────────────────────────────────────────────────────────

    def assign(self, label: str,
               assignment: Optional[DefensiveAssignment]) -> "DefensiveFormation":
        """Return a copy with one defender's assignment replaced."""
        return self.model_copy(update={
            "players": [p.model_copy(update={"assignment": assignment})
                        if p.label == label else p for p in self.players]
        })

    def with_assignments(self, assignments: dict[str, DefensiveAssignment],
                         coverage: Optional[str] = None,
                         pressure: Optional[str] = None) -> "DefensiveFormation":
        """Apply a whole call at once; labels not on the field are ignored."""
        players = [
            p.model_copy(update={"assignment": assignments[p.label]})
            if p.label in assignments else p
            for p in self.players
        ]
        updates: dict = {"players": players}
        if coverage:
            updates["coverage"] = coverage
        if pressure:
            updates["pressure"] = pressure
        return self.model_copy(update=updates)

    def clear_assignments(self) -> "DefensiveFormation":
        return self.model_copy(update={
            "players": [p.model_copy(update={"assignment": None})
                        for p in self.players]
        })

    def describe(self) -> str:
        head = f"{self.name}"
        if self.coverage:
            head += f" — {self.coverage}"
        if self.pressure:
            head += f" ({self.pressure})"
        lines = [head]
        for p in self.players:
            if p.assignment:
                lines.append(f"  {p.label:>4s}: {p.assignment.describe()}")
        return "\n".join(lines)

    def mirror(self) -> "DefensiveFormation":
        """Return a left-right mirrored copy (flip x positions and assignments)."""
        return self.model_copy(
            update={
                "players": [
                    p.model_copy(update={
                        "x": -p.x,
                        "assignment": (None if p.assignment is None
                                       else p.assignment.mirrored()),
                    })
                    for p in self.players
                ]
            }
        )


__all__ = [
    "DefensePosition", "DefensePlayer", "DefensiveFormation",
    "DefensiveRole", "DefensiveAssignment", "Zone",
    "zone_landmark", "zone_size",
    "DL_POSITIONS", "LB_POSITIONS", "DB_POSITIONS", "SAFETY_POSITIONS",
    "PRESSURE_ROLES",
]
