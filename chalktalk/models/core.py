from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

#: Words that swap when a play or formation is flipped, longest first so
#: "Right" is matched before "Rt".
_SIDE_WORDS = (("Right", "Left"), ("right", "left"), ("Rt", "Lt"),
               ("RT", "LT"), ("Rip", "Liz"))


def flip_side_name(name: Optional[str]) -> Optional[str]:
    """Swap the handedness in a name: 'Trips Right' -> 'Trips Left'."""
    if not name:
        return name
    for a, b in _SIDE_WORDS:
        if a in name:
            return name.replace(a, b)
        if b in name:
            return name.replace(b, a)
    return name


class Point(BaseModel):
    x: float  # yards from player start; +x = toward sideline, -x = toward middle
    y: float  # yards from player start; +y = downfield, -y = backfield

    def __add__(self, other: "Point") -> "Point":
        return Point(x=self.x + other.x, y=self.y + other.y)

    def mirrored(self) -> "Point":
        """Flip x-axis for left-side players (sideline is in -x direction)."""
        return Point(x=-self.x, y=self.y)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)
