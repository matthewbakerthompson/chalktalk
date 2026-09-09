from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


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


class DefensePlayer(BaseModel):
    label: str
    position: DefensePosition
    x: float = 0.0   # yards from center; +x = offense's right
    y: float = 1.0   # yards from LOS; +y = defensive side (away from QB)

    @property
    def is_dl(self) -> bool:
        return self.position in DL_POSITIONS

    @property
    def is_lb(self) -> bool:
        return self.position in LB_POSITIONS

    @property
    def is_db(self) -> bool:
        return self.position in DB_POSITIONS


class DefensiveFormation(BaseModel):
    name: str
    front: str          # "4-3", "3-4", "Nickel 4-2-5", etc.
    personnel: str      # "4-3-4" (DL-LB-DB counts)
    players: list[DefensePlayer]
    coverage: Optional[str] = None    # "Cover 2", "Cover 3", etc.
    description: Optional[str] = None

    def mirror(self) -> "DefensiveFormation":
        """Return a left-right mirrored copy (flip x positions of all players)."""
        return self.model_copy(
            update={
                "players": [
                    p.model_copy(update={"x": -p.x}) for p in self.players
                ]
            }
        )
