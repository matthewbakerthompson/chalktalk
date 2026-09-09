"""
gridiron.script — practice scripts, install scripts, and opening scripts.

A Script is an ordered list of calls with the situation, the scout look to
give, and how many reps each gets. Practice scripts group those into periods.

Usage
-----
from gridiron.script import Script, PracticeScript, Period
from gridiron.models import situation as S
from gridiron.templates import defense as D

opening = (
    Script(name="Opening 15", opponent="Central")
    .add(passing.mesh_concept(), S.FIRST_TEN, looks=[D.NICKEL_425()])
    .add(running.inside_zone(),  S.SECOND_MEDIUM)
    .add(passing.stick(),        S.THIRD_SHORT, note="Check to Fade vs press")
)
print(opening.table())
print(opening.balance())
"""
from __future__ import annotations
from typing import Optional, Sequence

from pydantic import BaseModel

from .models.play import Play, Playbook, PlayType
from .models.defense import DefensiveFormation
from .models.situation import Situation, Hash


class ScriptEntry(BaseModel):
    number: int
    play: Play
    situation: Optional[Situation] = None
    look: Optional[DefensiveFormation] = None    # scout-team look to give
    reps: int = 1
    hash_mark: Optional[Hash] = None
    period: Optional[str] = None
    note: Optional[str] = None
    result: Optional[str] = None                 # filled in after the rep

    @property
    def look_name(self) -> str:
        if self.look is None:
            return ""
        cov = f" {self.look.coverage}" if self.look.coverage else ""
        return f"{self.look.name}{cov}"

    @property
    def call(self) -> str:
        return self.play.call

    def with_result(self, result: str) -> "ScriptEntry":
        return self.model_copy(update={"result": result})


class Script(BaseModel):
    """An ordered list of calls. Immutable — every method returns a new Script."""
    name: str
    opponent: Optional[str] = None
    date: Optional[str] = None
    period_name: Optional[str] = None
    entries: list[ScriptEntry] = []
    notes: Optional[str] = None

    # ── Building ──────────────────────────────────────────────────────────────

    def add(
        self,
        play: Play,
        situation: Optional[Situation] = None,
        looks: Optional[Sequence[DefensiveFormation]] = None,
        reps: int = 1,
        hash_mark: Optional[Hash] = None,
        period: Optional[str] = None,
        note: Optional[str] = None,
    ) -> "Script":
        """
        Append a call. `looks` cycles: pass the scout looks you want to see
        and each new entry takes the next one.
        """
        look = None
        if looks:
            look = looks[len(self.entries) % len(looks)]
        elif play.defense is not None:
            look = play.defense
        entry = ScriptEntry(
            number=len(self.entries) + 1,
            play=play,
            situation=situation if situation is not None else play.situation,
            look=look,
            reps=reps,
            hash_mark=hash_mark or (situation.hash_mark if situation else None),
            period=period or self.period_name,
            note=note,
        )
        return self.model_copy(update={"entries": [*self.entries, entry]})

    def add_all(self, plays: Sequence[Play], **kwargs) -> "Script":
        script = self
        for p in plays:
            script = script.add(p, **kwargs)
        return script

    def extend(self, other: "Script") -> "Script":
        return self.model_copy(
            update={"entries": [*self.entries, *other.entries]}
        ).renumber()

    def renumber(self, start: int = 1) -> "Script":
        return self.model_copy(update={
            "entries": [e.model_copy(update={"number": start + i})
                        for i, e in enumerate(self.entries)]
        })

    def alternate_hashes(self) -> "Script":
        """Assign left/right hashes alternately — the way scripts are repped."""
        order = [Hash.LEFT, Hash.RIGHT, Hash.MIDDLE]
        return self.model_copy(update={
            "entries": [e.model_copy(update={"hash_mark": order[i % len(order)]})
                        for i, e in enumerate(self.entries)]
        })

    def with_looks(self, looks: Sequence[DefensiveFormation]) -> "Script":
        """Re-assign scout looks round-robin across every entry."""
        return self.model_copy(update={
            "entries": [e.model_copy(update={"look": looks[i % len(looks)]})
                        for i, e in enumerate(self.entries)]
        })

    # ── Views ─────────────────────────────────────────────────────────────────

    @property
    def plays(self) -> list[Play]:
        return [e.play for e in self.entries]

    @property
    def total_reps(self) -> int:
        return sum(e.reps for e in self.entries)

    def openers(self, n: int = 15) -> "Script":
        return self.model_copy(update={"entries": self.entries[:n]}).renumber()

    def to_playbook(self) -> Playbook:
        return Playbook(name=self.name, plays=self.plays)

    def balance(self) -> dict[str, object]:
        """Run/pass split and personnel distribution — a script sanity check."""
        counts: dict[str, int] = {}
        personnel: dict[str, int] = {}
        formations: dict[str, int] = {}
        for e in self.entries:
            counts[e.play.play_type.value] = counts.get(e.play.play_type.value, 0) + e.reps
            personnel[e.play.formation.personnel] = \
                personnel.get(e.play.formation.personnel, 0) + e.reps
            formations[e.play.formation.name] = \
                formations.get(e.play.formation.name, 0) + e.reps
        total = max(self.total_reps, 1)
        runs = counts.get(PlayType.RUN.value, 0)
        passes = counts.get(PlayType.PASS.value, 0) + counts.get(PlayType.SCREEN.value, 0)
        return {
            "total_reps": self.total_reps,
            "by_type": counts,
            "run_pct": round(100 * runs / total),
            "pass_pct": round(100 * passes / total),
            "personnel": personnel,
            "formations": formations,
        }

    def table(self, width: int = 96) -> str:
        """Plain-text script, the way it gets taped to a call sheet."""
        head = f"{self.name}"
        if self.opponent:
            head += f"  vs {self.opponent}"
        if self.date:
            head += f"  ({self.date})"
        lines = [head, "=" * min(width, len(head) + 20)]
        lines.append(f"{'#':>3}  {'SIT':<12} {'CALL':<44} {'LOOK':<20} REP")
        lines.append("-" * width)
        for e in self.entries:
            sit = e.situation.short() if e.situation else ""
            if e.hash_mark and e.situation and not e.situation.hash_mark:
                sit = f"{sit} {e.hash_mark.value}".strip()
            call = e.call
            lines.append(
                f"{e.number:>3}  {sit[:12]:<12} {call[:44]:<44} "
                f"{e.look_name[:20]:<20} {e.reps}"
            )
            if e.note:
                lines.append(f"{'':>3}  -> {e.note}")
        b = self.balance()
        lines.append("-" * width)
        lines.append(f"{self.total_reps} reps | {b['run_pct']}% run / {b['pass_pct']}% pass")
        return "\n".join(lines)

    def to_csv(self) -> str:
        import csv
        import io
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["#", "Period", "Situation", "Hash", "Formation", "Call",
                    "Type", "Personnel", "Look", "Reps", "Note", "Result"])
        for e in self.entries:
            w.writerow([
                e.number, e.period or "", e.situation.describe() if e.situation else "",
                e.hash_mark.value if e.hash_mark else "",
                e.play.formation.name, e.call, e.play.play_type.value,
                e.play.formation.personnel, e.look_name, e.reps,
                e.note or "", e.result or "",
            ])
        return buf.getvalue()

    def save_csv(self, path: str) -> None:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_csv())

    def to_html(self, **kwargs) -> str:
        from .renderer.sheets import script_html
        return script_html(self, **kwargs)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)


