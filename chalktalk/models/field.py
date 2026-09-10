"""
Field geometry — and the one thing that actually differs between levels: hashes.

The playing field is 53 1/3 yards (160 ft) wide everywhere. The inbound lines
are not:

    NFL      18 ft 6 in apart   ->  3.08 yards either side of the middle
    NCAA     40 ft apart        ->  6.67 yards either side
    NFHS     53 ft 4 in apart   ->  8.89 yards either side

That gap is the whole reason a play looks different in high school than it does
on Sunday: a college hash is more than twice as far from the middle as an NFL
hash, so the boundary side is much shorter and the field side much wider. Draw
a play on the wrong hashes and every leverage read in it is a lie.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from .situation import Hash

FEET_PER_YARD = 3.0
FIELD_WIDTH = 160.0 / FEET_PER_YARD          # 53.33 yards
FIELD_LENGTH = 100.0                          # between the goal lines
END_ZONE_DEPTH = 10.0


class Level(str, Enum):
    NFL = "nfl"
    NCAA = "ncaa"
    HS = "hs"


class FieldSpec(BaseModel):
    """Dimensions that matter when you draw a play."""
    level: Level
    name: str
    hash_separation: float                    # yards between the two hashes
    numbers_from_sideline: float = 9.0        # inside edge of the numbers
    width: float = FIELD_WIDTH
    goalpost_width: float = 18.5 / FEET_PER_YARD

    @property
    def hash_from_center(self) -> float:
        return self.hash_separation / 2.0

    @property
    def sideline(self) -> float:
        return self.width / 2.0

    def hash_x(self, hash_mark: Optional[Hash] = None) -> float:
        """Where the ball sits for a given hash mark, in yards from center."""
        if hash_mark is Hash.LEFT:
            return -self.hash_from_center
        if hash_mark is Hash.RIGHT:
            return self.hash_from_center
        return 0.0

    def boundary_width(self, hash_mark: Optional[Hash] = None) -> float:
        """Yards from the ball to the near sideline — the short side."""
        return self.sideline - abs(self.hash_x(hash_mark))

    def field_width(self, hash_mark: Optional[Hash] = None) -> float:
        """Yards from the ball to the far sideline — the wide side."""
        return self.sideline + abs(self.hash_x(hash_mark))


NFL = FieldSpec(
    level=Level.NFL, name="NFL",
    hash_separation=18.5 / FEET_PER_YARD,          # 6.17 yd
    numbers_from_sideline=12.0,
)

NCAA = FieldSpec(
    level=Level.NCAA, name="College",
    hash_separation=40.0 / FEET_PER_YARD,          # 13.33 yd
    numbers_from_sideline=9.0,
)

HS = FieldSpec(
    level=Level.HS, name="High School",
    hash_separation=(53.0 + 4.0 / 12.0) / FEET_PER_YARD,   # 17.78 yd
    numbers_from_sideline=9.0,
)

FIELDS: dict[Level, FieldSpec] = {Level.NFL: NFL, Level.NCAA: NCAA, Level.HS: HS}


def field_for(level: "Level | str | FieldSpec | None") -> FieldSpec:
    """Accept a Level, its string value, a FieldSpec, or None (-> NFL)."""
    if level is None:
        return NFL
    if isinstance(level, FieldSpec):
        return level
    return FIELDS[Level(level)]


__all__ = [
    "Level", "FieldSpec", "NFL", "NCAA", "HS", "FIELDS", "field_for",
    "FIELD_WIDTH", "FIELD_LENGTH", "END_ZONE_DEPTH",
]
