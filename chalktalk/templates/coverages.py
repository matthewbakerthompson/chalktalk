"""
Coverages and pressures — whole-defense calls.

Each takes a `DefensiveFormation` and returns a new one with every defender
assigned. Zone coverages only need the defense; man coverages also take the
offensive formation so they can match defenders to receivers.

    from chalktalk.templates import coverages as C, defense as D

    look = C.cover_3(D.NICKEL_425())
    print(look.describe())

    play.with_coverage(C.cover_1)          # matches man on the play's receivers

`strength` is +1 when the offense's strength is to the defense's right (the
offense's right), -1 to the left.
"""
from __future__ import annotations
from typing import Callable, Optional

from ..models.core import Point
from ..models.defense import (
    DefensePlayer, DefensePosition, DefensiveAssignment, DefensiveFormation,
    DefensiveRole, Zone,
)
from ..models.formation import Formation
from ..models.player import OL_POSITIONS, Position


# ── Assignment helpers ────────────────────────────────────────────────────────

def _pts(*pairs: tuple[float, float]) -> list[Point]:
    return [Point(x=x, y=y) for x, y in pairs]


def rush(player: DefensePlayer, gap: Optional[str] = None) -> DefensiveAssignment:
    """Straight-ahead rush that converges on the quarterback."""
    lean = -0.18 * player.x
    return DefensiveAssignment(
        role=DefensiveRole.RUSH, gap=gap,
        path=_pts((0, 0), (lean * 0.4, -1.6), (lean, -3.6)),
    )


def contain(player: DefensePlayer) -> DefensiveAssignment:
    """Set the edge — rush upfield and turn everything back inside."""
    side = 1.0 if player.x >= 0 else -1.0
    return DefensiveAssignment(
        role=DefensiveRole.CONTAIN, gap="D",
        path=_pts((0, 0), (side * 1.4, -1.2), (side * 1.9, -3.6)),
    )


def blitz(player: DefensePlayer, gap: str = "A") -> DefensiveAssignment:
    """Pressure from off the line, angled at the gap."""
    lean = -0.3 * player.x
    return DefensiveAssignment(
        role=DefensiveRole.BLITZ, gap=gap,
        path=_pts((0, 0), (lean * 0.35, -player.y * 0.5),
                  (lean, -player.y - 3.0)),
    )


def stunt(player: DefensePlayer, direction: int = 1,
          gap: Optional[str] = None) -> DefensiveAssignment:
    """Loop behind a teammate as part of a line game."""
    d = 1 if direction >= 0 else -1
    return DefensiveAssignment(
        role=DefensiveRole.STUNT, gap=gap,
        path=_pts((0, 0), (d * 0.6, 0.6), (d * 2.4, -0.6), (d * 3.2, -3.0)),
    )


def zone(z: Zone, side: float = 1.0) -> DefensiveAssignment:
    return DefensiveAssignment(role=DefensiveRole.ZONE, zone=z, side=side)


def man(covers: Optional[str] = None) -> DefensiveAssignment:
    return DefensiveAssignment(role=DefensiveRole.MAN, covers=covers)


def spy() -> DefensiveAssignment:
    return DefensiveAssignment(role=DefensiveRole.SPY,
                               path=_pts((0, 0), (0, -2.0)))


def robot(side: float = 1.0) -> DefensiveAssignment:
    """Rat in the hole — read the quarterback, sit under the crossers."""
    return DefensiveAssignment(role=DefensiveRole.ROBOT, zone=Zone.HOLE, side=side)


# ── Sorting the defense into roles ────────────────────────────────────────────

_SLOT_POSITIONS = {DefensePosition.NCB, DefensePosition.DCB, DefensePosition.QCB}


def _side(player: DefensePlayer) -> float:
    return 1.0 if player.x >= 0 else -1.0


def _free_safety(defense: DefensiveFormation) -> Optional[DefensePlayer]:
    """The deep middle player: the free safety, else whoever is deepest."""
    safeties = defense.safeties
    if not safeties:
        return None
    fs = [p for p in safeties if p.position is DefensePosition.FS]
    return fs[0] if fs else max(safeties, key=lambda p: p.y)


