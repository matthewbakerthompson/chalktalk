"""
The screen game.

A screen is a play that wins by losing on purpose: let the rush come, get out of
its way, and give the ball to somebody standing behind three blockers with grass
in front of him. The tell is always the same — linemen releasing downfield and a
quarterback who retreats further than the protection calls for.

    from chalktalk.catalog import screens

    screens.rb_slip()        # classic slip screen to the back
    screens.tunnel()         # receiver comes back inside behind blockers
"""
from __future__ import annotations
from typing import Optional

from ..builder import play as _b
from ..models.formation import Formation
from ..models.play import Play, PlayType
from ..templates import (blocking as B, formations as F, qb as Q, routes as R,
                         schemes as SC)


def rb_slip(formation: Optional[Formation] = None) -> Play:
    """Slip screen — the tackles let them through, the back slips out behind."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Screen Rt")
        .blocks(
            RG=B.CLIMB(1, target="M"),     # release and find a linebacker
            RT=B.CLIMB(1, target="S"),
            C=B.CLIMB(0, target="W"),
        )
        .routes(
            RB=R.SWING(width=6, depth=1),
            X=R.FLY(depth=18),             # clear the coverage out
            Z=R.FLY(depth=18),
            H=R.OUT(stem=5, depth=7),
            Y=R.FLAT(depth=3, width=6),
        )
        .bc("RB")
        .qb(Q.SCREEN(1, back="RB", reads=["RB"]))
        .name("RB Slip Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "slip", "rb-screen")
        .describe("Show a deep drop and let the rush run past. Three linemen "
                  "release; the back catches it with a wall in front of him.")
        .build()
    )


def tunnel(formation: Optional[Formation] = None) -> Play:
    """Tunnel screen — the receiver comes back inside behind his teammates."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Quick Screen")
        .blocks(Y=B.BASE(target="CB"), Z=B.BASE(target="N"))
        .routes(
            H=R.SCREEN(depth=-1.0, width=-5.0),   # works back to the middle
            X=R.FLY(depth=16),
            RB=R.FLAT(depth=3, width=6),
        )
        .bc("H")
        .qb(Q.GUN(0, reads=["H"], rule="Catch and throw it now"))
        .name("Tunnel Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "tunnel", "quick-screen")
        .describe("The slot takes one step out and comes back underneath two "
                  "blockers. Beats an outside-leverage corner.")
        .build()
    )


def bubble_screen(formation: Optional[Formation] = None) -> Play:
    """Bubble screen — the fastest way to make a light box pay."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Quick Screen")
        .blocks(Z=B.BASE(target="CB"), Y=B.BASE(target="S"))
        .routes(
            H=R.BUBBLE(width=6),
            X=R.FLY(depth=16),
            RB=R.FLAT(depth=2, width=5),
        )
        .bc("H")
        .qb(Q.GUN(0, reads=["H"], rule="Throw it out there and let him run"))
        .name("Bubble Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "bubble", "perimeter")
        .describe("Three receivers, two defenders. The ball gets to the flat "
                  "before anybody inside can help.")
        .build()
    )


def jailbreak(formation: Optional[Formation] = None) -> Play:
    """Jailbreak — everybody blocks for the receiver on the wide side."""
    f = formation or F.GUN_SPREAD_4WR()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Jailbreak")
        .blocks(
            LT=B.CLIMB(1, target="CB"),
            LG=B.CLIMB(1, target="S"),
            C=B.CLIMB(1, target="M"),
        )
        .routes(
            Z=R.SCREEN(depth=-1.5, width=2.0),
            X=R.FLY(depth=18),
            H=R.OUT(stem=4, depth=6),
            Y=R.FLAT(depth=3, width=7),
        )
        .bc("Z")
        .qb(Q.SCREEN(1, back="Z", reads=["Z"]))
        .name("Jailbreak Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "jailbreak", "wr-screen")
        .describe("Three linemen sprint to the perimeter. Slow-developing and "
                  "obvious once, enormous the first time.")
        .build()
    )


def middle(formation: Optional[Formation] = None) -> Play:
    """Middle screen — let them widen, then throw it right back inside."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Middle Screen")
        .blocks(
            LG=B.CLIMB(-1, target="W"),
            C=B.CLIMB(0, target="M"),
            RG=B.CLIMB(1, target="S"),
        )
        .routes(
            RB=R.ANGLE(depth=2),
            X=R.FLY(depth=20),
            Z=R.FLY(depth=20),
            H=R.SEAM(depth=16),
            Y=R.SEAM(depth=14),
        )
        .bc("RB")
        .qb(Q.SCREEN(-1, back="RB", reads=["RB"],
                     rule="Drive them wide, then step up and throw it inside"))
        .name("Middle Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "middle", "rb-screen")
        .describe("Four verticals clear everybody out. The back sits down in "
                  "the middle behind three climbing linemen.")
        .build()
    )


