"""
chalktalk.series — scripted series: families of plays that build off each other.

A series is how offenses actually get built. You have a base play, the
defense over-reacts to stop it, and every other play in the series punishes
one specific over-reaction. Each entry records the *tell* — what the defense
does that makes this the right call.

Usage
-----
from chalktalk.series import series, Role
from chalktalk.catalog import running, passing

iz = (
    series("Inside Zone Series", "Everything off the IZ mesh point")
    .base(running.inside_zone(), "Downhill A-gap read off the double team")
    .constraint(running.speed_sweep(), tell="Backside LB flowing hard inside")
    .play_action(passing.y_cross(), tell="Safeties dropping down to fit the run")
    .shot(passing.four_verticals(), tell="Single high with the FS cheating the box")
    .build()
)

print(iz.describe())
practice = iz.to_script(reps=2)         # ready-to-run practice script
iz.to_playbook().save("out/iz_series.json")
"""
from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from .models.play import Play, Playbook
from .models.situation import Situation

if TYPE_CHECKING:
    from .script import Script


class Role(str, Enum):
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


_ROLE_ORDER = {r: i for i, r in enumerate(
    [Role.BASE, Role.COMPLEMENT, Role.CONSTRAINT,
     Role.PLAY_ACTION, Role.SHOT, Role.ANSWER, Role.TRICK]
)}


class SeriesEntry(BaseModel):
    play: Play
    role: Role = Role.COMPLEMENT
    tell: Optional[str] = None       # the defensive reaction that triggers this call
    note: Optional[str] = None
    off_of: Optional[str] = None     # name of the play this builds from

    def describe(self) -> str:
        line = f"[{self.role.display}] {self.play.call}"
        if self.tell:
            line += f"\n      when: {self.tell}"
        if self.note:
            line += f"\n      note: {self.note}"
        return line


class Series(BaseModel):
    """An ordered family of plays that share a picture."""
    name: str
    description: Optional[str] = None
    entries: list[SeriesEntry] = []
    tags: list[str] = []

    # ── Access ────────────────────────────────────────────────────────────────

    @property
    def plays(self) -> list[Play]:
        return [e.play for e in self.entries]

    @property
    def base(self) -> Optional[Play]:
        e = next((e for e in self.entries if e.role is Role.BASE), None)
        return e.play if e else (self.entries[0].play if self.entries else None)

    def by_role(self, role: Role) -> list[Play]:
        return [e.play for e in self.entries if e.role is role]

    def sorted(self) -> "Series":
        """Order entries base-first, then by teaching progression."""
        return self.model_copy(update={
            "entries": sorted(self.entries, key=lambda e: _ROLE_ORDER.get(e.role, 99))
        })

    # ── Conversion ────────────────────────────────────────────────────────────

    def to_playbook(self, team: Optional[str] = None) -> Playbook:
        return Playbook(name=self.name, team=team, plays=self.plays)

    def to_script(self, reps: int = 1, period: Optional[str] = None,
                  looks: Optional[list] = None) -> "Script":
        """
        Turn the series into a practice script: base first, then each
        constraint, `reps` times through.
        """
        from .script import Script
        script = Script(name=f"{self.name} - Install", period_name=period)
        for _ in range(reps):
            for e in self.sorted().entries:
                script = script.add(
                    e.play,
                    situation=e.play.situation,
                    note=e.tell or e.note,
                    period=period,
                    looks=looks,
                )
        return script

    def install(self, days: int = 3) -> dict[int, list[Play]]:
        """
        Split the series across an install progression — base on day 1,
        constraints as the week goes on.
        """
        ordered = self.sorted().entries
        out: dict[int, list[Play]] = {d: [] for d in range(1, days + 1)}
        for i, e in enumerate(ordered):
            day = min(days, 1 + i * days // max(len(ordered), 1))
            out[day].append(e.play.model_copy(update={"install_day": day}))
        return out

    # ── Display ───────────────────────────────────────────────────────────────

    def describe(self) -> str:
        lines = [self.name]
        if self.description:
            lines.append(self.description)
        lines.append("-" * max(len(self.name), 24))
        for i, e in enumerate(self.sorted().entries, 1):
            lines.append(f"  {i}. {e.describe()}")
        return "\n".join(lines)

    def render_all(self, directory: str, prefix: str = "") -> list[str]:
        """Write an SVG per play into `directory`. Returns the file paths."""
        import os
        import re
        paths = []
        for i, play in enumerate(self.plays, 1):
            slug = re.sub(r"[^a-z0-9]+", "_", play.name.lower()).strip("_")
            path = os.path.join(directory, f"{prefix}{i:02d}_{slug}.svg")
            play.render().save(path)
            paths.append(path)
        return paths

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)


class SeriesBuilder:
    """Fluent builder — see module docstring."""

    def __init__(self, name: str, description: Optional[str] = None) -> None:
        self._name = name
        self._description = description
        self._entries: list[SeriesEntry] = []
        self._tags: list[str] = []
        self._base_name: Optional[str] = None

    def _add(self, play: Play, role: Role, tell: Optional[str],
             note: Optional[str], situation: Optional[Situation]) -> "SeriesBuilder":
        if situation is not None:
            play = play.at(situation)
        if role is not Role.BASE and play.concept is None and self._base_name:
            play = play.model_copy(update={"concept": play.name})
        self._entries.append(SeriesEntry(
            play=play, role=role, tell=tell, note=note,
            off_of=None if role is Role.BASE else self._base_name,
        ))
        if role is Role.BASE:
            self._base_name = play.name
        return self

    def base(self, play: Play, note: Optional[str] = None,
             situation: Optional[Situation] = None) -> "SeriesBuilder":
        return self._add(play, Role.BASE, None, note, situation)

    def complement(self, play: Play, tell: Optional[str] = None,
                   note: Optional[str] = None,
                   situation: Optional[Situation] = None) -> "SeriesBuilder":
        return self._add(play, Role.COMPLEMENT, tell, note, situation)

    def constraint(self, play: Play, tell: Optional[str] = None,
                   note: Optional[str] = None,
                   situation: Optional[Situation] = None) -> "SeriesBuilder":
        return self._add(play, Role.CONSTRAINT, tell, note, situation)

    def play_action(self, play: Play, tell: Optional[str] = None,
                    note: Optional[str] = None,
                    situation: Optional[Situation] = None) -> "SeriesBuilder":
        return self._add(play, Role.PLAY_ACTION, tell, note, situation)

    def shot(self, play: Play, tell: Optional[str] = None,
             note: Optional[str] = None,
             situation: Optional[Situation] = None) -> "SeriesBuilder":
        return self._add(play, Role.SHOT, tell, note, situation)

    def answer(self, play: Play, tell: Optional[str] = None,
               note: Optional[str] = None,
               situation: Optional[Situation] = None) -> "SeriesBuilder":
        return self._add(play, Role.ANSWER, tell, note, situation)

    def trick(self, play: Play, tell: Optional[str] = None,
              note: Optional[str] = None,
              situation: Optional[Situation] = None) -> "SeriesBuilder":
        return self._add(play, Role.TRICK, tell, note, situation)

    def tag(self, *tags: str) -> "SeriesBuilder":
        self._tags.extend(tags)
        return self

    def build(self) -> Series:
        return Series(name=self._name, description=self._description,
                      entries=self._entries, tags=self._tags)


def series(name: str, description: Optional[str] = None) -> SeriesBuilder:
    """Shorthand: `series('Inside Zone Series').base(iz)...build()`"""
    return SeriesBuilder(name, description)


__all__ = ["Role", "SeriesEntry", "Series", "SeriesBuilder", "series"]
