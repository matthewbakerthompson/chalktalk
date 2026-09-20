"""
Run-pass options.

The line blocks a run. Somebody runs a route. The quarterback rides the mesh and
reads one defender: if that man plays the run, throw it; if he covers, hand it
off. The whole play is one decision, which is why the `key` matters more than
the routes do.

    from chalktalk.catalog import rpo

    rpo.glance()      # the safety came down; throw it behind him
    rpo.bubble()      # the overhang is in the box; get it outside
"""
from __future__ import annotations
from typing import Optional

from ..builder import play as _b
from ..models.formation import Formation
from ..models.play import Play, PlayType
from ..templates import (blocking as B, formations as F, qb as Q, routes as R,
                         schemes as SC)


def bubble(formation: Optional[Formation] = None) -> Play:
    """Inside zone with a bubble attached — read the overhang defender."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(1), protection="Run action")
        .routes(H=R.BUBBLE(width=5), Z=R.SCREEN(depth=-0.5, width=3),
                RB=R.RUN(dx=1.5, dy=6))
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the overhang", reads=["H"],
                   rule="In the box, throw it; over the slot, hand it off"))
        .name("RPO Bubble")
        .play_type(PlayType.RPO)
        .tag("rpo", "bubble", "zone-read")
        .describe("Inside zone with a bubble behind it. The overhang defender "
                  "cannot be right — he is either in the run fit or out on the slot.")
        .build()
    )


def glance(formation: Optional[Formation] = None) -> Play:
    """Zone with a glance behind it — read the safety who fills."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).scheme(SC.inside_zone(1), protection="Run action")
        .routes(H=R.SLANT(stem=3, depth=12), X=R.FLY(depth=16),
                RB=R.RUN(dx=1.5, dy=6))
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the backside safety", reads=["H"],
                   rule="Safety fills, throw the glance behind him"))
        .name("RPO Glance")
        .play_type(PlayType.RPO)
        .tag("rpo", "glance", "post-snap")
        .describe("The glance is a skinny post from the backside slot. If the "
                  "safety triggers on the run, nobody is over the top of it.")
        .build()
    )


def slant(formation: Optional[Formation] = None) -> Play:
    """The quickest one there is — zone action, throw the slant off the backer."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(1), protection="Run action")
        .routes(H=R.QUICK_SLANT(depth=6), Z=R.FLY(depth=14),
                RB=R.RUN(dx=1.5, dy=6))
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the play-side linebacker", reads=["H"],
                   rule="Backer steps up, pull it and throw the slant"))
        .name("RPO Slant")
        .play_type(PlayType.RPO)
        .tag("rpo", "slant", "quick")
        .describe("One step, one read, one throw. The slant replaces the "
                  "linebacker the run just moved.")
        .build()
    )


def pop(formation: Optional[Formation] = None) -> Play:
    """Pop pass — the tight end sits down in the window the fit vacates."""
    f = formation or F.GUN_TRIPS_TE_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(1), protection="Run action")
        .routes(Y=R.SEAM(depth=10), Z=R.FLY(depth=16),
                RB=R.RUN(dx=1.5, dy=6))
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the Mike", reads=["Y"],
                   rule="Mike fits the run, pop it over his head"))
        .name("RPO Pop")
        .play_type(PlayType.RPO)
        .tag("rpo", "pop", "seam")
        .describe("The tight end releases straight up the seam. If the Mike "
                  "fills, the ball goes over him before the safety arrives.")
        .build()
    )


def arrow(formation: Optional[Formation] = None) -> Play:
    """Gap-scheme RPO — power blocking with a quick arrow to the flat."""
    f = formation or F.GUN_TREY_RIGHT()
    return (
        _b(f).scheme(SC.power(1, kicker=None), protection="Run action")
        .routes(H=R.FLAT(depth=2, width=8), Z=R.FLY(depth=16),
                RB=R.RUN(dx=3, dy=6))
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the flat defender", reads=["H"],
                   rule="He squeezes the run, throw the arrow outside him"))
        .name("RPO Arrow")
        .play_type(PlayType.RPO)
        .tag("rpo", "arrow", "gap-scheme")
        .describe("Gap-scheme run with a receiver leaking to the flat. "
                  "Harder to defend than a zone RPO because the pullers sell it.")
        .build()
    )


def zone_stick(formation: Optional[Formation] = None) -> Play:
    """Zone with stick-flat behind it - read the hook defender."""
    f = formation or F.SHOTGUN_TRIPS_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(1), protection="Run action")
        .block("X")
        .routes(Y=R.HITCH(depth=5), H=R.FLAT(depth=2, width=6), Z=R.FLY(depth=16),
                RB=R.RUN(dx=1.5, dy=6))
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the hook defender", reads=["Y", "H"],
                   rule="He fits the run, throw the stick; he walls it, hand it off"))
        .name("RPO Stick")
        .play_type(PlayType.RPO)
        .tag("rpo", "stick", "quick")
        .describe("Inside zone with the stick and flat behind it, reading the hook "
                  "defender who has to either fit the run or wall the tight end.")
        .build()
    )


def now(formation: Optional[Formation] = None) -> Play:
    """Zone to the trips side, a now screen to the single receiver."""
    f = formation or F.GUN_TRIPS_TE_RIGHT()
    return (
        _b(f).scheme(SC.inside_zone(1), protection="Run action")
        .blocks(Y=B.BASE(target="DE"), H=B.BASE(target="N"), Z=B.BASE(target="CB"))
        .routes(
            X=R.SCREEN(depth=-1.0, width=1.5),
            RB=R.RUN(dx=-5, dy=7),     # left-side back: mirrors to the right
        )
        .bc("RB")
        .qb(Q.MESH(1, back="RB", key="the boundary corner", reads=["X"],
                   rule="Corner off at seven or more, throw the now; pressed, give it"))
        .name("RPO Now")
        .play_type(PlayType.RPO)
        .tag("rpo", "now", "quick")
        .describe("Inside zone to the trips side with a now screen to the single "
                  "receiver, thrown whenever the backside corner gives him a cushion.")
        .build()
    )


__all__ = ["bubble", "glance", "slant", "pop", "arrow", "zone_stick", "now"]
