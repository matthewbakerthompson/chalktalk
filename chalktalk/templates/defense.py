"""
Defensive formation templates — 22 formations covering all major NFL/college packages.

Coordinate system (same as offense):
  x=0   = center of field
  +x    = offense's RIGHT (defense's left when facing the offense)
  y > 0 = defensive side of LOS (linebackers, safeties further from LOS = higher y)

Alignments are set against a generic spread offense (Shotgun Trips Right).
"""
from __future__ import annotations
from ..models.defense import DefensePlayer, DefensePosition as DP, DefensiveFormation


def _d(label: str, pos: DP, x: float, y: float) -> DefensePlayer:
    return DefensePlayer(label=label, position=pos, x=x, y=y)


# ── Shared DB alignment helpers ───────────────────────────────────────────────

def _corners_wide() -> list[DefensePlayer]:
    """CBs aligned wide vs X and Z receivers."""
    return [
        _d("CB", DP.CB, -22.0, 1.0),
        _d("CB", DP.CB,  20.0, 1.0),
    ]

def _corners_press() -> list[DefensePlayer]:
    return [
        _d("CB", DP.CB, -22.0, 0.5),
        _d("CB", DP.CB,  20.0, 0.5),
    ]


# ════════════════════════════════════════════════════════════════════════════
# 4-3 FRONTS
# ════════════════════════════════════════════════════════════════════════════

def FOUR_THREE_OVER() -> DefensiveFormation:
    """4-3 Over — 3-tech to strength (TE side right). Cover 2 shell."""
    return DefensiveFormation(
        name="4-3 Over",
        front="4-3",
        personnel="4-3-4",
        coverage="Cover 2",
        players=[
            # DL — over shift (toward TE side)
            _d("DE",  DP.DE,  -5.5, 1.2),   # 5-tech weak
            _d("1T",  DP.DT,  -1.5, 1.0),   # 1-tech weak shade
            _d("3T",  DP.DT,   3.0, 1.0),   # 3-tech strong
            _d("DE",  DP.DE,   6.0, 1.2),   # 5-tech strong (outside TE)
            # LBs
            _d("W",   DP.WILL, -5.0, 4.5),
            _d("M",   DP.MIKE,  0.5, 4.5),
            _d("S",   DP.SAM,   6.5, 3.5),  # walked up on TE
            # DBs — Cover 2 shell
            *_corners_wide(),
            _d("SS",  DP.SS,    9.0, 5.5),
            _d("FS",  DP.FS,   -1.0, 10.0),
        ],
        description="Over shift: 3-tech to strong side, Sam walked up on TE. Cover 2 two-deep look.",
    )


def FOUR_THREE_UNDER() -> DefensiveFormation:
    """4-3 Under — 3-tech to weak side. Cover 3 shell."""
    return DefensiveFormation(
        name="4-3 Under",
        front="4-3",
        personnel="4-3-4",
        coverage="Cover 3",
        players=[
            _d("DE",  DP.DE,  -6.0, 1.2),   # wide 9-tech weak
            _d("3T",  DP.DT,  -2.5, 1.0),   # 3-tech WEAK side
            _d("1T",  DP.DT,   1.5, 1.0),   # 1-tech strong shade
            _d("DE",  DP.DE,   5.5, 1.2),   # 5-tech strong
            _d("W",   DP.WILL, -3.5, 4.0),
            _d("M",   DP.MIKE,  2.0, 4.5),
            _d("S",   DP.SAM,   7.0, 3.5),
            *_corners_wide(),
            _d("SS",  DP.SS,    9.0, 6.0),
            _d("FS",  DP.FS,    0.0, 10.5),
        ],
        description="Under shift: 3-tech to weak, Will shades backside. Cover 3 single-high look.",
    )


def FOUR_THREE_EVEN() -> DefensiveFormation:
    """4-3 Even — two 2-tech DTs, two-gap philosophy. Cover 2."""
    return DefensiveFormation(
        name="4-3 Even",
        front="4-3",
        personnel="4-3-4",
        coverage="Cover 2",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),   # 2-tech
            _d("DT",  DP.DT,   2.0, 1.0),   # 2-tech
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("W",   DP.WILL, -4.5, 4.5),
            _d("M",   DP.MIKE,  0.0, 4.5),
            _d("S",   DP.SAM,   5.5, 4.5),
            *_corners_wide(),
            _d("SS",  DP.SS,    8.0, 6.0),
            _d("FS",  DP.FS,    0.0, 10.5),
        ],
        description="Even front: symmetric 2-gapping DTs. Base two-deep coverage.",
    )


