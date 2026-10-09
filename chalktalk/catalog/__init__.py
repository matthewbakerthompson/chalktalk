"""
chalktalk.catalog — ready-to-use named play concepts and scripted series.

Usage
-----
from chalktalk.catalog import passing, running, redzone, playaction, screens, rpo

mesh   = passing.mesh_concept()
iz     = running.inside_zone()
boot   = playaction.pa_boot()
slip   = screens.rb_slip()
glance = rpo.glance()

# Override formation
iz_gun = running.inside_zone(formation=F.GUN_OFFSET_BACK_RIGHT())

# Swap a route on any catalog play
post_version = mesh.with_route("X", R.POST())

# A whole scripted series — base play plus every constraint off it
iz_series = series.inside_zone_series()
print(iz_series.describe())

Everything at once
------------------
`all_plays()` returns every concept in the catalog, keyed by name. Anything
that enumerates plays — the CLI, the tests — goes through it, so
a new module is picked up everywhere the moment it lands in PLAY_MODULES.
"""
import inspect
from typing import Callable

from . import (passing, playaction, redzone, rpo, running, screens,
               series, systems)

#: Every module that contributes plays. Add new ones here and they show up in
#: the CLI and the test sweep without another edit.
PLAY_MODULES = (passing, running, redzone, playaction, screens, rpo)


def play_builders() -> dict[str, Callable]:
    """{name: builder} for every concept in the catalog."""
    out: dict[str, Callable] = {}
    for module in PLAY_MODULES:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_") or fn.__module__ != module.__name__:
                continue
            out[name] = fn
    return out


def all_plays() -> dict[str, "object"]:
    """{name: Play} — builds every concept in the catalog."""
    return {name: fn() for name, fn in play_builders().items()}


__all__ = [
    "passing", "running", "redzone", "playaction", "screens", "rpo",
    "series", "systems",
    "PLAY_MODULES", "play_builders", "all_plays",
]
