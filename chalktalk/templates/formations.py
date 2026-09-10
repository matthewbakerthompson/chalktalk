"""
Pre-built formation templates.

All player coordinates use the field system:
  x=0  = center of field (center's alignment)
  +x   = offense's right
  y=0  = line of scrimmage
  -y   = backfield
"""
from __future__ import annotations
from ..models.player import Player, Position
from ..models.formation import Formation


def _p(label: str, pos: Position, x: float, y: float) -> Player:
    return Player(label=label, position=pos, x=x, y=y)


# ── Offensive line (shared across formations) ────────────────────────────────

def _ol_standard() -> list[Player]:
    return [
        _p("LT", Position.LT, -4.5, 0),
        _p("LG", Position.LG, -2.0, 0),
        _p("C",  Position.C,   0.0, 0),
        _p("RG", Position.RG,  2.0, 0),
        _p("RT", Position.RT,  4.5, 0),
    ]


# ── 11 personnel ─────────────────────────────────────────────────────────────

def SHOTGUN_TRIPS_RIGHT() -> Formation:
    """Shotgun, 11 personnel. X split left. H+Z+Y trips right. RB offset right."""
    return Formation(
        name="Shotgun Trips Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),    # tight end (on LOS, right)
            _p("X",  Position.X, -22.0,  0),    # split end (on LOS, left)
            _p("Z",  Position.Z,  20.0, -1),    # flanker (off LOS, outside right)
            _p("H",  Position.H,  12.0, -1),    # slot (off LOS, inside right)
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  5.0, -5),
        ],
    )


def SHOTGUN_EMPTY_TRIPS_RIGHT() -> Formation:
    """Shotgun empty, 10 personnel. Trips right, pair left."""
    return Formation(
        name="Shotgun Empty Trips Right",
        personnel="10",
        players=[
            *_ol_standard(),
            _p("X",  Position.X, -22.0,  0),
            _p("Y",  Position.Y,  -11.0, -1),   # inner-left slot
            _p("Z",  Position.Z,  20.0, -1),
            _p("H",  Position.H,  12.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  6.0,  0),    # RB as wing/slot on LOS right
        ],
    )


def SHOTGUN_ACE() -> Formation:
    """Shotgun, 12 personnel. Two TEs, two WRs."""
    return Formation(
        name="Shotgun Ace",
        personnel="12",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("TE", Position.TE, -6.0,  0),    # second TE left of LT
            _p("X",  Position.X, -22.0,  0),
            _p("Z",  Position.Z,  20.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  1.5, -7),
        ],
    )


# ── 21 personnel ─────────────────────────────────────────────────────────────

def I_FORM_PRO_RIGHT() -> Formation:
    """I-Formation, 21 personnel. Pro right (TE right, split end left, flanker right)."""
    return Formation(
        name="I-Form Pro Right",
        personnel="21",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("Z",  Position.Z,  18.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("FB", Position.FB,  0.0, -7),
            _p("RB", Position.RB,  0.0, -10),
        ],
    )


def I_FORM_STRONG_RIGHT() -> Formation:
    """I-Formation strong right — FB aligned right, TE right."""
    return Formation(
        name="I-Form Strong Right",
        personnel="21",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("Z",  Position.Z,  18.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("FB", Position.FB,  5.0, -6),    # offset right
            _p("RB", Position.RB,  0.0, -9),
        ],
    )


# ── 12 personnel, under center ────────────────────────────────────────────────

def GUN_DOUBLES() -> Formation:
    """Shotgun, 11 personnel. Two WRs each side (doubles)."""
    return Formation(
        name="Shotgun Doubles",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("H",  Position.H, -12.0, -1),    # slot left
            _p("Z",  Position.Z,  20.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB, -3.0, -7),
        ],
    )


# ── Goal-line / heavy ────────────────────────────────────────────────────────

def GOAL_LINE() -> Formation:
    """Goal-line, 22 personnel. Two FBs, two TEs."""
    return Formation(
        name="Goal Line",
        personnel="22",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("TE", Position.TE, -6.0,  0),
            _p("X",  Position.X, -18.0,  0),
            _p("QB", Position.QB,  0.0, -5),
            _p("FB", Position.FB,  0.0, -7),
            _p("RB", Position.RB,  0.0, -10),
        ],
    )


# ── Mirror formations (trips left, etc.) ─────────────────────────────────────