def _rush_front(defense: DefensiveFormation) -> dict[str, DefensiveAssignment]:
    """Everyone with a hand in the dirt goes; the ends contain."""
    out: dict[str, DefensiveAssignment] = {}
    ends = [p for p in defense.dl if p.position is DefensePosition.DE]
    for p in defense.dl:
        out[p.label] = contain(p) if p in ends else rush(p)
    return out


def eligible_receivers(offense: Optional[Formation]) -> list:
    """Everyone who can catch the ball, outside in."""
    if offense is None:
        return []
    skill = [p for p in offense.players
             if p.position not in OL_POSITIONS and p.position is not Position.QB]
    return sorted(skill, key=lambda p: -abs(p.x))


def match_man(defenders: list[DefensePlayer],
              offense: Optional[Formation]) -> dict[str, Optional[str]]:
    """
    Pair man defenders with receivers, outside in — the corners take the
    widest players, the inside defenders take what is left.
    """
    receivers = eligible_receivers(offense)
    if not receivers:
        return {d.label: None for d in defenders}

    out: dict[str, Optional[str]] = {}
    taken: set[str] = set()

    # Cover your own side first, outside in: the widest defender on a side
    # takes the widest receiver on that side. That is how a corner ends up on
    # the split end and the nickel on the slot rather than on the back.
    for side in (1, -1):
        d_side = sorted([d for d in defenders if (1 if d.x >= 0 else -1) == side],
                        key=lambda p: -abs(p.x))
        r_side = sorted([r for r in receivers if (1 if r.x >= 0 else -1) == side],
                        key=lambda p: -abs(p.x))
        for defender, receiver in zip(d_side, r_side):
            out[defender.label] = receiver.label
            taken.add(receiver.label)

    # Whoever is left takes the nearest receiver nobody has.
    for defender in sorted(defenders, key=lambda p: abs(p.x)):
        if out.get(defender.label):
            continue
        options = [r for r in receivers if r.label not in taken]
        if not options:
            out[defender.label] = None
            continue
        best = min(options, key=lambda r: abs(r.x - defender.x))
        taken.add(best.label)
        out[defender.label] = best.label
    return out


# ── Zone coverages ────────────────────────────────────────────────────────────
#
# Landmarks are handed out by rank, not by which side of the ball a defender
# happens to stand on. The underneath droppers are sorted left to right and
# spread across the slots the coverage owns; the two deep safeties take the
# left and right halves. Sorting by sign put the Mike and the Sam in the same
# hook, and both safeties in the same half, whenever one of them lined up on
# the ball — two defenders drawn on top of each other and a hole where the
# other one belonged.

def _by_x(players: list[DefensePlayer]) -> list[DefensePlayer]:
    return sorted(players, key=lambda p: p.x)


def _outer_two(players: list[DefensePlayer]
               ) -> tuple[list[DefensePlayer], list[DefensePlayer]]:
    """The two widest players, left then right, and whoever is left over."""
    if len(players) <= 2:
        return _by_x(players), []
    wide = sorted(players, key=lambda p: -abs(p.x))[:2]
    return _by_x(wide), [p for p in players if p not in wide]


def _deepest_two(players: list[DefensePlayer]
                 ) -> tuple[list[DefensePlayer], list[DefensePlayer]]:
    """The two deepest players, left then right, and whoever is left over."""
    if len(players) <= 2:
        return _by_x(players), []
    deep = sorted(players, key=lambda p: -p.y)[:2]
    return _by_x(deep), [p for p in players if p not in deep]


def _pair_sides(pair: list[DefensePlayer]) -> list[float]:
    """Left and right for a pair; a lone player keeps his own side."""
    if len(pair) == 2:
        return [-1.0, 1.0]
    return [_side(p) for p in pair]


def _spread(count: int) -> list[float]:
    """Evenly spaced sides for the inside droppers, -0.6 to 0.6."""
    if count <= 0:
        return []
    if count == 1:
        return [0.0]
    return [round(-0.6 + 1.2 * i / (count - 1), 2) for i in range(count)]


def _hooks(sides: list[float]) -> list[tuple[Zone, float]]:
    return [(Zone.HOOK if abs(s) < 1e-9 else Zone.HOOK_CURL, s) for s in sides]


