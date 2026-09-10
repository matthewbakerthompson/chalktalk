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

from .models.block import Block
from .models.qb import QBPlan
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
        self._blocks: dict[str, Block]         = {}
        self._qb: Optional[QBPlan]             = None
        self._qb_label: str                    = "QB"
        self._ball_carriers: set[str]          = set()
        self._motion: dict[str, tuple[float, float]] = {}
        self._defense: Optional["DefensiveFormation"] = None
        self._name: str                        = "Unnamed Play"
        self._play_type: PlayType              = PlayType.PASS
        self._description: Optional[str]       = None
        self._protection: Optional[str]        = None
        self._tags: list[str]                  = []

    # ── Routing ───────────────────────────────────────────────────────────────

    def route(self, label: str, r: Route) -> "PlayBuilder":
        """Assign a route to a single player. A player blocks or runs, not both."""
        self._routes[label] = r
        self._blocks.pop(label, None)
        return self

    def routes(self, **kwargs: Route) -> "PlayBuilder":
        """Assign multiple routes at once: .routes(X=R.FLY(), Z=R.SLANT())"""
        for label, r in kwargs.items():
            self.route(label, r)
        return self

    def block_ol(self) -> "PlayBuilder":
        """Give every offensive lineman a base block."""
        from .templates.blocking import BASE
        for p in self._formation.players:
            if p.is_ol and p.label not in self._routes and p.label not in self._blocks:
                self._blocks[p.label] = BASE()
        return self

    def block(self, *labels: str) -> "PlayBuilder":
        """Assign a base block to specific players by label."""
        from .templates.blocking import BASE
        for lbl in labels:
            self._blocks[lbl] = BASE()
            self._routes.pop(lbl, None)
        return self

    def blocks(self, **kwargs: Block) -> "PlayBuilder":
        """Assign blocks by label: .blocks(LT=B.SCOOP(), RG=B.WRAP(1))"""
        self._blocks.update(kwargs)
        return self

    def scheme(self, blocks: dict[str, Block],
               protection: Optional[str] = None) -> "PlayBuilder":
        """
        Apply a whole-line scheme from `chalktalk.templates.schemes`.

            .scheme(S.power(+1), protection="Power Rt")

        Anyone in the scheme who is not in the formation is ignored, so the
        same scheme works whether or not there is a fullback on the field.
        """
        present = {p.label for p in self._formation.players}
        self._blocks.update({k: v for k, v in blocks.items() if k in present})
        if protection:
            self._protection = protection
        for label in self._blocks:
            self._routes.pop(label, None)
        return self

    def pass_pro(self, blocks: Optional[dict[str, Block]] = None,
                 protection: Optional[str] = None) -> "PlayBuilder":
        """Protect with a scheme, defaulting to big-on-big."""
        from .templates.schemes import big_on_big
        return self.scheme(blocks if blocks is not None else big_on_big(),
                           protection)

    def qb(self, plan: QBPlan, label: str = "QB") -> "PlayBuilder":
        """Give the quarterback his action and progression."""
        self._qb = plan
        self._qb_label = label
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

    def protect(self, name: str) -> "PlayBuilder":
        """Name the protection without changing the blocks."""
        self._protection = name
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
                    block=self._blocks.get(p.label),
                    qb=self._qb if p.label == self._qb_label else None,
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
            protection=self._protection,
            description=self._description,
            tags=self._tags,
        )


def play(formation: Formation) -> PlayBuilder:
    """Shorthand constructor — `play(F.SHOTGUN_TRIPS_RIGHT()).block_ol()...`"""
    return PlayBuilder(formation)