def SHOTGUN_TRIPS_LEFT() -> Formation:
    """Shotgun, 11 personnel. X split right. H+Z+Y trips left. RB offset left."""
    return Formation(
        name="Shotgun Trips Left",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,  -6.0,  0),   # TE on LOS, left
            _p("X",  Position.X,  22.0,  0),   # split end on LOS, right
            _p("Z",  Position.Z, -20.0, -1),   # flanker off LOS, outside left
            _p("H",  Position.H, -12.0, -1),   # slot off LOS, inside left
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB, -5.0, -5),
        ],
    )


def GUN_DOUBLES_LEFT() -> Formation:
    """Shotgun doubles — two WRs left, one WR + TE right."""
    return Formation(
        name="Shotgun Doubles Left",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("H",  Position.H, -12.0, -1),   # slot left
            _p("Z",  Position.Z,  20.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  3.0, -7),
        ],
    )


# ── Bunch formations ──────────────────────────────────────────────────────────

def SHOTGUN_BUNCH_RIGHT() -> Formation:
    """Shotgun, 11 personnel. Lone X left. Tight three-man bunch right (Y/H/Z)."""
    return Formation(
        name="Shotgun Bunch Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("X",  Position.X, -22.0,  0),   # lone split end left
            _p("Y",  Position.Y,   8.0,  0),   # inner bunch (on LOS)
            _p("H",  Position.H,  11.5, -1),   # middle bunch (off LOS)
            _p("Z",  Position.Z,  14.5, -1),   # outer bunch (off LOS)
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB, -3.0, -7),
        ],
    )


def SHOTGUN_BUNCH_LEFT() -> Formation:
    """Shotgun, 11 personnel. Lone Z right. Tight three-man bunch left (Y/H/X)."""
    return Formation(
        name="Shotgun Bunch Left",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Z",  Position.Z,  22.0, -1),   # lone flanker right
            _p("Y",  Position.Y,  -8.0,  0),   # inner bunch (on LOS, left)
            _p("H",  Position.H, -11.5, -1),   # middle bunch
            _p("X",  Position.X, -14.5, -1),   # outer bunch
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  3.0, -7),
        ],
    )


# ── Pistol ────────────────────────────────────────────────────────────────────

def PISTOL_TRIPS_RIGHT() -> Formation:
    """Pistol, 11 personnel. QB under center-ish, RB directly behind. Trips right."""
    return Formation(
        name="Pistol Trips Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("Z",  Position.Z,  20.0, -1),
            _p("H",  Position.H,  12.0, -1),
            _p("QB", Position.QB,  0.0, -3.5),  # pistol depth
            _p("RB", Position.RB,  0.0, -7.0),  # directly behind QB
        ],
    )


# ── Red zone (compressed splits) ─────────────────────────────────────────────

def RED_ZONE_TRIPS_RIGHT() -> Formation:
    """Red zone 11-personnel. Receivers use compressed splits (no full field)."""
    return Formation(
        name="Red Zone Trips Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -18.0,  0),   # compressed from -22
            _p("Z",  Position.Z,  17.0, -1),
            _p("H",  Position.H,  11.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  5.0, -5),
        ],
    )


def RED_ZONE_BUNCH_RIGHT() -> Formation:
    """Red zone bunch — three-man bunch right, TE+WR left. Classic end zone package."""
    return Formation(
        name="Red Zone Bunch Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,  -6.0,  0),   # TE left (extra blocker / release)
            _p("X",  Position.X, -18.0,  0),
            _p("Z",  Position.Z,  14.0, -1),   # compressed bunch
            _p("H",  Position.H,  10.5, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  3.5, -5),
        ],
    )


def GOAL_LINE_HEAVY() -> Formation:
    """Heavy goal line — 23 personnel. Double-tight, FB lead, RB."""
    return Formation(
        name="Goal Line Heavy",
        personnel="23",
        players=[
            *_ol_standard(),
            _p("Y",   Position.Y,    6.0,  0),
            _p("TE",  Position.TE,  -6.0,  0),
            _p("TE2", Position.TE,   8.0, -1),  # wing TE right
            _p("QB",  Position.QB,   0.0, -5),
            _p("FB",  Position.FB,   0.0, -7),
            _p("RB",  Position.RB,   0.0, -10),
        ],
    )


# ════════════════════════════════════════════════════════════════════════════
# UNDER CENTER — PRO-STYLE
# ════════════════════════════════════════════════════════════════════════════

def PRO_SET() -> Formation:
    """Pro Set (Split Backs) under center — 21 personnel, balanced."""
    return Formation(
        name="Pro Set",
        personnel="21",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("Z",  Position.Z,  18.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("HB", Position.RB,  4.0, -7),   # split back right
            _p("FB", Position.FB, -4.0, -7),   # split back left
        ],
    )


