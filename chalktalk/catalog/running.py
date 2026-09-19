"""
Running play catalog — 21 named concepts with default formations.
"""
from __future__ import annotations
from typing import Optional

from ..models.formation import Formation
from ..models.play import Play, PlayType
from ..builder import play as _b
from ..templates import (routes as R, formations as F, schemes as SC, qb as Q,
                         blocking as B)


def inside_zone(formation: Optional[Formation] = None) -> Play:
    """Base inside zone — RB reads backside A/B gap."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(1)).block("Y", "X", "Z", "FB")
        .routes(RB=R.RUN(dx=1.5, dy=7))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
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
        _b(f).scheme(SC.outside_zone(1)).block("Y", "X", "Z", "FB")
        .routes(RB=R.RUN(dx=7, dy=5))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
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
        _b(f).scheme(SC.power(1, kicker="FB")).block("Y", "X", "Z")
        .routes(RB=R.RUN(dx=4, dy=7))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
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
        _b(f).scheme(SC.power(-1, kicker=None)).block("Y", "X", "Z")
        .routes(FB=R.RUN(dx=-4, dy=4), RB=R.RUN(dx=-4, dy=7))
        .bc("RB")
        .qb(Q.HANDOFF(-1, back="RB"))
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
        _b(f).scheme(SC.counter(1)).block("Y", "X", "Z")
        .routes(RB=R.RUN(dx=-3, dy=6))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
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
        _b(f).scheme(SC.trap(1)).block("Y", "X", "Z", "FB")
        .routes(RB=R.RUN(dx=1, dy=6))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
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
        _b(f).scheme(SC.big_on_big(), protection="Draw - show pass")
        .routes(
            X=R.FLY(),
            Z=R.FLY(),
            H=R.SEAM(),
            Y=R.BLOCK(),
            RB=R.RUN(dx=0, dy=8),
        )
        .bc("RB")
        .qb(Q.DRAW(1, back="RB"))
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
        _b(f).scheme(SC.outside_zone(1))
        .routes(
            X=R.BLOCK(),
            Y=R.BLOCK(),
            Z=R.BLOCK(),
            H=R.RUN(dx=8, dy=3),   # H takes the jet sweep
            RB=R.BLOCK(),
        )
        .bc("H")
        .qb(Q.HANDOFF(1, back="H", rule="Hand the jet on the move"))
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
        _b(f).scheme(SC.outside_zone(1)).block("Y", "X", "Z")
        .routes(FB=R.RUN(dx=6, dy=2), RB=R.RUN(dx=8, dy=4))
        .bc("RB")
        .qb(Q.PITCH(1, back="RB"))
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
        _b(f).scheme(SC.iso(1, lead="FB")).block("Y", "X", "Z")
        .routes(RB=R.RUN(dx=0, dy=8))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
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
        _b(f).scheme(SC.inside_zone(1)).block("Y")
        .routes(
            X=R.BLOCK(),
            Z=R.BLOCK(),
            H=R.BLOCK(),
            RB=R.RUN(dx=-2, dy=6),  # mesh read
        )
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the backside end"))
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
        _b(f).scheme(SC.power(1, kicker=None)).block("Y", "X", "Z", "H")
        .routes(
            QB=R.RUN(dx=5, dy=6),
            RB=R.BLOCK(),
        )
        .bc("QB")
        .qb(Q.KEEP(1, depth=7.0, rule="Read the edge, then get vertical"))
        .name("QB Keeper")
        .play_type(PlayType.RUN)
        .tag("keeper", "qb-run", "run")
        .describe("QB pulls and runs behind pulling guard to the edge. "
                  "Receivers crack-block corners and safeties.")
        .build()
    )


def duo(formation: Optional[Formation] = None) -> Play:
    """Duo - two double teams straight downhill, no puller, the back reads the Mike."""
    f = formation or F.SINGLE_BACK_ACE()
    return (
        _b(f)
        .blocks(
            RT=B.COMBO("RG", 1, target="3T", climb=False),
            RG=B.COMBO("RT", 1, target="M"),          # comes off to the Mike
            C=B.COMBO("LG", -1, target="1T", climb=False),
            LG=B.COMBO("C", -1, target="W"),          # comes off to the Will
            LT=B.BASE(target="DE"),
            Y=B.BASE(target="DE"),
        )
        .block("TE", "X", "Z")
        .routes(RB=R.RUN(dx=1.5, dy=7))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
        .name("Duo")
        .play_type(PlayType.RUN)
        .tag("duo", "iso", "gap", "run")
        .describe("Two vertical double teams work up to both linebackers with no "
                  "puller, and the back presses the B-gap and cuts off the Mike's fit.")
        .build()
    )


def split_zone(formation: Optional[Formation] = None) -> Play:
    """Split zone - inside zone right, the H-back goes the other way and kicks the end."""
    f = formation or F.JUMBO_TIGHT()
    return (
        _b(f).scheme(SC.split_zone(1, kicker="TE2"))
        .blocks(Y=B.REACH(1, target="DE"), TE=B.REACH(1, target="S"))
        .block("X")
        .routes(RB=R.RUN(dx=1.0, dy=7))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
        .name("Split Zone")
        .play_type(PlayType.RUN)
        .tag("inside-zone", "split-zone", "zone", "run")
        .describe("The line zone-steps right while the H-back goes the other way to "
                  "kick out the backside end, so the cutback lane stays clean.")
        .build()
    )


def buck_sweep(formation: Optional[Formation] = None) -> Play:
    """Buck sweep - both guards pull, everybody else blocks down or back."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f)
        .blocks(
            Y=B.DOWN(-1, target="DE"),
            RT=B.DOWN(-1, target="3T"),
            RG=B.KICK(1, target="CB"),                # kicks the first man outside
            C=B.DOWN(-1, target="backside A"),        # blocks back for the guard
            LG=B.PULL(1, target="S", width=8.0),      # turns up inside the kick
            LT=B.HINGE(-1),
        )
        .block("X", "Z")
        .routes(
            FB=R.RUN(dx=-1.5, dy=4),   # fakes the dive and fills the backside A-gap
            RB=R.RUN(dx=9, dy=8),
        )
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
        .name("Buck Sweep")
        .play_type(PlayType.RUN)
        .tag("sweep", "perimeter", "gap", "run")
        .describe("Both guards pull while the tight end, tackle and center block "
                  "down, and the back follows them outside off the fullback's dive fake.")
        .build()
    )