def _under_slots(n: int) -> list[tuple[Zone, float]]:
    """
    Underneath landmarks for `n` droppers behind three deep, left to right:
    curl/flat on each edge, hook/curl inside, and a hook in the middle when
    the count is odd.
    """
    if n <= 0:
        return []
    if n == 1:
        return [(Zone.HOOK, 0.0)]
    if n == 2:
        return [(Zone.HOOK_CURL, -0.6), (Zone.HOOK_CURL, 0.6)]
    return [(Zone.CURL_FLAT, -1.0), *_hooks(_spread(n - 2)), (Zone.CURL_FLAT, 1.0)]


def _two_deep_slots(n: int) -> list[tuple[Zone, float]]:
    """
    Underneath landmarks behind two deep, where the corners already own the
    flats: hook/curl either side of a middle hook, seams for any extras.
    """
    if n < 3:
        return _under_slots(n)
    if n == 3:
        return [(Zone.HOOK_CURL, -0.6), (Zone.HOOK, 0.0), (Zone.HOOK_CURL, 0.6)]
    return [(Zone.SEAM, -1.0), *_hooks(_spread(n - 2)), (Zone.SEAM, 1.0)]


def _assign_slots(calls: dict[str, DefensiveAssignment],
                  players: list[DefensePlayer],
                  slots: list[tuple[Zone, float]]) -> None:
    for p, (z, side) in zip(_by_x(players), slots):
        calls[p.label] = zone(z, side)


def _droppers(defense: DefensiveFormation, taken: set[str]) -> list[DefensePlayer]:
    """Everyone off the line who has not already been given a deep job."""
    return [p for p in defense.players if not p.is_dl and p.label not in taken]


def cover_3(defense: DefensiveFormation, offense: Optional[Formation] = None,
            strength: int = 1) -> DefensiveFormation:
    """Three deep, four under. The widest dropper on each side takes the curl/flat."""
    calls = _rush_front(defense)
    corners, _ = _outer_two(defense.corners)
    for cb, side in zip(corners, _pair_sides(corners)):
        calls[cb.label] = zone(Zone.DEEP_THIRD, side)
    taken = {p.label for p in corners}
    fs = _free_safety(defense)
    if fs:
        calls[fs.label] = zone(Zone.MIDDLE_THIRD, 0.0)
        taken.add(fs.label)
    under = _droppers(defense, taken)
    _assign_slots(calls, under, _under_slots(len(under)))
    return defense.with_assignments(calls, coverage="Cover 3")


def cover_2(defense: DefensiveFormation, offense: Optional[Formation] = None,
            strength: int = 1) -> DefensiveFormation:
    """Two deep halves, five under. Corners jam and sink to the flat."""
    calls = _rush_front(defense)
    corners, _ = _outer_two(defense.corners)
    for cb, side in zip(corners, _pair_sides(corners)):
        calls[cb.label] = zone(Zone.FLAT, side)
    deep, _ = _deepest_two(defense.safeties)
    for s, side in zip(deep, _pair_sides(deep)):
        calls[s.label] = zone(Zone.DEEP_HALF, side)
    taken = {p.label for p in corners} | {p.label for p in deep}
    under = _droppers(defense, taken)
    _assign_slots(calls, under, _two_deep_slots(len(under)))
    return defense.with_assignments(calls, coverage="Cover 2")


def tampa_2(defense: DefensiveFormation, offense: Optional[Formation] = None,
            strength: int = 1) -> DefensiveFormation:
    """Cover 2 with the Mike running the deep middle."""
    out = cover_2(defense, offense, strength)
    mike = next((p for p in out.linebackers
                 if p.position is DefensePosition.MIKE), None)
    if mike is None and out.linebackers:
        mike = min(out.linebackers, key=lambda p: abs(p.x))
    if mike:
        out = out.assign(mike.label, zone(Zone.DEEP_MIDDLE, 0.0))
    return out.model_copy(update={"coverage": "Tampa 2"})


def cover_4(defense: DefensiveFormation, offense: Optional[Formation] = None,
            strength: int = 1) -> DefensiveFormation:
    """Quarters — four deep, three under, safeties read the number two."""
    calls = _rush_front(defense)
    corners, _ = _outer_two(defense.corners)
    for cb, side in zip(corners, _pair_sides(corners)):
        calls[cb.label] = zone(Zone.DEEP_QUARTER, side)
    deep, _ = _deepest_two(defense.safeties)
    for s, side in zip(deep, _pair_sides(deep)):
        calls[s.label] = zone(Zone.DEEP_QUARTER, side * 0.38)
    taken = {p.label for p in corners} | {p.label for p in deep}
    under = _droppers(defense, taken)
    _assign_slots(calls, under, _under_slots(len(under)))
    return defense.with_assignments(calls, coverage="Cover 4")


