"""
Stock scripted series — a base play plus the calls that punish each way a
defense can over-play it. Every entry records the *tell*: the thing you see
on film (or on the sideline) that makes it the right call.

    from gridiron.catalog import series as SR

    iz = SR.inside_zone_series()
    print(iz.describe())
    iz.to_script(reps=2).table()
"""
from __future__ import annotations

from ..series import series, Series
from ..models import situation as S
from .. import adjustments as A
from ..templates import routes as R, formations as F
from . import passing, running, redzone


def inside_zone_series() -> Series:
    """The spine of a zone-run offense: everything off the same mesh point."""
    return (
        series("Inside Zone Series",
               "Every call shows the same first two steps. Punish whoever "
               "cheats the A-gap double team.")
        .base(running.inside_zone(),
              note="Downhill off the double team, cut off the backside 3-tech",
              situation=S.FIRST_TEN)
        .constraint(running.speed_sweep(),
                    tell="Backside LB fast-flowing inside, DE squeezing",
                    situation=S.Situation(down=2, distance=6))
        .constraint(running.qb_keeper().adjust(A.MOTION("H", "orbit")),
                    tell="Unblocked end crashing on the mesh",
                    situation=S.Situation(down=1, distance=10))
        .complement(running.outside_zone(),
                    tell="Front spilling everything inside / heavy A-gap fits",
                    situation=S.FIRST_TEN)
        .play_action(passing.y_cross().adjust(A.PLAY_ACTION("RB"),
                                              A.PROTECTION("Slide Rt")),
                     tell="Safeties triggering downhill on run action",
                     situation=S.Situation(down=2, distance=4))
        .shot(passing.four_verticals().adjust(A.PLAY_ACTION("RB")),
              tell="Single-high with the FS cheating into the box",
              situation=S.Situation(down=1, distance=10))
        .answer(passing.rpo_bubble(),
                tell="Overhang defender playing inside the box, no leverage",
                situation=S.FIRST_TEN)
        .tag("run", "zone", "install-week-1")
        .build()
    )


def power_counter_series() -> Series:
    """Gap-scheme series: pullers, wrong-shoulder answers, and the boot off it."""
    return (
        series("Power / Counter Series",
               "Same backfield action, different pullers. Attack over-flow "
               "and the linebacker who reads guards.")
        .base(running.power_right(),
              note="Down block, kick the end, wrap the play-side LB",
              situation=S.Situation(down=1, distance=10))
        .complement(running.counter_trey(),
                    tell="LBs keying the guard and flowing hard to power",
                    situation=S.Situation(down=2, distance=5))
        .constraint(running.trap(),
                    tell="Penetrating 3-tech chasing the pull upfield",
                    situation=S.Situation(down=2, distance=3))
        .constraint(running.toss_sweep(),
                    tell="Everything squeezing inside, edge left soft",
                    situation=S.Situation(down=1, distance=10))
        .play_action(passing.sail_concept().adjust(A.PLAY_ACTION("RB"),
                                                   A.PROTECTION("Boot Rt")),
                     tell="Backside safety filling the alley",
                     situation=S.Situation(down=2, distance=6))
        .shot(passing.scissors().adjust(A.PLAY_ACTION("RB")),
              tell="Corners squatting, safety rotating to the run",
              situation=S.Situation(down=1, distance=10))
        .tag("run", "gap", "install-week-2")
        .build()
    )


def mesh_series() -> Series:
    """One picture, many answers — the modern third-down staple."""
    mesh = passing.mesh_concept()
    return (
        series("Mesh Series",
               "Rub the crossers, then tag the third receiver to beat "
               "whatever the coverage gives you.")
        .base(mesh.protect("Slide Rt"),
              note="Sit vs zone, run vs man. QB works the mesh to the back",
              situation=S.THIRD_MEDIUM)
        .complement(mesh.adjust(A.TAG("Y", R.CORNER(), name="Y Corner")),
                    tell="Buzz/hook defender widening with the crossers",
                    situation=S.THIRD_MEDIUM)
        .complement(mesh.adjust(A.TAG("X", R.DIG(), name="X Dig")),
                    tell="Two-high with soft corners",
                    situation=S.THIRD_LONG)
        .constraint(mesh.adjust(A.MOTION("Z", "jet"), A.TAG("Z", R.BUBBLE(),
                                                            name="Z Now")),
                    tell="Off coverage, no one over the slot",
                    situation=S.Situation(down=1, distance=10))
        .answer(mesh.adjust(A.MAX_PROTECT("RB"), A.ALERT("Alert Fade vs Cover 0")),
                tell="Pressure look, six in the box, man free",
                situation=S.THIRD_LONG)
        .trick(passing.snag().adjust(A.MOTION("H", "return")),
               tell="Defense jumping the crossers on tape",
               situation=S.THIRD_SHORT)
        .tag("pass", "third-down", "install-week-1")
        .build()
    )