def FOUR_THREE_BEAR() -> DefensiveFormation:
    """Bear front — 0-tech NT, 3-techs outside, 9-tech DEs. Max run stuffing."""
    return DefensiveFormation(
        name="Bear Front",
        front="4-3 Bear",
        personnel="4-3-4",
        coverage="Cover 0 / Cover 1",
        players=[
            _d("DE",  DP.DE,  -6.0, 1.2),   # 9-tech
            _d("3T",  DP.DT,  -3.0, 1.0),
            _d("NT",  DP.NT,   0.0, 1.0),   # 0-tech over center
            _d("3T",  DP.DT,   3.0, 1.0),
            _d("DE",  DP.DE,   6.0, 1.2),
            _d("W",   DP.WILL, -2.0, 4.0),
            _d("M",   DP.MIKE,  0.0, 5.0),
            _d("S",   DP.SAM,   2.0, 4.0),  # 3 LBs stacked behind DL
            *_corners_press(),
            _d("FS",  DP.FS,    0.0, 9.0),  # single high
        ],
        description="Bear / Buddy Ryan front — 5-man DL look, 3 stacked LBs, blitz-heavy.",
    )


def FORTY_SIX() -> DefensiveFormation:
    """46 Defense — 8 in the box, 6-man pressure look."""
    return DefensiveFormation(
        name="46 Defense",
        front="4-6 Bear",
        personnel="4-3-4",
        coverage="Cover 0",
        players=[
            _d("DE",  DP.DE,  -6.0, 1.2),
            _d("DT",  DP.DT,  -2.5, 1.0),
            _d("NT",  DP.NT,   0.5, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("W",   DP.WILL, -5.0, 2.5),  # walked up
            _d("M",   DP.MIKE, -1.5, 3.5),
            _d("S",   DP.SAM,   7.5, 2.0),  # edge rusher
            _d("SS",  DP.SS,    3.5, 2.5),  # walked up strong
            *_corners_press(),
            _d("FS",  DP.FS,    0.0, 9.0),
        ],
        description="Buddy Ryan's 46: 8 near the LOS, one-on-one coverage outside.",
    )


# ════════════════════════════════════════════════════════════════════════════
# 3-4 FRONTS
# ════════════════════════════════════════════════════════════════════════════

def THREE_FOUR_BASE() -> DefensiveFormation:
    """3-4 Base — NT over center, 5-tech DEs, 4 LBs. Cover 2."""
    return DefensiveFormation(
        name="3-4 Base",
        front="3-4",
        personnel="3-4-4",
        coverage="Cover 2",
        players=[
            _d("DE",  DP.DE,  -4.5, 1.2),   # 5-tech
            _d("NT",  DP.NT,   0.0, 1.0),   # 0-tech
            _d("DE",  DP.DE,   5.0, 1.2),   # 5-tech
            _d("OLB", DP.OLB, -6.5, 2.0),   # standup weak OLB
            _d("ILB", DP.ILB, -1.5, 4.5),
            _d("ILB", DP.ILB,  2.0, 4.5),
            _d("OLB", DP.OLB,  7.0, 2.0),   # standup strong OLB
            *_corners_wide(),
            _d("SS",  DP.SS,   10.0, 5.5),
            _d("FS",  DP.FS,   -1.0, 10.5),
        ],
        description="Classic 3-4 base. Both OLBs can rush or drop. Two-deep shell.",
    )


def THREE_FOUR_ODD() -> DefensiveFormation:
    """3-4 Odd Stack — tighter DL, stacked ILBs. Gap attack scheme."""
    return DefensiveFormation(
        name="3-4 Odd Stack",
        front="3-4 Odd",
        personnel="3-4-4",
        coverage="Cover 3",
        players=[
            _d("DE",  DP.DE,  -3.5, 1.2),
            _d("NT",  DP.NT,   0.0, 1.0),
            _d("DE",  DP.DE,   3.5, 1.2),
            _d("OLB", DP.OLB, -5.5, 2.5),
            _d("ILB", DP.ILB, -1.5, 4.5),
            _d("ILB", DP.ILB,  2.0, 4.5),
            _d("OLB", DP.OLB,  6.0, 2.5),
            *_corners_wide(),
            _d("SS",  DP.SS,    8.0, 6.0),
            _d("FS",  DP.FS,    0.0, 11.0),
        ],
        description="Odd-shaded 3-4. Tighter DL alignment, ILBs stack behind. Single-high look.",
    )


def THREE_FOUR_EVEN() -> DefensiveFormation:
    """3-4 Even — wide 5-tech DEs, aggressive gap control."""
    return DefensiveFormation(
        name="3-4 Even",
        front="3-4 Even",
        personnel="3-4-4",
        coverage="Cover 2",
        players=[
            _d("DE",  DP.DE,  -5.0, 1.2),
            _d("NT",  DP.NT,   0.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("OLB", DP.OLB, -7.0, 1.5),
            _d("ILB", DP.ILB, -2.0, 4.5),
            _d("ILB", DP.ILB,  2.5, 4.5),
            _d("OLB", DP.OLB,  7.5, 1.5),
            *_corners_wide(),
            _d("SS",  DP.SS,    9.0, 5.5),
            _d("FS",  DP.FS,    0.0, 10.5),
        ],
        description="3-4 Even: balanced look with aggressive edge OLBs.",
    )


def THREE_FOUR_BEAR() -> DefensiveFormation:
    """3-4 Bear (Double-Eagle) — 5-3 look with OLBs acting as DEs."""
    return DefensiveFormation(
        name="3-4 Bear / Double Eagle",
        front="3-4 Bear",
        personnel="3-4-4",
        coverage="Cover 1",
        players=[
            _d("OLB", DP.OLB, -7.0, 1.0),  # standup DE role
            _d("DE",  DP.DE,  -3.0, 1.0),
            _d("NT",  DP.NT,   0.0, 1.0),
            _d("DE",  DP.DE,   3.0, 1.0),
            _d("OLB", DP.OLB,  7.5, 1.0),
            _d("ILB", DP.ILB, -2.0, 4.5),
            _d("ILB", DP.ILB,  2.5, 4.5),
            *_corners_press(),
            _d("SS",  DP.SS,   -6.0, 3.5),  # walked up
            _d("FS",  DP.FS,    1.0, 9.5),
        ],
        description="Five across the LOS. Hybrid 3-4/5-2 with gap accountability.",
    )


# ════════════════════════════════════════════════════════════════════════════
# 5-2 / OKLAHOMA
# ════════════════════════════════════════════════════════════════════════════

def FIVE_TWO_OKLAHOMA() -> DefensiveFormation:
    """Oklahoma 5-2 — 5 DL, 2 LBs, classic run-stopping base."""
    return DefensiveFormation(
        name="5-2 Oklahoma",
        front="5-2",
        personnel="5-2-4",
        coverage="Cover 2",
        players=[
            _d("DE",  DP.DE,  -6.0, 1.2),
            _d("DT",  DP.DT,  -3.0, 1.0),
            _d("NT",  DP.NT,   0.0, 1.0),
            _d("DT",  DP.DT,   3.0, 1.0),
            _d("DE",  DP.DE,   6.0, 1.2),
            _d("LB",  DP.LB,  -2.5, 4.5),
            _d("LB",  DP.LB,   3.0, 4.5),
            *_corners_wide(),
            _d("SS",  DP.SS,    8.0, 5.5),
            _d("FS",  DP.FS,    0.0, 10.5),
        ],
        description="Classic Oklahoma 5-2. Run-first defense with two deep safeties.",
    )


# ════════════════════════════════════════════════════════════════════════════
# NICKEL (5-DB) PACKAGES
# ════════════════════════════════════════════════════════════════════════════

def NICKEL_425() -> DefensiveFormation:
    """Nickel 4-2-5 — standard nickel. 4 DL, 2 LBs, 5 DBs."""
    return DefensiveFormation(
        name="Nickel 4-2-5",
        front="Nickel",
        personnel="4-2-5",
        coverage="Cover 2 / Cover 3",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("W",   DP.WILL, -3.5, 4.0),
            _d("M",   DP.MIKE,  1.5, 4.0),
            # 5 DBs
            _d("CB",  DP.CB,  -22.0, 1.0),
            _d("N",   DP.NCB, -11.5, 1.5),  # nickel on slot
            _d("SS",  DP.SS,    8.5, 5.5),
            _d("FS",  DP.FS,   -1.0, 10.0),
            _d("CB",  DP.CB,   20.0, 1.0),
        ],
        description="Base nickel: 4-2-5. NCB covers slot. Flexible two or single high.",
    )


def NICKEL_335() -> DefensiveFormation:
    """Nickel 3-3-5 (Odd Nickel) — 3 DL, 3 LBs, 5 DBs. Multiple disguise."""
    return DefensiveFormation(
        name="Nickel 3-3-5",
        front="Nickel Odd",
        personnel="3-3-5",
        coverage="Cover 3 / Cover 1",
        players=[
            _d("DE",  DP.DE,  -4.5, 1.2),
            _d("NT",  DP.NT,   0.0, 1.0),
            _d("DE",  DP.DE,   4.5, 1.2),
            _d("OLB", DP.OLB, -6.0, 2.0),
            _d("M",   DP.MIKE,  0.0, 4.0),
            _d("OLB", DP.OLB,  6.5, 2.0),
            _d("CB",  DP.CB,  -22.0, 1.0),
            _d("N",   DP.NCB, -11.0, 1.5),
            _d("SS",  DP.SS,    8.0, 5.0),
            _d("FS",  DP.FS,    0.0, 10.0),
            _d("CB",  DP.CB,   20.0, 1.0),
        ],
        description="Odd nickel: 3 down, 3 LBs (2 standup), 5 DBs. Great blitz disguise.",
    )


def NICKEL_425_OVER() -> DefensiveFormation:
    """Nickel Over — 4-2-5 with over-shifted DL. Vs strong-side run."""
    return DefensiveFormation(
        name="Nickel Over",
        front="Nickel Over",
        personnel="4-2-5",
        coverage="Cover 2 / Cover 4",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("1T",  DP.DT,  -1.5, 1.0),
            _d("3T",  DP.DT,   2.5, 1.0),
            _d("DE",  DP.DE,   6.0, 1.2),
            _d("W",   DP.WILL, -4.0, 4.0),
            _d("M",   DP.MIKE,  1.5, 4.5),
            _d("CB",  DP.CB,  -22.0, 1.0),
            _d("N",   DP.NCB, -11.5, 1.5),
            _d("SS",  DP.SS,    9.0, 5.0),
            _d("FS",  DP.FS,   -1.0, 10.0),
            _d("CB",  DP.CB,   20.0, 1.0),
        ],
        description="Nickel over shift. Heavy run support with over-front DL.",
    )