def SINGLE_BACK_ACE() -> Formation:
    """Single Back Ace under center — 12 personnel, balanced TEs."""
    return Formation(
        name="Single Back Ace",
        personnel="12",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("TE", Position.TE, -6.0,  0),
            _p("X",  Position.X, -20.0,  0),
            _p("Z",  Position.Z,  18.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  0.0, -8),
        ],
    )


def SINGLE_BACK_PRO_RIGHT() -> Formation:
    """Single Back Pro Right under center — 11 personnel, one back."""
    return Formation(
        name="Single Back Pro Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("H",  Position.H, -12.0, -1),
            _p("Z",  Position.Z,  19.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  2.5, -8),
        ],
    )


def WISHBONE() -> Formation:
    """Wishbone — 23 personnel. Power run, option-oriented."""
    return Formation(
        name="Wishbone",
        personnel="23",
        players=[
            *_ol_standard(),
            _p("X",  Position.X, -18.0,  0),
            _p("Z",  Position.Z,  18.0,  0),
            _p("QB", Position.QB,  0.0, -5),
            _p("FB", Position.FB,  0.0, -7),
            _p("LH", Position.RB, -5.0, -9),   # left halfback
            _p("RH", Position.RB,  5.0, -9),   # right halfback
        ],
    )


# ════════════════════════════════════════════════════════════════════════════
# SHOTGUN — SPREAD VARIANTS
# ════════════════════════════════════════════════════════════════════════════

def GUN_SPREAD_4WR() -> Formation:
    """Shotgun Spread — 10 personnel, 4 WRs, no TE, no RB as blocker."""
    return Formation(
        name="Shotgun Spread 4-Wide",
        personnel="10",
        players=[
            *_ol_standard(),
            _p("X",  Position.X, -22.0,  0),
            _p("H",  Position.H, -11.0, -1),
            _p("Z",  Position.Z,  20.0, -1),
            _p("Y",  Position.Y,  11.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  4.5, -5),
        ],
    )


def GUN_QUADS_RIGHT() -> Formation:
    """Shotgun Quads — 4 receivers to the right, lone X left. 10 personnel."""
    return Formation(
        name="Shotgun Quads Right",
        personnel="10",
        players=[
            *_ol_standard(),
            _p("X",  Position.X, -20.0,  0),    # lone left
            _p("Y",  Position.Y,   7.0,  0),    # inner right (on LOS)
            _p("H",  Position.H,  11.5, -1),
            _p("Z",  Position.Z,  16.5, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB, -5.0, -5),    # offset left
        ],
    )


def GUN_QUADS_LEFT() -> Formation:
    """Shotgun Quads Left — 4 receivers to the left."""
    return Formation(
        name="Shotgun Quads Left",
        personnel="10",
        players=[
            *_ol_standard(),
            _p("Z",  Position.Z,  20.0, -1),    # lone right
            _p("Y",  Position.Y,  -7.0,  0),
            _p("H",  Position.H, -11.5, -1),
            _p("X",  Position.X, -16.5, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  5.0, -5),
        ],
    )


def GUN_TRIPS_TE_RIGHT() -> Formation:
    """Shotgun 12 personnel — TE Y inline right, H slot, Z outside. Run/pass balance."""
    return Formation(
        name="Shotgun Trips TE Right",
        personnel="12",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),    # TE inline
            _p("H",  Position.H,  12.0, -1),    # slot
            _p("Z",  Position.Z,  19.0, -1),    # flanker
            _p("X",  Position.X, -22.0,  0),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB, -3.0, -7),
        ],
    )


def GUN_UNBALANCED_RIGHT() -> Formation:
    """Shotgun Unbalanced — extra OL/TE to right, overloads one side."""
    return Formation(
        name="Shotgun Unbalanced Right",
        personnel="12",
        players=[
            # Unbalanced line — extra blocker right of RT
            _p("LT", Position.LT, -4.5,  0),
            _p("LG", Position.LG, -2.0,  0),
            _p("C",  Position.C,   0.0,  0),
            _p("RG", Position.RG,  2.0,  0),
            _p("RT", Position.RT,  4.5,  0),
            _p("TE", Position.TE,  6.5,  0),    # extra blocker on LOS
            _p("Y",  Position.Y,   9.0,  0),    # second TE/H
            _p("X",  Position.X, -20.0,  0),
            _p("Z",  Position.Z,  20.0, -1),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB,  3.0, -7),
        ],
    )


