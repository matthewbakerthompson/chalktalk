from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from .player import Player
from .route import Route


class Assignment(BaseModel):
    player: Player
    route: Optional[Route] = None
    is_ball_carrier: bool = False
    # Pre-snap motion: player starts at this (x, y) before moving to player.x/y
    motion_from: Optional[tuple[float, float]] = None
    motion_type: Optional[str] = None   # "jet", "orbit", "shift", ... (display only)
    # Free-text coaching point shown in the play's assignment table.
    note: Optional[str] = None

    @property
    def in_motion(self) -> bool:
        return self.motion_from is not None
