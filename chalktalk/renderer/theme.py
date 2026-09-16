"""
Themes — the ink and paper every diagram is drawn with.

One table, three consumers: the SVG renderer, the PDF exporter, and the
browser designer (which receives the same table inside its catalog). Change a
colour here and every diagram changes together.

    turf   — the screen default: a field under lights, chalk-white ink
    paper  — for printing: white field, black ink, print-safe accents

A diagram is ink on a surface. The offense is drawn in one ink — open circles
and their routes — the defense in a second, the ball's path in the accent.
Everything else (yard lines, hashes, numbers) is texture and stays quiet.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Iterable, Optional, Union


@dataclass(frozen=True)
class Theme:
    name: str
    dark: bool

    # the surface
    field: str
    field_alt: str        # alternate five-yard band
    oob: str              # out of bounds, past the sideline
    endzone: str
    line: str             # yard lines
    los: str              # line of scrimmage, goal line
    hash: str             # hash ticks
    sideline: str
    number: str           # yard numbers, when the ball spot is known

    # the offense's ink
    offense_fill: str
    offense_stroke: str
    offense_text: str
    ball_ring: str        # the quarterback and the ball carrier
    route: str
    run: str
    block: str
    motion: str
    qb: str               # the quarterback's footwork and mesh point
    read_fill: str
    read_text: str

    # the defense's ink
    defense_fill: str
    defense_stroke: str
    defense_text: str
    def_assign: str
    zone_fill: str
    zone_stroke: str

    # words and the ball
    title: str
    subtitle: str
    ball: str

    # printed pages
    page_bg: str
    page_text: str
    page_muted: str
    page_rule: str


TURF = Theme(
    name="turf", dark=True,
    field="#22503a", field_alt="#1f4b37", oob="#1a3a2b", endzone="#1d4432",
    line="rgba(255,255,255,0.22)", los="rgba(255,255,255,0.92)",
    hash="rgba(255,255,255,0.20)", sideline="rgba(255,255,255,0.78)",
    number="rgba(255,255,255,0.30)",
    offense_fill="#f4f1e8", offense_stroke="#15221b", offense_text="#15221b",
    ball_ring="#fbbf24",
    route="#ffffff", run="#f59e0b", block="#ffffff", motion="#7dd3fc",
    qb="#fbbf24", read_fill="#15221b", read_text="#fde68a",
    defense_fill="#222d28", defense_stroke="#cfd6d1", defense_text="#f4f1e8",
    def_assign="#f0806a", zone_fill="rgba(240,128,106,0.13)",
    zone_stroke="rgba(240,128,106,0.35)",
    title="#ffffff", subtitle="rgba(255,255,255,0.62)", ball="#c2703a",
    page_bg="#14201a", page_text="#f0efe8", page_muted="#9aa8a0",
    page_rule="#fbbf24",
)

PAPER = Theme(
    name="paper", dark=False,
    field="#ffffff", field_alt="#f6f6f3", oob="#ebebe7", endzone="#f0f0ec",
    line="rgba(0,0,0,0.18)", los="#111111",
    hash="rgba(0,0,0,0.28)", sideline="rgba(0,0,0,0.6)",
    number="rgba(0,0,0,0.28)",
    offense_fill="#ffffff", offense_stroke="#111111", offense_text="#111111",
    ball_ring="#b45309",
    route="#111111", run="#b45309", block="#111111", motion="#2563eb",
    qb="#b45309", read_fill="#111111", read_text="#ffffff",
    defense_fill="#d9d9d4", defense_stroke="#333333", defense_text="#111111",
    def_assign="#c0392b", zone_fill="rgba(192,57,43,0.10)",
    zone_stroke="rgba(192,57,43,0.35)",
    title="#111111", subtitle="rgba(0,0,0,0.55)", ball="#a05a2c",
    page_bg="#ffffff", page_text="#111111", page_muted="#6b6b66",
    page_rule="#111111",
)

THEMES: dict[str, Theme] = {"turf": TURF, "paper": PAPER}

#: What a diagram is made of, in drawing order. Any of these can be hidden.
LAYERS: tuple[str, ...] = ("motion", "blocks", "qb", "routes", "reads",
                           "defense", "coverage", "zones", "title")

#: The typeface every renderer sets — system sans, so nothing is fetched.
FONT = "Inter,'Segoe UI',Helvetica,Arial,sans-serif"


def theme_for(theme: Union[Theme, str, None]) -> Theme:
    """Accept a Theme, its name, or nothing (turf)."""
    if theme is None:
        return TURF
    if isinstance(theme, Theme):
        return theme
    try:
        return THEMES[str(theme).lower()]
    except KeyError:
        raise ValueError(
            f"Unknown theme {theme!r}; pick one of {', '.join(THEMES)}") from None


def layer_set(layers: Optional[Iterable[str]] = None,
              hide: Optional[Iterable[str]] = None) -> frozenset[str]:
    """
    Which layers to draw: everything, or `layers`, minus `hide`. Names are
    checked so a typo does not silently draw the whole play.
    """
    chosen = set(LAYERS) if layers is None else set(layers)
    chosen -= set(hide or ())
    unknown = (set(layers or ()) | set(hide or ())) - set(LAYERS)
    if unknown:
        raise ValueError(
            f"Unknown layer(s) {sorted(unknown)}; the layers are {', '.join(LAYERS)}")
    return frozenset(chosen)


def themes_json() -> dict[str, dict]:
    """The table as plain data, for the designer's catalog."""
    return {name: asdict(theme) for name, theme in THEMES.items()}


def theme_keys() -> list[str]:
    return [f.name for f in fields(Theme)]


def to_rgba(color: str) -> tuple[float, float, float, float]:
    """
    A theme colour as (r, g, b, a) in 0..1 — for renderers that do not speak
    CSS. Accepts #rrggbb and rgba(r,g,b,a).
    """
    c = color.strip()
    if c.startswith("#") and len(c) == 7:
        return (int(c[1:3], 16) / 255, int(c[3:5], 16) / 255,
                int(c[5:7], 16) / 255, 1.0)
    if c.startswith("rgba(") and c.endswith(")"):
        r, g, b, a = (float(v) for v in c[5:-1].split(","))
        return (r / 255, g / 255, b / 255, a)
    raise ValueError(f"Cannot parse colour {color!r}")


__all__ = ["Theme", "TURF", "PAPER", "THEMES", "LAYERS", "FONT",
           "theme_for", "layer_set", "themes_json", "theme_keys", "to_rgba"]