def NICKEL_BEAR() -> DefensiveFormation:
    """Nickel Bear — 6 in the box, nickel back walked up. Heavy pressure."""
    return DefensiveFormation(
        name="Nickel Bear",
        front="Nickel Bear",
        personnel="4-2-5",
        coverage="Cover 0 / Cover 1",
        players=[
            _d("DE",  DP.DE,  -6.0, 1.2),
            _d("DT",  DP.DT,  -2.5, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("W",   DP.WILL, -2.0, 3.0),  # walked up
            _d("M",   DP.MIKE,  1.0, 3.5),
            _d("CB",  DP.CB,  -22.0, 0.5),
            _d("N",   DP.NCB,  -4.5, 2.0),  # walked up in box
            _d("SS",  DP.SS,    7.5, 2.5),  # edge player
            _d("FS",  DP.FS,    0.0, 9.0),
            _d("CB",  DP.CB,   20.0, 0.5),
        ],
        description="Nickel bear: 6-man box with NCB walked up. Designed to overwhelm OL.",
    )


# ════════════════════════════════════════════════════════════════════════════
# DIME (6-DB) PACKAGES
# ════════════════════════════════════════════════════════════════════════════

def DIME_416() -> DefensiveFormation:
    """Dime 4-1-6 — 4 DL, 1 LB, 6 DBs. Pass rush with coverage depth."""
    return DefensiveFormation(
        name="Dime 4-1-6",
        front="Dime",
        personnel="4-1-6",
        coverage="Cover 2 / Cover 4",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("M",   DP.MIKE,  0.0, 4.0),  # lone LB
            _d("CB",  DP.CB,  -22.0, 1.0),
            _d("N",   DP.NCB, -12.0, 1.5),
            _d("D",   DP.DCB,  -5.5, 3.0),  # dime in slot area
            _d("SS",  DP.SS,    8.0, 5.0),
            _d("FS",  DP.FS,    0.0, 10.0),
            _d("CB",  DP.CB,   20.0, 1.0),
        ],
        description="Standard dime: 6 DBs, 1 LB. Used in clear passing situations.",
    )


