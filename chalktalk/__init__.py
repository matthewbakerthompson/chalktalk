"""
chalktalk — design, manage, and render American football plays.

Playbook as code: plays are data, so they diff in git, round-trip through
JSON, and render to SVG, PDF, and printable call sheets.

Quick-start
-----------
from chalktalk import adjustments as A
from chalktalk.catalog import (passing, running, redzone,
                               playaction, screens, rpo)
from chalktalk.templates import routes as R, defense as D

mesh = passing.mesh_concept()
mesh.render().save("mesh.svg")

# Alts: motion, tags, protection, flip — all composable and serializable
mesh_jet = mesh.adjust(A.MOTION("Z", "jet"), A.PROTECTION("Slide Rt"))

# Scripted series — a base play plus everything that punishes over-reaction
from chalktalk.catalog import series as SR
iz = SR.inside_zone_series()
print(iz.describe())

# Practice script, call sheet, wristband
script = iz.to_script(reps=2).with_looks([D.NICKEL_425(), D.FOUR_THREE_OVER()])
print(script.table())
"""
from .models import (
    Point, Player, Position,
    Route, RouteType,
    Assignment,
    Formation,
    DefensePlayer, DefensePosition, DefensiveFormation,
    Situation, Hash, Tempo, FieldZone,
    Play, PlayType, Playbook,
)
from . import templates, catalog, adjustments
from .adjustments import Adjustment
from .builder import PlayBuilder, play as build_play
from .series import (Series, SeriesBuilder, Role, series,
                     SeriesSet, SeriesSetBuilder, series_set)
from .script import Script, ScriptEntry, Period, PracticeScript
from .callsheet import CallSheet, Wristband, STANDARD_BUCKETS
from .renderer import SVGRenderer, PDFExporter

__all__ = [
    "Point", "Player", "Position",
    "Route", "RouteType",
    "Assignment",
    "Formation",
    "DefensePlayer", "DefensePosition", "DefensiveFormation",
    "Situation", "Hash", "Tempo", "FieldZone",
    "Play", "PlayType", "Playbook",
    "PlayBuilder", "build_play",
    "Adjustment", "adjustments",
    "Series", "SeriesBuilder", "Role", "series",
    "SeriesSet", "SeriesSetBuilder", "series_set",
    "Script", "ScriptEntry", "Period", "PracticeScript",
    "CallSheet", "Wristband", "STANDARD_BUCKETS",
    "SVGRenderer", "PDFExporter",
    "templates", "catalog",
]

__version__ = "0.5.0"
