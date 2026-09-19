"""
SVG renderer for Play objects.

Field coordinate system → SVG pixel system:
  field x  →  svg x   (left = negative, right = positive; both increase rightward)
  field y  →  svg y   (field +y = downfield, but SVG y increases downward, so we flip)

Resulting transform:
  svg_x = (field_x - x_min) * scale + pad
  svg_y = (y_max  - field_y) * scale + pad

Colours come from a theme (see `theme.py`) so the SVG, the PDF and the browser
designer draw the same diagram. Every part of the drawing is a layer that can
be left out:

    play.render(theme="paper", hide=["defense", "zones"]).save("mesh.svg")
"""
from __future__ import annotations
import html
import math
import os
from typing import TYPE_CHECKING, Iterable, Optional, Union

from .theme import FONT, Theme, layer_set, theme_for

if TYPE_CHECKING:
    from ..models.play import Play

# The zone areas are drawn smaller than they really are, or five overlapping
# bubbles hide the play.
_ZONE_SCALE = 0.7

_PLAY_TYPE_LABELS = {"rpo": "RPO"}


def zone_drop_target(start: tuple[float, float], spot: tuple[float, float],
                     half_w: float, half_h: float,
                     scale: float = _ZONE_SCALE) -> tuple[tuple[float, float], bool]:
    """
    Where a zone drop's arrow ends, in field yards: on the edge of the drawn
    area, on the line from its landmark to the defender, so the arrow meets
    the zone he owns. A defender already standing inside his area points at
    the landmark instead. Returns (point, inside).
    """
    aw, ah = half_w * scale, half_h * scale
    dx, dy = start[0] - spot[0], start[1] - spot[1]
    k = math.sqrt((dx / aw) ** 2 + (dy / ah) ** 2)
    if k <= 1.0:
        return spot, True
    return (spot[0] + dx / k, spot[1] + dy / k), False


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
        theme: Union[Theme, str, None] = None,
        layers: Optional[Iterable[str]] = None,
        hide: Optional[Iterable[str]] = None,
    ):
        from ..models.field import field_for
        self.play    = play
        self.scale   = scale
        self.x_range = x_range
        self.y_range = y_range
        self.pad     = padding
        self.field   = field_for(level)
        self.theme   = theme_for(theme)
        self.layers  = layer_set(layers, hide)
        if not zones:
            self.layers = self.layers - {"zones"}

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self) -> str:
        on = self.layers
        parts = [
            self._defs(),
            self._field(),
            self._motions() if "motion" in on else "",
            self._blocks() if "blocks" in on else "",
            self._qb() if "qb" in on else "",
            self._routes() if "routes" in on else "",
            self._reads() if "reads" in on else "",
            self._defense_assignments() if "defense" in on else "",
            self._defense_players() if "defense" in on else "",
            self._players(),
            self._title() if "title" in on else "",
        ]
        return self._wrap("\n".join(p for p in parts if p))

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

    def _text(self, x: float, y: float, text: str, fill: str, size: float,
              weight: Optional[int] = None, anchor: Optional[str] = None,
              opacity: Optional[float] = None) -> str:
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"']
        if anchor:
            attrs.append(f'text-anchor="{anchor}"')
        attrs += [f'fill="{fill}"', f'font-family="{FONT}"',
                  f'font-size="{size:g}"']
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity:g}"')
        return f'<text {" ".join(attrs)}>{html.escape(str(text))}</text>'

    # ── SVG structure ─────────────────────────────────────────────────────────

    def _wrap(self, content: str) -> str:
        w, h = self._width, self._height
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'{content}\n</svg>'
        )

    def _defs(self) -> str:
        T = self.theme

        def arrowhead(id_: str, color: str) -> str:
            return (
                f'<marker id="{id_}" markerWidth="9" markerHeight="7" '
                f'refX="8" refY="3.5" orient="auto" markerUnits="userSpaceOnUse">'
                f'<polygon points="0 0.5, 9 3.5, 0 6.5" fill="{color}"/>'
                f'</marker>'
            )
        return (
            "<defs>\n"
            + "  " + arrowhead("arr-route",  T.route) + "\n"
            + "  " + arrowhead("arr-run",    T.run) + "\n"
            + "  " + arrowhead("arr-motion", T.motion) + "\n"
            + "  " + arrowhead("arr-def",    T.def_assign) + "\n"
            + "  " + arrowhead("arr-qb",     T.qb) + "\n"
            + "</defs>"
        )

    # ── Field background ──────────────────────────────────────────────────────

    def _spot(self) -> Optional[int]:
        """Yards from the line of scrimmage to the opponent's goal, if known."""
        sit = self.play.situation
        if sit is None or sit.yard_line is None:
            return None
        return int(round(sit.yard_line))

    def _goal_y(self) -> Optional[float]:
        """Where the goal line is, in yards past the line of scrimmage."""
        spot = self._spot()
        return None if spot is None else float(spot)

    def _phase(self) -> int:
        """
        Which yards carry the five-yard lines. Without a ball spot the
        scrimmage line sits on one; with a spot, the grid is the real one
        and the ball is wherever it was placed.
        """
        spot = self._spot()
        return 0 if spot is None else spot % 5

    def _field(self) -> str:
        T = self.theme
        els: list[str] = []
        w, h = self._width, self._height
        side = self.field.sideline
        x_lo, x_hi = self.x_range
        y_lo, y_hi = self.y_range

        # The surface, with the mowing pattern on the five-yard grid
        phase = self._phase()
        els.append(f'<rect width="{w}" height="{h}" fill="{T.field}"/>')
        for y_yd in range(phase - 5, int(y_hi) + 5, 10):
            y0, y1 = self._sy(y_yd + 5), self._sy(y_yd)
            els.append(
                f'<rect x="0" y="{min(y0, y1):.1f}" width="{w}" '
                f'height="{abs(y1 - y0):.1f}" fill="{T.field_alt}"/>'
            )

        # The end zone, when the ball spot says it is in view
        goal = self._goal_y()
        if goal is not None and y_lo < goal < y_hi:
            top, gy = self._sy(y_hi), self._sy(goal)
            els.append(
                f'<rect x="0" y="{top:.1f}" width="{w}" height="{gy - top:.1f}" '
                f'fill="{T.endzone}"/>'
            )

        # Out of bounds, past the real sidelines (53 1/3 yards apart)
        if x_lo < -side:
            els.append(f'<rect x="0" y="0" width="{self._sx(-side):.1f}" '
                       f'height="{h}" fill="{T.oob}"/>')
        if x_hi > side:
            sx = self._sx(side)
            els.append(f'<rect x="{sx:.1f}" y="0" width="{w - sx:.1f}" '
                       f'height="{h}" fill="{T.oob}"/>')

        # Yard lines between the sidelines; the line of scrimmage is solid ink
        lx0, lx1 = self._sx(max(x_lo, -side)), self._sx(min(x_hi, side))
        for y_yd in range(int(y_lo), int(y_hi) + 1):
            if y_yd != 0 and y_yd % 5 != phase:
                continue
            y_s = self._sy(y_yd)
            if y_yd == 0:
                els.append(
                    f'<line x1="{lx0:.1f}" y1="{y_s:.1f}" x2="{lx1:.1f}" y2="{y_s:.1f}" '
                    f'stroke="{T.los}" stroke-width="2.2"/>'
                )
            else:
                els.append(
                    f'<line x1="{lx0:.1f}" y1="{y_s:.1f}" x2="{lx1:.1f}" y2="{y_s:.1f}" '
                    f'stroke="{T.line}" stroke-width="1"/>'
                )
        if goal is not None and y_lo < goal < y_hi and goal != 0:
            gy = self._sy(goal)
            els.append(
                f'<line x1="{lx0:.1f}" y1="{gy:.1f}" x2="{lx1:.1f}" y2="{gy:.1f}" '
                f'stroke="{T.los}" stroke-width="2"/>'
            )

        # Hash marks (short ticks)
        hash_x = self.field.hash_from_center
        for hx in (-hash_x, hash_x):
            sx = self._sx(hx)
            for y_yd in range(int(y_lo), int(y_hi) + 1):
                sy = self._sy(y_yd)
                tick = self.scale * 0.25
                els.append(
                    f'<line x1="{sx - tick:.1f}" y1="{sy:.1f}" x2="{sx + tick:.1f}" y2="{sy:.1f}" '
                    f'stroke="{T.hash}" stroke-width="1.5"/>'
                )

        # Sidelines
        for field_x in (-side, side):
            if not (x_lo <= field_x <= x_hi):
                continue
            sx = self._sx(field_x)
            els.append(
                f'<line x1="{sx:.1f}" y1="{self._sy(y_hi):.1f}" '
                f'x2="{sx:.1f}" y2="{self._sy(y_lo):.1f}" '
                f'stroke="{T.sideline}" stroke-width="2"/>'
            )

        els.extend(self._numbers())

        # Ball spot on the hash this play is run from
        if self.play.situation is not None and self.play.situation.hash_mark:
            bx, by = self._s(self.field.hash_x(self.play.situation.hash_mark), 0)
            els.append(
                f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{self.scale * 0.3:.1f}" '
                f'ry="{self.scale * 0.18:.1f}" fill="{T.ball}" '
                f'stroke="{T.los}" stroke-width="1"/>'
            )
        return "\n".join(els)

    def _numbers(self) -> list[str]:
        """Yard numbers on the tens, once the ball spot pins the field down."""
        sit = self.play.situation
        if sit is None or sit.yard_line is None:
            return []
        T = self.theme
        els: list[str] = []
        fs = self.scale * 0.95
        nx = self.field.sideline - self.field.numbers_from_sideline
        spot = self._spot()
        for y_yd in range(int(self.y_range[0]), int(self.y_range[1]) + 1):
            to_goal = spot - y_yd
            if to_goal % 10 or not (0 < to_goal < 100):
                continue
            label = str(to_goal if to_goal <= 50 else 100 - to_goal)
            ys = self._sy(y_yd) + fs * 0.36
            for fx in (-nx, nx):
                if not (self.x_range[0] < fx < self.x_range[1]):
                    continue
                els.append(self._text(self._sx(fx), ys, label, T.number, fs,
                                      weight=700, anchor="middle"))
        return els

    # ── Pre-snap motion ───────────────────────────────────────────────────────

    def _motions(self) -> str:
        """Dashed trail from the pre-snap alignment to where the ball is snapped."""
        T = self.theme
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
                f'fill="none" stroke="{T.motion}" stroke-width="1.8" '
                f'stroke-dasharray="5,4" stroke-linecap="round" '
                f'marker-end="url(#arr-motion)" opacity="0.9"/>'
            )
            # Ghost of the original alignment.
            gsx, gsy = self._s(fx, fy)
            r = self.scale * 0.42
            els.append(
                f'<circle cx="{gsx:.1f}" cy="{gsy:.1f}" r="{r:.1f}" fill="none" '
                f'stroke="{T.motion}" stroke-width="1.4" stroke-dasharray="3,3" '
                f'opacity="0.75"/>'
            )
            if a.motion_type:
                els.append(self._text(gsx, gsy - r - 4, a.motion_type.upper(),
                                      T.motion, 9, weight=700, anchor="middle",
                                      opacity=0.9))
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

        T = self.theme
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
                f'stroke="{T.block}" stroke-width="2.4" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
            )
            els.append(_block_cap(svg_pts, self.scale, T.block,
                                  block.kind is BlockKind.CUT))

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
            f'fill="none" stroke="{self.theme.block}" stroke-width="1.4" '
            f'stroke-dasharray="4,3" opacity="0.65"/>'
        )

    # ── Quarterback ───────────────────────────────────────────────────────────

    def _qb(self) -> str:
        """His footwork, and the mesh point where the play gets decided."""
        T = self.theme
        els: list[str] = []
        for a in self.play.assignments:
            plan = a.qb
            if plan is None or len(plan.path) < 2:
                continue
            pts = [self._s(x, y)
                   for x, y in plan.absolute_path(a.player.x, a.player.y)]
            pts = _trim_start(pts, self.scale * 0.5)
            els.append(
                f'<path d="{_smooth_path(pts)}" fill="none" stroke="{T.qb}" '
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
                    f'fill="none" stroke="{T.qb}" stroke-width="1.8" '
                    f'opacity="0.95"/>'
                )
        return "\n".join(els)

    def _reads(self) -> str:
        """Number the progression so the play says what he works, in order."""
        plan = self.play.qb
        if plan is None or not plan.reads:
            return ""
        T = self.theme
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
                f'fill="{T.read_fill}" stroke="{T.qb}" stroke-width="1.4" '
                f'opacity="0.95"/>'
            )
            els.append(self._text(cx, cy + r * 0.36, order, T.read_text,
                                  round(r * 1.05), weight=700, anchor="middle"))
        return "\n".join(els)

    # ── Routes ────────────────────────────────────────────────────────────────

    def _routes(self) -> str:
        T = self.theme
        els: list[str] = []
        for a in self.play.assignments:
            if a.route is None:
                continue
            rt = a.route.route_type.value
            if rt == "block":
                continue   # linemen are drawn by the blocking layer

            abs_pts = a.absolute_waypoints()
            if a.is_ball_carrier or rt == "run":
                color, marker, stroke_w = T.run, "url(#arr-run)", 2.8
            else:
                color, marker, stroke_w = T.route, "url(#arr-route)", 2.4

            svg_pts = [self._s(x, y) for x, y in abs_pts]
            els.append(
                f'<path d="{_smooth_path(svg_pts)}" fill="none" stroke="{color}" '
                f'stroke-width="{stroke_w}" stroke-linecap="round" '
                f'stroke-linejoin="round" marker-end="{marker}" opacity="0.94"/>'
            )
        return "\n".join(els)

    # ── Players ───────────────────────────────────────────────────────────────

    def _players(self) -> str:
        T = self.theme
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
            has_ball = a.is_ball_carrier or p.position.value == "QB"
            stroke = T.ball_ring if has_ball else T.offense_stroke
            width = 2.2 if has_ball else 1.4
            els.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r}" '
                f'fill="{T.offense_fill}" stroke="{stroke}" stroke-width="{width}"/>'
            )
            fs = 9 if len(p.label) > 2 else 10
            els.append(self._text(sx, sy + fs * 0.37, p.label, T.offense_text,
                                  fs, weight=700, anchor="middle"))
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
        T = self.theme
        draw_zones = "zones" in self.layers
        draw_calls = "coverage" in self.layers
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
                half_w, half_h = zone_size(call.zone)
                if draw_zones:
                    cx, cy = self._s(*spot)
                    els.append(
                        f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" '
                        f'rx="{half_w * self.scale * _ZONE_SCALE:.1f}" '
                        f'ry="{half_h * self.scale * _ZONE_SCALE:.1f}" '
                        f'fill="{T.zone_fill}" stroke="{T.zone_stroke}" '
                        f'stroke-width="1"/>'
                    )
                    # the zone says whose it is, even where the drops cross
                    els.append(self._text(cx, cy + 3.5, d.label, T.def_assign, 9,
                                          weight=700, anchor="middle", opacity=0.9))
                if draw_calls and draw_zones:
                    # the drop runs all the way to the area it owns
                    end, inside = zone_drop_target((d.x, d.y), spot, half_w, half_h)
                    els.append(self._def_arrow((d.x, d.y), end, dashed=True,
                                               end_gap=None if inside else 0.0,
                                               min_yards=1.2 if inside else 0.0))
                elif draw_calls:
                    # no areas drawn: a short arrow says which way he drops
                    els.append(self._def_arrow((d.x, d.y), spot, dashed=True,
                                               max_yards=6.0))

            elif not draw_calls:
                continue

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
                    f'stroke="{T.def_assign}" stroke-width="2.2" '
                    f'stroke-linecap="round" marker-end="url(#arr-def)" '
                    f'opacity="0.9"/>'
                )

        return "\n".join(els)

    def _def_arrow(self, start: tuple[float, float], end: tuple[float, float],
                   dashed: bool, gap: float = 0.5,
                   max_yards: Optional[float] = None,
                   min_yards: float = 0.0,
                   end_gap: Optional[float] = None) -> str:
        """
        An assignment arrow, trimmed clear of the defender at the start and,
        by `end_gap` (default: the same as `gap`), clear of its target. A zone
        drop ends exactly on its area's edge, so it passes `end_gap=0`. A press
        corner standing on his receiver still gets a visible mark, which is
        what `min_yards` is for.
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
        trim_end = self.scale * (gap if end_gap is None else end_gap)
        visible = dist - trim - trim_end
        floor = min_yards * self.scale
        if visible < floor:
            visible = floor
        sx += ux * trim
        sy += uy * trim
        ex, ey = sx + ux * visible, sy + uy * visible

        dash = ' stroke-dasharray="7,5"' if dashed else ""
        return (
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="{self.theme.def_assign}" stroke-width="2"{dash} '
            f'marker-end="url(#arr-def)" opacity="0.85"/>'
        )

    # ── Defensive players ─────────────────────────────────────────────────────

    def _defense_players(self) -> str:
        if not self.play.defense:
            return ""
        T = self.theme
        els: list[str] = []
        for dp in self.play.defense.players:
            sx, sy = self._sx(dp.x), self._sy(dp.y)
            half = 10
            # Squares for the defense, so they read differently from the offense
            els.append(
                f'<rect x="{sx - half:.1f}" y="{sy - half:.1f}" '
                f'width="{half * 2}" height="{half * 2}" rx="2.5" '
                f'fill="{T.defense_fill}" stroke="{T.defense_stroke}" '
                f'stroke-width="1.3"/>'
            )
            fs = 9 if len(dp.label) > 2 else 10
            els.append(self._text(sx, sy + fs * 0.37, dp.label, T.defense_text,
                                  fs, weight=700, anchor="middle"))
        return "\n".join(els)

    # ── Title ─────────────────────────────────────────────────────────────────

    def _title(self) -> str:
        """A name plate in the corner nothing else needs — the backfield's left."""
        T = self.theme
        play = self.play
        kind = play.play_type.value
        kind = _PLAY_TYPE_LABELS.get(kind, kind.capitalize())
        sub = f"{play.formation.name}  ·  {play.formation.personnel} personnel  ·  {kind}"
        x, h = 14.0, self._height
        return (
            self._text(x, h - 26, play.name, T.title, 14, weight=700) + "\n"
            + self._text(x, h - 10, sub, T.subtitle, 10.5)
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


def _block_cap(svg_pts: list[tuple[float, float]], scale: float, color: str,
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
            f'stroke="{color}" stroke-width="2.4" '
            f'stroke-linecap="round" opacity="0.9"/>'
        )
    return (
        f'<line x1="{x1 - nx * half:.1f}" y1="{y1 - ny * half:.1f}" '
        f'x2="{x1 + nx * half:.1f}" y2="{y1 + ny * half:.1f}" '
        f'stroke="{color}" stroke-width="2.4" '
        f'stroke-linecap="round" opacity="0.9"/>'
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
