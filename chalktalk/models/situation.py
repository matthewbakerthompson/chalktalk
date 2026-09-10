"""
Situational context — down, distance, field position, hash, tempo.

Used by scripted series, practice scripts, and call sheets to say *when*
a play gets called, not just *what* it is.

Field position convention
-------------------------
`yard_line` is yards to the OPPONENT'S goal line (1-99).
  99 = own 1 yard line      75 = own 25      50 = midfield
  25 = opponent's 25         3 = opponent's 3
Use Situation.own(n) / Situation.opp(n) if you'd rather not do the math.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Hash(str, Enum):
    LEFT   = "L"
    MIDDLE = "M"
    RIGHT  = "R"


class Tempo(str, Enum):
    NORMAL    = "normal"      # huddle, normal cadence
    NO_HUDDLE = "no_huddle"   # sprint to the ball
    CHECK     = "check"       # check-with-me at the line
    FREEZE    = "freeze"      # hard count / draw offsides
    KILL      = "kill"        # two plays called, kill to the second


class FieldZone(str, Enum):
    BACKED_UP = "backed_up"   # own 1-10
    OWN       = "own"         # own 11-40
    MIDFIELD  = "midfield"    # own 41 - opp 41
    FRINGE    = "fringe"      # opp 40-21  (4-down / long FG territory)
    RED_ZONE  = "red_zone"    # opp 20-11
    LOW_RED   = "low_red"     # opp 10-4
    GOAL_LINE = "goal_line"   # opp 3-1

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").title()


class Distance(str, Enum):
    SHORT  = "short"    # 1-3
    MEDIUM = "medium"   # 4-6
    LONG   = "long"     # 7-10
    XLONG  = "xlong"    # 11+

    @property
    def display(self) -> str:
        return {"short": "Short", "medium": "Medium",
                "long": "Long", "xlong": "Extra Long"}[self.value]


def zone_for(yard_line: int) -> FieldZone:
    """Map yards-to-opponent-goal-line onto a coaching field zone."""
    if yard_line >= 90:
        return FieldZone.BACKED_UP
    if yard_line >= 60:
        return FieldZone.OWN
    if yard_line >= 41:
        return FieldZone.MIDFIELD
    if yard_line >= 21:
        return FieldZone.FRINGE
    if yard_line >= 11:
        return FieldZone.RED_ZONE
    if yard_line >= 4:
        return FieldZone.LOW_RED
    return FieldZone.GOAL_LINE


def distance_for(distance: float) -> Distance:
    if distance <= 3:
        return Distance.SHORT
    if distance <= 6:
        return Distance.MEDIUM
    if distance <= 10:
        return Distance.LONG
    return Distance.XLONG


_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}


class Situation(BaseModel):
    """When a play is called. Every field is optional — use what you need."""
    down: Optional[int] = Field(default=None, ge=1, le=4)
    distance: Optional[float] = Field(default=None, ge=0)
    yard_line: Optional[int] = Field(default=None, ge=1, le=99)
    hash_mark: Optional[Hash] = None
    tempo: Tempo = Tempo.NORMAL
    personnel: Optional[str] = None          # "11", "12", "21"
    clock: Optional[str] = None              # "2:00", "under 4:00"
    score_diff: Optional[int] = None         # offense score - defense score
    label: Optional[str] = None              # free-text override ("Openers")
    notes: Optional[str] = None

    # ── Constructors ──────────────────────────────────────────────────────────

    @classmethod
    def own(cls, yard: int, **kwargs) -> "Situation":
        """Situation.own(25) -> ball on our own 25."""
        return cls(yard_line=100 - yard, **kwargs)

    @classmethod
    def opp(cls, yard: int, **kwargs) -> "Situation":
        """Situation.opp(8) -> ball on the opponent's 8."""
        return cls(yard_line=yard, **kwargs)

    @classmethod
    def dd(cls, down: int, distance: float, **kwargs) -> "Situation":
        """Situation.dd(3, 5) -> 3rd & 5."""
        return cls(down=down, distance=distance, **kwargs)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def zone(self) -> Optional[FieldZone]:
        return zone_for(self.yard_line) if self.yard_line is not None else None

    @property
    def distance_bucket(self) -> Optional[Distance]:
        return distance_for(self.distance) if self.distance is not None else None

    @property
    def is_scoring_range(self) -> bool:
        return self.yard_line is not None and self.yard_line <= 20

    @property
    def down_distance(self) -> Optional[str]:
        if self.down is None:
            return None
        d = _ORDINAL.get(self.down, f"{self.down}th")
        if self.distance is None:
            return d
        goal = (self.yard_line is not None and self.distance >= self.yard_line)
        return f"{d} & {'Goal' if goal else format(self.distance, 'g')}"

    @property
    def field_position(self) -> Optional[str]:
        if self.yard_line is None:
            return None
        if self.yard_line == 50:
            return "50"
        if self.yard_line > 50:
            return f"Own {100 - self.yard_line}"
        return f"Opp {self.yard_line}"

    # ── Display ───────────────────────────────────────────────────────────────

    def describe(self) -> str:
        if self.label:
            return self.label
        bits = [b for b in (self.down_distance, self.field_position) if b]
        if self.hash_mark:
            bits.append(f"{self.hash_mark.value} Hash")
        if self.tempo is not Tempo.NORMAL:
            bits.append(self.tempo.value.replace("_", "-").title())
        if self.clock:
            bits.append(self.clock)
        return ", ".join(bits) if bits else "Any"

    def short(self) -> str:
        """Compact form for dense tables: '3&5 O32 L'."""
        if self.label and self.down is None and self.yard_line is None:
            return self.label
        bits = []
        if self.down is not None:
            bits.append(f"{self.down}&{self.distance:g}" if self.distance is not None
                        else str(self.down))
        if self.yard_line is not None:
            bits.append(f"O{self.yard_line}" if self.yard_line <= 50
                        else f"-{100 - self.yard_line}")
        if self.hash_mark:
            bits.append(self.hash_mark.value)
        return " ".join(bits)

    @property
    def is_wildcard(self) -> bool:
        """No positional constraints — a pure named bucket like 'Openers'."""
        return (self.down is None and self.distance is None
                and self.yard_line is None and self.hash_mark is None)

    def matches(self, other: "Situation") -> bool:
        """
        True if `other` is compatible with this. Unset fields are wildcards, so
        `Situation(down=3)` matches any third down. A situation with no
        positional constraints at all (e.g. OPENERS) matches only by label.
        """
        if self.is_wildcard:
            return self.label is not None and other.label == self.label
        if self.down is not None and other.down != self.down:
            return False
        if self.distance_bucket is not None and other.distance_bucket != self.distance_bucket:
            return False
        if self.zone is not None and other.zone != self.zone:
            return False
        if self.hash_mark is not None and other.hash_mark != self.hash_mark:
            return False
        return True

    def __str__(self) -> str:
        return self.describe()