def pin_pull(formation: Optional[Formation] = None) -> Play:
    """Pin and pull - covered linemen pin inside, uncovered linemen pull to the edge."""
    f = formation or F.GUN_TRIPS_TE_RIGHT()
    return (
        _b(f)
        .blocks(
            Y=B.DOWN(-1, target="DE"),                # pin
            RT=B.PULL(1, target="S", width=6.0),      # pull around the pin
            RG=B.DOWN(-1, target="3T"),               # pin
            C=B.PULL(1, target="M", width=5.0),       # pull to the first backer
            LG=B.REACH(1, target="NT"),               # covers for the center
            LT=B.SCOOP(1),
            H=B.DOWN(-1, target="SS"),                # crack the force
            Z=B.BASE(target="CB"),
        )
        .block("X")
        # The back starts on the left, so his path is authored as a left-side
        # route: it mirrors to the right when drawn.
        .routes(RB=R.RUN(dx=-12, dy=7))
        .bc("RB")
        .qb(Q.HANDOFF(1, back="RB"))
        .name("Pin Pull")
        .play_type(PlayType.RUN)
        .tag("outside-zone", "pin-pull", "perimeter", "run")
        .describe("Covered linemen pin their man inside and the uncovered tackle and "
                  "center pull around them, so the back gets the edge with two escorts.")
        .build()
    )


