"""
PDF exporter for Playbook objects.

Uses reportlab for pure-Python PDF generation.

Layout options
--------------
plays_per_page=1  Portrait letter, one large play per page
plays_per_page=2  Landscape letter, two plays side-by-side per page
plays_per_page=4  Landscape letter, 2×2 grid (four plays per page)

Each page shows: diagram + play name + formation + route table + tags.
A cover page lists all plays in the playbook.
"""
from __future__ import annotations
import math
import os
from datetime import date
from typing import TYPE_CHECKING

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

if TYPE_CHECKING:
    from ..models.play import Play, Playbook

# ── Colours ───────────────────────────────────────────────────────────────────
# Everything comes from the shared theme table, so a PDF page, an SVG and the
# designer show the same diagram.
from .theme import theme_for as _theme_for, to_rgba as _to_rgba


def _rl(color: str):
    r, g, b, a = _to_rgba(color)
    return colors.Color(r, g, b, alpha=a)


class _Palette:
    """The theme as reportlab colours, under the names the drawing code uses."""

    def __init__(self, theme):
        t = theme
        self.theme = t
        self.FIELD      = _rl(t.field)
        self.FIELD_ALT  = _rl(t.field_alt)
        self.OOB        = _rl(t.oob)
        self.LINE       = _rl(t.line)
        self.LOS        = _rl(t.los)
        self.HASH       = _rl(t.hash)
        self.SIDELINE   = _rl(t.sideline)
        self.PLAYER     = _rl(t.offense_fill)
        self.PLAYER_STK = _rl(t.offense_stroke)
        self.BALL_RING  = _rl(t.ball_ring)
        self.LABEL      = _rl(t.offense_text)
        self.ROUTE      = _rl(t.route)
        self.AMBER      = _rl(t.run)
        self.BLOCK      = _rl(t.block)
        self.QB         = _rl(t.qb)
        self.READ_FILL  = _rl(t.read_fill)
        self.READ_TEXT  = _rl(t.read_text)
        self.DEF_ASSIGN = _rl(t.def_assign)
        self.DEF_FILL   = _rl(t.defense_fill)
        self.DEF_STROKE = _rl(t.defense_stroke)
        self.DEF_TEXT   = _rl(t.defense_text)
        self.ZONE_FILL  = _rl(t.zone_fill)
        self.ZONE_STROKE = _rl(t.zone_stroke)
        self.PAGE_BG    = _rl(t.page_bg)
        self.PAGE_TEXT  = _rl(t.page_text)
        self.MUTED      = _rl(t.page_muted)
        self.ACCENT     = _rl(t.page_rule)


from ..models.field import field_for as _field_for
from .svg import _ZONE_SCALE, zone_drop_target


