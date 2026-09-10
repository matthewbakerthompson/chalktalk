"""
Red zone / goal line catalog — 8 plays.
"""
from __future__ import annotations
from typing import Optional

from ..models.formation import Formation
from ..models.play import Play, PlayType
from ..builder import play as _b
from ..templates import routes as R, formations as F, schemes as SC


def fade_corner(formation: Optional[Formation] = None) -> Play:
    """Fade + corner high-low. Attacks back-side defender in end zone."""
    f = formation or F.RED_ZONE_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.FADE(depth=9),
            Y=R.SEAM(depth=8),
            Z=R.CORNER_ENDZONE(),
            H=R.FLAT(),
            RB=R.ANGLE(),
        )
        .name("Fade / Corner")
        .play_type(PlayType.PASS)
        .tag("red-zone", "fade", "end-zone")
        .describe("Back-shoulder fade left, corner route right, seam up the hash. "
                  "Corner and fade isolate the single-high safety.")
        .build()
    )


def back_shoulder(formation: Optional[Formation] = None) -> Play:
    """Back shoulder fade — WR sells go, breaks back to QB."""
    f = formation or F.RED_ZONE_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.BACK_SHOULDER(depth=8),
            Z=R.POST(stem=6, depth=10),
            Y=R.FLAT(),
            H=R.SLANT(),
            RB=R.ANGLE(),
        )
        .name("Back Shoulder")
        .play_type(PlayType.PASS)
        .tag("red-zone", "back-shoulder", "end-zone")
        .describe("X runs a back-shoulder fade. Requires precise timing with the QB. "
                  "Z post clears safety; H slant is the hot route vs. Cover 0.")
        .build()
    )


def bunch_rubs_endzone(formation: Optional[Formation] = None) -> Play:
    """Bunch rub routes — pick/rub from tight bunch in end zone."""
    f = formation or F.RED_ZONE_BUNCH_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.CORNER_ENDZONE(),
            Y=R.SEAM(depth=7),
            Z=R.OUT(stem=4, depth=6),
            H=R.DRAG(depth=4, cross=10),
            RB=R.FLAT(),
        )
        .name("Bunch Rub Routes")
        .play_type(PlayType.PASS)
        .tag("red-zone", "bunch", "rub", "end-zone")
        .describe("Three-man bunch creates natural picks. Z uses H's drag as a rub "
                  "on the cornerback. Y seam splits the safety.")
        .build()
    )


def end_zone_corner(formation: Optional[Formation] = None) -> Play:
    """End zone corner route — quick strike to back corner of end zone."""
    f = formation or F.SHOTGUN_BUNCH_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.POST(stem=6, depth=10),
            Y=R.CORNER_ENDZONE(),
            H=R.DRAG(depth=4, cross=8),
            Z=R.FLAT(),
            RB=R.ANGLE(),
        )
        .name("End Zone Corner")
        .play_type(PlayType.PASS)
        .tag("red-zone", "corner", "end-zone")
        .describe("Quick corner to back of end zone. X post clears safety; "
                  "H drag is safety valve.")
        .build()
    )


def goal_line_power(formation: Optional[Formation] = None) -> Play:
    """Goal line power — double-tight, FB lead, short yardage."""
    f = formation or F.GOAL_LINE_HEAVY()
    return (
        _b(f).scheme(SC.power(1, kicker="FB")).block("Y", "TE", "TE2")
        .routes(RB=R.RUN(dx=3, dy=6))
        .bc("RB")
        .name("Goal Line Power")
        .play_type(PlayType.RUN)
        .tag("goal-line", "power", "run")
        .describe("Heavy personnel, double-tight, FB lead through B-gap. "
                  "Use vs. goal line 5-5-1 or any run-heavy D.")
        .build()
    )


def qb_sneak(formation: Optional[Formation] = None) -> Play:
    """QB Sneak — QB follows center surge, short-yardage."""
    f = formation or F.GOAL_LINE()
    return (
        _b(f).scheme(SC.gap_down(1)).block("Y", "TE", "X")
        .routes(QB=R.RUN(dx=0, dy=2), RB=R.RUN(dx=0, dy=1))
        .bc("QB")
        .name("QB Sneak")
        .play_type(PlayType.RUN)
        .tag("goal-line", "sneak", "short-yardage")
        .describe("QB sneaks directly behind center. Highest conversion rate "
                  "in football on 4th-and-inches.")
        .build()
    )


def jumbo_iso(formation: Optional[Formation] = None) -> Play:
    """Jumbo Iso — 13 personnel, H-back iso block, RB straight ahead."""
    f = formation or F.JUMBO_TIGHT()
    return (
        _b(f).scheme(SC.iso(1, lead="TE2")).block("Y", "TE", "X")
        .routes(RB=R.RUN(dx=1, dy=7))
        .bc("RB")
        .name("Jumbo Iso")
        .play_type(PlayType.RUN)
        .tag("goal-line", "iso", "13-personnel")
        .describe("Max run-blocking personnel. H-back isolates MLB. "
                  "RB follows into A/B gap.")
        .build()
    )


def fade_slant(formation: Optional[Formation] = None) -> Play:
    """Fade + slant — quick two-man concept vs. press coverage in red zone."""
    f = formation or F.RED_ZONE_TRIPS_RIGHT()
    return (
        _b(f).pass_pro()
        .routes(
            X=R.FADE(depth=8),
            Z=R.SLANT(stem=1.5, depth=5),
            H=R.ANGLE(),
            Y=R.FLAT(),
            RB=R.SWING(),
        )
        .name("Fade / Slant")
        .play_type(PlayType.PASS)
        .tag("red-zone", "fade", "slant", "quick-game")
        .describe("Fade outside, slant inside on same side. QB reads off cornerback: "
                  "press = throw fade; bail = throw slant.")
        .build()
    )
