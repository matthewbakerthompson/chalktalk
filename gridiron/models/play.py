from __future__ import annotations
from enum import Enum
from typing import Optional, TYPE_CHECKING  # TYPE_CHECKING used for SVGRenderer
from pydantic import BaseModel
from .formation import Formation
from .assignment import Assignment
from .route import Route
from .defense import DefensiveFormation
from .situation import Situation, Tempo

if TYPE_CHECKING:
    from ..renderer.svg import SVGRenderer
    from ..adjustments import Adjustment


class PlayType(str, Enum):
    PASS    = "pass"
    RUN     = "run"
    RPO     = "rpo"
    SCREEN  = "screen"
    SPECIAL = "special"


class Play(BaseModel):
    name: str
    formation: Formation
    play_type: PlayType
    assignments: list[Assignment]
    defense: Optional[DefensiveFormation] = None
    description: Optional[str] = None
    tags: list[str] = []

    # ── Call-sheet / install metadata ─────────────────────────────────────────
    concept: Optional[str] = None            # base concept, e.g. "Mesh"
    protection: Optional[str] = None         # "Slide Rt", "Half-Slide", "Max"
    tempo: Tempo = Tempo.NORMAL
    alerts: list[str] = []                   # "Alert Fade vs press"
    adjustments: list[str] = []              # applied adjustment names, in order
    situation: Optional[Situation] = None    # when this play is meant to be called
    install_day: Optional[int] = None        # install/teaching progression day
    call_number: Optional[int] = None        # wristband / call-sheet number

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render(self, **kwargs) -> "SVGRenderer":
        from ..renderer.svg import SVGRenderer
        return SVGRenderer(self, **kwargs)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Play":
        return cls.model_validate_json(json_str)

    # ── Description ───────────────────────────────────────────────────────────

    def describe(self) -> str:
        lines = [
            f"{self.formation.name}  --  {self.name}  [{self.play_type.value.upper()}]",
            f"Personnel: {self.formation.personnel}",
        ]
        if self.protection:
            lines.append(f"Protection: {self.protection}")
        if self.adjustments:
            lines.append(f"Adjustments: {', '.join(self.adjustments)}")
        for a in self.assignments:
            if a.route:
                bc = " [BC]" if a.is_ball_carrier else ""
                mo = f" (motion: {a.motion_type})" if a.motion_type else ""
                lines.append(f"  {a.player.label:>4s}: {a.route.route_type.value}{bc}{mo}")
        for al in self.alerts:
            lines.append(f"  ! {al}")
        if self.situation:
            lines.append(f"Situation: {self.situation.describe()}")
        if self.defense:
            lines.append(f"vs: {self.defense.name} ({self.defense.coverage or ''})")
        if self.description:
            lines.append(f"\n{self.description}")
        return "\n".join(lines)

    # ── Immutable mutation helpers (return new Play) ──────────────────────────

    def with_route(self, label: str, route: Route) -> "Play":
        """Return a copy of this play with one player's route replaced."""
        new_assignments = [
            a.model_copy(update={"route": route}) if a.player.label == label else a
            for a in self.assignments
        ]
        return self.model_copy(update={"assignments": new_assignments})

    def with_routes(self, **kwargs: Route) -> "Play":
        """Return a copy with multiple routes replaced at once."""
        play = self
        for label, route in kwargs.items():
            play = play.with_route(label, route)
        return play

    def with_formation(self, new_formation: Formation) -> "Play":
        """
        Transfer route assignments to a new formation by matching player labels.
        Players in the new formation without a matching label get no route.
        """
        route_map = {a.player.label: a for a in self.assignments}
        new_assignments = [
            Assignment(
                player=p,
                route=route_map[p.label].route if p.label in route_map else None,
                is_ball_carrier=(
                    route_map[p.label].is_ball_carrier if p.label in route_map else False
                ),
            )
            for p in new_formation.players
        ]
        return self.model_copy(update={
            "formation": new_formation,
            "assignments": new_assignments,
        })

    def mirror(self) -> "Play":
        """
        Return a left-right mirrored copy of the play.

        Player x-positions are negated; the SVG renderer automatically mirrors
        route waypoints for players on the left side, so routes stay correct.
        """
        mirrored_assignments = [
            a.model_copy(update={
                "player": a.player.model_copy(update={"x": -a.player.x},),
                "motion_from": (None if a.motion_from is None
                                else (-a.motion_from[0], a.motion_from[1])),
            })
            for a in self.assignments
        ]
        mirrored_formation = self.formation.model_copy(
            update={
                "players": [
                    p.model_copy(update={"x": -p.x})
                    for p in self.formation.players
                ]
            }
        )
        updates: dict = {
            "assignments": mirrored_assignments,
            "formation": mirrored_formation,
        }
        if self.defense:
            updates["defense"] = self.defense.mirror()
        return self.model_copy(update=updates)

    def vs(self, defense: "DefensiveFormation") -> "Play":
        """Return a copy of this play with a defensive formation attached."""
        return self.model_copy(update={"defense": defense})

    def tag(self, *tags: str) -> "Play":
        """Return a copy with additional tags appended."""
        return self.model_copy(update={"tags": [*self.tags, *tags]})

    # ── Adjustments / alts ────────────────────────────────────────────────────

    def adjust(self, *adjustments: "Adjustment") -> "Play":
        """
        Apply one or more adjustments, returning a new Play.

            gun_mesh.adjust(A.MOTION("Z", "jet"), A.TAG("Y", R.CORNER()))
        """
        play = self
        for adj in adjustments:
            play = adj.apply(play)
        return play

    def alert(self, *alerts: str) -> "Play":
        """Attach pre-snap alerts/checks ('Alert Fade vs press')."""
        return self.model_copy(update={"alerts": [*self.alerts, *alerts]})

    def protect(self, scheme: str) -> "Play":
        """Set the protection call."""
        return self.model_copy(update={"protection": scheme})

    def at(self, situation: Situation) -> "Play":
        """Attach the situation this play is designed for."""
        return self.model_copy(update={"situation": situation})

    def numbered(self, n: int) -> "Play":
        """Assign a wristband / call-sheet number."""
        return self.model_copy(update={"call_number": n})

    def rename(self, name: str) -> "Play":
        return self.model_copy(update={"name": name})

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def call(self) -> str:
        """
        The full verbal call as a coach would say it:
        'Gun Trips Rt Mesh Slide Rt Z Jet'
        """
        bits = [self.formation.name, self.name]
        if self.protection:
            bits.append(self.protection)
        bits.extend(self.adjustments)
        if self.tempo is not Tempo.NORMAL:
            bits.append(self.tempo.value.replace("_", "-").title())
        return " ".join(b for b in bits if b)

    @property
    def base_concept(self) -> str:
        return self.concept or self.name

    @property
    def ball_carrier(self) -> Optional[Assignment]:
        return next((a for a in self.assignments if a.is_ball_carrier), None)

    def assignment(self, label: str) -> Optional[Assignment]:
        return next((a for a in self.assignments if a.player.label == label), None)


