"""
Passing play catalog — 16 named concepts with default formations.

Each function returns a Play and accepts an optional Formation override.
Use .with_route(label, route) on the returned play to create variants.
"""
from __future__ import annotations
from typing import Optional

from ..models.formation import Formation
from ..models.play import Play, PlayType
from ..builder import play as _b
from ..templates import routes as R, formations as F, schemes as SC, qb as Q


def mesh_concept(formation: Optional[Formation] = None) -> Play:
    """Classic two-man mesh crossing with fly clearout."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(X=R.FLY(), Y=R.FLAT(), Z=R.MESH(5, 22), H=R.MESH(6, 22), RB=R.SWING())
        .qb(Q.GUN(3, reads=["Y", "H", "Z", "RB"],
                rule="High-low the flat defender, then work the mesh"))
        .name("Mesh Concept")
        .play_type(PlayType.PASS)
        .tag("mesh", "crossing", "11-personnel")
        .describe("Two-man mesh crossing. H and Z create natural rubs. "
                  "X clears deep, Y and RB are checkdowns.")
        .build()
    )


def curl_flat(formation: Optional[Formation] = None) -> Play:
    """Curl/flat — high-low stress on the hook-curl defender."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(X=R.CURL(), Y=R.FLAT(), Z=R.OUT(), H=R.CURL(depth=10), RB=R.FLAT())
        .qb(Q.GUN(3, reads=["H", "Y", "X", "RB"],
                rule="Curl-flat: high-low the flat defender"))
        .name("Curl / Flat")
        .play_type(PlayType.PASS)
        .tag("curl-flat", "hi-lo", "11-personnel")
        .describe("Curls underneath with flat route as high-low read. "
                  "Attack the hook-curl defender.")
        .build()
    )


def four_verticals(formation: Optional[Formation] = None) -> Play:
    """Four Verts — stretch the coverage deep on all levels."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).pass_pro()
        .routes(X=R.FLY(), Y=R.SEAM(), H=R.SEAM(depth=20), Z=R.FLY(), RB=R.FLAT())
        .qb(Q.GUN(5, reads=["H", "Y", "Z", "RB"],
                rule="Read the middle of the field; take the open seam"))
        .name("Four Verticals")
        .play_type(PlayType.PASS)
        .tag("verts", "four-verticals", "shot-play")
        .describe("Four vertical routes stress every safety. "
                  "Slot seams split safeties vs. Cover 2; outs vs. Cover 4.")
        .build()
    )


def smash(formation: Optional[Formation] = None) -> Play:
    """Smash — corner + hitch high-low vs. Cover 2 cornerback."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.HITCH(),
            Z=R.CORNER(stem=6, depth=12),
            H=R.SEAM(),
            Y=R.FLAT(),
            RB=R.ANGLE(),
        )
        .qb(Q.GUN(3, reads=["Z", "Y", "X", "RB"],
                rule="Corner-flat high-low on the corner"))
        .name("Smash")
        .play_type(PlayType.PASS)
        .tag("smash", "hi-lo", "cover-2-beater")
        .describe("Corner/hitch high-low. Corner route over hitch isolates the CB. "
                  "Destroys Cover 2; check to seam vs Cover 4.")
        .build()
    )


def levels(formation: Optional[Formation] = None) -> Play:
    """Levels — three routes at different depths on same side. Cover 3 stress."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.FLY(),
            Z=R.IN(stem=12, depth=14),
            H=R.DRAG(depth=5, cross=12),
            Y=R.FLAT(),
            RB=R.ANGLE(),
        )
        .qb(Q.GUN(3, reads=["H", "Z", "Y", "RB"],
                rule="Low to high off the hook defender"))
        .name("Levels")
        .play_type(PlayType.PASS)
        .tag("levels", "crossing", "cover-3-beater")
        .describe("Three routes at different depths stress the single-high safety "
                  "and zone defenders laterally.")
        .build()
    )


def flood(formation: Optional[Formation] = None) -> Play:
    """Flood — three routes to one side at different depths. Overloads the flat."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.POST(),
            Z=R.CORNER(stem=8, depth=14),
            H=R.OUT(stem=6, depth=8),
            Y=R.FLAT(),
            RB=R.SWING(),
        )
        .qb(Q.SPRINT(1, reads=["Z", "H", "Y"],
                   rule="Three levels to the sprint side, high to low"))
        .name("Flood")
        .play_type(PlayType.PASS)
        .tag("flood", "three-level", "overload")
        .describe("Corner/out/flat three-level flood to the trips side. "
                  "Three routes, two defenders — someone is open.")
        .build()
    )


