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

from .models.play import Play, Playbook, PlayType
from .models.situation import Situation

if TYPE_CHECKING:
    from .callsheet import CallSheet
    from .script import PracticeScript, Script


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


# ════════════════════════════════════════════════════════════════════════════
# SERIES SETS
# ════════════════════════════════════════════════════════════════════════════

class SeriesSetEntry(BaseModel):
    """One series inside a set, and when it goes in."""
    series: Series
    install_week: int = 1
    priority: int = 0                 # lower sorts first inside a week
    note: Optional[str] = None


class SeriesSet(BaseModel):
    """
    Several series treated as one thing: a system, a game plan, an install.

    A series answers a question. A set of series is an offense — and the useful
    questions are about the whole of it: what goes in first, how it gets repped,
    whether it is balanced, and what it still cannot answer.
    """
    name: str
    description: Optional[str] = None
    team: Optional[str] = None
    season: Optional[int] = None
    entries: list[SeriesSetEntry] = []
    tags: list[str] = []

    # ── Access ────────────────────────────────────────────────────────────────

    @property
    def series(self) -> list[Series]:
        return [e.series for e in self.entries]

    @property
    def plays(self) -> list[Play]:
        return [p for e in self.entries for p in e.series.plays]

    @property
    def bases(self) -> list[Play]:
        return [e.series.base for e in self.entries if e.series.base]

    def get(self, name: str) -> Optional[Series]:
        """Find a series by exact name, then by case-insensitive substring."""
        for e in self.entries:
            if e.series.name == name:
                return e.series
        lowered = name.lower()
        return next((e.series for e in self.entries
                     if lowered in e.series.name.lower()), None)

    def by_week(self) -> dict[int, list[Series]]:
        out: dict[int, list[Series]] = {}
        for e in sorted(self.entries, key=lambda e: (e.install_week, e.priority)):
            out.setdefault(e.install_week, []).append(e.series)
        return out

    def ordered(self) -> list["SeriesSetEntry"]:
        return sorted(self.entries, key=lambda e: (e.install_week, e.priority))

    # ── Installing ────────────────────────────────────────────────────────────

    def install(self, weeks: Optional[int] = None) -> dict[int, list[Play]]:
        """
        The teaching order, week by week.

        Inside a week every base goes in before anybody's constraints, because
        a constraint installed before the play it constrains teaches nothing.
        """
        plan: dict[int, list[Play]] = {}
        for week, series_list in self.by_week().items():
            ordered: list[Play] = []
            for s in series_list:                       # every base first
                if s.base is not None:
                    ordered.append(s.base.model_copy(update={"install_day": week}))
            for s in series_list:                       # then the answers
                for entry in s.sorted().entries:
                    if entry.role is not Role.BASE:
                        ordered.append(
                            entry.play.model_copy(update={"install_day": week}))
            plan[week] = ordered

        if weeks is not None:
            for week in range(1, weeks + 1):
                plan.setdefault(week, [])
        return dict(sorted(plan.items()))

    # ── Repping ───────────────────────────────────────────────────────────────

    def to_script(self, reps: int = 1, looks: Optional[list] = None,
                  week: Optional[int] = None) -> "Script":
        """One continuous script across every series in the set."""
        from .script import Script

        script = Script(name=f"{self.name} - Install")
        for entry in self.ordered():
            if week is not None and entry.install_week != week:
                continue
            script = script.extend(
                entry.series.to_script(reps=reps, period=entry.series.name,
                                       looks=looks))
        return script

    def to_practice(self, minutes: int = 12, reps: int = 1,
                    looks: Optional[list] = None,
                    week: Optional[int] = None) -> "PracticeScript":
        """A practice with one period per series — the way it gets repped."""
        from .script import PracticeScript

        practice = PracticeScript(name=f"{self.name} Practice", team=self.team)
        for entry in self.ordered():
            if week is not None and entry.install_week != week:
                continue
            practice = practice.add_period(
                entry.series.name,
                entry.series.to_script(reps=reps, looks=looks),
                minutes=minutes,
                focus=entry.note or entry.series.description,
            )
        return practice

    # ── Printing ──────────────────────────────────────────────────────────────

    def to_playbook(self) -> Playbook:
        return Playbook(name=self.name, team=self.team, season=self.season,
                        plays=self.plays)

    def to_call_sheet(self, name: Optional[str] = None) -> "CallSheet":
        """Every play in the set, bucketed by the situation it is called in."""
        from .callsheet import CallSheet
        return CallSheet.from_playbook(self.to_playbook(),
                                       name=name or self.name).number()

    def render_all(self, directory: str) -> list[str]:
        """One folder per series, one SVG per play."""
        import os
        import re
        paths: list[str] = []
        for entry in self.ordered():
            slug = re.sub(r"[^a-z0-9]+", "_", entry.series.name.lower()).strip("_")
            paths.extend(entry.series.render_all(os.path.join(directory, slug)))
        return paths

    # ── Checking it ───────────────────────────────────────────────────────────

    def balance(self) -> dict:
        """Is this an offense, or five versions of the same play?"""
        counts: dict[str, int] = {}
        personnel: dict[str, int] = {}
        formations: dict[str, int] = {}
        roles: dict[str, int] = {}
        for entry in self.entries:
            for e in entry.series.entries:
                play = e.play
                counts[play.play_type.value] = counts.get(play.play_type.value, 0) + 1
                key = play.formation.personnel
                personnel[key] = personnel.get(key, 0) + 1
                formations[play.formation.name] = (
                    formations.get(play.formation.name, 0) + 1)
                roles[e.role.value] = roles.get(e.role.value, 0) + 1
        total = max(len(self.plays), 1)
        runs = counts.get(PlayType.RUN.value, 0)
        passes = (counts.get(PlayType.PASS.value, 0)
                  + counts.get(PlayType.SCREEN.value, 0))
        return {
            "series": len(self.entries),
            "plays": len(self.plays),
            "by_type": counts,
            "run_pct": round(100 * runs / total),
            "pass_pct": round(100 * passes / total),
            "personnel": personnel,
            "formations": formations,
            "roles": roles,
            "answers_per_base": {
                e.series.name: len(e.series) - 1 for e in self.ordered()
            },
        }

    def gaps(self) -> list[str]:
        """
        What this system cannot answer yet.

        Not a style linter — these are the holes a defensive coordinator finds
        on Sunday: a base play with no constraint off it, a series with nothing
        that goes over the top, everything from one personnel grouping.
        """
        notes: list[str] = []
        b = self.balance()

        for name, answers in b["answers_per_base"].items():
            if answers < 2:
                notes.append(f"{name}: only {answers} answer off the base play")

        for entry in self.ordered():
            roles = {e.role for e in entry.series.entries}
            if not roles & {Role.SHOT, Role.PLAY_ACTION}:
                notes.append(f"{entry.series.name}: nothing that goes over the top")
            if Role.CONSTRAINT not in roles:
                notes.append(f"{entry.series.name}: no constraint on the base")

        if b["plays"] and (b["run_pct"] > 70 or b["pass_pct"] > 70):
            notes.append(
                f"the whole set is {b['run_pct']}% run / {b['pass_pct']}% pass")

        if len(b["personnel"]) < 2:
            notes.append("everything comes from one personnel grouping")

        situations = {p.situation.describe() for p in self.plays
                      if p.situation is not None}
        if len(self.entries) >= 3 and len(situations) < 3:
            notes.append("the set is not spread across situations")

        return notes

    # ── Display ───────────────────────────────────────────────────────────────

    def describe(self) -> str:
        lines = [self.name]
        if self.description:
            lines.append(self.description)
        b = self.balance()
        lines.append(f"{b['series']} series | {b['plays']} plays | "
                     f"{b['run_pct']}% run / {b['pass_pct']}% pass")
        lines.append("=" * max(len(self.name), 28))
        for week, series_list in self.by_week().items():
            lines.append("")
            lines.append(f"Week {week}")
            for s in series_list:
                base = s.base.name if s.base else "-"
                lines.append(f"  {s.name}  ({len(s)} plays, base: {base})")
        holes = self.gaps()
        if holes:
            lines.append("")
            lines.append("Gaps")
            lines.extend(f"  - {note}" for note in holes)
        return "\n".join(lines)

    def to_html(self, **kwargs) -> str:
        from .renderer.sheets import series_set_html
        return series_set_html(self, **kwargs)

    def save_html(self, path: str, **kwargs) -> None:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_html(**kwargs))

    def save(self, path: str) -> None:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: str) -> "SeriesSet":
        with open(path, encoding="utf-8") as fh:
            return cls.model_validate_json(fh.read())

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.series)


