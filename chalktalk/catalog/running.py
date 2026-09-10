"""
Running play catalog — 12 named concepts with default formations.
"""
from __future__ import annotations
from typing import Optional

from ..models.formation import Formation
from ..models.play import Play, PlayType
from ..builder import play as _b
from ..templates import routes as R, formations as F


def inside_zone(formation: Optional[Formation] = None) -> Play:
    """Base inside zone — RB reads backside A/B gap."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z", "FB")
        .routes(RB=R.RUN(dx=1.5, dy=7))
        .bc("RB")
        .name("Inside Zone")
        .play_type(PlayType.RUN)
        .tag("inside-zone", "zone", "run")
        .describe("OL zone-steps right. RB reads backside A-gap. "
                  "If the gap closes, bend back.")
        .build()
    )


def outside_zone(formation: Optional[Formation] = None) -> Play:
    """Outside zone — OL stretch, RB looks for cutback or corner."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z", "FB")
        .routes(RB=R.RUN(dx=7, dy=5))
        .bc("RB")
        .name("Outside Zone")
        .play_type(PlayType.RUN)
        .tag("outside-zone", "zone", "run", "stretch")
        .describe("OL stretch blocks to perimeter. RB presses edge, "
                  "reads interior for cutback lane.")
        .build()
    )


def power_right(formation: Optional[Formation] = None) -> Play:
    """Power Right — pulling guard, FB lead, off-tackle."""
    f = formation or F.I_FORM_STRONG_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z")
        .routes(FB=R.RUN(dx=4, dy=4), RB=R.RUN(dx=4, dy=7))
        .bc("RB")
        .name("Power Right")
        .play_type(PlayType.RUN)
        .tag("power", "gap", "run")
        .describe("Double-team at POA, RG pulls around to second level. "
                  "FB leads through B/C gap right.")
        .build()
    )


def power_left(formation: Optional[Formation] = None) -> Play:
    """Power Left — mirror of power right."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z")
        .routes(FB=R.RUN(dx=-4, dy=4), RB=R.RUN(dx=-4, dy=7))
        .bc("RB")
        .name("Power Left")
        .play_type(PlayType.RUN)
        .tag("power", "gap", "run")
        .describe("Power run to the weak (left) side. LG pulls and leads.")
        .build()
    )


def counter_trey(formation: Optional[Formation] = None) -> Play:
    """Counter Trey — two pulling linemen, misdirection off zone-fake."""
    f = formation or F.GUN_OFFSET_BACK_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z")
        .routes(RB=R.RUN(dx=-3, dy=6))
        .bc("RB")
        .name("Counter Trey")
        .play_type(PlayType.RUN)
        .tag("counter", "gap", "misdirection", "run")
        .describe("Initial flow away from POA pulls defenders. "
                  "Two pulling OL lead back to the counter gap.")
        .build()
    )


def trap(formation: Optional[Formation] = None) -> Play:
    """Trap — guard traps the backside DT. Quick-hitting A/B gap."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z", "FB")
        .routes(RB=R.RUN(dx=1, dy=6))
        .bc("RB")
        .name("Trap")
        .play_type(PlayType.RUN)
        .tag("trap", "gap", "run")
        .describe("Center and playside guard down-block. Backside guard traps "
                  "upfield DT. Quick-hitting through A-gap.")
        .build()
    )


def draw(formation: Optional[Formation] = None) -> Play:
    """Draw — QB drop-back fake, delayed hand-off to RB."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).block_ol()
        .routes(
            X=R.FLY(),
            Z=R.FLY(),
            H=R.SEAM(),
            Y=R.BLOCK(),
            RB=R.RUN(dx=0, dy=8),
        )
        .bc("RB")
        .name("Draw")
        .play_type(PlayType.RUN)
        .tag("draw", "delayed", "run", "pass-action")
        .describe("QB sets up like pass. OL pass-sets then releases to second level. "
                  "RB delays and hits the vacated middle.")
        .build()
    )


def speed_sweep(formation: Optional[Formation] = None) -> Play:
    """Speed Sweep — WR/RB jet sweep to the perimeter."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).block_ol()
        .routes(
            X=R.BLOCK(),
            Y=R.BLOCK(),
            Z=R.BLOCK(),
            H=R.RUN(dx=8, dy=3),   # H takes the jet sweep
            RB=R.BLOCK(),
        )
        .bc("H")
        .name("Speed Sweep")
        .play_type(PlayType.RUN)
        .tag("sweep", "jet", "perimeter", "run")
        .describe("H-back goes in pre-snap motion and takes jet sweep handoff. "
                  "OL seals backside, X and Z crack blocks.")
        .build()
    )


def toss_sweep(formation: Optional[Formation] = None) -> Play:
    """Toss Sweep — QB toss to RB going outside."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z")
        .routes(FB=R.RUN(dx=6, dy=2), RB=R.RUN(dx=8, dy=4))
        .bc("RB")
        .name("Toss Sweep")
        .play_type(PlayType.RUN)
        .tag("toss", "sweep", "perimeter", "run")
        .describe("QB tosses to RB running wide. FB leads outside, "
                  "TE kicks out the end man on the line.")
        .build()
    )


def lead_iso(formation: Optional[Formation] = None) -> Play:
    """Isolation — FB isolates MLB, RB runs off the block."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z")
        .routes(FB=R.RUN(dx=0, dy=5), RB=R.RUN(dx=0, dy=8))
        .bc("RB")
        .name("Lead Iso")
        .play_type(PlayType.RUN)
        .tag("iso", "lead", "run")
        .describe("OL double-teams at point of attack. FB isolates (blocks) "
                  "the MLB. RB reads and runs off the block.")
        .build()
    )


def veer_read(formation: Optional[Formation] = None) -> Play:
    """Zone Read / Veer — QB reads unblocked DE; hand-off or keep."""
    f = formation or F.GUN_OFFSET_BACK_RIGHT()
    return (
        _b(f).block_ol().block("Y")
        .routes(
            X=R.BLOCK(),
            Z=R.BLOCK(),
            H=R.BLOCK(),
            RB=R.RUN(dx=-2, dy=6),  # mesh read
        )
        .bc("RB")
        .name("Zone Read")
        .play_type(PlayType.RPO)
        .tag("zone-read", "option", "rpo", "run")
        .describe("QB reads backside DE. If DE crashes, QB keeps and runs edge. "
                  "If DE holds, QB hands off inside zone.")
        .build()
    )


def qb_keeper(formation: Optional[Formation] = None) -> Play:
    """QB Keeper — QB runs behind pulling OL."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).block_ol().block("Y", "X", "Z", "H")
        .routes(
            QB=R.RUN(dx=5, dy=6),
            RB=R.BLOCK(),
        )
        .bc("QB")
        .name("QB Keeper")
        .play_type(PlayType.RUN)
        .tag("keeper", "qb-run", "run")
        .describe("QB pulls and runs behind pulling guard to the edge. "
                  "Receivers crack-block corners and safeties.")
        .build()
    )
