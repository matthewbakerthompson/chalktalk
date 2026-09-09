"""
SVG renderer for Play objects.

Field coordinate system → SVG pixel system:
  field x  →  svg x   (left = negative, right = positive; both increase rightward)
  field y  →  svg y   (field +y = downfield, but SVG y increases downward, so we flip)

Resulting transform:
  svg_x = (field_x - x_min) * scale + pad
  svg_y = (y_max  - field_y) * scale + pad
"""
from __future__ import annotations
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.play import Play

# ── Visual constants ──────────────────────────────────────────────────────────
_FIELD_GREEN      = "#1e5c2e"
_FIELD_GREEN_ALT  = "#1a5229"   # alternating stripe (subtle)
_LINE_COLOR       = "rgba(255,255,255,0.30)"
_LOS_COLOR        = "rgba(255,255,255,0.85)"
_HASH_COLOR       = "rgba(255,255,255,0.20)"
_PLAYER_FILL      = "#1d4ed8"   # offense blue
_PLAYER_STROKE    = "#93c5fd"
_LABEL_COLOR      = "#ffffff"
_TITLE_COLOR      = "#f1f5f9"

# Route colors  (RouteType.value → hex)
_ROUTE_COLORS: dict[str, str] = {
    "block":  "#6b7280",   # gray  – blockers
    "run":    "#f59e0b",   # amber – ball carrier
    "default":"#ffffff",   # white – all pass routes
}

# Defensive player colors (by role)
_DEF_DL_FILL    = "#374151"
_DEF_LB_FILL    = "#4b5563"
_DEF_DB_FILL    = "#6b7280"
_DEF_STROKE     = "#d1d5db"
_DEF_LABEL      = "#ffffff"

# Pre-snap motion
_MOTION_COLOR   = "#7dd3fc"   # light cyan — clearly not a route

# NFL hash mark positions (±13.33 yards from center)
_NFL_HASH_X = 13.33


