"""
The game plan: what a staff carries into a game, and the drive it is living.

A plan never copies plays. It points at plays in the playbook by id, so an
edit to a diagram shows up in every section, script and card at once. By
default the plan builds itself from the book: every play lands in the sections
its situation says it belongs in, plays labelled "Openers" form the script, and
each play's series and role (set in the play sheet) say what it sets up and
what sets it up. A staff that wants its own sections can list them instead.

How calls reach the field is part of the plan too (`CallSystem`): the verbal
call, coded wristband numbers, code words, or sign boards. The secret that
scrambles wristbands and boards is never part of the plan or the book.

Everything here is plain data and JSON, and stays in the coach's own file.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

from .field import Level
from .situation import Hash, Situation

if TYPE_CHECKING:
    from .play import Play, Playbook


class Role(str, Enum):
    """A play's job in its series."""
    BASE        = "base"          # the play the series is built on
    COMPLEMENT  = "complement"    # same picture, different answer
    CONSTRAINT  = "constraint"    # punishes over-reaction to the base
    PLAY_ACTION = "play_action"   # sells the base, throws off it
    SHOT        = "shot"          # explosive off the same look
    TRICK       = "trick"         # once-a-game gadget off the series
    ANSWER      = "answer"        # answer to a specific coverage/pressure

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").title()


# Roles that only make sense once their base has been shown in the game.
HELD_ROLES = {Role.CONSTRAINT, Role.PLAY_ACTION, Role.SHOT, Role.TRICK}


class Mode(str, Enum):
    """Game situations that change what gets called, whatever the down."""
    TWO_MINUTE  = "two_minute"
    FOUR_MINUTE = "four_minute"


class When(BaseModel):
    """
    A situation filter with ranges, so a staff can set its own buckets.
    Unset fields match anything.
    """
    downs: list[int] = []
    distance: Optional[tuple[float, float]] = None     # inclusive yards to go
    yard_line: Optional[tuple[int, int]] = None        # inclusive yards to goal
    hash_mark: Optional[Hash] = None
    mode: Optional[Mode] = None

    def matches(self, down: Optional[int], distance: Optional[float],
                yard_line: Optional[int], hash_mark: Optional[str] = None,
                mode: Optional[str] = None) -> bool:
        if self.mode is not None and mode != self.mode.value:
            return False
        if self.downs and down not in self.downs:
            return False
        if self.distance is not None and (
                distance is None or not self.distance[0] <= distance <= self.distance[1]):
            return False
        if self.yard_line is not None and (
                yard_line is None or not self.yard_line[0] <= yard_line <= self.yard_line[1]):
            return False
        if self.hash_mark is not None and hash_mark != self.hash_mark.value:
            return False
        return True

    @property
    def kind(self) -> str:
        """What this section is keyed on: "mode", "down", "zone" or "base"."""
        if self.mode is not None:
            return "mode"
        if self.downs:
            return "down"
        if self.yard_line is not None:
            return "zone"
        return "base"


class PlanSection(BaseModel):
    title: str
    when: When = When()
    plays: list[str] = []          # play ids; empty in a derived plan (filled from the book)


# The default sections, in call-sheet order. Ranges rather than the fixed
# distance buckets, so 2nd & 15 lands in "2nd & 7+" instead of falling through.
DEFAULT_SECTIONS: list[PlanSection] = [
    PlanSection(title="1st & 10", when=When(downs=[1], distance=(7, 99))),
    PlanSection(title="2nd & 1-3", when=When(downs=[2], distance=(0, 3))),
    PlanSection(title="2nd & 4-6", when=When(downs=[2], distance=(4, 6))),
    PlanSection(title="2nd & 7+", when=When(downs=[2], distance=(7, 99))),
    PlanSection(title="3rd & 1-3", when=When(downs=[3], distance=(0, 3))),
    PlanSection(title="3rd & 4-6", when=When(downs=[3], distance=(4, 6))),
    PlanSection(title="3rd & 7+", when=When(downs=[3], distance=(7, 99))),
    PlanSection(title="4th & short", when=When(downs=[4], distance=(0, 3))),
    PlanSection(title="Backed up", when=When(yard_line=(90, 99))),
    PlanSection(title="Red zone", when=When(yard_line=(11, 20))),
    PlanSection(title="Low red", when=When(yard_line=(4, 10))),
    PlanSection(title="Goal line", when=When(yard_line=(1, 3))),
    PlanSection(title="Two minute", when=When(mode=Mode.TWO_MINUTE)),
    PlanSection(title="Four minute", when=When(mode=Mode.FOUR_MINUTE)),
    PlanSection(title="Base", when=When()),
]

# Situation labels that place a play by name rather than by down and spot.
OPENERS_LABEL = "Openers"
MODE_LABELS = {"Two Minute": Mode.TWO_MINUTE, "Four Minute": Mode.FOUR_MINUTE}
# Field-zone sections take a play that also has a down only when the zone is
# its own plan: red zone, low red, goal line and backed up. A 3rd & 2 at the
# opponent's 35 is a third-down call, not a fringe call.
ZONES_WITH_DOWNS = {"Backed up", "Red zone", "Low red", "Goal line"}


class CallMethod(str, Enum):
    VERBAL    = "verbal"      # the call as spoken, relayed by the quarterback
    WRISTBAND = "wristband"   # a number signalled in, read off the QB's card
    WORDS     = "words"       # line calls: a code word per play and a live colour
    BOARDS    = "boards"      # sideline sign boards: symbols, one cell live