def drive_concept(formation: Optional[Formation] = None) -> Play:
    """Drive — backside drag + frontside out. Stretch cover-4 horizontally."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.DRAG(depth=5, cross=20),
            H=R.SEAM(),
            Y=R.OUT(stem=6, depth=8),
            Z=R.CORNER(),
            RB=R.FLAT(),
        )
        .qb(Q.GUN(3, reads=["X", "Z", "Y", "RB"],
                rule="Shallow first, dig behind it"))
        .name("Drive Concept")
        .play_type(PlayType.PASS)
        .tag("drive", "crossing", "cover-4-beater")
        .describe("Backside X drag runs underneath everything. Y out attacks the "
                  "flat defender. Good vs. Tampa 2 and Cover 4.")
        .build()
    )


def y_cross(formation: Optional[Formation] = None) -> Play:
    """Y-Cross — TE digs across the field. Middle of the field open concept."""
    f = formation or F.SHOTGUN_ACE()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.FLY(),
            Y=R.DIG(stem=10, cross=18),
            Z=R.OUT(),
            RB=R.FLAT(),
            TE=R.SEAM(),
        )
        .qb(Q.GUN(5, reads=["Y", "TE", "Z", "RB"],
                rule="Cross behind the seam; checkdown late"))
        .name("Y-Cross")
        .play_type(PlayType.PASS)
        .tag("y-cross", "dig", "12-personnel")
        .describe("TE runs a crossing dig at 10 yards. Splits the field and "
                  "attacks middle zone defenders. Classic red zone + mid-field concept.")
        .build()
    )


def spacing(formation: Optional[Formation] = None) -> Play:
    """Spacing — 5 route combination with even distribution. Attacks zones."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.HITCH(depth=6),
            Y=R.FLAT(),
            Z=R.HITCH(depth=6),
            H=R.ANGLE(),
            RB=R.ANGLE(),
        )
        .qb(Q.GUN(1, reads=["H", "Z", "X", "RB"],
                rule="Find the open window and throw on rhythm"))
        .name("Spacing")
        .play_type(PlayType.PASS)
        .tag("spacing", "quick-game", "5-route")
        .describe("Five short routes distributed across the field. "
                  "One of them is always open vs any zone — read the open window.")
        .build()
    )


def scissors(formation: Optional[Formation] = None) -> Play:
    """Scissors — post + corner from same side. Splits the safety."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.POST(stem=8),
            Z=R.CORNER(stem=8, depth=15),
            H=R.SLANT(),
            Y=R.SEAM(),
            RB=R.FLAT(),
        )
        .qb(Q.GUN(5, reads=["Z", "X", "H", "RB"],
                rule="Corner over the post; take what the safety leaves"))
        .name("Scissors")
        .play_type(PlayType.PASS)
        .tag("scissors", "post-corner", "shot-play")
        .describe("Post/corner combination on same side isolates the safety. "
                  "Backside H slant and Y seam are hot reads.")
        .build()
    )


def stick(formation: Optional[Formation] = None) -> Play:
    """Stick — TE stick (stop route) + flat + seam. Quick-game triangle."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.FLY(),
            Y=R.HITCH(depth=5),
            Z=R.OUT(),
            H=R.FLAT(),
            RB=R.ANGLE(),
        )
        .qb(Q.GUN(3, reads=["Y", "H", "Z", "RB"],
                rule="Stick-flat: read the flat defender"))
        .name("Stick")
        .play_type(PlayType.PASS)
        .tag("stick", "quick-game", "triangle")
        .describe("Triangle read: stick (hitch) + flat + seam. "
                  "Read cover type to determine hot route.")
        .build()
    )