class PDFExporter:
    """Render a Playbook to a multi-page PDF file."""

    # Field view in yards
    _X_RANGE = (-29.0, 29.0)   # 58 yards wide
    _Y_RANGE = (-7.0,  21.0)   # 28 yards tall

    def __init__(
        self,
        playbook: "Playbook",
        path: str,
        plays_per_page: int = 1,
        level=None,
        theme=None,
    ):
        self.playbook = playbook
        self.theme = _theme_for(theme)
        self.c = _Palette(self.theme)
        self.path = path
        self.ppp = plays_per_page
        self.field = _field_for(level)

        if plays_per_page == 1:
            self._page_size = letter          # 612 × 792 pt  (portrait)
        else:
            self._page_size = landscape(letter)  # 792 × 612 pt  (landscape)

        self._pw, self._ph = self._page_size
        self._margin = 36.0  # 0.5 inch

    # ── Public API ─────────────────────────────────────────────────────────────

    def export(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        c = rl_canvas.Canvas(self.path, pagesize=self._page_size)
        c.setTitle(self.playbook.name)

        self._cover_page(c)
        c.showPage()

        if self.ppp == 1:
            for play in self.playbook.plays:
                self._single_play_page(c, play)
                c.showPage()
        elif self.ppp == 2:
            plays = list(self.playbook.plays)
            for i in range(0, len(plays), 2):
                pair = plays[i:i + 2]
                self._two_play_page(c, pair)
                c.showPage()
        elif self.ppp == 4:
            plays = list(self.playbook.plays)
            for i in range(0, len(plays), 4):
                group = plays[i:i + 4]
                self._four_play_page(c, group)
                c.showPage()

        c.save()
        print(f"PDF saved: {os.path.abspath(self.path)}  ({len(self.playbook.plays)} plays)")

    # ── Cover page ─────────────────────────────────────────────────────────────

    def _cover_page(self, c: rl_canvas.Canvas) -> None:
        pw, ph = self._pw, self._ph
        m = self._margin

        # Dark background
        c.setFillColor(self.c.PAGE_BG)
        c.rect(0, 0, pw, ph, fill=1, stroke=0)

        # Accent bar left edge
        c.setFillColor(self.c.ACCENT)
        c.rect(0, 0, 6, ph, fill=1, stroke=0)

        # Title
        c.setFillColor(self.c.PAGE_TEXT)
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(pw / 2, ph * 0.62, self.playbook.name)

        if self.playbook.team:
            c.setFont("Helvetica", 18)
            c.setFillColor(self.c.ACCENT)
            c.drawCentredString(pw / 2, ph * 0.55, self.playbook.team)

        if self.playbook.season:
            c.setFont("Helvetica", 14)
            c.setFillColor(self.c.MUTED)
            c.drawCentredString(pw / 2, ph * 0.50, str(self.playbook.season))

        # Divider
        c.setStrokeColor(self.c.ACCENT)
        c.setLineWidth(1.5)
        c.line(pw * 0.2, ph * 0.46, pw * 0.8, ph * 0.46)

        # Stats row
        c.setFont("Helvetica", 12)
        c.setFillColor(self.c.MUTED)
        total = len(self.playbook.plays)
        from ..models.play import PlayType
        n_pass = sum(1 for p in self.playbook.plays if p.play_type == PlayType.PASS)
        n_run  = sum(1 for p in self.playbook.plays if p.play_type == PlayType.RUN)
        n_rpo  = sum(1 for p in self.playbook.plays if p.play_type == PlayType.RPO)
        stats = f"{total} plays   |   {n_pass} pass   {n_run} run   {n_rpo} RPO"
        c.drawCentredString(pw / 2, ph * 0.41, stats)

        # Play index
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.c.ACCENT)
        c.drawString(m, ph * 0.35, "PLAY INDEX")
        c.setLineWidth(0.5)
        c.setStrokeColor(self.c.MUTED)
        c.line(m, ph * 0.34, pw - m, ph * 0.34)

        col_w = (pw - 2 * m) / 2
        for idx, play in enumerate(self.playbook.plays):
            col  = idx % 2
            row  = idx // 2
            x    = m + col * col_w
            y    = ph * 0.32 - row * 16
            if y < m + 20:
                break  # truncate if too many plays
            c.setFillColor(self.c.MUTED)
            c.setFont("Helvetica", 9)
            c.drawString(x, y, f"{idx + 1:>2}.")
            c.setFillColor(self.c.PAGE_TEXT)
            c.drawString(x + 16, y, play.name)
            c.setFillColor(self.c.MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(x + 16, y - 9, f"{play.formation.name}  |  {play.play_type.value}")

        # Footer
        c.setFillColor(self.c.MUTED)
        c.setFont("Helvetica", 8)
        c.drawRightString(pw - m, m, f"Generated {date.today().isoformat()} by chalktalk")

    # ── 1-per-page layout ─────────────────────────────────────────────────────

    def _single_play_page(self, c: rl_canvas.Canvas, play: "Play") -> None:
        pw, ph = self._pw, self._ph
        m = self._margin

        # Dark background
        c.setFillColor(self.c.PAGE_BG)
        c.rect(0, 0, pw, ph, fill=1, stroke=0)
        c.setFillColor(self.c.ACCENT)
        c.rect(0, 0, 4, ph, fill=1, stroke=0)

        # Header area
        header_y = ph - m
        c.setFillColor(self.c.PAGE_TEXT)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(pw / 2, header_y - 20, play.name)

        c.setFont("Helvetica", 11)
        c.setFillColor(self.c.MUTED)
        sub = f"{play.formation.name}   |   {play.formation.personnel} personnel   |   {play.play_type.value.upper()}"
        c.drawCentredString(pw / 2, header_y - 38, sub)

        # Divider
        c.setStrokeColor(self.c.ACCENT)
        c.setLineWidth(1)
        c.line(m, header_y - 46, pw - m, header_y - 46)

        # Diagram: centered, 88% of available width
        diag_w = (pw - 2 * m) * 0.88
        scale  = diag_w / (self._X_RANGE[1] - self._X_RANGE[0])
        diag_h = (self._Y_RANGE[1] - self._Y_RANGE[0]) * scale
        diag_x = (pw - diag_w) / 2
        diag_y = header_y - 56 - diag_h  # bottom-left of diagram

        self._draw_field(c, diag_x, diag_y, scale)
        self._draw_blocks(c, play, diag_x, diag_y, scale)
        self._draw_qb(c, play, diag_x, diag_y, scale)
        self._draw_routes(c, play, diag_x, diag_y, scale)
        self._draw_reads(c, play, diag_x, diag_y, scale)
        self._draw_defense(c, play, diag_x, diag_y, scale)
        self._draw_players(c, play, diag_x, diag_y, scale)

        # Route table below diagram
        table_y = diag_y - 24
        self._draw_route_table(c, play, m, table_y, pw - 2 * m)

        # Description
        if play.description:
            desc_y = table_y - 44
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(self.c.MUTED)
            c.drawString(m, desc_y, play.description)

        # Tags
        tag_y = table_y - 58
        if play.tags:
            self._draw_tags(c, play.tags, m, tag_y)

        # Footer
        c.setFillColor(self.c.MUTED)
        c.setFont("Helvetica", 8)
        c.drawRightString(pw - m, m, self.playbook.name)

    # ── 2-per-page layout ─────────────────────────────────────────────────────

    def _two_play_page(self, c: rl_canvas.Canvas, plays: list["Play"]) -> None:
        pw, ph = self._pw, self._ph
        m = self._margin
        gap = 20.0

        c.setFillColor(self.c.PAGE_BG)
        c.rect(0, 0, pw, ph, fill=1, stroke=0)
        c.setFillColor(self.c.ACCENT)
        c.rect(0, 0, 4, ph, fill=1, stroke=0)

        cell_w = (pw - 2 * m - gap) / 2
        scale  = cell_w / (self._X_RANGE[1] - self._X_RANGE[0])
        diag_h = (self._Y_RANGE[1] - self._Y_RANGE[0]) * scale

        origins = [
            (m, ph - m - 50 - diag_h),
            (m + cell_w + gap, ph - m - 50 - diag_h),
        ]

        for idx, play in enumerate(plays):
            dx, dy = origins[idx]

            # Play header
            c.setFillColor(self.c.PAGE_TEXT)
            c.setFont("Helvetica-Bold", 13)
            c.drawString(dx, dy + diag_h + 32, play.name)
            c.setFont("Helvetica", 9)
            c.setFillColor(self.c.MUTED)
            c.drawString(dx, dy + diag_h + 18,
                         f"{play.formation.name}  |  {play.play_type.value.upper()}")

            self._draw_field(c, dx, dy, scale)
            self._draw_blocks(c, play, dx, dy, scale)
            self._draw_qb(c, play, dx, dy, scale)
            self._draw_routes(c, play, dx, dy, scale)
            self._draw_reads(c, play, dx, dy, scale)
            self._draw_defense(c, play, dx, dy, scale)
            self._draw_players(c, play, dx, dy, scale)

            # Route table compact
            self._draw_route_table(c, play, dx, dy - 20, cell_w, compact=True)

        # Footer
        c.setFillColor(self.c.MUTED)
        c.setFont("Helvetica", 8)
        c.drawRightString(pw - m, m, self.playbook.name)

    # ── 4-per-page layout ─────────────────────────────────────────────────────

    def _four_play_page(self, c: rl_canvas.Canvas, plays: list["Play"]) -> None:
        pw, ph = self._pw, self._ph
        m = self._margin
        gap = 16.0
        header_h = 44.0
        footer_h = m

        cell_w = (pw - 2 * m - gap) / 2
        # Use a tighter y range so diagrams aren't too short
        y_span = 24.0   # show -6 to +18 instead of full range
        scale  = cell_w / (self._X_RANGE[1] - self._X_RANGE[0])
        diag_h = y_span * scale

        available_h = ph - m - footer_h
        row_h = header_h + diag_h + 28  # diagram + titles + route line

        row_origins = [
            ph - m - row_h,
            ph - m - 2 * row_h - gap,
        ]
        col_origins = [m, m + cell_w + gap]

        for idx, play in enumerate(plays):
            row, col = divmod(idx, 2)
            if row >= 2:
                break
            dx = col_origins[col]
            dy = row_origins[row] + 28   # leave space for compact route line below

            # Tight y range for 4-up
            y_range = (-6.0, -6.0 + y_span)

            c.setFillColor(self.c.PAGE_TEXT)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(dx, dy + diag_h + 16, play.name)
            c.setFont("Helvetica", 8)
            c.setFillColor(self.c.MUTED)
            c.drawString(dx, dy + diag_h + 4,
                         f"{play.formation.name}  |  {play.play_type.value.upper()}")

            self._draw_field(c, dx, dy, scale, y_range=y_range)
            self._draw_blocks(c, play, dx, dy, scale, y_range=y_range)
            self._draw_qb(c, play, dx, dy, scale, y_range=y_range)
            self._draw_routes(c, play, dx, dy, scale, y_range=y_range)
            self._draw_reads(c, play, dx, dy, scale, y_range=y_range)
            self._draw_defense(c, play, dx, dy, scale, y_range=y_range)
            self._draw_players(c, play, dx, dy, scale, y_range=y_range)

            self._draw_route_table(c, play, dx, dy - 20, cell_w, compact=True)

        c.setFillColor(self.c.MUTED)
        c.setFont("Helvetica", 8)
        c.drawRightString(pw - m, m, self.playbook.name)

    # ── Field drawing ─────────────────────────────────────────────────────────

    def _draw_field(
        self,
        c: rl_canvas.Canvas,
        ox: float,
        oy: float,
        scale: float,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        xr = self._X_RANGE
        yr = y_range or self._Y_RANGE
        w  = (xr[1] - xr[0]) * scale
        h  = (yr[1] - yr[0]) * scale

        # Field background
        c.setFillColor(self.c.FIELD)
        c.rect(ox, oy, w, h, fill=1, stroke=0)
        side = self.field.sideline
        sx_l = ox + (-side - xr[0]) * scale
        sx_r = ox + (side - xr[0]) * scale

        # Alternating 5-yard bands
        c.setFillColor(self.c.FIELD_ALT)
        band_h = 5 * scale
        y_start = int(yr[0] // 5) * 5
        band_num = 0
        y_yd = y_start
        while y_yd < yr[1]:
            if band_num % 2 == 0:
                y_bot = max(yr[0], y_yd)
                y_top = min(yr[1], y_yd + 5)
                rl_bot = oy + (y_bot - yr[0]) * scale
                rl_top = oy + (y_top - yr[0]) * scale
                c.setFillColor(self.c.FIELD_ALT)
                c.rect(ox, rl_bot, w, rl_top - rl_bot, fill=1, stroke=0)
            y_yd += 5
            band_num += 1

        # Yard lines
        c.setLineWidth(0.5)
        for y_yd in range(int(yr[0]) - 1, int(yr[1]) + 2):
            if y_yd % 5 != 0:
                continue
            rl_y = oy + (y_yd - yr[0]) * scale
            if rl_y < oy or rl_y > oy + h:
                continue
            if y_yd == 0:
                c.setStrokeColor(self.c.LOS)
                c.setLineWidth(2.0)
                c.setDash(1, 0)
            else:
                c.setStrokeColor(self.c.LINE)
                c.setLineWidth(0.5)
                c.setDash(1, 0)
            c.line(max(ox, sx_l), rl_y, min(ox + w, sx_r), rl_y)

        c.setDash(1, 0)
        c.setLineWidth(0.5)

        # Hash mark ticks
        hash_x = self.field.hash_from_center
        for hx in (-hash_x, hash_x):
            sx = ox + (hx - xr[0]) * scale
            tick = scale * 0.22
            for y_yd in range(int(yr[0]) - 1, int(yr[1]) + 2):
                rl_y = oy + (y_yd - yr[0]) * scale
                if rl_y < oy or rl_y > oy + h:
                    continue
                c.setStrokeColor(self.c.HASH)
                c.setLineWidth(1.2)
                c.line(sx - tick, rl_y, sx + tick, rl_y)

        # Out of bounds past the real sidelines, then the sidelines themselves
        c.setFillColor(self.c.OOB)
        if sx_l > ox:
            c.rect(ox, oy, sx_l - ox, h, fill=1, stroke=0)
        if sx_r < ox + w:
            c.rect(sx_r, oy, ox + w - sx_r, h, fill=1, stroke=0)
        c.setStrokeColor(self.c.SIDELINE)
        c.setLineWidth(1.6)
        for sx in (sx_l, sx_r):
            if ox <= sx <= ox + w:
                c.line(sx, oy, sx, oy + h)

    # ── Routes ────────────────────────────────────────────────────────────────

    def _draw_blocks(
        self,
        c: rl_canvas.Canvas,
        play: "Play",
        ox: float,
        oy: float,
        scale: float,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        """Blocking, drawn the same way as the SVG renderer."""
        from ..models.block import BlockKind
        from ..templates.blocking import BASE

        yr = y_range or self._Y_RANGE
        xr = self._X_RANGE
        combos: set[frozenset] = set()
        to_rl = lambda fx, fy: (ox + (fx - xr[0]) * scale,  # noqa: E731
                                oy + (fy - yr[0]) * scale)

        for a in play.assignments:
            block = a.block
            if block is None:
                if a.route is not None and a.route.route_type.value == "block":
                    block = BASE()
                else:
                    continue

            pts = block.absolute_path(a.player.x, a.player.y)
            if len(pts) < 2:
                continue
            rl_pts = _trim_start([to_rl(fx, fy) for fx, fy in pts], scale * 0.42)

            c.setStrokeColor(self.c.BLOCK)
            c.setLineWidth(2.0)
            c.setLineCap(1)
            path = c.beginPath()
            _path_catmull_rom(path, rl_pts)
            c.drawPath(path, stroke=1, fill=0)
            _draw_block_cap(c, rl_pts, scale, block.kind is BlockKind.CUT)

            if block.combo_with:
                pair = frozenset((a.player.label, block.combo_with))
                partner = next((x for x in play.assignments
                                if x.player.label == block.combo_with), None)
                if partner is not None and pair not in combos:
                    combos.add(pair)
                    x1, y1 = to_rl(a.player.x, a.player.y)
                    x2, y2 = to_rl(partner.player.x, partner.player.y)
                    c.setLineWidth(1.2)
                    c.setDash(3, 3)
                    bracket = c.beginPath()
                    bracket.moveTo(x1, y1 - scale * 0.5)
                    bracket.curveTo((x1 + x2) / 2, min(y1, y2) - scale * 1.25,
                                    (x1 + x2) / 2, min(y1, y2) - scale * 1.25,
                                    x2, y2 - scale * 0.5)
                    c.drawPath(bracket, stroke=1, fill=0)
                    c.setDash(1, 0)

    def _draw_routes(
        self,
        c: rl_canvas.Canvas,
        play: "Play",
        ox: float,
        oy: float,
        scale: float,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        yr = y_range or self._Y_RANGE
        xr = self._X_RANGE

        for a in play.assignments:
            if a.route is None:
                continue
            if a.route.route_type.value == "block":
                continue

            abs_pts = a.absolute_waypoints()

            # Convert to reportlab coords
            rl_pts = [
                (ox + (fx - xr[0]) * scale,
                 oy + (fy - yr[0]) * scale)
                for fx, fy in abs_pts
            ]

            if a.is_ball_carrier or a.route.route_type.value == "run":
                stroke_color = self.c.AMBER
                lw = 2.5
            else:
                stroke_color = self.c.ROUTE
                lw = 2.0

            c.setStrokeColor(stroke_color)
            c.setLineWidth(lw)
            c.setLineCap(1)  # round cap

            p = c.beginPath()
            _path_catmull_rom(p, rl_pts)
            c.drawPath(p, stroke=1, fill=0)

            # Arrowhead at the last point
            if len(rl_pts) >= 2:
                ex, ey = rl_pts[-1]
                dx = ex - rl_pts[-2][0]
                dy = ey - rl_pts[-2][1]
                ah_size = max(4.0, scale * 0.45)
                _draw_arrowhead(c, ex, ey, dx, dy, ah_size, stroke_color)

    # ── Players ───────────────────────────────────────────────────────────────

    def _draw_players(
        self,
        c: rl_canvas.Canvas,
        play: "Play",
        ox: float,
        oy: float,
        scale: float,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        yr = y_range or self._Y_RANGE
        xr = self._X_RANGE
        seen: set[str] = set()

        for a in play.assignments:
            p = a.player
            key = f"{p.label}_{p.x}_{p.y}"
            if key in seen:
                continue
            seen.add(key)

            sx = ox + (p.x - xr[0]) * scale
            sy = oy + (p.y - yr[0]) * scale

            r = max(3.5, scale * (0.55 if p.is_ol else 0.65))
            has_ball = a.is_ball_carrier or p.position.value == "QB"
            c.setFillColor(self.c.PLAYER)
            c.setStrokeColor(self.c.BALL_RING if has_ball else self.c.PLAYER_STK)
            c.setLineWidth(1.8 if has_ball else 1.1)
            c.circle(sx, sy, r, fill=1, stroke=1)

            fs = max(5, min(10, int(r * 0.95)))
            c.setFillColor(self.c.LABEL)
            c.setFont("Helvetica-Bold", fs)
            c.drawCentredString(sx, sy - fs * 0.35, p.label)

    # ── Quarterback ───────────────────────────────────────────────────────────

    def _draw_qb(
        self,
        c: rl_canvas.Canvas,
        play: "Play",
        ox: float,
        oy: float,
        scale: float,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        yr = y_range or self._Y_RANGE
        xr = self._X_RANGE
        for a in play.assignments:
            plan = a.qb
            if plan is None or len(plan.path) < 2:
                continue
            pts = [(ox + (fx - xr[0]) * scale, oy + (fy - yr[0]) * scale)
                   for fx, fy in plan.absolute_path(a.player.x, a.player.y)]
            pts = _trim_start(pts, scale * 0.5)
            c.setStrokeColor(self.c.QB)
            c.setLineWidth(1.8)
            c.setLineCap(1)
            path = c.beginPath()
            _path_catmull_rom(path, pts)
            c.drawPath(path, stroke=1, fill=0)
            ex, ey = pts[-1]
            _draw_arrowhead(c, ex, ey, ex - pts[-2][0], ey - pts[-2][1],
                            max(3.5, scale * 0.4), self.c.QB)
            mesh = plan.mesh_point
            if mesh is not None:
                mx = ox + (a.player.x + mesh.x - xr[0]) * scale
                my = oy + (a.player.y + mesh.y - yr[0]) * scale
                c.setLineWidth(1.4)
                c.circle(mx, my, max(2.0, scale * 0.28), fill=0, stroke=1)

    def _draw_reads(
        self,
        c: rl_canvas.Canvas,
        play: "Play",
        ox: float,
        oy: float,
        scale: float,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        plan = play.qb
        coverage = play.defense.coverage if play.defense else None   # the look drawn with it
        if plan is None or not plan.reads_against(coverage):
            return
        yr = y_range or self._Y_RANGE
        xr = self._X_RANGE
        for a in play.assignments:
            order = plan.read_order(a.player.label, coverage)
            if order is None:
                continue
            pts = a.absolute_waypoints()
            if len(pts) < 2:
                continue
            (px, py), (ex, ey) = pts[-2], pts[-1]
            dx, dy = ex - px, ey - py
            length = (dx * dx + dy * dy) ** 0.5 or 1.0
            fx = ex - dy / length * 1.3
            fy = ey + dx / length * 1.3
            cx = ox + (fx - xr[0]) * scale
            cy = oy + (fy - yr[0]) * scale
            r = max(4.0, scale * 0.36)
            c.setFillColor(self.c.READ_FILL)
            c.setStrokeColor(self.c.QB)
            c.setLineWidth(1.1)
            c.circle(cx, cy, r, fill=1, stroke=1)
            fs = max(4, min(9, int(r * 1.05)))
            c.setFillColor(self.c.READ_TEXT)
            c.setFont("Helvetica-Bold", fs)
            c.drawCentredString(cx, cy - fs * 0.35, str(order))

    # ── Defense ───────────────────────────────────────────────────────────────

    def _draw_defense(
        self,
        c: rl_canvas.Canvas,
        play: "Play",
        ox: float,
        oy: float,
        scale: float,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        """Defensive alignment and, when the look has a call, what each man does."""
        from ..models.defense import DL_POSITIONS, LB_POSITIONS, DefensiveRole
        from ..models.defense import zone_size

        if not play.defense:
            return
        yr = y_range or self._Y_RANGE
        xr = self._X_RANGE
        to_rl = lambda fx, fy: (ox + (fx - xr[0]) * scale,   # noqa: E731
                                oy + (fy - yr[0]) * scale)
        offense = {a.player.label: a.player for a in play.assignments}
        ball_x = 0.0
        if play.situation is not None and play.situation.hash_mark:
            ball_x = self.field.hash_x(play.situation.hash_mark)

        # Assignments first, so the defenders sit on top of their own ink.
        c.setStrokeColor(self.c.DEF_ASSIGN)
        c.setLineWidth(1.6)
        c.setLineCap(1)
        for d in play.defense.players:
            call = d.assignment
            if call is None:
                continue
            if call.zone is not None:
                spot = call.landmark(self.field, ball_x)
                half_w, half_h = zone_size(call.zone)
                cx, cy = to_rl(*spot)
                c.saveState()
                c.setFillColor(self.c.ZONE_FILL)
                c.setStrokeColor(self.c.ZONE_STROKE)
                c.setLineWidth(0.8)
                c.ellipse(cx - half_w * scale * _ZONE_SCALE, cy - half_h * scale * _ZONE_SCALE,
                          cx + half_w * scale * _ZONE_SCALE, cy + half_h * scale * _ZONE_SCALE,
                          fill=1, stroke=1)
                # the zone says whose it is, and the drop runs to its edge
                fs = max(4.5, min(8.0, scale * 0.45))
                c.setFillColor(self.c.DEF_ASSIGN)
                c.setFont("Helvetica-Bold", fs)
                c.drawCentredString(cx, cy - fs * 0.35, d.label)
                c.restoreState()
                end, inside = zone_drop_target((d.x, d.y), spot, half_w, half_h)
                self._def_line(c, to_rl(d.x, d.y), to_rl(*end), scale,
                               min_yards=1.2 if inside else 0.0,
                               end_gap=None if inside else 0.0)
            elif call.role is DefensiveRole.MAN and call.covers in offense:
                target = offense[call.covers]
                self._def_line(c, to_rl(d.x, d.y), to_rl(target.x, target.y),
                               scale, min_yards=2.2)
            elif call.path:
                pts = [to_rl(fx, fy)
                       for fx, fy in call.absolute_path(d.x, d.y)]
                path = c.beginPath()
                _path_catmull_rom(path, _trim_start(pts, scale * 0.5))
                c.drawPath(path, stroke=1, fill=0)
                ex, ey = pts[-1]
                _draw_arrowhead(c, ex, ey, ex - pts[-2][0], ey - pts[-2][1],
                                max(4.0, scale * 0.4), self.c.DEF_ASSIGN)

        # Defenders: squares, so they read differently from the offense.
        for d in play.defense.players:
            sx, sy = to_rl(d.x, d.y)
            r = max(3.5, scale * 0.6)
            c.setFillColor(self.c.DEF_FILL)
            c.setStrokeColor(self.c.DEF_STROKE)
            c.setLineWidth(1.2)
            c.roundRect(sx - r, sy - r, r * 2, r * 2, 1.5, fill=1, stroke=1)
            fs = max(4, min(9, int(r * 0.85)))
            c.setFillColor(self.c.DEF_TEXT)
            c.setFont("Helvetica-Bold", fs)
            c.drawCentredString(sx, sy - fs * 0.35, d.label)

    def _def_line(self, c, start, end, scale: float,
                  max_yards: float | None = None,
                  min_yards: float = 0.0,
                  end_gap: float | None = None) -> None:
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1e-6:
            dx, dy, dist = 0.0, -scale, scale
        ux, uy = dx / dist, dy / dist
        if max_yards is not None:
            dist = min(dist, max_yards * scale)
        trim = scale * 0.5
        trim_end = trim if end_gap is None else scale * end_gap
        visible = max(dist - trim - trim_end, min_yards * scale)
        sx += ux * trim
        sy += uy * trim
        ex, ey = sx + ux * visible, sy + uy * visible
        c.setStrokeColor(self.c.DEF_ASSIGN)
        c.setLineWidth(1.6)
        c.line(sx, sy, ex, ey)
        _draw_arrowhead(c, ex, ey, ux, uy, max(3.5, scale * 0.38), self.c.DEF_ASSIGN)

    # ── Route table ───────────────────────────────────────────────────────────

    def _draw_route_table(
        self,
        c: rl_canvas.Canvas,
        play: "Play",
        x: float,
        y: float,
        width: float,
        compact: bool = False,
    ) -> None:
        rows = [
            (a.player.label, a.route.route_type.value if a.route else "-",
             a.is_ball_carrier)
            for a in play.assignments
            if a.route and a.route.route_type.value != "block"
        ]
        if not rows:
            return

        if compact:
            # Single-line summary
            summary = "  ".join(
                f"{lbl}:{rt.upper()}" + (" [BC]" if bc else "")
                for lbl, rt, bc in rows
            )
            c.setFont("Helvetica", 7.5)
            c.setFillColor(self.c.MUTED)
            c.drawString(x, y, summary)
        else:
            # 3-column table
            col_w = width / 3
            col = 0
            row_y = y
            for lbl, rt, bc in rows:
                cx = x + col * col_w
                c.setFillColor(self.c.ACCENT)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(cx, row_y, lbl)
                c.setFillColor(self.c.PAGE_TEXT)
                c.setFont("Helvetica", 9)
                suffix = "  [BC]" if bc else ""
                c.drawString(cx + 22, row_y, rt + suffix)
                col += 1
                if col >= 3:
                    col = 0
                    row_y -= 13

    def _draw_tags(
        self,
        c: rl_canvas.Canvas,
        tags: list[str],
        x: float,
        y: float,
    ) -> None:
        cx = x
        for tag in tags:
            label = f"  {tag}  "
            c.setFont("Helvetica", 8)
            tw = c.stringWidth(label, "Helvetica", 8) + 4
            c.setFillColor(colors.HexColor("#1e3a5f"))
            c.roundRect(cx, y, tw, 13, 3, fill=1, stroke=0)
            c.setFillColor(self.c.ACCENT)
            c.drawString(cx + 2, y + 3, label)
            cx += tw + 6


# ── Path / arrowhead helpers ──────────────────────────────────────────────────

def _trim_start(pts, amount: float):
    """Pull a path's first point back so it starts at the edge of the circle."""
    if len(pts) < 2 or amount <= 0:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[1]
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    if length <= amount:
        return pts
    return [(x0 + dx / length * amount, y0 + dy / length * amount), *pts[1:]]


def _draw_block_cap(c, pts, scale: float, is_cut: bool = False) -> None:
    """The bar across the end of a block path."""
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    nx, ny = -dy / length, dx / length
    half = scale * 0.42
    if is_cut:
        ux, uy = dx / length * half, dy / length * half
        c.line(x1 - ux - nx * half, y1 - uy - ny * half,
               x1 + ux + nx * half, y1 + uy + ny * half)
    else:
        c.line(x1 - nx * half, y1 - ny * half, x1 + nx * half, y1 + ny * half)


def _path_catmull_rom(
    path,
    pts: list[tuple[float, float]],
) -> None:
    """Write a Catmull-Rom spline as cubic bezier segments into a reportlab path."""
    if len(pts) < 2:
        return
    path.moveTo(pts[0][0], pts[0][1])
    n = len(pts)
    if n == 2:
        path.lineTo(pts[1][0], pts[1][1])
        return
    for i in range(n - 1):
        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(n - 1, i + 2)]
        cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1y = p1[1] + (p2[1] - p0[1]) / 6.0
        cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2y = p2[1] - (p3[1] - p1[1]) / 6.0
        path.curveTo(cp1x, cp1y, cp2x, cp2y, p2[0], p2[1])


def _draw_arrowhead(
    c: rl_canvas.Canvas,
    x: float,
    y: float,
    dx: float,
    dy: float,
    size: float,
    color,
) -> None:
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.001:
        return
    nx, ny = dx / length, dy / length
    px, py = -ny, nx

    half = size * 0.38
    base_x = x - nx * size
    base_y = y - ny * size

    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(base_x + px * half, base_y + py * half)
    p.lineTo(base_x - px * half, base_y - py * half)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
