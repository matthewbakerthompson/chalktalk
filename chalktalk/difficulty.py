"""
chalktalk.difficulty — how hard a play is to execute.

Some teams can run anything; many high school teams cannot run a play with
jet motion, a three-read progression and two pullers on Friday night. Every
play gets a difficulty worked out from what it asks of the players: a small,
additive score where each group of points has a named reason, and three tiers.

    Basic     0-3   simple assignments any team can carry
    Standard  4-7   what a typical varsity offense runs
    Advanced  8+    timing, reads and moving parts that take real reps

No published scale exists for this. The weights follow what coaches name,
again and again, as the cost of a play: motion timing, reading a defender,
the length of the progression, pullers, screen timing, checks at the line.

A coach can override the tier for any play (`Play.difficulty`), which also
marks it as repped; a plan says what its team can execute
(`GamePlan.execution`), and the drive planner takes a point off for every
point a play scores above that. The browser designer computes the same score
with the same table, and a test holds the two together.
"""
from __future__ import annotations

from pydantic import BaseModel

from .models.play import Play, PlayType

TIER_NAMES = {1: "Basic", 2: "Standard", 3: "Advanced"}
TIERS = (3, 7)              # score <= 3: Basic, <= 7: Standard, above: Advanced
# The highest score a team at each execution level runs comfortably:
# youth or JV, varsity high school, college and up.
TEAM_LEVELS = {1: 3, 2: 7, 3: 12}

# Points per feature. One table, mirrored in the designer.
RUBRIC = {
    "motion": {"short": 1, "in": 1, "out": 1, "across": 1, "return": 1, "shift": 1,
               "jet": 2, "orbit": 2},
    "motion_other": 1,       # a motion the table doesn't name
    "motion_ball": 1,        # the jet or orbit man takes the ball or the mesh
    "motion_many": 1,        # two or more players move before the snap
    "motion_cap": 5,
    "motion_named": 2,       # jet or orbit named only in the tags
    "motion_named_run": 1,   # ... and the play is a run or RPO
    "tag": 1, "tag_cap": 2,  # each tag that changes one assignment
    "qb": {"play_action": 1, "boot": 1, "sprint": 1, "mesh": 2, "screen": 2, "option": 3},
    "read": 1, "read_cap": 2,  # each read past the second
    "seven_step": 1,
    "rpo": 1,                # run blocking with a live throw
    "puller": 1,             # each player who pulls, wraps, traps or kicks
    "pullers_line": 1,       # two or more linemen pull
    "zone": 1,               # reach, scoop or combo steps
    "climb": 1,              # a combo that climbs to a linebacker
    "cut": 1, "cut_cap": 2,
    "alert": 1, "alert_cap": 2,
    "tempo": {"no_huddle": 1, "freeze": 1, "kill": 1, "check": 2},
    "trick": 2,
}

_PULLS = {"pull", "wrap", "trap", "kick"}
_ZONE = {"reach", "scoop", "combo"}
_LINE = {"LT", "LG", "C", "RG", "RT"}
_QB_WORDS = {"play_action": "play-action fake", "boot": "throw on the move",
             "sprint": "throw on the move", "mesh": "mesh read", "screen": "screen timing",
             "option": "option read"}
_TEMPO_WORDS = {"no_huddle": "no-huddle", "freeze": "freeze count", "kill": "kill call",
                "check": "check at the line"}


class Difficulty(BaseModel):
    score: int
    tier: int
    reasons: list[str] = []
    coached: bool = False    # the coach set the tier: the team has repped it

    @property
    def name(self) -> str:
        return TIER_NAMES[self.tier]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def score(play: Play) -> tuple[int, list[str]]:
    R = RUBRIC
    total, reasons = 0, []

    def add(points: int, why: str) -> None:
        nonlocal total
        if points:
            total += points
            reasons.append(f"{why} ({points})")

    plan = play.qb

    # Movement: every player who moves, and whether the snap has to meet him.
    movers = [a for a in play.assignments if a.motion_type]
    points = 0
    for a in movers:
        points += R["motion"].get(a.motion_type, R["motion_other"])
        if a.motion_type in ("jet", "orbit") and (
                a.is_ball_carrier or (plan is not None and plan.mesh_with == a.player.label)):
            points += R["motion_ball"]
    if len(movers) >= 2:
        points += R["motion_many"]
    if movers:
        add(min(points, R["motion_cap"]),
            ", ".join(f"{a.player.label} {a.motion_type}" for a in movers) + " motion")
    else:
        named = next((k for k in ("jet", "orbit") if k in play.tags), None)
        if named:
            run = play.play_type in (PlayType.RUN, PlayType.RPO)
            add(R["motion_named"] + (R["motion_named_run"] if run else 0), f"{named} motion")

    tags = play.tags.count("tag")
    add(min(tags * R["tag"], R["tag_cap"]), _plural(tags, "tag"))

    # The quarterback: what he does, how many reads, how deep.
    if plan is not None:
        action = plan.action.value
        add(R["qb"].get(action, 0), _QB_WORDS.get(action, action))
        reads = len(plan.reads)
        add(min(max(0, reads - 2) * R["read"], R["read_cap"]), f"{reads}-read progression")
        if (plan.steps or 0) >= 7:
            add(R["seven_step"], "7-step drop")
        if play.play_type is PlayType.RPO and plan.reads:
            add(R["rpo"], "run blocking with a live throw")

    # Blocking.
    blocks = [a for a in play.assignments if a.block is not None]
    pulls = [a for a in blocks if a.block.kind.value in _PULLS]
    linemen = sum(1 for a in pulls if a.player.position.value in _LINE)
    add(len(pulls) * R["puller"] + (R["pullers_line"] if linemen >= 2 else 0),
        _plural(len(pulls), "puller"))
    if any(a.block.kind.value in _ZONE for a in blocks):
        climbs = any(a.block.kind.value == "combo" and a.block.climbs for a in blocks)
        add(R["zone"] + (R["climb"] if climbs else 0),
            "zone combos to the second level" if climbs else "zone steps")
    cuts = sum(1 for a in blocks if a.block.kind.value == "cut")
    add(min(cuts * R["cut"], R["cut_cap"]), _plural(cuts, "cut block"))

    # The play as a whole.
    add(min(len(play.alerts) * R["alert"], R["alert_cap"]), _plural(len(play.alerts), "alert"))
    tempo = play.tempo.value
    add(R["tempo"].get(tempo, 0), _TEMPO_WORDS.get(tempo, tempo))
    if play.play_type is PlayType.SPECIAL:
        add(R["trick"], "trick play")
    return total, reasons


def tier_of(points: int) -> int:
    return 1 if points <= TIERS[0] else 2 if points <= TIERS[1] else 3


def difficulty(play: Play) -> Difficulty:
    points, reasons = score(play)
    if play.difficulty in (1, 2, 3):
        return Difficulty(score=points, tier=play.difficulty, coached=True,
                          reasons=["set by the coach"] + reasons)
    return Difficulty(score=points, tier=tier_of(points), reasons=reasons)


def over_level(d: Difficulty, execution: int) -> int:
    """
    How far a play sits above what the team runs comfortably: the points
    above its level. A tier the coach set stands for reps: no penalty at or
    below the team's tier, and at least one point above it.
    """
    over = d.score - TEAM_LEVELS[execution]
    if d.coached:
        return 0 if d.tier <= execution else max(1, over)
    return max(0, over)


__all__ = ["Difficulty", "RUBRIC", "TIERS", "TIER_NAMES", "TEAM_LEVELS", "difficulty",
           "over_level", "score", "tier_of"]
