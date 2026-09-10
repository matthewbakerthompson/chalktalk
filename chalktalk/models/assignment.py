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

    def absolute_waypoints(self) -> list[tuple[float, float]]:
        """
        The route in field coordinates.

        Routes are authored as if the player is on the right side of the ball
        and mirrored for left-side players, so this is the one place that
        convention is applied. The browser designer mirrors this exactly; if
        the two ever disagree, a play drawn on screen renders somewhere else.
        """
        if self.route is None:
            return []
        route = self.route.mirror() if self.player.is_left_side else self.route
        return [(self.player.x + w.x, self.player.y + w.y) for w in route.waypoints]