def cover_6(defense: DefensiveFormation, offense: Optional[Formation] = None,
            strength: int = 1) -> DefensiveFormation:
    """Quarter-quarter-half: quarters to the field, cover 2 to the boundary."""
    d = 1.0 if strength >= 0 else -1.0
    calls = _rush_front(defense)
    corners, _ = _outer_two(defense.corners)
    for cb, side in zip(corners, _pair_sides(corners)):
        calls[cb.label] = (zone(Zone.DEEP_QUARTER, side) if side == d
                           else zone(Zone.FLAT, side))
    deep, _ = _deepest_two(defense.safeties)
    for s, side in zip(deep, _pair_sides(deep)):
        calls[s.label] = (zone(Zone.DEEP_QUARTER, side * 0.38) if side == d
                          else zone(Zone.DEEP_HALF, side))
    taken = {p.label for p in corners} | {p.label for p in deep}
    under = _droppers(defense, taken)
    _assign_slots(calls, under, _under_slots(len(under)))
    return defense.with_assignments(calls, coverage="Cover 6")


# ── Man coverages ─────────────────────────────────────────────────────────────

def _man_defenders(defense: DefensiveFormation,
                   exclude: set[str]) -> list[DefensePlayer]:
    return [p for p in defense.players
            if not p.is_dl and p.label not in exclude]


def cover_1(defense: DefensiveFormation, offense: Optional[Formation] = None,
            strength: int = 1) -> DefensiveFormation:
    """Man free — everybody matched, one safety over the top, a rat underneath."""
    calls = _rush_front(defense)
    fs = _free_safety(defense)
    exclude = {fs.label} if fs else set()
    if fs:
        calls[fs.label] = zone(Zone.DEEP_MIDDLE, 0.0)

    covering = _man_defenders(defense, exclude)
    receivers = eligible_receivers(offense)
    # With more coverage players than receivers, the odd man is the rat.
    rat = None
    if len(covering) > len(receivers) > 0:
        inside = [p for p in covering if p.is_lb]
        rat = min(inside, key=lambda p: abs(p.x)) if inside else None
        if rat:
            covering = [p for p in covering if p.label != rat.label]
            calls[rat.label] = robot(0.0)

    for label, target in match_man(covering, offense).items():
        calls[label] = man(target)
    return defense.with_assignments(calls, coverage="Cover 1")


def cover_2_man(defense: DefensiveFormation, offense: Optional[Formation] = None,
                strength: int = 1) -> DefensiveFormation:
    """Two deep, man underneath."""
    calls = _rush_front(defense)
    deep, _ = _deepest_two(defense.safeties)
    exclude = {s.label for s in deep}
    for s, side in zip(deep, _pair_sides(deep)):
        calls[s.label] = zone(Zone.DEEP_HALF, side)
    for label, target in match_man(_man_defenders(defense, exclude), offense).items():
        calls[label] = man(target)
    return defense.with_assignments(calls, coverage="Cover 2 Man")


def cover_0(defense: DefensiveFormation, offense: Optional[Formation] = None,
            strength: int = 1) -> DefensiveFormation:
    """No help. Everyone covers a man; anyone left over comes."""
    calls = _rush_front(defense)
    covering = _man_defenders(defense, set())
    receivers = eligible_receivers(offense)
    matchups = match_man(covering, offense)

    extra = [p for p in covering if matchups.get(p.label) is None]
    for p in covering:
        target = matchups.get(p.label)
        calls[p.label] = man(target) if target else blitz(p, "A")
    if receivers and not extra:
        # everyone is accounted for; send the nearest linebacker anyway
        inside = [p for p in covering if p.is_lb]
        if inside:
            p = min(inside, key=lambda q: abs(q.x))
            calls[p.label] = blitz(p, "A")
    return defense.with_assignments(calls, coverage="Cover 0",
                                    pressure="All-out")


# ── Pressures ─────────────────────────────────────────────────────────────────