# ── Stock situations ──────────────────────────────────────────────────────────

OPENERS       = Situation(label="Openers")
FIRST_TEN     = Situation(down=1, distance=10)
SECOND_SHORT  = Situation(down=2, distance=2)
SECOND_MEDIUM = Situation(down=2, distance=5)
SECOND_LONG   = Situation(down=2, distance=9)
THIRD_ONE     = Situation(down=3, distance=1)
THIRD_SHORT   = Situation(down=3, distance=2)
THIRD_MEDIUM  = Situation(down=3, distance=5)
THIRD_LONG    = Situation(down=3, distance=9)
THIRD_XLONG   = Situation(down=3, distance=13)
FOURTH_SHORT  = Situation(down=4, distance=1)
BACKED_UP     = Situation.own(5, label="Backed Up")
MIDFIELD      = Situation.own(50, label="Midfield")
FRINGE        = Situation.opp(35, label="Fringe / 4-Down")
RED_ZONE      = Situation.opp(15, label="Red Zone")
LOW_RED       = Situation.opp(7,  label="Low Red")
GOAL_LINE     = Situation.opp(2,  label="Goal Line")
TWO_MINUTE    = Situation(clock="2:00", tempo=Tempo.NO_HUDDLE, label="Two Minute")
FOUR_MINUTE   = Situation(clock="4:00", label="Four Minute")
TWO_POINT     = Situation.opp(2, label="Two-Point")
