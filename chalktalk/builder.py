"""
PlayBuilder — fluent API for constructing Play objects concisely.

Usage
-----
from chalktalk.builder import play
from chalktalk.templates import routes as R, formations as F
from chalktalk.models import PlayType

mesh = (
    play(F.SHOTGUN_TRIPS_RIGHT())
    .block_ol()
    .routes(X=R.FLY(), Y=R.FLAT(), Z=R.MESH(5, 22), H=R.MESH(6, 22), RB=R.SWING())
    .name("Mesh Concept")
    .play_type(PlayType.PASS)
    .tag("mesh", "trips", "crossing")
    .build()
)

# Easy route swap — returns a brand new Play
post_version = mesh.with_route("X", R.POST())
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .models.formation import Formation
from .models.route import Route
from .models.assignment import Assignment
from .models.play import Play, PlayType

if TYPE_CHECKING:
    from .models.defense import DefensiveFormation


class PlayBuilder:
    def __init__(self, formation: Formation) -> None:
        self._formation  = formation
        self._routes: dict[str, Route]         = {}
        self._ball_carriers: set[str]          = set()
        self._motion: dict[str, tuple[float, float]] = {}
        self._defense: Optional["DefensiveFormation"] = None
        self._name: str                        = "Unnamed Play"
        self._play_type: PlayType              = PlayType.PASS
        self._description: Optional[str]       = None
        self._tags: list[str]                  = []

    # ── Routing ───────────────────────────────────────────────────────────────

    def route(self, label: str, r: Route) -> "PlayBuilder":
        """Assign a route to a single player by label."""
        self._routes[label] = r
        return self

    def routes(self, **kwargs: Route) -> "PlayBuilder":
        """Assign multiple routes at once: .routes(X=R.FLY(), Z=R.SLANT())"""
        self._routes.update(kwargs)
        return self

    def block_ol(self) -> "PlayBuilder":
        """Auto-assign BLOCK to every offensive lineman in the formation."""
        from .templates.routes import BLOCK
        for p in self._formation.players:
            if p.is_ol and p.label not in self._routes:
                self._routes[p.label] = BLOCK()
        return self

    def block(self, *labels: str) -> "PlayBuilder":
        """Assign BLOCK to specific players by label."""
        from .templates.routes import BLOCK
        for lbl in labels:
            self._routes[lbl] = BLOCK()
        return self

    def bc(self, label: str) -> "PlayBuilder":
        """Designate a player as ball carrier."""
        self._ball_carriers.add(label)
        return self

    def motion(self, label: str, from_x: float, from_y: float) -> "PlayBuilder":
        """Mark a player as going in motion pre-snap, starting at (from_x, from_y)."""
        self._motion[label] = (from_x, from_y)
        return self

    # ── Metadata ──────────────────────────────────────────────────────────────

    def name(self, n: str) -> "PlayBuilder":
        self._name = n
        return self

    def play_type(self, pt: PlayType) -> "PlayBuilder":
        self._play_type = pt
        return self

    def tag(self, *tags: str) -> "PlayBuilder":
        self._tags.extend(tags)
        return self

    def describe(self, d: str) -> "PlayBuilder":
        self._description = d
        return self

    def vs(self, defense: "DefensiveFormation") -> "PlayBuilder":
        self._defense = defense
        return self

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> Play:
        assignments = []
        for p in self._formation.players:
            assignments.append(
                Assignment(
                    player=p,
                    route=self._routes.get(p.label),
                    is_ball_carrier=p.label in self._ball_carriers,
                    motion_from=self._motion.get(p.label),
                )
            )
        return Play(
            name=self._name,
            formation=self._formation,
            play_type=self._play_type,
            assignments=assignments,
            defense=self._defense,
            description=self._description,
            tags=self._tags,
        )


def play(formation: Formation) -> PlayBuilder:
    """Shorthand constructor — `play(F.SHOTGUN_TRIPS_RIGHT()).block_ol()...`"""
    return PlayBuilder(formation)