def fire_zone(defense: DefensiveFormation, offense: Optional[Formation] = None,
              strength: int = 1) -> DefensiveFormation:
    """
    Five rush, three under, three deep — and one lineman drops out of it,
    which is the whole trick.
    """
    d = 1.0 if strength >= 0 else -1.0
    calls = _rush_front(defense)

    # A defensive end to the call side drops to the curl/flat.
    ends = [p for p in defense.dl if p.position is DefensePosition.DE]
    dropper = max(ends, key=lambda p: p.x * d) if ends else None
    if dropper:
        calls[dropper.label] = zone(Zone.CURL_FLAT, d)

    # Three deep behind it.
    corners, _ = _outer_two(defense.corners)
    for cb, side in zip(corners, _pair_sides(corners)):
        calls[cb.label] = zone(Zone.DEEP_THIRD, side)
    taken = {p.label for p in corners}
    fs = _free_safety(defense)
    if fs:
        calls[fs.label] = zone(Zone.MIDDLE_THIRD, 0.0)
        taken.add(fs.label)

    # Five come: the linemen still rushing plus enough second-level players
    # from the call side to make five. Everyone else fills in underneath,
    # around the curl/flat the end already owns.
    others = sorted(_droppers(defense, taken), key=lambda p: p.x * d, reverse=True)
    rushing = len(defense.dl) - (1 if dropper else 0)
    count = max(1, min(len(others) - 2, 5 - rushing))
    blitzers, rest = others[:count], others[count:]
    for i, p in enumerate(blitzers):
        calls[p.label] = blitz(p, "B" if i == 0 else "A")
    slots = _under_slots(len(rest) + (1 if dropper else 0))
    if dropper:
        slots = [s for s in slots if s != (Zone.CURL_FLAT, d)]
    _assign_slots(calls, rest, slots)
    return defense.with_assignments(
        calls, coverage="3 Under 3 Deep",
        pressure=f"Fire Zone {'Rt' if d > 0 else 'Lt'}")


def zero_blitz(defense: DefensiveFormation, offense: Optional[Formation] = None,
               strength: int = 1) -> DefensiveFormation:
    """Cover 0 with everyone who is not covering somebody coming."""
    out = cover_0(defense, offense, strength)
    return out.model_copy(update={"pressure": "Zero"})


def line_game(defense: DefensiveFormation, offense: Optional[Formation] = None,
              strength: int = 1) -> DefensiveFormation:
    """
    A tackle-end game to one side. This is a *front*, not a coverage: it only
    touches the defensive line, so layer it on top of a call —

        C.line_game(C.cover_3(look))
    """
    d = 1 if strength >= 0 else -1
    calls = _rush_front(defense)
    tackles = [p for p in defense.dl if p.position is not DefensePosition.DE]
    ends = [p for p in defense.dl if p.position is DefensePosition.DE]
    if tackles and ends:
        penetrator = max(tackles, key=lambda p: p.x * d)
        looper = max(ends, key=lambda p: p.x * d)
        calls[penetrator.label] = rush(penetrator, gap="B")
        calls[looper.label] = stunt(looper, -d, gap="A")
    return defense.with_assignments(calls, pressure="T-E Game")


#: Complete calls — every defender gets a job.
COVERAGES: dict[str, Callable] = {
    "cover_0": cover_0,
    "cover_1": cover_1,
    "cover_2": cover_2,
    "cover_2_man": cover_2_man,
    "cover_3": cover_3,
    "cover_4": cover_4,
    "cover_6": cover_6,
    "tampa_2": tampa_2,
    "fire_zone": fire_zone,
    "zero_blitz": zero_blitz,
}

#: Front calls that only touch the line — layer them over a coverage.
FRONTS: dict[str, Callable] = {
    "line_game": line_game,
}

#: The calls that bring extra pressure.
PRESSURES = {"cover_0", "zero_blitz", "fire_zone"}


__all__ = [
    "rush", "contain", "blitz", "stunt", "zone", "man", "spy", "robot",
    "cover_0", "cover_1", "cover_2", "cover_2_man", "cover_3", "cover_4",
    "cover_6", "tampa_2", "fire_zone", "zero_blitz", "line_game",
    "match_man", "eligible_receivers", "COVERAGES", "FRONTS", "PRESSURES",
]
