"""
Whole-line blocking schemes.

Each scheme returns `{player_label: Block}` for the five linemen — plus the
kicker or lead blocker when the scheme needs one — with every path already
pointing the right way for the direction the play is going.

    from chalktalk.templates import schemes as S

    S.inside_zone(+1)                  # zone right
    S.power(+1, kicker="FB")           # power right, fullback kicks the edge
    S.half_slide(-1)                   # half slide to the left, man backside

`direction` is +1 for a play going to the offense's right, -1 for left.
"""
from __future__ import annotations
from typing import Optional

from ..models.block import Block
from . import blocking as B

#: The offensive line, from the outside in.
LINE = ("LT", "LG", "C", "RG", "RT")


def _sides(direction: int) -> dict[str, str]:
    """Map playside/backside roles onto actual player labels."""
    if direction >= 0:
        return {"pst": "RT", "psg": "RG", "c": "C", "bsg": "LG", "bst": "LT"}
    return {"pst": "LT", "psg": "LG", "c": "C", "bsg": "RG", "bst": "RT"}


def _d(direction: int) -> int:
    return 1 if direction >= 0 else -1


# ── Zone ──────────────────────────────────────────────────────────────────────

def inside_zone(direction: int = 1) -> dict[str, Block]:
    """
    Playside combo up to the Mike, center and backside guard on the nose to the
    Will, backside tackle cuts off pursuit.
    """
    d, s = _d(direction), _sides(direction)
    return {
        s["pst"]: B.COMBO(s["psg"], d, climb=False),
        s["psg"]: B.COMBO(s["pst"], d, target="M"),
        s["c"]:   B.COMBO(s["bsg"], d, climb=False, target="NT"),
        s["bsg"]: B.COMBO(s["c"], d, target="W"),
        s["bst"]: B.SCOOP(d),
    }


def outside_zone(direction: int = 1) -> dict[str, Block]:
    """Everybody reaches playside; the backside tackle runs to cut off."""
    d, s = _d(direction), _sides(direction)
    return {
        s["pst"]: B.REACH(d, target="EMLOS"),
        s["psg"]: B.REACH(d),
        s["c"]:   B.REACH(d),
        s["bsg"]: B.REACH(d),
        s["bst"]: B.SCOOP(d),
    }


def split_zone(direction: int = 1, kicker: str = "Y") -> dict[str, Block]:
    """Inside zone with the backside tight end or H-back kicking the end."""
    out = inside_zone(direction)
    out[kicker] = B.KICK(-_d(direction), target="DE")
    return out


# ── Gap ───────────────────────────────────────────────────────────────────────

def power(direction: int = 1, kicker: Optional[str] = "FB") -> dict[str, Block]:
    """Playside blocks down, backside guard pulls and wraps, the edge gets kicked."""
    d, s = _d(direction), _sides(direction)
    out = {
        s["pst"]: B.DOWN(-d),
        s["psg"]: B.DOWN(-d),
        s["c"]:   B.DOWN(-d, target="backside A"),
        s["bsg"]: B.WRAP(d, target="M"),
        s["bst"]: B.HINGE(-d),
    }
    if kicker:
        out[kicker] = B.KICK(d, target="DE")
    return out


def counter(direction: int = 1) -> dict[str, Block]:
    """Same down blocks as power, but the guard kicks and the tackle wraps."""
    d, s = _d(direction), _sides(direction)
    return {
        s["pst"]: B.DOWN(-d),
        s["psg"]: B.DOWN(-d),
        s["c"]:   B.DOWN(-d, target="backside A"),
        s["bsg"]: B.KICK(d, target="DE"),
        s["bst"]: B.WRAP(d, target="M"),
    }


def trap(direction: int = 1) -> dict[str, Block]:
    """Let the 3-tech come, then trap him with the backside guard."""
    d, s = _d(direction), _sides(direction)
    return {
        s["pst"]: B.DOWN(-d),
        s["psg"]: B.CLIMB(d, target="M"),
        s["c"]:   B.DOWN(-d),
        s["bsg"]: B.TRAP(d, target="3T"),
        s["bst"]: B.HINGE(-d),
    }


