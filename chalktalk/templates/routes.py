"""
Named route constructors.

Coordinate convention for waypoints:
  +x = toward sideline  |  -x = toward middle
  +y = downfield        |  -y = backfield (behind LOS)

All routes are defined as if the player is on the RIGHT side of the field.
The SVG renderer automatically mirrors x for left-side players.
"""
from __future__ import annotations
from ..models.core import Point
from ..models.route import Route, RouteType


def _pts(*pairs: tuple[float, float]) -> list[Point]:
    return [Point(x=x, y=y) for x, y in pairs]


# ── Vertical / deep ──────────────────────────────────────────────────────────

def FLY(depth: float = 20.0) -> Route:
    return Route(route_type=RouteType.FLY,
                 waypoints=_pts((0, 0), (0, depth)),
                 depth=depth)


def SEAM(depth: float = 18.0) -> Route:
    return Route(route_type=RouteType.SEAM,
                 waypoints=_pts((0, 0), (-0.5, depth * 0.5), (-1.0, depth)),
                 depth=depth)


def POST(stem: float = 10.0, depth: float = 16.0) -> Route:
    run = depth - stem
    return Route(route_type=RouteType.POST,
                 waypoints=_pts((0, 0), (0, stem), (-run * 0.65, depth)),
                 depth=depth)


def CORNER(stem: float = 10.0, depth: float = 16.0) -> Route:
    run = depth - stem
    return Route(route_type=RouteType.CORNER,
                 waypoints=_pts((0, 0), (0, stem), (run * 0.65, depth)),
                 depth=depth)


# ── Breaking routes ───────────────────────────────────────────────────────────

def OUT(stem: float = 6.0, depth: float = 8.0) -> Route:
    run = depth - stem
    return Route(route_type=RouteType.OUT,
                 waypoints=_pts((0, 0), (0, stem), (run * 0.9, depth)),
                 depth=depth)


def IN(stem: float = 10.0, depth: float = 12.0) -> Route:
    run = depth - stem
    return Route(route_type=RouteType.IN,
                 waypoints=_pts((0, 0), (0, stem), (-run * 1.4, depth)),
                 depth=depth)


def DIG(stem: float = 10.0, cross: float = 8.0) -> Route:
    depth = stem
    return Route(route_type=RouteType.DIG,
                 waypoints=_pts((0, 0), (0, stem), (-cross, depth)),
                 depth=depth)


def CURL(depth: float = 12.0) -> Route:
    return Route(route_type=RouteType.CURL,
                 waypoints=_pts((0, 0), (0.5, depth * 0.6), (0, depth), (0.8, depth - 2.0)),
                 depth=depth)


def COMEBACK(depth: float = 16.0) -> Route:
    return Route(route_type=RouteType.COMEBACK,
                 waypoints=_pts((0, 0), (0.5, depth * 0.7), (1.0, depth), (0.5, depth - 3.0)),
                 depth=depth)


# ── Short routes ──────────────────────────────────────────────────────────────

def SLANT(stem: float = 2.5, depth: float = 8.0) -> Route:
    run = depth - stem
    return Route(route_type=RouteType.SLANT,
                 waypoints=_pts((0, 0), (0, stem), (-run * 0.75, depth)),
                 depth=depth)


def HITCH(depth: float = 5.0) -> Route:
    return Route(route_type=RouteType.HITCH,
                 waypoints=_pts((0, 0), (0, depth), (0.8, depth - 1.5)),
                 depth=depth)


def FLAT(depth: float = 3.0, width: float = 6.0) -> Route:
    return Route(route_type=RouteType.FLAT,
                 waypoints=_pts((0, 0), (width * 0.5, 1.0), (width, depth)),
                 depth=depth)


def ANGLE(depth: float = 5.0) -> Route:
    return Route(route_type=RouteType.ANGLE,
                 waypoints=_pts((0, 0), (-depth * 0.65, depth)),
                 depth=depth)


def DRAG(depth: float = 5.0, cross: float = 15.0) -> Route:
    """Short stem then hard break across the field — used in mesh concepts."""
    return Route(route_type=RouteType.DRAG,
                 waypoints=_pts((0, 0), (0, 1.5), (-cross, depth)),
                 depth=depth)


