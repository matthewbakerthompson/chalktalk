from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from .player import Player


class Formation(BaseModel):
    name: str                       # e.g. "Shotgun Trips Right"
    personnel: str                  # e.g. "11", "12", "21"
    players: list[Player]
    description: Optional[str] = None