class CallSystem(BaseModel):
    """
    How calls reach the field, and the coach's strategy for each channel.
    Nothing here is secret: the key that scrambles codes, words and boards
    lives elsewhere.
    """
    methods: list[CallMethod] = [CallMethod.VERBAL]
    # What is live changes every period: wristband cards, the live colour,
    # the live cell on the boards. What things mean (words, symbols) holds for
    # the game, so the team can learn it during the week.
    rotate: Literal["game", "half", "quarter"] = "half"
    # How a signal is built. The method is public, so anything the coach
    # leaves to the key ("key") is chosen per game or per period from the
    # secret: two teams on chalktalk can't assume each other's format.
    signals: int = Field(default=1, ge=1, le=3)           # shown each snap; the key picks the live one
    # wristband numbers
    digits: Literal[2, 3] = 2
    code_style: Literal["number", "letter", "key"] = "number"   # 47, B7, or the key picks
    dummy_digit: Literal["none", "first", "middle", "last", "key"] = "none"
    extra_codes: int = Field(default=2, ge=0, le=4)       # more codes for top calls
    top_calls: int = Field(default=6, ge=0, le=20)        # how many plays get them
    dead_codes: int = Field(default=6, ge=0, le=40)       # codes that mean "wait"
    # line calls
    word_list: Literal["mix", "animals", "cities", "things", "own"] = "mix"
    own_words: list[str] = []                             # the team's own list
    live_signal: Literal["colors", "numbers", "own", "order"] = "colors"
    own_live: list[str] = []                              # the team's own live words
    dummy_words: int = Field(default=4, ge=0, le=20)      # words that mean nothing
    burned_words: list[str] = []                          # heard on film: decoys from now on
    # sign boards
    board_cells: Literal[1, 2, 4, "key"] = 4              # symbols on each board
    dummy_boards: int = Field(default=4, ge=0, le=20)
    boards_by: Literal["play", "series"] = "play"          # a symbol per play, or per series


class DriveState(BaseModel):
    """Where the ball is, and what kind of drive this is."""
    down: int = Field(default=1, ge=1, le=4)
    distance: float = Field(default=10, ge=0)
    yard_line: int = Field(default=75, ge=1, le=99)        # yards to the opponent's goal
    hash_mark: Optional[Hash] = None
    mode: Optional[Mode] = None
    drive: int = 1
    snap: int = 0                                          # plays run in this drive
    over: Optional[Literal["touchdown", "turnover", "downs", "safety"]] = None

    def label(self) -> str:
        if self.over:
            return {"touchdown": "Touchdown", "turnover": "Turnover",
                    "downs": "Turnover on downs", "safety": "Safety"}[self.over]
        situation = Situation(down=self.down, distance=self.distance, yard_line=self.yard_line)
        return situation.describe()


class ScriptCall(BaseModel):
    """
    One call in a drive script, and what follows it: the next call if this
    one keeps the drive on schedule, and the next if it doesn't.
    """
    play: Optional[str] = None                # play id; empty until the coach picks
    on: Optional["ScriptCall"] = None         # next call when it stays on schedule
    off: Optional["ScriptCall"] = None        # next call when it doesn't


class DriveScript(BaseModel):
    """
    A drive pattern scripted during the week: the 1st-down call, the 2nd-down
    call on and off schedule, then 3rd down under each. It covers one set of
    downs; a new first down starts it again from the top.
    """
    name: str = "Drive"
    start: "DriveState" = Field(default_factory=lambda: DriveState())
    first: ScriptCall = Field(default_factory=ScriptCall)


class Outcome(str, Enum):
    GAIN = "gain"                 # a run or completion; the gain can be negative
    INCOMPLETE = "incomplete"
    SACK = "sack"
    PENALTY_US = "penalty_us"     # yards back, same down
    PENALTY_THEM = "penalty_them"  # yards forward
    TURNOVER = "turnover"


class Snap(BaseModel):
    """One logged play: what was called, where, and what happened."""
    before: DriveState
    play: str                                 # the play's id
    call: str                                 # the call as made
    outcome: Outcome = Outcome.GAIN
    gain: float = 0
    tells: list[str] = []                     # what the defense showed on this snap


# Success thresholds: the percent of the yards to go a play needs on 1st, 2nd
# and 3rd-4th down to keep the drive on schedule. The NFL figure is the DVOA
# baseline, college is the standard college definition, and high school is
# what high school staffs already chart: 4 yards on 1st & 10, half on 2nd.
# A plan can override them.
SUCCESS_BY_LEVEL: dict[Level, tuple[int, int, int]] = {
    Level.NFL: (45, 60, 100),
    Level.NCAA: (50, 70, 100),
    Level.HS: (40, 50, 100),
}


class GamePlan(BaseModel):
    name: str = "Game plan"
    opponent: Optional[str] = None
    level: Level = Level.HS
    execution: int = Field(default=2, ge=1, le=3)   # what the team can run: 1 Basic .. 3 Advanced
    success: Optional[tuple[int, int, int]] = None  # None: the level's default
    sections: list[PlanSection] = []                 # empty: derived from the book
    openers: list[str] = []                          # empty: plays labelled "Openers"
    drives: list[DriveScript] = []                   # drive patterns scripted in the week
    calls: CallSystem = CallSystem()
    log: list[Snap] = []
    notes: list[str] = []

    @property
    def thresholds(self) -> tuple[int, int, int]:
        return self.success or SUCCESS_BY_LEVEL[self.level]


__all__ = ["Role", "HELD_ROLES", "Mode", "When", "PlanSection", "DEFAULT_SECTIONS",
           "OPENERS_LABEL", "MODE_LABELS", "ZONES_WITH_DOWNS", "CallMethod", "CallSystem",
           "DriveState", "ScriptCall", "DriveScript", "Outcome", "Snap", "SUCCESS_BY_LEVEL",
           "GamePlan"]