class Playbook(BaseModel):
    name: str
    team: Optional[str] = None
    season: Optional[int] = None
    plays: list[Play] = []

    def add(self, *plays: Play) -> "Playbook":
        return self.model_copy(update={"plays": [*self.plays, *plays]})

    def get(self, name: str) -> Optional[Play]:
        """Find a play by exact name, then by case-insensitive substring."""
        for p in self.plays:
            if p.name == name:
                return p
        lowered = name.lower()
        return next((p for p in self.plays if lowered in p.name.lower()), None)

    def number(self, start: int = 1) -> "Playbook":
        """Assign sequential call numbers to every play (for wristbands)."""
        return self.model_copy(update={
            "plays": [p.numbered(start + i) for i, p in enumerate(self.plays)]
        })

    def for_situation(self, situation: "Situation") -> "Playbook":
        """Plays whose attached situation is compatible with `situation`."""
        return self.model_copy(update={
            "plays": [p for p in self.plays
                      if p.situation is not None and p.situation.matches(situation)]
        })

    def concepts(self) -> dict[str, list[Play]]:
        """Group plays by base concept — a base plus all of its alts."""
        out: dict[str, list[Play]] = {}
        for p in self.plays:
            out.setdefault(p.base_concept, []).append(p)
        return out

    def save(self, path: str) -> None:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    def to_html(self, **kwargs) -> str:
        """Printable playbook page with a diagram per play."""
        from ..renderer.sheets import playbook_html
        return playbook_html(self, **kwargs)

    def save_html(self, path: str, **kwargs) -> None:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_html(**kwargs))

    def save_pdf(self, path: str, **kwargs) -> None:
        from ..renderer.pdf import PDFExporter
        PDFExporter(self, path, **kwargs).export()

    @classmethod
    def load(cls, path: str) -> "Playbook":
        with open(path, encoding="utf-8") as fh:
            return cls.from_json(fh.read())

    def filter(
        self,
        play_type: Optional[PlayType] = None,
        tag: Optional[str] = None,
        formation: Optional[str] = None,
    ) -> "Playbook":
        results = self.plays
        if play_type is not None:
            results = [p for p in results if p.play_type == play_type]
        if tag is not None:
            results = [p for p in results if tag in p.tags]
        if formation is not None:
            results = [p for p in results if formation.lower() in p.formation.name.lower()]
        return Playbook(name=self.name, team=self.team, season=self.season, plays=results)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Playbook":
        return cls.model_validate_json(json_str)

    def __len__(self) -> int:
        return len(self.plays)

    def __iter__(self):
        return iter(self.plays)

    def __getitem__(self, index):
        return self.plays[index]