def sprint_out_series() -> Series:
    """Move the launch point: flood the boundary, punish the rush."""
    return (
        series("Sprint-Out / Flood Series",
               "Three levels to one side, on the move. Simple reads for the "
               "quarterback and a built-in run answer.")
        .base(passing.flood().protect("Sprint Rt"),
              note="High-low the flat defender: corner, sail, flat",
              situation=S.Situation(down=2, distance=7))
        .complement(passing.sail_concept().protect("Sprint Rt"),
                    tell="Flat defender sinking under the sail",
                    situation=S.THIRD_MEDIUM)
        .constraint(running.qb_keeper(),
                    tell="Coverage turning its back, no contain player",
                    situation=S.THIRD_SHORT)
        .constraint(passing.drive_concept().adjust(A.FLIP()),
                    tell="Defense over-rotating to the sprint side",
                    situation=S.Situation(down=2, distance=8))
        .shot(passing.deep_cross().adjust(A.PLAY_ACTION("RB")),
              tell="Backside safety chasing the sprint action",
              situation=S.Situation(down=1, distance=10))
        .tag("pass", "movement", "install-week-3")
        .build()
    )


def red_zone_series() -> Series:
    """Tight-field answers: rubs, fades, and the run that closes it out."""
    return (
        series("Red Zone Series",
               "The field is short — win with leverage, picks, and the fade "
               "the corner can't play.")
        .base(redzone.fade_corner(),
              note="Iso the outside receiver, corner route as the safety valve",
              situation=S.RED_ZONE)
        .complement(redzone.bunch_rubs_endzone(),
                    tell="Man coverage across the board inside the 10",
                    situation=S.LOW_RED)
        .complement(redzone.fade_slant(),
                    tell="Press with inside leverage",
                    situation=S.LOW_RED)
        .constraint(redzone.goal_line_power(),
                    tell="Light box, nickel personnel still on the field",
                    situation=S.GOAL_LINE)
        .answer(redzone.back_shoulder(),
                tell="Corner turning and running with the fade",
                situation=S.LOW_RED)
        .trick(redzone.qb_sneak(),
               tell="Anything short of the goal line on 4th down",
               situation=S.Situation(down=4, distance=1, yard_line=1))
        .tag("red-zone", "scoring", "install-week-2")
        .build()
    )


def two_minute_series() -> Series:
    """Sideline, chunk, clock. What you rep on Thursday."""
    from ..models.situation import Tempo
    hurry = A.TEMPO(Tempo.NO_HUDDLE.value)
    return (
        series("Two-Minute Series",
               "Get out of bounds, take the chunk when it is there, "
               "never take a sack.")
        .base(passing.stick().adjust(hurry),
              note="Ball out on time, receiver works to the sideline",
              situation=S.TWO_MINUTE)
        .complement(passing.spacing().adjust(hurry),
                    tell="Soft zone giving up everything underneath",
                    situation=S.TWO_MINUTE)
        .complement(passing.smash().adjust(hurry),
                    tell="Cover 2 corners squatting on the sideline routes",
                    situation=S.TWO_MINUTE)
        .shot(passing.four_verticals().adjust(hurry),
              tell="Single high, one timeout left, need 25+",
              situation=S.TWO_MINUTE)
        .answer(passing.double_slant().adjust(hurry, A.MAX_PROTECT("RB")),
                tell="All-out pressure with the clock running",
                situation=S.TWO_MINUTE)
        .tag("two-minute", "situational", "install-week-4")
        .build()
    )


ALL_SERIES = {
    "inside_zone": inside_zone_series,
    "power_counter": power_counter_series,
    "mesh": mesh_series,
    "sprint_out": sprint_out_series,
    "red_zone": red_zone_series,
    "two_minute": two_minute_series,
}


def all_series() -> list[Series]:
    """Build every stock series."""
    return [fn() for fn in ALL_SERIES.values()]


__all__ = [
    "inside_zone_series", "power_counter_series", "mesh_series",
    "sprint_out_series", "red_zone_series", "two_minute_series",
    "ALL_SERIES", "all_series",
]