class Period(BaseModel):
    """One period of practice."""
    name: str                       # "Indy", "Inside Run", "7-on-7", "Team"
    minutes: int = 10
    focus: Optional[str] = None
    script: Script = Script(name="")

    @property
    def reps(self) -> int:
        return self.script.total_reps


class PracticeScript(BaseModel):
    """A full practice: named periods, each with its own script."""
    name: str
    date: Optional[str] = None
    team: Optional[str] = None
    opponent: Optional[str] = None
    periods: list[Period] = []
    notes: Optional[str] = None

    def add_period(self, name: str, script: Script, minutes: int = 10,
                   focus: Optional[str] = None) -> "PracticeScript":
        period = Period(name=name, minutes=minutes, focus=focus,
                        script=script.model_copy(update={"period_name": name}))
        return self.model_copy(update={"periods": [*self.periods, period]})

    @property
    def total_minutes(self) -> int:
        return sum(p.minutes for p in self.periods)

    @property
    def total_reps(self) -> int:
        return sum(p.reps for p in self.periods)

    def flatten(self) -> Script:
        """All periods merged into one continuous script."""
        out = Script(name=self.name, opponent=self.opponent, date=self.date)
        for p in self.periods:
            out = out.extend(p.script)
        return out

    def to_playbook(self) -> Playbook:
        seen: dict[str, Play] = {}
        for p in self.periods:
            for play in p.script.plays:
                seen.setdefault(play.call, play)
        return Playbook(name=self.name, team=self.team, plays=list(seen.values()))

    def table(self) -> str:
        head = f"{self.name}"
        if self.date:
            head += f" — {self.date}"
        if self.opponent:
            head += f" (vs {self.opponent})"
        lines = [head, "=" * len(head),
                 f"{self.total_minutes} min | {self.total_reps} reps | "
                 f"{len(self.periods)} periods", ""]
        clock = 0
        for p in self.periods:
            focus = f" - {p.focus}" if p.focus else ""
            lines.append(f"[{clock:>3}'] {p.name} ({p.minutes} min){focus}")
            clock += p.minutes
            for e in p.script.entries:
                sit = e.situation.short() if e.situation else ""
                look = f"  vs {e.look_name}" if e.look else ""
                lines.append(f"        {e.number:>2}. {sit:<10} {e.call}{look}")
            lines.append("")
        return "\n".join(lines)

    def to_html(self, **kwargs) -> str:
        from .renderer.sheets import practice_html
        return practice_html(self, **kwargs)

    def save_csv(self, path: str) -> None:
        self.flatten().save_csv(path)


__all__ = ["ScriptEntry", "Script", "Period", "PracticeScript"]