class SVGRenderer:
    def __init__(
        self,
        play: "Play",
        scale: float = 18.0,
        x_range: tuple[float, float] = (-29.0, 29.0),
        y_range: tuple[float, float] = (-8.0,  22.0),
        padding: int = 28,
    ):
        self.play    = play
        self.scale   = scale
        self.x_range = x_range
        self.y_range = y_range
        self.pad     = padding

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self) -> str:
        parts = [
            self._defs(),
            self._field(),
            self._motions(),
            self._routes(),
            self._defense_players(),
            self._players(),
            self._title(),
        ]
        return self._wrap("\n".join(parts))

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.render())
        print(f"Saved: {os.path.abspath(path)}")

    # ── Coordinate helpers ────────────────────────────────────────────────────

    @property
    def _width(self) -> int:
        return int((self.x_range[1] - self.x_range[0]) * self.scale + 2 * self.pad)

    @property
    def _height(self) -> int:
        return int((self.y_range[1] - self.y_range[0]) * self.scale + 2 * self.pad)

    def _sx(self, field_x: float) -> float:
        return (field_x - self.x_range[0]) * self.scale + self.pad

    def _sy(self, field_y: float) -> float:
        return (self.y_range[1] - field_y) * self.scale + self.pad

    def _s(self, field_x: float, field_y: float) -> tuple[float, float]:
        return self._sx(field_x), self._sy(field_y)

    # ── SVG structure ─────────────────────────────────────────────────────────

    def _wrap(self, content: str) -> str:
        w, h = self._width, self._height
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'{content}\n</svg>'
        )

    def _defs(self) -> str:
        def arrowhead(id_: str, color: str) -> str:
            return (
                f'<marker id="{id_}" markerWidth="10" markerHeight="7" '
                f'refX="9" refY="3.5" orient="auto">'
                f'<polygon points="0 0, 10 3.5, 0 7" fill="{color}"/>'
                f'</marker>'
            )
        return (
            "<defs>\n"
            + "  " + arrowhead("arr-white",  "#ffffff") + "\n"
            + "  " + arrowhead("arr-amber",  "#f59e0b") + "\n"
            + "  " + arrowhead("arr-gray",   "#9ca3af") + "\n"
            + "</defs>"
        )

    # ── Field background ──────────────────────────────────────────────────────

    def _field(self) -> str:
        els: list[str] = []
        w, h = self._width, self._height

        # Base green
        els.append(f'<rect width="{w}" height="{h}" fill="{_FIELD_GREEN}"/>')

        # 5-yard horizontal stripes (alternating shade)
        for y_yd in range(-5, int(self.y_range[1]) + 5, 10):
            y0 = self._sy(y_yd + 5)
            y1 = self._sy(y_yd)
            band_h = abs(y1 - y0)
            els.append(
                f'<rect x="0" y="{min(y0,y1):.1f}" width="{w}" height="{band_h:.1f}" '
                f'fill="{_FIELD_GREEN_ALT}" opacity="0.4"/>'
            )

        # Subtle yard lines
        for y_yd in range(int(self.y_range[0]), int(self.y_range[1]) + 1, 5):
            x0, y_s = self._s(self.x_range[0], y_yd)
            x1, _   = self._s(self.x_range[1], y_yd)
            if y_yd == 0:
                # Line of scrimmage — solid, bright
                els.append(
                    f'<line x1="{x0:.1f}" y1="{y_s:.1f}" x2="{x1:.1f}" y2="{y_s:.1f}" '
                    f'stroke="{_LOS_COLOR}" stroke-width="2.5" stroke-dasharray="10,6"/>'
                )
            else:
                els.append(
                    f'<line x1="{x0:.1f}" y1="{y_s:.1f}" x2="{x1:.1f}" y2="{y_s:.1f}" '
                    f'stroke="{_LINE_COLOR}" stroke-width="0.8"/>'
                )

        # Hash marks (short ticks)
        for hx in (-_NFL_HASH_X, _NFL_HASH_X):
            sx = self._sx(hx)
            for y_yd in range(int(self.y_range[0]), int(self.y_range[1]) + 1):
                sy = self._sy(y_yd)
                tick = self.scale * 0.25
                els.append(
                    f'<line x1="{sx - tick:.1f}" y1="{sy:.1f}" x2="{sx + tick:.1f}" y2="{sy:.1f}" '
                    f'stroke="{_HASH_COLOR}" stroke-width="1.5"/>'
                )

        # Sidelines
        for field_x in (self.x_range[0], self.x_range[1]):
            sx = self._sx(field_x)
            y_top = self._sy(self.y_range[1])
            y_bot = self._sy(self.y_range[0])
            els.append(
                f'<line x1="{sx:.1f}" y1="{y_top:.1f}" x2="{sx:.1f}" y2="{y_bot:.1f}" '
                f'stroke="rgba(255,255,255,0.55)" stroke-width="1.5"/>'
            )

        # LOS label
        los_x, los_y = self._s(self.x_range[0] + 0.8, 0)
        els.append(
            f'<text x="{los_x:.1f}" y="{los_y - 5:.1f}" '
            f'fill="rgba(255,255,255,0.65)" font-family="Arial,sans-serif" '
            f'font-size="11" font-weight="bold">LOS</text>'
        )

        return "\n".join(els)

    # ── Pre-snap motion ───────────────────────────────────────────────────────

    def _motions(self) -> str:
        """Dashed trail from the pre-snap alignment to where the ball is snapped."""
        els: list[str] = []
        for a in self.play.assignments:
            if a.motion_from is None:
                continue
            fx, fy = a.motion_from
            tx, ty = a.player.x, a.player.y
            sx, sy = self._s(fx, fy)
            ex, ey = self._s(tx, ty)

            # Stop just short of the player circle so the arrow stays visible.
            dx, dy = ex - sx, ey - sy
            dist = (dx * dx + dy * dy) ** 0.5 or 1.0
            gap = self.scale * 0.55
            ex -= dx / dist * gap
            ey -= dy / dist * gap

            # Slight arc so motion never hides under a route line.
            mx, my = (sx + ex) / 2, (sy + ey) / 2 - self.scale * 0.55
            els.append(
                f'<path d="M {sx:.1f} {sy:.1f} Q {mx:.1f} {my:.1f} {ex:.1f} {ey:.1f}" '
                f'fill="none" stroke="{_MOTION_COLOR}" stroke-width="1.8" '
                f'stroke-dasharray="5,4" stroke-linecap="round" '
                f'marker-end="url(#arr-motion)" opacity="0.9"/>'
            )
            # Ghost of the original alignment.
            gsx, gsy = self._s(fx, fy)
            r = self.scale * 0.42
            els.append(
                f'<circle cx="{gsx:.1f}" cy="{gsy:.1f}" r="{r:.1f}" fill="none" '
                f'stroke="{_MOTION_COLOR}" stroke-width="1.4" stroke-dasharray="3,3" '
                f'opacity="0.75"/>'
            )
            if a.motion_type:
                els.append(
                    f'<text x="{gsx:.1f}" y="{gsy - r - 4:.1f}" text-anchor="middle" '
                    f'fill="{_MOTION_COLOR}" font-family="Arial,sans-serif" '
                    f'font-size="9" font-weight="bold" opacity="0.9">'
                    f'{a.motion_type.upper()}</text>'
                )
        return "\n".join(els)

    # ── Routes ────────────────────────────────────────────────────────────────

    def _routes(self) -> str:
        els: list[str] = []
        for a in self.play.assignments:
            if a.route is None:
                continue
            rt = a.route.route_type.value
            if rt == "block":
                continue   # OL blocking — skip route lines for now

            # Mirror waypoints for left-side players
            route = a.route.mirror() if a.player.is_left_side else a.route
            waypoints = route.waypoints

            # Convert to absolute field coords
            px, py = a.player.x, a.player.y
            abs_pts = [(px + wp.x, py + wp.y) for wp in waypoints]

            # Determine color and marker
            if a.is_ball_carrier or rt == "run":
                color, marker = "#f59e0b", "url(#arr-amber)"
                stroke_w = 2.8
            else:
                color, marker = "#ffffff", "url(#arr-white)"
                stroke_w = 2.2

            # Build smooth SVG path
            svg_pts = [self._s(x, y) for x, y in abs_pts]
            path_d  = _smooth_path(svg_pts)

            els.append(
                f'<path d="{path_d}" fill="none" stroke="{color}" '
                f'stroke-width="{stroke_w}" stroke-linecap="round" '
                f'stroke-linejoin="round" marker-end="{marker}" opacity="0.92"/>'
            )

        return "\n".join(els)

    # ── Players ───────────────────────────────────────────────────────────────

    def _players(self) -> str:
        els: list[str] = []
        seen: set[str] = set()
        for a in self.play.assignments:
            p = a.player
            key = f"{p.label}_{p.x}_{p.y}"
            if key in seen:
                continue
            seen.add(key)

            sx, sy = self._s(p.x, p.y)
            r = 9 if p.is_ol else 11

            # Circle
            els.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r}" '
                f'fill="{_PLAYER_FILL}" stroke="{_PLAYER_STROKE}" stroke-width="1.5"/>'
            )

            # Label
            fs = 9 if len(p.label) > 2 else 10
            els.append(
                f'<text x="{sx:.1f}" y="{sy + fs * 0.37:.1f}" '
                f'text-anchor="middle" fill="{_LABEL_COLOR}" '
                f'font-family="Arial,sans-serif" font-size="{fs}" font-weight="bold">'
                f'{p.label}</text>'
            )

        return "\n".join(els)

    # ── Defensive players ─────────────────────────────────────────────────────

    def _defense_players(self) -> str:
        if not self.play.defense:
            return ""
        from ..models.defense import DL_POSITIONS, LB_POSITIONS
        els: list[str] = []
        for dp in self.play.defense.players:
            sx, sy = self._sx(dp.x), self._sy(dp.y)
            r = 10

            if dp.position in DL_POSITIONS:
                fill = _DEF_DL_FILL
            elif dp.position in LB_POSITIONS:
                fill = _DEF_LB_FILL
            else:
                fill = _DEF_DB_FILL

            # Hollow square for defense (distinguishes from offense circles)
            half = r
            els.append(
                f'<rect x="{sx - half:.1f}" y="{sy - half:.1f}" '
                f'width="{half * 2}" height="{half * 2}" rx="2" '
                f'fill="{fill}" stroke="{_DEF_STROKE}" stroke-width="1.5" opacity="0.92"/>'
            )
            fs = 9 if len(dp.label) > 2 else 10
            els.append(
                f'<text x="{sx:.1f}" y="{sy + fs * 0.37:.1f}" '
                f'text-anchor="middle" fill="{_DEF_LABEL}" '
                f'font-family="Arial,sans-serif" font-size="{fs}" font-weight="bold">'
                f'{dp.label}</text>'
            )
        return "\n".join(els)

    # ── Title ─────────────────────────────────────────────────────────────────

    def _title(self) -> str:
        w = self._width
        play = self.play
        title   = play.name
        sub     = f"{play.formation.name}  ·  {play.formation.personnel} personnel  ·  {play.play_type.value.upper()}"
        title_y = self._height - 10
        sub_y   = self.pad - 8

        return (
            f'<text x="{w / 2:.1f}" y="{title_y}" text-anchor="middle" '
            f'fill="{_TITLE_COLOR}" font-family="Arial,sans-serif" '
            f'font-size="15" font-weight="bold">{title}</text>\n'
            f'<text x="{w / 2:.1f}" y="{sub_y}" text-anchor="middle" '
            f'fill="rgba(255,255,255,0.55)" font-family="Arial,sans-serif" '
            f'font-size="11">{sub}</text>'
        )


# ── Path generation helpers ───────────────────────────────────────────────────

def _smooth_path(svg_pts: list[tuple[float, float]]) -> str:
    """
    Generate an SVG path string using a Catmull-Rom → cubic Bezier conversion
    so routes curve smoothly through each waypoint.
    """
    if len(svg_pts) < 2:
        return ""

    if len(svg_pts) == 2:
        x0, y0 = svg_pts[0]
        x1, y1 = svg_pts[1]
        return f"M {x0:.1f},{y0:.1f} L {x1:.1f},{y1:.1f}"

    parts = [f"M {svg_pts[0][0]:.1f},{svg_pts[0][1]:.1f}"]
    n = len(svg_pts)

    for i in range(n - 1):
        p0 = svg_pts[max(0, i - 1)]
        p1 = svg_pts[i]
        p2 = svg_pts[i + 1]
        p3 = svg_pts[min(n - 1, i + 2)]

        cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1y = p1[1] + (p2[1] - p0[1]) / 6.0
        cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2y = p2[1] - (p3[1] - p1[1]) / 6.0

        parts.append(
            f"C {cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        )

    return " ".join(parts)
