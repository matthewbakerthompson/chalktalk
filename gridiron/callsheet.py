"""
gridiron.callsheet — game-day call sheets and player wristbands.

A CallSheet is the laminated page in a coordinator's hands: plays bucketed by
situation. A Wristband is the numbered grid on a player's forearm, generated
from the same source so the numbers always agree.

Usage
-----
from gridiron.callsheet import CallSheet, Wristband
from gridiron.models import situation as S

sheet = (
    CallSheet(name="Week 3", opponent="Central")
    .section("Openers",      openers_script.plays,  S.OPENERS)
    .section("3rd & Short",  [stick, qb_sneak],     S.THIRD_SHORT)
    .section("Red Zone",     rz_plays,              S.RED_ZONE)
    .number()
)
print(sheet.table())

band = Wristband.from_call_sheet(sheet, columns=3)
open("wristband.html", "w").write(band.to_html())
"""
from __future__ import annotations
from typing import Optional, Sequence

from pydantic import BaseModel

from .models.play import Play, Playbook
from .models import situation as S
from .models.situation import Situation


class CallSheetSection(BaseModel):
    title: str
    plays: list[Play] = []
    situation: Optional[Situation] = None
    note: Optional[str] = None

    def __len__(self) -> int:
        return len(self.plays)


class CallSheet(BaseModel):
    name: str
    team: Optional[str] = None
    opponent: Optional[str] = None
    date: Optional[str] = None
    sections: list[CallSheetSection] = []
    notes: list[str] = []

    # ── Building ──────────────────────────────────────────────────────────────

    def section(self, title: str, plays: Sequence[Play],
                situation: Optional[Situation] = None,
                note: Optional[str] = None) -> "CallSheet":
        sec = CallSheetSection(title=title, plays=list(plays),
                               situation=situation, note=note)
        return self.model_copy(update={"sections": [*self.sections, sec]})

    def note(self, *notes: str) -> "CallSheet":
        return self.model_copy(update={"notes": [*self.notes, *notes]})

    def number(self, start: int = 1) -> "CallSheet":
        """
        Assign sequential call numbers across the whole sheet. These are the
        numbers that end up on the wristband, so number once, at the end.
        """
        n = start
        sections = []
        for sec in self.sections:
            numbered = []
            for p in sec.plays:
                numbered.append(p.numbered(n))
                n += 1
            sections.append(sec.model_copy(update={"plays": numbered}))
        return self.model_copy(update={"sections": sections})

    @classmethod
    def from_playbook(cls, playbook: Playbook, name: Optional[str] = None,
                      buckets: Optional[dict[str, Situation]] = None) -> "CallSheet":
        """
        Auto-bucket a playbook into standard situational sections using each
        play's attached situation. Plays with no situation land in "Base".
        """
        buckets = buckets or STANDARD_BUCKETS
        sheet = cls(name=name or playbook.name, team=playbook.team)
        placed: set[int] = set()
        for title, sit in buckets.items():
            hits: list[Play] = []
            for i, p in enumerate(playbook.plays):
                if i in placed or p.situation is None:
                    continue
                if sit.matches(p.situation):
                    hits.append(p)
                    placed.add(i)
            if hits:
                sheet = sheet.section(title, hits, sit)
        leftover = [p for i, p in enumerate(playbook.plays) if i not in placed]
        if leftover:
            sheet = sheet.section("Base", leftover)
        return sheet

    # ── Views ─────────────────────────────────────────────────────────────────

    @property
    def plays(self) -> list[Play]:
        return [p for sec in self.sections for p in sec.plays]

    def to_playbook(self) -> Playbook:
        return Playbook(name=self.name, team=self.team, plays=self.plays)

    def table(self, width: int = 92) -> str:
        head = self.name
        if self.opponent:
            head += f"  vs {self.opponent}"
        if self.date:
            head += f"  ({self.date})"
        lines = [head, "=" * min(width, max(len(head), 40))]
        for sec in self.sections:
            sub = f"{sec.title.upper()}"
            if sec.situation and not sec.situation.label:
                sub += f"  [{sec.situation.describe()}]"
            lines += ["", sub, "-" * len(sub)]
            if sec.note:
                lines.append(f"  ({sec.note})")
            for p in sec.plays:
                num = f"{p.call_number:>3}. " if p.call_number else "   -  "
                lines.append(f"{num}{p.call}")
                for a in p.alerts:
                    lines.append(f"      ! {a}")
        if self.notes:
            lines += ["", "NOTES", "-----"]
            lines += [f"  - {n}" for n in self.notes]
        return "\n".join(lines)

    def to_html(self, **kwargs) -> str:
        from .renderer.sheets import call_sheet_html
        return call_sheet_html(self, **kwargs)

    def save_html(self, path: str, **kwargs) -> None:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_html(**kwargs))

    def __len__(self) -> int:
        return sum(len(s) for s in self.sections)