def iso(direction: int = 1, lead: Optional[str] = "FB") -> dict[str, Block]:
    """Straight-ahead man blocking with a lead blocker on the linebacker."""
    d, s = _d(direction), _sides(direction)
    out = {
        s["pst"]: B.BASE(),
        s["psg"]: B.BASE(),
        s["c"]:   B.BASE(target="NT"),
        s["bsg"]: B.BASE(),
        s["bst"]: B.BASE(),
    }
    if lead:
        out[lead] = B.CLIMB(d, target="M")
    return out


def gap_down(direction: int = 1) -> dict[str, Block]:
    """Everyone blocks down — goal line and short yardage."""
    d, s = _d(direction), _sides(direction)
    return {label: B.DOWN(-d) for label in (s["pst"], s["psg"], s["c"],
                                            s["bsg"], s["bst"])}


# ── Pass protection ───────────────────────────────────────────────────────────

def big_on_big() -> dict[str, Block]:
    """Man protection — everybody has a man, tackles set to the edge."""
    return {
        "LT": B.PASS_SET(-1), "LG": B.PASS_SET(), "C": B.PASS_SET(),
        "RG": B.PASS_SET(), "RT": B.PASS_SET(1),
    }


def slide(direction: int = 1) -> dict[str, Block]:
    """Full slide — every lineman owns the gap to one side."""
    d = _d(direction)
    return {label: B.SLIDE(d) for label in LINE}


def half_slide(direction: int = 1) -> dict[str, Block]:
    """Center and the two playside linemen slide; the backside pair is man."""
    d, s = _d(direction), _sides(direction)
    return {
        s["pst"]: B.SLIDE(d),
        s["psg"]: B.SLIDE(d),
        s["c"]:   B.SLIDE(d),
        s["bsg"]: B.PASS_SET(),
        s["bst"]: B.PASS_SET(-d),
    }


def max_protect(direction: int = 1, extras: tuple[str, ...] = ("RB",)
                ) -> dict[str, Block]:
    """Man protection plus extra bodies staying in."""
    out = big_on_big()
    d = _d(direction)
    for i, label in enumerate(extras):
        out[label] = B.PASS_SET(d if i % 2 == 0 else -d)
    return out


def sprint(direction: int = 1) -> dict[str, Block]:
    """Sprint-out protection — the whole line turns and runs with the launch point."""
    d = _d(direction)
    return {label: B.FAN(d) for label in LINE}


def boot(direction: int = 1) -> dict[str, Block]:
    """Boot protection — the line sells run away from the quarterback's path."""
    d, s = _d(direction), _sides(direction)
    return {
        s["pst"]: B.REACH(-d), s["psg"]: B.REACH(-d), s["c"]: B.REACH(-d),
        s["bsg"]: B.REACH(-d), s["bst"]: B.HINGE(d),
    }


#: Everything above, addressable by name (used by the CLI and the designer).
SCHEMES = {
    "inside_zone": inside_zone,
    "outside_zone": outside_zone,
    "split_zone": split_zone,
    "power": power,
    "counter": counter,
    "trap": trap,
    "iso": iso,
    "gap_down": gap_down,
    "big_on_big": big_on_big,
    "slide": slide,
    "half_slide": half_slide,
    "max_protect": max_protect,
    "sprint": sprint,
    "boot": boot,
}

#: Which schemes are protections rather than run blocking.
PROTECTIONS = {"big_on_big", "slide", "half_slide", "max_protect", "sprint", "boot"}


__all__ = [
    "inside_zone", "outside_zone", "split_zone", "power", "counter", "trap",
    "iso", "gap_down", "big_on_big", "slide", "half_slide", "max_protect",
    "sprint", "boot", "SCHEMES", "PROTECTIONS", "LINE",
]
