from __future__ import annotations
from enum import Enum
from pydantic import BaseModel


class Position(str, Enum):
    # Skill
    QB = "QB"
    RB = "RB"
    FB = "FB"
    TE = "TE"
    WR = "WR"
    X  = "X"    # split end (outside WR, on LOS)
    Y  = "Y"    # tight end / Y receiver
    Z  = "Z"    # flanker (outside WR, off LOS)
    H  = "H"    # slot / H-back
    # Offensive line
    C  = "C"
    LG = "LG"
    RG = "RG"
    LT = "LT"
    RT = "RT"
    # Special teams
    K  = "K"
    P  = "P"

# Positions that are treated as OL in rendering
OL_POSITIONS = {Position.C, Position.LG, Position.RG, Position.LT, Position.RT}

# Positions that are skill/pass-catchers
SKILL_POSITIONS = {
    Position.QB, Position.RB, Position.FB,
    Position.TE, Position.WR, Position.X,
    Position.Y, Position.Z, Position.H,
}


class Player(BaseModel):
    label: str          # display text inside circle, e.g. "X", "QB", "H"
    position: Position
    x: float = 0.0     # yards from center of field; +x = offense right, -x = offense left
    y: float = 0.0     # yards from LOS; 0 = on LOS, negative = backfield

    @property
    def is_ol(self) -> bool:
        return self.position in OL_POSITIONS

    @property
    def is_left_side(self) -> bool:
        """Routes for left-side players must have their x-axis mirrored."""
        return self.x < -1.0
