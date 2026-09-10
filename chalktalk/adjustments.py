"""
chalktalk.adjustments — composable, serializable play alts.

An Adjustment is a small piece of data (not an opaque lambda) that turns one
Play into another. Because they are data, a variant of a play is just
`base + [adjustments]`: it round-trips through JSON, diffs cleanly in git, and
prints itself onto a call sheet.

Usage
-----
from chalktalk import adjustments as A
from chalktalk.templates import routes as R

mesh = passing.mesh_concept()

# One alt
mesh_jet = mesh.adjust(A.MOTION("Z", "jet"))

# Stacked alts — name and tags update automatically
third_down = mesh.adjust(
    A.PROTECTION("Slide Rt"),
    A.TAG("Y", R.CORNER(), name="Y Corner"),
    A.ALERT("Alert Fade vs press"),
)

# Every single-alt variant of a play, as its own Play
family = A.variants(mesh, A.FLIP(), A.MOTION("Z", "jet"), A.MAX_PROTECT())
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel

from .models.play import Play, PlayType
from .models.route import Route
from .models.formation import Formation
from .models.situation import Tempo
from .templates import routes as R


class AdjustmentKind(str, Enum):
    TAG        = "tag"          # swap one player's route
    MOTION     = "motion"       # pre-snap movement, same final alignment
    SHIFT      = "shift"        # pre-snap movement to a NEW alignment
    FLIP       = "flip"         # mirror the whole play
    FORMATION  = "formation"    # same concept, new formation
    PROTECTION = "protection"   # protection call
    TEMPO      = "tempo"        # no-huddle / check / freeze
    ALERT      = "alert"        # pre-snap check, no geometry change
    BLOCK      = "block"        # keep a player in to protect
    RELEASE    = "release"      # send a blocker out on a route
    PLAY_ACTION = "play_action"  # add a run fake to a pass
    PERSONNEL  = "personnel"    # personnel-grouping change (metadata)


# Pre-snap motion presets. Each returns the (x, y) the player STARTS at,
# given where they line up at the snap. Sign follows the player's own side.
_MOTION_PRESETS: dict[str, str] = {
    "jet":    "Full-speed across the formation, ball snapped on the move.",
    "orbit":  "Loops behind the QB from the opposite side.",
    "short":  "Two-step tighten inside; ghost/return look.",
    "across": "Crosses the formation and stops (trade).",
    "return": "Starts across, returns to the original side.",
    "out":    "Widens from a tight alignment.",
    "in":     "Tightens down from a wide alignment.",
}


_SIDELINE = 25.0   # keep pre-snap alignments on the field


def _motion_geometry(kind: str, x: float, y: float
                     ) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Given where a player lines up, return (origin, snap_position).

    Some motions end where the player already was (short, out, in, return);
    the full-speed ones — jet, orbit, across — move the player, so the snap
    happens somewhere else entirely.
    """
    side = 1.0 if x >= 0 else -1.0
    clamp = lambda v: max(-_SIDELINE, min(_SIDELINE, v))   # noqa: E731

    if kind == "jet":
        # Full speed across; ball is snapped as they pass the quarterback.
        return ((x, y), (clamp(-side * 2.0), y - 0.5))
    if kind == "orbit":
        # Loops behind the QB and is still moving at the snap.
        return ((x, y), (clamp(-side * 5.0), y - 4.0))
    if kind == "across":
        # Trade: crosses the formation and re-sets.
        return ((x, y), (clamp(-x), y))
    if kind == "return":
        return ((clamp(x - side * 8.0), y), (x, y))
    if kind == "out":
        return ((clamp(x - side * 6.0), y), (x, y))
    if kind == "in":
        return ((clamp(x + side * 6.0), y), (x, y))
    # "short" / ghost — a couple of steps inside and back to the alignment
    return ((clamp(x - side * 3.5), y), (x, y))


