from __future__ import annotations
from pydantic import BaseModel


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
