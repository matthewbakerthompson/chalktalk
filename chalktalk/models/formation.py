from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from .core import flip_side_name
from .player import Player


class Formation(BaseModel):
    name: str                       # e.g. "Shotgun Trips Right"
    personnel: str                  # e.g. "11", "12", "21"
    players: list[Player]
    description: Optional[str] = None

    def player(self, label: str) -> Optional[Player]:
        return next((p for p in self.players if p.label == label), None)

    def mirror(self, name: Optional[str] = None) -> "Formation":
        """
        The same formation to the other side. Names flip with it, so
        'I-Form Pro Right' comes back as 'I-Form Pro Left'.
        """
        return self.model_copy(update={
            "name": name or flip_side_name(self.name),
            "players": [p.model_copy(update={"x": -p.x}) for p in self.players],
        })