class Adjustment(BaseModel):
    """
    A named modification to a Play. Construct with the factory helpers below
    (TAG, MOTION, FLIP, ...) rather than by hand.
    """
    kind: AdjustmentKind
    name: str                                # call-sheet suffix, e.g. "Z Jet"
    label: Optional[str] = None              # target player, when relevant
    route: Optional[Route] = None
    formation: Optional[Formation] = None
    value: Optional[str] = None              # protection / tempo / personnel / text
    position: Optional[tuple[float, float]] = None
    tags: list[str] = []
    # Adjustments that write to a dedicated Play field (protection, tempo,
    # alerts) show up there instead of in the call suffix.
    stamp_name: bool = True

    # ── Application ───────────────────────────────────────────────────────────

    def apply(self, play: Play) -> Play:
        handler = getattr(self, f"_apply_{self.kind.value}")
        out: Play = handler(play)
        return self._stamp(out)

    def _stamp(self, play: Play) -> Play:
        """Record the adjustment on the play (call suffix, concept, tags)."""
        updates: dict[str, Any] = {
            "concept": play.concept or play.name,
            "tags": [*play.tags, *self.tags],
        }
        if self.stamp_name:
            updates["adjustments"] = [*play.adjustments, self.name]
        return play.model_copy(update=updates)

    # Each handler returns a Play with geometry/metadata changed but the
    # adjustment bookkeeping left to _stamp().

    def _apply_tag(self, play: Play) -> Play:
        assert self.label and self.route
        return play.with_route(self.label, self.route)

    def _apply_motion(self, play: Play) -> Play:
        kind = self.value or "short"
        new_assignments = []
        snap: Optional[tuple[float, float]] = None
        for a in play.assignments:
            if a.player.label == self.label:
                origin, snap = _motion_geometry(kind, a.player.x, a.player.y)
                if self.position is not None:
                    origin = self.position
                a = a.model_copy(update={
                    "player": a.player.model_copy(update={"x": snap[0], "y": snap[1]}),
                    "motion_from": origin,
                    "motion_type": kind,
                })
            new_assignments.append(a)
        updates: dict[str, Any] = {"assignments": new_assignments}
        if snap is not None:
            updates["formation"] = play.formation.model_copy(update={
                "players": [p.model_copy(update={"x": snap[0], "y": snap[1]})
                            if p.label == self.label else p
                            for p in play.formation.players]
            })
        return play.model_copy(update=updates)

    def _apply_shift(self, play: Play) -> Play:
        assert self.label and self.position
        nx, ny = self.position
        new_assignments = []
        for a in play.assignments:
            if a.player.label == self.label:
                a = a.model_copy(update={
                    "player": a.player.model_copy(update={"x": nx, "y": ny}),
                    "motion_from": (a.player.x, a.player.y),
                    "motion_type": self.value or "shift",
                })
            new_assignments.append(a)
        new_players = [
            p.model_copy(update={"x": nx, "y": ny}) if p.label == self.label else p
            for p in play.formation.players
        ]
        return play.model_copy(update={
            "assignments": new_assignments,
            "formation": play.formation.model_copy(update={"players": new_players}),
        })

    def _apply_flip(self, play: Play) -> Play:
        flipped = play.mirror()
        return flipped.model_copy(update={
            "name": _flip_name(flipped.name),
            "formation": flipped.formation.model_copy(
                update={"name": _flip_name(flipped.formation.name)}
            ),
        })

    def _apply_formation(self, play: Play) -> Play:
        assert self.formation
        return play.with_formation(self.formation)

    def _apply_protection(self, play: Play) -> Play:
        return play.model_copy(update={"protection": self.value})

    def _apply_tempo(self, play: Play) -> Play:
        return play.model_copy(update={"tempo": Tempo(self.value)})

    def _apply_alert(self, play: Play) -> Play:
        return play.model_copy(update={"alerts": [*play.alerts, self.value or self.name]})

    def _apply_block(self, play: Play) -> Play:
        assert self.label
        from .templates.blocking import PASS_SET
        return play.with_block(self.label, PASS_SET()).model_copy(
            update={"protection": self.value or play.protection}
        )

    def _apply_release(self, play: Play) -> Play:
        assert self.label
        return play.with_route(self.label, self.route or R.FLAT())

    def _apply_play_action(self, play: Play) -> Play:
        fake_to = self.label
        new = []
        for a in play.assignments:
            if fake_to and a.player.label == fake_to:
                a = a.model_copy(update={
                    "route": self.route or R.RUN(dx=4.0, dy=-1.0),
                    "is_ball_carrier": False,
                    "note": "Sell the fake — full mesh with QB",
                })
            new.append(a)
        return play.model_copy(update={
            "assignments": new,
            "play_type": PlayType.PASS,
            "protection": play.protection or "Max - 6 Man",
        })

    def _apply_personnel(self, play: Play) -> Play:
        return play.model_copy(update={
            "formation": play.formation.model_copy(update={"personnel": self.value or ""})
        })

    def __str__(self) -> str:
        return self.name


def _flip_name(name: str) -> str:
    """Swap right/left words in a play or formation name."""
    from .models.core import flip_side_name
    return flip_side_name(name) or name


# ── Factory helpers ───────────────────────────────────────────────────────────

def TAG(label: str, route: Route, name: Optional[str] = None) -> Adjustment:
    """Swap one player's route: A.TAG('Y', R.CORNER()) -> 'Y Corner'."""
    return Adjustment(
        kind=AdjustmentKind.TAG, label=label, route=route,
        name=name or f"{label} {route.route_type.value.title()}",
        tags=["tag"],
    )


