"""
gridiron.catalog — ready-to-use named play concepts and scripted series.

Usage
-----
from gridiron.catalog import passing, running, redzone, series

mesh      = passing.mesh_concept()
iz        = running.inside_zone()
fade_corn = redzone.fade_corner()

# Override formation
iz_gun = running.inside_zone(formation=F.GUN_OFFSET_BACK_RIGHT())

# Swap a route on any catalog play
post_version = mesh.with_route("X", R.POST())

# A whole scripted series — base play plus every constraint off it
iz_series = series.inside_zone_series()
print(iz_series.describe())
"""
from . import passing, running, redzone, series

__all__ = ["passing", "running", "redzone", "series"]
