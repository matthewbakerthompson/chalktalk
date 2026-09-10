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
from typing import TYPE_CHECKING, Optional

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

# Blocking
_BLOCK_COLOR    = "#e5e7eb"
_BLOCK_WIDTH    = 2.2

# Quarterback
_QB_COLOR       = "#fbbf24"   # amber — he has the ball on every snap
_READ_FILL      = "#0f172a"
_READ_TEXT      = "#fde68a"

# Defensive assignments
_DEF_ASSIGN     = "#f87171"   # red — the defense's side of the ink
_ZONE_FILL      = "rgba(248,113,113,0.07)"
_ZONE_SCALE     = 0.7    # draw the area smaller than it really is,
                         # or five overlapping bubbles hide the play

# Hash positions come from the field spec — they differ by level.


class SVGRenderer:
    def __init__(
        self,
        play: "Play",
        scale: float = 18.0,
        x_range: tuple[float, float] = (-29.0, 29.0),
        y_range: tuple[float, float] = (-8.0,  22.0),
        padding: int = 28,
        level=None,
        zones: bool = True,
    ):
        from ..models.field import field_for
        self.play    = play
        self.scale   = scale
        self.x_range = x_range
        self.y_range = y_range
        self.pad     = padding
        self.field   = field_for(level)
        self.zones   = zones

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self) -> str:
        parts = [
            self._defs(),
            self._field(),
            self._motions(),
            self._blocks(),
            self._qb(),
            self._routes(),
            self._reads(),
            self._defense_assignments(),
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
            + "  " + arrowhead("arr-motion", _MOTION_COLOR) + "\n"
            + "  " + arrowhead("arr-def",    _DEF_ASSIGN) + "\n"
            + "  " + arrowhead("arr-qb",     _QB_COLOR) + "\n"
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
        hash_x = self.field.hash_from_center
        for hx in (-hash_x, hash_x):
            sx = self._sx(hx)
            for y_yd in range(int(self.y_range[0]), int(self.y_range[1]) + 1):
                sy = self._sy(y_yd)
                tick = self.scale * 0.25
                els.append(
                    f'<line x1="{sx - tick:.1f}" y1="{sy:.1f}" x2="{sx + tick:.1f}" y2="{sy:.1f}" '
                    f'stroke="{_HASH_COLOR}" stroke-width="1.5"/>'
                )

        # Sidelines — the real ones, 53 1/3 yards apart, not the edge of the view
        for field_x in (-self.field.sideline, self.field.sideline):
            if not (self.x_range[0] <= field_x <= self.x_range[1]):
                continue
            sx = self._sx(field_x)
            y_top = self._sy(self.y_range[1])
            y_bot = self._sy(self.y_range[0])
            els.append(
                f'<line x1="{sx:.1f}" y1="{y_top:.1f}" x2="{sx:.1f}" y2="{y_bot:.1f}" '
                f'stroke="rgba(255,255,255,0.55)" stroke-width="1.5"/>'
            )

        # Ball spot on the hash this play is run from
        if self.play.situation is not None and self.play.situation.hash_mark:
            bx, by = self._s(self.field.hash_x(self.play.situation.hash_mark), 0)
            els.append(
                f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{self.scale * 0.3:.1f}" '
                f'ry="{self.scale * 0.18:.1f}" fill="#c2703a" '
                f'stroke="rgba(255,255,255,0.85)" stroke-width="1"/>'
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

    # ── Blocking ──────────────────────────────────────────────────────────────

    def _blocks(self) -> str:
        """
        Blocks are drawn the way a playbook draws them: a path ending in a bar
        across the defender, a curve behind the line for a puller, and a
        bracket under a double team. Block paths are never mirrored.
        """
        from ..models.block import BlockKind
        from ..templates.blocking import BASE

        els: list[str] = []
        combos: set[frozenset] = set()

        for a in self.play.assignments:
            block = a.block
            if block is None:
                # A play built before blocks existed still says "block" with a
                # route; draw it as a base block rather than nothing at all.
                if a.route is not None and a.route.route_type.value == "block":
                    block = BASE()
                else:
                    continue

            pts = block.absolute_path(a.player.x, a.player.y)
            if len(pts) < 2:
                continue
            svg_pts = _trim_start([self._s(x, y) for x, y in pts],
                                 self.scale * 0.42)
            els.append(
                f'<path d="{_smooth_path(svg_pts)}" fill="none" '
                f'stroke="{_BLOCK_COLOR}" stroke-width="{_BLOCK_WIDTH}" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="0.88"/>'
            )
            els.append(_block_cap(svg_pts, self.scale, block.kind is BlockKind.CUT))

            if block.combo_with:
                pair = frozenset((a.player.label, block.combo_with))
                partner = next((x for x in self.play.assignments
                                if x.player.label == block.combo_with), None)
                if partner is not None and pair not in combos:
                    combos.add(pair)
                    els.append(self._combo_bracket(a.player, partner.player))

        return "\n".join(els)

    def _combo_bracket(self, a, b) -> str:
        """The arc under a double team."""
        x1, y1 = self._s(a.x, a.y)
        x2, y2 = self._s(b.x, b.y)
        dip = self.scale * 0.75
        mx, my = (x1 + x2) / 2, max(y1, y2) + dip
        return (
            f'<path d="M {x1:.1f} {y1 + self.scale * 0.5:.1f} '
            f'Q {mx:.1f} {my:.1f} {x2:.1f} {y2 + self.scale * 0.5:.1f}" '
            f'fill="none" stroke="{_BLOCK_COLOR}" stroke-width="1.4" '
            f'stroke-dasharray="4,3" opacity="0.65"/>'
        )

    # ── Quarterback ───────────────────────────────────────────────────────────

    def _qb(self) -> str:
        """His footwork, and the mesh point where the play gets decided."""
        els: list[str] = []
        for a in self.play.assignments:
            plan = a.qb
            if plan is None or len(plan.path) < 2:
                continue
            pts = [self._s(x, y)
                   for x, y in plan.absolute_path(a.player.x, a.player.y)]
            pts = _trim_start(pts, self.scale * 0.5)
            els.append(
                f'<path d="{_smooth_path(pts)}" fill="none" stroke="{_QB_COLOR}" '
                f'stroke-width="2.2" stroke-linecap="round" '
                f'stroke-linejoin="round" marker-end="url(#arr-qb)" '
                f'opacity="0.95"/>'
            )
            mesh = plan.mesh_point
            if mesh is not None:
                mx, my = self._s(a.player.x + mesh.x, a.player.y + mesh.y)
                r = self.scale * 0.28
                els.append(
                    f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{r:.1f}" '
                    f'fill="none" stroke="{_QB_COLOR}" stroke-width="1.8" '
                    f'opacity="0.95"/>'
                )
        return "\n".join(els)

    def _reads(self) -> str:
        """Number the progression so the play says what he works, in order."""
        plan = self.play.qb
        if plan is None or not plan.reads:
            return ""
        els: list[str] = []
        for a in self.play.assignments:
            order = plan.read_order(a.player.label)
            if order is None:
                continue
            pts = a.absolute_waypoints()
            if len(pts) < 2:
                continue
            (px, py), (ex, ey) = pts[-2], pts[-1]
            dx, dy = ex - px, ey - py
            length = (dx * dx + dy * dy) ** 0.5 or 1.0
            # sit the marker just off the end of the route, on the outside
            ox, oy = -dy / length * 1.3, dx / length * 1.3
            cx, cy = self._s(ex + ox, ey + oy)
            r = max(6.0, self.scale * 0.36)
            els.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                f'fill="{_READ_FILL}" stroke="{_QB_COLOR}" stroke-width="1.4" '
                f'opacity="0.92"/>'
            )
            els.append(
                f'<text x="{cx:.1f}" y="{cy + r * 0.36:.1f}" text-anchor="middle" '
                f'fill="{_READ_TEXT}" font-family="Arial,sans-serif" '
                f'font-size="{r * 1.05:.0f}" font-weight="bold">{order}</text>'
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

            abs_pts = a.absolute_waypoints()

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

    # ── Defensive assignments ─────────────────────────────────────────────────

    @property
    def _ball_x(self) -> float:
        """Zones move with the ball, so a boundary flat is a smaller area."""
        sit = self.play.situation
        if sit is None or sit.hash_mark is None:
            return 0.0
        return self.field.hash_x(sit.hash_mark)

    def _defense_assignments(self) -> str:
        from ..models.defense import DefensiveRole, zone_size

        if not self.play.defense:
            return ""
        els: list[str] = []
        offense = {a.player.label: a.player for a in self.play.assignments}

        for d in self.play.defense.players:
            call = d.assignment
            if call is None:
                continue

            if call.role is DefensiveRole.ZONE or (
                    call.role is DefensiveRole.ROBOT and call.zone):
                spot = call.landmark(self.field, self._ball_x)
                if spot is None:
                    continue
                if self.zones:
                    half_w, half_h = zone_size(call.zone)
                    cx, cy = self._s(*spot)
                    els.append(
                        f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" '
                        f'rx="{half_w * self.scale * _ZONE_SCALE:.1f}" '
                        f'ry="{half_h * self.scale * _ZONE_SCALE:.1f}" '
                        f'fill="{_ZONE_FILL}" stroke="{_DEF_ASSIGN}" '
                        f'stroke-width="1" stroke-dasharray="5,6" opacity="0.45"/>'
                    )
                els.append(self._def_arrow((d.x, d.y), spot, dashed=True,
                                           max_yards=6.0))

            elif call.role is DefensiveRole.MAN and call.covers in offense:
                target = offense[call.covers]
                els.append(self._def_arrow((d.x, d.y), (target.x, target.y),
                                           dashed=False, gap=0.55,
                                           min_yards=2.2))

            elif call.path:
                pts = [self._s(x, y) for x, y in call.absolute_path(d.x, d.y)]
                pts = _trim_start(pts, self.scale * 0.5)
                els.append(
                    f'<path d="{_smooth_path(pts)}" fill="none" '
                    f'stroke="{_DEF_ASSIGN}" stroke-width="2.2" '
                    f'stroke-linecap="round" marker-end="url(#arr-def)" '
                    f'opacity="0.9"/>'
                )

        return "\n".join(els)

    def _def_arrow(self, start: tuple[float, float], end: tuple[float, float],
                   dashed: bool, gap: float = 0.5,
                   max_yards: Optional[float] = None,
                   min_yards: float = 0.0) -> str:
        """
        A drop is drawn as a short arrow toward the landmark rather than a line
        all the way across the field. A press corner standing on his receiver
        still gets a visible mark, which is what `min_yards` is for.
        """
        sx, sy = self._s(*start)
        ex, ey = self._s(*end)
        dx, dy = ex - sx, ey - sy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1e-6:                       # exactly on top of him
            dx, dy, dist = 0.0, -self.scale, self.scale
        ux, uy = dx / dist, dy / dist

        if max_yards is not None:
            dist = min(dist, max_yards * self.scale)

        trim = self.scale * gap
        visible = dist - 2 * trim
        floor = min_yards * self.scale
        if visible < floor:
            visible = floor
        sx += ux * trim
        sy += uy * trim
        ex, ey = sx + ux * visible, sy + uy * visible

        dash = ' stroke-dasharray="7,5"' if dashed else ""
        return (
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="{_DEF_ASSIGN}" stroke-width="2"{dash} '
            f'marker-end="url(#arr-def)" opacity="0.85"/>'
        )

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

def _trim_start(pts: list[tuple[float, float]], amount: float
                ) -> list[tuple[float, float]]:
    """Pull a path's first point back so it starts at the edge of the circle."""
    if len(pts) < 2 or amount <= 0:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[1]
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    if length <= amount:
        return pts
    return [(x0 + dx / length * amount, y0 + dy / length * amount), *pts[1:]]


def _block_cap(svg_pts: list[tuple[float, float]], scale: float,
               is_cut: bool = False) -> str:
    """
    The bar across the end of a block path — the mark that says "engaged",
    and the reason a block reads differently from a route at a glance.
    """
    (x0, y0), (x1, y1) = svg_pts[-2], svg_pts[-1]
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    nx, ny = -dy / length, dx / length          # unit normal
    half = scale * 0.42

    if is_cut:
        # a slash through the end instead of a bar
        ux, uy = dx / length * half, dy / length * half
        return (
            f'<line x1="{x1 - ux - nx * half:.1f}" y1="{y1 - uy - ny * half:.1f}" '
            f'x2="{x1 + ux + nx * half:.1f}" y2="{y1 + uy + ny * half:.1f}" '
            f'stroke="{_BLOCK_COLOR}" stroke-width="{_BLOCK_WIDTH}" '
            f'stroke-linecap="round" opacity="0.88"/>'
        )
    return (
        f'<line x1="{x1 - nx * half:.1f}" y1="{y1 - ny * half:.1f}" '
        f'x2="{x1 + nx * half:.1f}" y2="{y1 + ny * half:.1f}" '
        f'stroke="{_BLOCK_COLOR}" stroke-width="{_BLOCK_WIDTH}" '
        f'stroke-linecap="round" opacity="0.88"/>'
    )


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