def MOTION(label: str, kind: str = "short", name: Optional[str] = None) -> Adjustment:
    """
    Pre-snap motion that ends where the player started aligning.
    kind: jet | orbit | short | across | return | out | in
    """
    if kind not in _MOTION_PRESETS:
        raise ValueError(f"unknown motion '{kind}' (have: {', '.join(_MOTION_PRESETS)})")
    return Adjustment(
        kind=AdjustmentKind.MOTION, label=label, value=kind,
        name=name or f"{label} {kind.title()}", tags=["motion", kind],
    )


def SHIFT(label: str, x: float, y: float, name: Optional[str] = None) -> Adjustment:
    """Move a player to a new alignment pre-snap (formation into formation)."""
    return Adjustment(
        kind=AdjustmentKind.SHIFT, label=label, position=(x, y),
        name=name or f"{label} Shift", tags=["shift"],
    )


def FLIP(name: str = "Flip") -> Adjustment:
    """Mirror the whole play; Right/Left in the name swaps too."""
    return Adjustment(kind=AdjustmentKind.FLIP, name=name, tags=["flip"])


def FORMATION(formation: Formation, name: Optional[str] = None) -> Adjustment:
    """Run the same concept from a different formation."""
    return Adjustment(
        kind=AdjustmentKind.FORMATION, formation=formation,
        name=name or f"from {formation.name}", tags=["formation"],
    )


def PROTECTION(scheme: str) -> Adjustment:
    """Set the protection call ('Slide Rt', 'Half-Slide', '7-Man')."""
    return Adjustment(kind=AdjustmentKind.PROTECTION, value=scheme,
                      name=scheme, tags=["protection"], stamp_name=False)


def MAX_PROTECT(label: str = "RB", scheme: str = "Max - 7 Man") -> Adjustment:
    """Keep a back in to block."""
    return Adjustment(kind=AdjustmentKind.BLOCK, label=label, value=scheme,
                      name="Max", tags=["protection", "max"], stamp_name=False)


def RELEASE(label: str = "RB", route: Optional[Route] = None,
            name: Optional[str] = None) -> Adjustment:
    """Send a would-be blocker out into the pattern."""
    route = route or R.FLAT()
    return Adjustment(kind=AdjustmentKind.RELEASE, label=label, route=route,
                      name=name or f"{label} Release", tags=["release"])


def TEMPO(tempo: str) -> Adjustment:
    """no_huddle | check | freeze | kill | normal"""
    t = Tempo(tempo)
    return Adjustment(kind=AdjustmentKind.TEMPO, value=t.value,
                      name=t.value.replace("_", "-").title(), tags=["tempo"],
                      stamp_name=False)


def ALERT(text: str) -> Adjustment:
    """A pre-snap check that changes nothing on paper ('Alert Fade vs press')."""
    return Adjustment(kind=AdjustmentKind.ALERT, value=text, name=text,
                      tags=["alert"], stamp_name=False)


def PLAY_ACTION(fake_to: str = "RB", name: str = "Play Action") -> Adjustment:
    """Add a run fake to the named back and force max protection."""
    return Adjustment(kind=AdjustmentKind.PLAY_ACTION, label=fake_to,
                      name=name, tags=["play-action", "pa"])


def PERSONNEL(grouping: str) -> Adjustment:
    """Relabel the personnel grouping ('12', '21', '10')."""
    return Adjustment(kind=AdjustmentKind.PERSONNEL, value=grouping,
                      name=f"{grouping} Pers", tags=["personnel"])


# ── Composition helpers ───────────────────────────────────────────────────────

def apply_all(play: Play, *adjustments: Adjustment) -> Play:
    """Apply adjustments in order (same as Play.adjust)."""
    return play.adjust(*adjustments)


def variants(play: Play, *adjustments: Adjustment,
             include_base: bool = False) -> list[Play]:
    """
    One new Play per adjustment — the way a coach sheet lists a base call
    with its alts underneath.
    """
    out = [play] if include_base else []
    out.extend(play.adjust(a) for a in adjustments)
    return out


def matrix(play: Play, *groups: list[Adjustment]) -> list[Play]:
    """
    Cartesian product of adjustment groups — every combination.

        matrix(mesh, [A.FLIP()], [A.MOTION('Z','jet'), A.MOTION('H','orbit')])
    """
    from itertools import product
    plays: list[Play] = []
    for combo in product(*groups):
        plays.append(play.adjust(*combo))
    return plays


__all__ = [
    "Adjustment", "AdjustmentKind",
    "TAG", "MOTION", "SHIFT", "FLIP", "FORMATION", "PROTECTION",
    "MAX_PROTECT", "RELEASE", "TEMPO", "ALERT", "PLAY_ACTION", "PERSONNEL",
    "apply_all", "variants", "matrix",
]