def DIME_326() -> DefensiveFormation:
    """Dime 3-2-6 — 3 DL, 2 LBs, 6 DBs. Balanced pass rush + coverage."""
    return DefensiveFormation(
        name="Dime 3-2-6",
        front="Dime 3-down",
        personnel="3-2-6",
        coverage="Cover 2 / Cover 4",
        players=[
            _d("DE",  DP.DE,  -4.5, 1.2),
            _d("NT",  DP.NT,   0.0, 1.0),
            _d("DE",  DP.DE,   4.5, 1.2),
            _d("OLB", DP.OLB, -6.5, 1.5),  # rush OLB
            _d("M",   DP.MIKE,  0.5, 4.0),
            _d("CB",  DP.CB,  -22.0, 1.0),
            _d("N",   DP.NCB, -11.5, 1.5),
            _d("D",   DP.DCB,  -5.0, 2.5),
            _d("SS",  DP.SS,    8.0, 5.0),
            _d("FS",  DP.FS,    0.0, 10.0),
            _d("CB",  DP.CB,   20.0, 1.0),
        ],
        description="Three-down dime: trades a DT for a sixth DB. Good vs spread empty.",
    )


# ════════════════════════════════════════════════════════════════════════════
# QUARTER / PREVENT
# ════════════════════════════════════════════════════════════════════════════