def deep_cross(formation: Optional[Formation] = None) -> Play:
    """Deep Cross (Over) — WR runs a deep crossing route across the field."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.OVER(stem=10, cross=22),
            Y=R.SEAM(),
            Z=R.POST(),
            H=R.DRAG(depth=5, cross=15),
            RB=R.FLAT(),
        )
        .qb(Q.GUN(5, reads=["Z", "H", "X", "RB"],
                rule="Post first, then the crosser behind it"))
        .name("Deep Cross")
        .play_type(PlayType.PASS)
        .tag("deep-cross", "over", "shot-play")
        .describe("X runs deep crossing route (over) at 10+ yards. "
                  "Combined with Z post and H shallow drag — three-level attack.")
        .build()
    )


def double_slant(formation: Optional[Formation] = None) -> Play:
    """Double Slant — slants on both sides. High-percentage quick game."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.SLANT(),
            H=R.SLANT(),
            Z=R.SLANT(),
            Y=R.FLAT(),
            RB=R.FLAT(),
        )
        .qb(Q.GUN(1, reads=["H", "Z", "X", "RB"],
                rule="Ball out on the third step"))
        .name("Double Slant")
        .play_type(PlayType.PASS)
        .tag("slant", "quick-game", "two-high-beater")
        .describe("Slants on both sides stress man coverage. "
                  "Inside leverage = slant is open. Check to flat vs Cover 2.")
        .build()
    )


def hitch_seam(formation: Optional[Formation] = None) -> Play:
    """Hitch + Seam — outside hitch with TE/slot seam. Beats Cover 2."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.HITCH(),
            Y=R.SEAM(depth=15),
            Z=R.HITCH(depth=5),
            H=R.SEAM(depth=18),
            RB=R.SWING(),
        )
        .qb(Q.GUN(1, reads=["Z", "H", "X"],
                rule="Off coverage takes the hitch, soft takes the seam"))
        .name("Hitch / Seam")
        .play_type(PlayType.PASS)
        .tag("hitch-seam", "cover-2-beater")
        .describe("Outside hitches hold the CBs; slot seams attack behind "
                  "the safeties in Cover 2.")
        .build()
    )


def sail_concept(formation: Optional[Formation] = None) -> Play:
    """Sail — fly + out + flat three-level flood to one side."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.FLY(),
            Z=R.SAIL(stem=5, depth=14),
            H=R.OUT(stem=4, depth=6),
            Y=R.FLAT(),
            RB=R.ANGLE(),
        )
        .qb(Q.GUN(5, reads=["Z", "H", "Y", "RB"],
                rule="Corner, sail, flat — off the flat defender"))
        .name("Sail Concept")
        .play_type(PlayType.PASS)
        .tag("sail", "flood", "three-level")
        .describe("Fly / sail / flat — three routes at three depths to same side. "
                  "Classic Cover 3 beater: run away from the deep hook zone.")
        .build()
    )


def snag(formation: Optional[Formation] = None) -> Play:
    """Snag — angle + flat + corner triangle. Quick read vs zone."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.CORNER(stem=5, depth=10),
            Y=R.ANGLE(),
            Z=R.OUT(stem=5, depth=7),
            H=R.FLAT(),
            RB=R.SWING(),
        )
        .qb(Q.GUN(3, reads=["X", "Y", "H", "RB"],
                rule="Triangle: corner, snag, flat"))
        .name("Snag")
        .play_type(PlayType.PASS)
        .tag("snag", "triangle", "quick-game")
        .describe("Corner/angle/flat triangle read. Angle under the corner, "
                  "flat as hot read vs. pressure.")
        .build()
    )


def rpo_bubble(formation: Optional[Formation] = None) -> Play:
    """RPO Bubble — run-pass option with outside bubble screen as backside read."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(1), protection="Run action")
        .routes(
            X=R.BUBBLE(),
            Y=R.BLOCK(),
            Z=R.BLOCK(),
            H=R.BUBBLE(),
            RB=R.RUN(dx=1, dy=5),
        )
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the overhang", reads=["H"],
               rule="Overhang in the box, throw it; out, give it"))
        .name("RPO Bubble")
        .play_type(PlayType.RPO)
        .tag("rpo", "bubble", "zone-read")
        .describe("Zone run with pre-snap bubble screen read. QB hands off or "
                  "pulls and throws bubble based on unblocked edge defender.")
        .build()
    )