class SeriesSetBuilder:
    """Fluent builder — see the module docstring."""

    def __init__(self, name: str, description: Optional[str] = None) -> None:
        self._name = name
        self._description = description
        self._entries: list[SeriesSetEntry] = []
        self._tags: list[str] = []
        self._team: Optional[str] = None
        self._season: Optional[int] = None

    def add(self, series_: Series, install_week: int = 1, priority: int = 0,
            note: Optional[str] = None) -> "SeriesSetBuilder":
        self._entries.append(SeriesSetEntry(
            series=series_, install_week=install_week, priority=priority,
            note=note))
        return self

    def team(self, name: str, season: Optional[int] = None) -> "SeriesSetBuilder":
        self._team = name
        self._season = season
        return self

    def tag(self, *tags: str) -> "SeriesSetBuilder":
        self._tags.extend(tags)
        return self

    def build(self) -> SeriesSet:
        return SeriesSet(name=self._name, description=self._description,
                         team=self._team, season=self._season,
                         entries=self._entries, tags=self._tags)


def series_set(name: str, description: Optional[str] = None) -> SeriesSetBuilder:
    """Shorthand: `series_set('Base Offense').add(iz).add(mesh).build()`"""
    return SeriesSetBuilder(name, description)


__all__ = ["Role", "SeriesEntry", "Series", "SeriesBuilder", "series",
           "SeriesSet", "SeriesSetEntry", "SeriesSetBuilder", "series_set"]