def QUARTER_407() -> DefensiveFormation:
    """Quarter 4-0-7 — 4 DL, no LBs, 7 DBs. Two-minute defense."""
    return DefensiveFormation(
        name="Quarter 4-0-7",
        front="Quarter",
        personnel="4-0-7",
        coverage="Cover 2 / Cover 4",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            # 7 DBs
            _d("CB",  DP.CB,  -22.0, 1.0),
            _d("N",   DP.NCB, -12.0, 1.5),
            _d("D",   DP.DCB,  -5.5, 3.0),
            _d("SS",  DP.SS,    6.5, 4.5),
            _d("Q",   DP.QCB,   0.0, 6.5),  # seventh DB
            _d("FS",  DP.FS,   -2.0, 10.5),
            _d("CB",  DP.CB,   20.0, 1.0),
        ],
        description="Quarter package: 7 DBs for deep coverage. Eliminates big play.",
    )


def PREVENT_47() -> DefensiveFormation:
    """Prevent Defense — 4 DL, 7 DBs, safeties playing 15+ yards deep."""
    return DefensiveFormation(
        name="Prevent Defense",
        front="Prevent",
        personnel="4-0-7",
        coverage="Cover 2 Deep / Hail Mary D",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("CB",  DP.CB,  -22.0, 2.0),
            _d("N",   DP.NCB, -12.0, 4.0),
            _d("D",   DP.DCB,  -5.0, 5.0),
            _d("SS",  DP.SS,    8.0, 8.0),
            _d("Q",   DP.QCB,   0.0, 10.0),
            _d("FS",  DP.FS,   -1.0, 14.0),
            _d("CB",  DP.CB,   20.0, 2.0),
        ],
        description="Prevent: safeties playing 14-16 yards deep. Surrenders short, denies big.",
    )


# ════════════════════════════════════════════════════════════════════════════
# GOAL LINE
# ════════════════════════════════════════════════════════════════════════════

def GOAL_LINE_55() -> DefensiveFormation:
    """Goal Line 5-5-1 — 5 DL, 5 LBs, 1 safety. Maximum run stop."""
    return DefensiveFormation(
        name="Goal Line 5-5-1",
        front="Goal Line",
        personnel="5-5-1",
        coverage="Man / Cover 0",
        players=[
            _d("DE",  DP.DE,  -6.5, 1.0),
            _d("DT",  DP.DT,  -3.5, 1.0),
            _d("NT",  DP.NT,   0.0, 1.0),
            _d("DT",  DP.DT,   3.5, 1.0),
            _d("DE",  DP.DE,   6.5, 1.0),
            # 5 LBs stacked behind
            _d("LB",  DP.LB,  -8.0, 1.5),  # outside
            _d("LB",  DP.LB,  -4.0, 3.0),
            _d("M",   DP.MIKE,  0.0, 3.5),
            _d("LB",  DP.LB,   4.5, 3.0),
            _d("LB",  DP.LB,   8.5, 1.5),
            # 1 Safety
            _d("FS",  DP.FS,    0.0, 7.0),
        ],
        description="Max run stop. 10 defenders near LOS. Used inside 5-yard line.",
    )