def MESH(depth: float = 6.0, cross: float = 18.0) -> Route:
    """Classic mesh/crossing route — slightly deeper than drag."""
    return Route(route_type=RouteType.MESH,
                 waypoints=_pts((0, 0), (0, 2.0), (-cross, depth)),
                 depth=depth)


def WHEEL(flat_width: float = 6.0, flat_depth: float = 2.0, total_depth: float = 18.0) -> Route:
    return Route(route_type=RouteType.WHEEL,
                 waypoints=_pts((0, 0), (flat_width, flat_depth), (flat_width + 1.0, total_depth)),
                 depth=total_depth)


def SWING(width: float = 5.0, depth: float = 3.0) -> Route:
    return Route(route_type=RouteType.SWING,
                 waypoints=_pts((0, 0), (width * 0.6, 0), (width, depth)),
                 depth=depth)


def SCREEN(depth: float = -2.0, width: float = 4.0) -> Route:
    """Bubble / tunnel screen — goes back behind LOS."""
    return Route(route_type=RouteType.SCREEN,
                 waypoints=_pts((0, 0), (width * 0.4, -1.0), (width, depth)),
                 depth=depth)


# ── Blocking / run ────────────────────────────────────────────────────────────

def BLOCK() -> Route:
    return Route(route_type=RouteType.BLOCK,
                 waypoints=_pts((0, 0), (0, 1.5)),
                 depth=0)


def RUN(dx: float = 0.0, dy: float = 5.0) -> Route:
    """Generic run path for a ball carrier."""
    if dx == 0:
        pts = _pts((0, 0), (0, dy))
    else:
        pts = _pts((0, 0), (dx * 0.4, dy * 0.5), (dx, dy))
    return Route(route_type=RouteType.RUN, waypoints=pts, depth=dy)


# ── Red zone / specialty routes ───────────────────────────────────────────────

def FADE(depth: float = 10.0, drift: float = 2.5) -> Route:
    """Back-shoulder fade or end zone fade — vertical with slight outside drift."""
    return Route(
        route_type=RouteType.FLY,
        waypoints=_pts((0, 0), (drift * 0.4, depth * 0.5), (drift, depth)),
        depth=depth,
    )


def BACK_SHOULDER(depth: float = 8.0) -> Route:
    """Back-shoulder throw — receiver sells go, breaks back toward QB outside."""
    return Route(
        route_type=RouteType.COMEBACK,
        waypoints=_pts((0, 0), (0.5, depth * 0.6), (1.5, depth), (2.5, depth - 2.0)),
        depth=depth,
    )


def CORNER_ENDZONE(stem: float = 5.0, depth: float = 8.0) -> Route:
    """Short corner route for red zone / end zone — less depth than standard corner."""
    run = depth - stem
    return Route(
        route_type=RouteType.CORNER,
        waypoints=_pts((0, 0), (0, stem), (run * 0.75, depth)),
        depth=depth,
    )


def OVER(stem: float = 8.0, cross: float = 12.0) -> Route:
    """Over / deep crossing route — breaks inside at 8+ yards, covers ground."""
    return Route(
        route_type=RouteType.IN,
        waypoints=_pts((0, 0), (0, stem), (-cross, stem + 2.0)),
        depth=stem,
    )


def BUBBLE(width: float = 5.0) -> Route:
    """Bubble screen — immediate flat release, ball delivered at or behind LOS."""
    return Route(
        route_type=RouteType.SCREEN,
        waypoints=_pts((0, 0), (width * 0.5, 0.5), (width, -0.5)),
        depth=0,
    )


def QUICK_SLANT(depth: float = 5.0) -> Route:
    """One-step slant — immediate inside break, no stem."""
    return Route(
        route_type=RouteType.SLANT,
        waypoints=_pts((0, 0), (-depth * 0.7, depth)),
        depth=depth,
    )


def SAIL(stem: float = 5.0, depth: float = 14.0) -> Route:
    """Sail / deep out — intermediate stem then break outside at 45 degrees upfield."""
    run = depth - stem
    return Route(
        route_type=RouteType.CORNER,
        waypoints=_pts((0, 0), (0, stem), (run * 0.55, depth)),
        depth=depth,
    )


# Convenience aliases
GO = FLY
POST_CORNER = CORNER
CROSS = DRAG