# The classic coordinator's buckets, in call-sheet order.
STANDARD_BUCKETS: dict[str, Situation] = {
    "Openers":        S.OPENERS,
    "1st & 10":       S.FIRST_TEN,
    "2nd & Short":    S.SECOND_SHORT,
    "2nd & Medium":   S.SECOND_MEDIUM,
    "2nd & Long":     S.SECOND_LONG,
    "3rd & 1-2":      S.THIRD_SHORT,
    "3rd & 3-6":      S.THIRD_MEDIUM,
    "3rd & 7+":       S.THIRD_LONG,
    "4th Down":       S.FOURTH_SHORT,
    "Backed Up":      S.BACKED_UP,
    "Fringe":         S.FRINGE,
    "Red Zone":       S.RED_ZONE,
    "Low Red":        S.LOW_RED,
    "Goal Line":      S.GOAL_LINE,
    "Two Minute":     S.TWO_MINUTE,
    "Four Minute":    S.FOUR_MINUTE,
    "Two-Point":      S.TWO_POINT,
}


class WristbandEntry(BaseModel):
    number: int
    call: str
    group: Optional[str] = None
    note: Optional[str] = None


class Wristband(BaseModel):
    """
    A numbered play grid. Build it from a call sheet or script so the numbers
    match what the coordinator is reading.
    """
    name: str
    team: Optional[str] = None
    columns: int = 3
    entries: list[WristbandEntry] = []

    @classmethod
    def from_plays(cls, plays: Sequence[Play], name: str = "Wristband",
                   columns: int = 3, start: int = 1,
                   group: Optional[str] = None) -> "Wristband":
        entries = [
            WristbandEntry(number=p.call_number or (start + i),
                           call=p.call, group=group,
                           note="; ".join(p.alerts) or None)
            for i, p in enumerate(plays)
        ]
        return cls(name=name, columns=columns, entries=entries)

    @classmethod
    def from_call_sheet(cls, sheet: CallSheet, columns: int = 3) -> "Wristband":
        numbered = sheet if any(p.call_number for p in sheet.plays) else sheet.number()
        entries: list[WristbandEntry] = []
        n = 1
        for sec in numbered.sections:
            for p in sec.plays:
                entries.append(WristbandEntry(
                    number=p.call_number or n, call=p.call, group=sec.title,
                    note="; ".join(p.alerts) or None,
                ))
                n = (p.call_number or n) + 1
        return cls(name=numbered.name, team=numbered.team,
                   columns=columns, entries=entries)

    @classmethod
    def from_script(cls, script, columns: int = 3) -> "Wristband":
        return cls.from_plays([e.play for e in script.entries],
                              name=script.name, columns=columns)

    def groups(self) -> dict[str, list[WristbandEntry]]:
        out: dict[str, list[WristbandEntry]] = {}
        for e in self.entries:
            out.setdefault(e.group or "Plays", []).append(e)
        return out

    def table(self, cell_width: int = 30) -> str:
        lines = [self.name, "=" * len(self.name)]
        for group, entries in self.groups().items():
            lines += ["", group, "-" * len(group)]
            row: list[str] = []
            for e in entries:
                row.append(f"{e.number:>3} {e.call}"[:cell_width].ljust(cell_width))
                if len(row) == self.columns:
                    lines.append(" | ".join(row))
                    row = []
            if row:
                lines.append(" | ".join(row))
        return "\n".join(lines)

    def to_html(self, **kwargs) -> str:
        from .renderer.sheets import wristband_html
        return wristband_html(self, **kwargs)

    def save_html(self, path: str, **kwargs) -> None:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_html(**kwargs))

    def __len__(self) -> int:
        return len(self.entries)


__all__ = [
    "CallSheet", "CallSheetSection", "STANDARD_BUCKETS",
    "Wristband", "WristbandEntry",
]
