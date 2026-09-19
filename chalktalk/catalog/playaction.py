"""
Play action and the movement game.

Every one of these starts by looking exactly like a run. The blocking sells it,
the quarterback's eyes sell it, and the concept behind it attacks whoever
believed it — usually a linebacker who came downhill or a safety who rotated.

    from chalktalk.catalog import playaction as PA

    PA.pa_boot()          # zone action one way, quarterback out the other
    PA.pa_shot()          # the safety bit; take the top off
"""
from __future__ import annotations
from typing import Optional

from ..builder import play as _b
from ..models.formation import Formation
from ..models.play import Play, PlayType
from ..templates import (blocking as B, formations as F, qb as Q, routes as R,
                         schemes as SC)


def pa_boot(formation: Optional[Formation] = None) -> Play:
    """Boot — zone action right, quarterback off the edge left, three levels."""
    f = formation or F.I_FORM_PRO_RIGHT()
    return (
        _b(f).scheme(SC.boot(-1), protection="Boot Lt")
        .blocks(FB=B.KICK(-1, target="DE"))
        .routes(
            X=R.COMEBACK(depth=14),      # backside receiver comes back to him
            Y=R.DRAG(depth=4, cross=14),  # tight end crosses to the boot side
            Z=R.OVER(stem=12, cross=16),  # deep over on top
        )
        .qb(Q.BOOT(-1, back="RB", reads=["Y", "X", "Z"],
                   rule="Flat to the edge: crosser, comeback, then run"))
        .name("PA Boot Left")
        .play_type(PlayType.PASS)
        .tag("play-action", "boot", "movement")
        .describe("Sell inside zone right, take it out the back door left. "
                  "The crosser beats the linebacker who filled.")
        .build()
    )


def pa_cross(formation: Optional[Formation] = None) -> Play:
    """Play action Y-cross — the deep crosser behind a run-action linebacker."""
    f = formation or F.SINGLE_BACK_PRO_RIGHT()
    return (
        _b(f).pass_pro(SC.max_protect(1, extras=("RB",)), "Max - 7 Man")
        .routes(
            Y=R.OVER(stem=12, cross=18),
            X=R.FLY(depth=22),
            Z=R.COMEBACK(depth=16),
            H=R.FLAT(depth=4, width=8),
        )
        .qb(Q.PLAY_ACTION(1, back="RB", steps=5, reads=["Y", "Z", "H"],
                          rule="Fake it, find the crosser behind the backers"))
        .name("PA Y-Cross")
        .play_type(PlayType.PASS)
        .tag("play-action", "cross", "shot")
        .describe("Heavy run fake pulls the second level up. Y crosses into "
                  "the window they vacate; the comeback is the outlet.")
        .build()
    )


def pa_shot(formation: Optional[Formation] = None) -> Play:
    """The safety came down. Take the top off."""
    f = formation or F.I_FORM_STRONG_RIGHT()
    return (
        _b(f).pass_pro(SC.max_protect(1, extras=("FB", "RB")), "Max - 8 Man")
        .routes(
            Z=R.POST(stem=12, depth=22),
            X=R.FLY(depth=24),
            Y=R.SEAM(depth=16),
        )
        .qb(Q.PLAY_ACTION(1, back="RB", steps=7, reads=["Z", "X", "Y"],
                          rule="One safety means the post; two means check it down"))
        .name("PA Shot")
        .play_type(PlayType.PASS)
        .tag("play-action", "shot", "explosive")
        .describe("Maximum protection, minimum receivers, one answer: if the "
                  "safety triggers on the fake, the post is behind him.")
        .build()
    )


def pa_waggle(formation: Optional[Formation] = None) -> Play:
    """Waggle — power action right, quarterback and the flood go left."""
    f = formation or F.I_FORM_STRONG_RIGHT()
    return (
        _b(f).scheme(SC.boot(-1), protection="Waggle Lt")
        .blocks(FB=B.KICK(-1, target="DE"))
        .routes(
            X=R.CORNER(stem=8, depth=16),
            Y=R.DRAG(depth=5, cross=16),
            Z=R.OVER(stem=10, cross=20),
        )
        .qb(Q.BOOT(-1, back="RB", reads=["X", "Y", "Z"],
                   rule="Corner, crosser, then take what is left"))
        .name("Waggle Left")
        .play_type(PlayType.PASS)
        .tag("play-action", "waggle", "movement", "flood")
        .describe("Power action to the right with the guard pulling. Three "
                  "levels flood the boundary the quarterback is running to.")
        .build()
    )


def naked(formation: Optional[Formation] = None) -> Play:
    """Naked — no protection at all, just the fake and the edge."""
    f = formation or F.GUN_OFFSET_BACK_RIGHT()
    return (
        _b(f).scheme(SC.outside_zone(1), protection="Naked - no help")
        .routes(
            Y=R.FLAT(depth=3, width=9),
            H=R.DRAG(depth=5, cross=14),
            X=R.COMEBACK(depth=13),
            Z=R.FLY(depth=20),
        )
        .qb(Q.BOOT(-1, back="RB", reads=["Y", "H", "X"],
                   rule="Nobody is blocking the backside — be decisive"))
        .name("Naked Left")
        .play_type(PlayType.PASS)
        .tag("play-action", "naked", "movement", "boot")
        .describe("Outside zone right with the whole line running that way. "
                  "The quarterback keeps it and nothing is blocked behind him.")
        .build()
    )


def pa_keeper(formation: Optional[Formation] = None) -> Play:
    """Keeper — run action, then a two-man high-low on the edge defender."""
    f = formation or F.GUN_TRIPS_TE_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(-1), protection="Keep Rt")
        .routes(
            Y=R.CORNER_ENDZONE(stem=6, depth=10),
            H=R.FLAT(depth=3, width=8),
            Z=R.FLY(depth=18),
            X=R.DRAG(depth=6, cross=16),
        )
        .qb(Q.BOOT(1, back="RB", reads=["Y", "H", "X"],
                   rule="High-low the flat defender; run if he takes both"))
        .name("Keeper Right")
        .play_type(PlayType.PASS)
        .tag("play-action", "keeper", "movement", "hi-lo")
        .describe("Zone action away, quarterback keeps it to the trips side. "
                  "Corner over flat puts the flat defender in a bind.")
        .build()
    )


def pa_dagger(formation: Optional[Formation] = None) -> Play:
    """Dagger off run action — clear the seam, throw the dig underneath it."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).pass_pro(SC.half_slide(1), "Half Slide Rt")
        .routes(
            H=R.SEAM(depth=20),          # clears the middle
            X=R.DIG(stem=14, cross=12),  # dig in behind it
            Z=R.COMEBACK(depth=15),
            Y=R.FLAT(depth=4, width=7),
            RB=R.SWING(),
        )
        .qb(Q.PLAY_ACTION(1, back="RB", steps=5, reads=["X", "Z", "Y", "RB"],
                          rule="Seam clears the safety; the dig replaces him"))
        .name("PA Dagger")
        .play_type(PlayType.PASS)
        .tag("play-action", "dagger", "vertical-stretch")
        .describe("The seam runs the safety out of the middle and the dig "
                  "sits down in the space he leaves.")
        .build()
    )


__all__ = ["pa_boot", "pa_cross", "pa_shot", "pa_waggle", "naked",
           "pa_keeper", "pa_dagger"]
