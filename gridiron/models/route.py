from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from .core import Point


class RouteType(str, Enum):
    # Vertical / deep
    FLY        = "fly"
    SEAM       = "seam"
    POST       = "post"
    CORNER     = "corner"
    # Breaking routes
    OUT        = "out"
    IN         = "in"
    DIG        = "dig"
    CURL       = "curl"
    COMEBACK   = "comeback"
    # Short routes
    SLANT      = "slant"
    HITCH      = "hitch"
    FLAT       = "flat"
    ANGLE      = "angle"
    DRAG       = "drag"
    WHEEL      = "wheel"
    SWING      = "swing"
    SCREEN     = "screen"
    MESH       = "mesh"
    # Blocking / run
    BLOCK      = "block"
    RUN        = "run"
    CUSTOM     = "custom"


class Route(BaseModel):
    route_type: RouteType
    # Relative waypoints from player position.
    # Coordinate convention: +x = toward sideline, -x = toward middle, +y = downfield.
    # For left-side players the renderer mirrors x automatically.
    waypoints: list[Point]
    depth: Optional[float] = None   # primary break depth (yards)

    def mirror(self) -> "Route":
        return Route(
            route_type=self.route_type,
            waypoints=[p.mirrored() for p in self.waypoints],
            depth=self.depth,
        )