def GOAL_LINE_64() -> DefensiveFormation:
    """Goal Line 6-4-1 — 6 DL, 4 LBs, 1 safety."""
    return DefensiveFormation(
        name="Goal Line 6-4-1",
        front="Goal Line Heavy",
        personnel="6-4-1",
        coverage="Man / Cover 0",
        players=[
            _d("DE",  DP.DE,  -7.0, 1.0),
            _d("DT",  DP.DT,  -4.5, 1.0),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("NT",  DP.NT,   0.5, 1.0),
            _d("DT",  DP.DT,   3.0, 1.0),
            _d("DE",  DP.DE,   6.5, 1.0),
            _d("LB",  DP.LB,  -5.5, 2.5),
            _d("M",   DP.MIKE, -1.0, 3.5),
            _d("LB",  DP.LB,   2.5, 3.5),
            _d("LB",  DP.LB,   7.5, 2.5),
            _d("FS",  DP.FS,    0.0, 6.5),
        ],
        description="6-4-1 goal line: 10 defenders within 4 yards of LOS.",
    )


# ════════════════════════════════════════════════════════════════════════════
# PRESSURE / BLITZ PACKAGES
# ════════════════════════════════════════════════════════════════════════════

def ZERO_BLITZ() -> DefensiveFormation:
    """Cover 0 All-Out Blitz — 6+ rushers, zero coverage behind."""
    return DefensiveFormation(
        name="Cover 0 Blitz",
        front="Zero Blitz",
        personnel="4-2-5",
        coverage="Cover 0",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("W",   DP.WILL, -5.0, 2.5),  # blitzing
            _d("M",   DP.MIKE,  0.0, 3.0),  # blitzing
            *_corners_press(),
            _d("SS",  DP.SS,    8.0, 2.0),  # blitzing
            _d("N",   DP.NCB, -11.0, 1.0),  # man on slot
            _d("FS",  DP.FS,    0.0, 8.0),
        ],
        description="Cover 0: every DB has man coverage, 6 rushers. Fastest QB gets the ball out.",
    )


def FIRE_ZONE() -> DefensiveFormation:
    """Fire Zone — 5-man pressure, 3-deep zone coverage."""
    return DefensiveFormation(
        name="Fire Zone",
        front="Fire Zone",
        personnel="4-2-5",
        coverage="3-Deep Zone",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("W",   DP.WILL, -4.5, 2.5),  # fifth rusher
            _d("M",   DP.MIKE,  2.0, 4.5),  # drops to hook/curl
            *_corners_wide(),
            _d("N",   DP.NCB,  -5.0, 4.0),  # drops to flat
            _d("SS",  DP.SS,    3.0, 6.0),  # drops to deep third
            _d("FS",  DP.FS,    0.0, 11.0),
        ],
        description="Fire zone: 5 rush, 3 deep zones + 2 underneath. Best of both worlds.",
    )


def COVER_2_TAMPA() -> DefensiveFormation:
    """Tampa 2 — MLB drops to deep middle, CBs funnel, 2 safeties split."""
    return DefensiveFormation(
        name="Tampa 2",
        front="4-3",
        personnel="4-3-4",
        coverage="Tampa 2",
        players=[
            _d("DE",  DP.DE,  -5.5, 1.2),
            _d("DT",  DP.DT,  -2.0, 1.0),
            _d("DT",  DP.DT,   2.0, 1.0),
            _d("DE",  DP.DE,   5.5, 1.2),
            _d("W",   DP.WILL, -5.0, 4.0),
            _d("M",   DP.MIKE,  0.0, 5.5),  # MLB drops deep middle seam
            _d("S",   DP.SAM,   6.0, 4.0),
            # CBs press-funnel (jam + re-route inside)
            _d("CB",  DP.CB,  -22.0, 0.5),
            _d("CB",  DP.CB,   20.0, 0.5),
            _d("SS",  DP.SS,   11.0, 5.5),  # split wide
            _d("FS",  DP.FS,  -10.0, 5.5),
        ],
        description="Tampa 2: CBs jam receivers, MLB covers deep middle, safeties split halves.",
    )