def power_read(formation: Optional[Formation] = None) -> Play:
    """Power read - power blocking, the back sweeps, the QB reads the end."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).scheme(SC.power(1, kicker=None))
        .blocks(Y=B.CLIMB(1, target="SS"),          # arc past the end he is reading
                Z=B.BASE(target="CB"))
        .block("X", "H")
        .routes(
            RB=R.RUN(dx=-13, dy=6),    # left-side back: sweeps right when mirrored
            QB=R.RUN(dx=3, dy=6),      # the keep, inside the end behind the guard
        )
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the play-side end",
                   rule="He widens with the sweep, pull it and follow the guard; "
                        "he squeezes, give it"))
        .name("Power Read")
        .play_type(PlayType.RUN)
        .tag("power", "option", "read", "run")
        .describe("Power blocking leaves the play-side end alone, and the "
                  "quarterback keeps it behind the pulling guard whenever the end "
                  "widens with the sweeping back.")
        .build()
    )


def speed_option(formation: Optional[Formation] = None) -> Play:
    """Speed option - attack the end and pitch it off him, no mesh at all."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).scheme(SC.outside_zone(1))
        .blocks(RT=B.CLIMB(1, target="S"),          # leave the end, take the Sam
                Y=B.CLIMB(1, target="SS"))          # arc to the force
        .block("H", "Z", "X")
        .routes(RB=R.RUN(dx=7, dy=4))
        .bc("RB")
        .qb(Q.OPTION(1, back="RB", key="the play-side end"))
        .name("Speed Option")
        .play_type(PlayType.RUN)
        .tag("option", "perimeter", "pitch", "run")
        .describe("The quarterback attacks the unblocked end and pitches it to the "
                  "trailing back unless the end lets him turn upfield.")
        .build()
    )


def qb_counter(formation: Optional[Formation] = None) -> Play:
    """QB counter - zone fake one way, the QB follows guard and tackle the other."""
    f = formation or F.GUN_TREY_RIGHT()
    return (
        _b(f).scheme(SC.counter(-1))
        .blocks(Y=B.DOWN(-1, target="DE"),          # fills for the pulling tackle
                X=B.BASE(target="CB"))
        .block("H", "Z")
        .routes(
            RB=R.RUN(dx=-8, dy=3),     # left-side back: the zone fake goes right
            QB=R.RUN(dx=-4, dy=6),
        )
        .bc("QB")
        .qb(Q.KEEP(-1, depth=6.0,
                   rule="Ride the zone fake right, then follow the pullers back left"))
        .name("QB Counter")
        .play_type(PlayType.RUN)
        .tag("counter", "gap", "qb-run", "misdirection", "run")
        .describe("The back sells zone right across the quarterback's face while the "
                  "guard kicks and the tackle wraps, and the quarterback keeps it back "
                  "left behind them.")
        .build()
    )


def qb_draw(formation: Optional[Formation] = None) -> Play:
    """QB draw - show pass, let the rush go by, and the quarterback runs it."""
    f = formation or F.GUN_SPREAD_4WR()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Draw - show pass")
        .blocks(RB=B.CLIMB(-1, target="M"))         # leads up through the A-gap
        .routes(
            X=R.FLY(depth=18),
            Z=R.FLY(depth=18),
            H=R.SEAM(depth=16),
            Y=R.SEAM(depth=16),
            QB=R.RUN(dx=2, dy=8),
        )
        .bc("QB")
        .qb(Q.KEEP(1, depth=8.0,
                   rule="Show pass for a count, let the rush go by, then run it"))
        .name("QB Draw")
        .play_type(PlayType.RUN)
        .tag("draw", "qb-run", "delayed", "run")
        .describe("The line shows pass and lets the rush run itself upfield, then the "
                  "quarterback runs it up the middle behind the back's lead on the Mike.")
        .build()
    )


def toss_crack(formation: Optional[Formation] = None) -> Play:
    """Toss crack - the flanker cracks the force and the tackle pulls to replace him."""
    f = formation or F.SINGLE_BACK_PRO_RIGHT()
    return (
        _b(f).scheme(SC.outside_zone(1))
        .blocks(
            RT=B.PULL(1, target="CB", width=9.0),     # replaces the cracking flanker
            Y=B.DOWN(-1, target="DE"),
            Z=B.DOWN(-1, target="SS"),                # crack
        )
        .block("X", "H")
        .routes(RB=R.RUN(dx=9, dy=7))
        .bc("RB")
        .qb(Q.PITCH(1, back="RB"))
        .name("Toss Crack")
        .play_type(PlayType.RUN)
        .tag("toss", "sweep", "crack", "perimeter", "run")
        .describe("The flanker cracks the force player, the tackle pulls around to "
                  "take the corner he left, and the back takes the toss outside it all.")
        .build()
    )