def te_leak(formation: Optional[Formation] = None) -> Play:
    """TE leak — he blocks, they forget about him, he leaks out the back."""
    f = formation or F.SHOTGUN_ACE()
    return (
        _b(f).pass_pro(SC.max_protect(1, extras=("RB",)), "Max - Leak")
        .blocks(TE=B.PASS_SET(-1, target="DE"))
        .routes(
            Y=R.FLAT(depth=2, width=10),   # leaks late to the flat
            X=R.FLY(depth=20),
            Z=R.POST(stem=10, depth=18),
        )
        .bc("Y")
        .qb(Q.SCREEN(1, back="Y", reads=["Y", "Z"],
                     rule="Hold them with your eyes, then find him late"))
        .name("TE Leak Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "leak", "te-screen", "gadget")
        .describe("The tight end sets like he is protecting, then releases "
                  "into the flat once the rush has committed.")
        .build()
    )


def swing_screen(formation: Optional[Formation] = None) -> Play:
    """Swing screen - the back swings wide and two linemen release to lead him."""
    f = formation or F.GUN_DOUBLES_LEFT()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Swing Screen Rt")
        .blocks(
            RT=B.PULL(1, target="S", width=6.0),     # release flat to the edge
            RG=B.PULL(1, target="M", width=4.5),
            Z=B.BASE(target="CB"),
            Y=B.CLIMB(1, target="SS"),
        )
        .routes(
            RB=R.SWING(width=7, depth=2),
            X=R.FLY(depth=18),
            H=R.SEAM(depth=16),
        )
        .bc("RB")
        .qb(Q.GUN(1, reads=["RB"],
                  rule="Catch it and throw it now; lead him toward the sideline"))
        .name("Swing Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "swing", "rb-screen", "quick-screen")
        .describe("The back swings wide on the snap and catches it behind the right "
                  "tackle and guard, who release flat to lead him while the receivers "
                  "block the corner and safety.")
        .build()
    )


def double_screen(formation: Optional[Formation] = None) -> Play:
    """Double screen - a screen set up on each side; throw to the one they left."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).pass_pro(SC.big_on_big(), "Double Screen")
        .blocks(
            LT=B.CLIMB(-1, target="W"),              # release for the back
            LG=B.CLIMB(-1, target="M"),
            RT=B.CLIMB(1, target="N"),               # release for the flanker
            X=B.BASE(target="CB"),
            H=B.BASE(target="SS"),
            Y=B.CLIMB(1, target="CB"),
        )
        .routes(
            RB=R.SWING(width=6, depth=1),            # slip screen to the left
            Z=R.SCREEN(depth=-1.0, width=-5.0),      # tunnel screen to the right
        )
        .bc("RB")
        .qb(Q.SCREEN(-1, back="RB", reads=["RB", "Z"],
                     rule="Sell the drop, then throw the screen they did not flow to"))
        .name("Double Screen")
        .play_type(PlayType.SCREEN)
        .tag("screen", "double-screen", "rb-screen", "wr-screen")
        .describe("A slip screen to the back on one side and a tunnel screen to the "
                  "flanker on the other, so the quarterback throws to whichever side "
                  "the defense did not flow to.")
        .build()
    )


__all__ = ["rb_slip", "tunnel", "bubble_screen", "jailbreak", "middle", "te_leak",
           "swing_screen", "double_screen"]