def GUN_OFFSET_BACK_RIGHT() -> Formation:
    """Shotgun Offset — QB shotgun, RB aligned offset right (I-gun hybrid)."""
    return Formation(
        name="Shotgun Offset Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("Z",  Position.Z,  19.0, -1),
            _p("H",  Position.H,  12.0, -1),
            _p("QB", Position.QB, -1.5, -5),
            _p("RB", Position.RB,  4.0, -6),
        ],
    )


def GUN_TREY_RIGHT() -> Formation:
    """Shotgun Trey Right — TE + 2 WRs to right, X left, RB left. 11 personnel."""
    return Formation(
        name="Shotgun Trey Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),    # inline TE
            _p("H",  Position.H,  12.5, -1),    # inner WR
            _p("Z",  Position.Z,  18.5, -1),    # outer WR
            _p("X",  Position.X, -22.0,  0),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB, -4.5, -5),
        ],
    )


# ════════════════════════════════════════════════════════════════════════════
# PISTOL VARIANTS
# ════════════════════════════════════════════════════════════════════════════

def PISTOL_DOUBLES() -> Formation:
    """Pistol Doubles — balanced WR set, QB pistol, RB behind. 11 personnel."""
    return Formation(
        name="Pistol Doubles",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("H",  Position.H, -12.0, -1),
            _p("Z",  Position.Z,  19.0, -1),
            _p("QB", Position.QB,  0.0, -3.5),
            _p("RB", Position.RB,  0.0, -7.0),
        ],
    )


def PISTOL_ACE() -> Formation:
    """Pistol Ace — 12 personnel, two TEs, pistol depth."""
    return Formation(
        name="Pistol Ace",
        personnel="12",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("TE", Position.TE, -6.0,  0),
            _p("X",  Position.X, -20.0,  0),
            _p("Z",  Position.Z,  18.0, -1),
            _p("QB", Position.QB,  0.0, -3.5),
            _p("RB", Position.RB,  0.0, -7.0),
        ],
    )


# ════════════════════════════════════════════════════════════════════════════
# SPECIALTY / TRICK
# ════════════════════════════════════════════════════════════════════════════

def WILDCAT() -> Formation:
    """Wildcat — RB takes direct snap, QB as decoy WR."""
    return Formation(
        name="Wildcat",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,   6.0,  0),
            _p("X",  Position.X, -22.0,  0),
            _p("Z",  Position.Z,  19.0, -1),
            _p("H",  Position.H,  12.0, -1),
            _p("QB", Position.QB, -18.0, -1),  # QB out wide as WR
            _p("RB", Position.RB,   0.0, -5),  # RB takes direct snap
        ],
    )


def DIAMOND_BACKFIELD() -> Formation:
    """Diamond — QB + FB + 2 HBs in diamond shape. Power run from gun."""
    return Formation(
        name="Diamond Backfield",
        personnel="22",
        players=[
            *_ol_standard(),
            _p("X",  Position.X, -18.0,  0),
            _p("Y",  Position.Y,  18.0,  0),
            _p("QB", Position.QB,  0.0, -4),
            _p("FB", Position.FB,  0.0, -6),    # lead back
            _p("LH", Position.RB, -4.0, -8),
            _p("RH", Position.RB,  4.0, -8),
        ],
    )


def JUMBO_TIGHT() -> Formation:
    """Jumbo — 13 personnel, 3 TEs with the third as an H-back lead blocker."""
    return Formation(
        name="Jumbo Tight",
        personnel="13",
        players=[
            *_ol_standard(),
            _p("Y",   Position.Y,    6.0,  0),
            _p("TE",  Position.TE,   8.5,  0),   # wing TE
            _p("TE2", Position.TE,  -2.5, -3.5),   # H-back / lead blocker
            _p("X",   Position.X,  -17.0,  0),
            _p("QB",  Position.QB,   0.0, -5),
            _p("RB",  Position.RB,   0.0, -8),
        ],
    )


def BUNCH_STACK_RIGHT() -> Formation:
    """Stack Right — 3 receivers stacked vertically, run/RPO threat."""
    return Formation(
        name="Stack Right",
        personnel="11",
        players=[
            *_ol_standard(),
            _p("Y",  Position.Y,  13.0,  0),    # lead stack (on LOS)
            _p("H",  Position.H,  13.5, -2),    # middle stack
            _p("Z",  Position.Z,  14.0, -4),    # back stack
            _p("X",  Position.X, -22.0,  0),
            _p("QB", Position.QB,  0.0, -5),
            _p("RB", Position.RB, -3.5, -7),
        ],
    )
