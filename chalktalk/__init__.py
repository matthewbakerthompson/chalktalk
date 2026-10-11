"""
chalktalk: football plays and playbooks in Python.

Plays are Pydantic models that save as JSON. The library builds plays from
formations, routes, blocking schemes and quarterback actions, draws them as
SVG, PDF and HTML, and makes call sheets, practice scripts, wristbands and
game plans from a playbook. `chalk design` opens the designer in a browser.

    from chalktalk import adjustments as A
    from chalktalk.catalog import passing, series as SR
    from chalktalk.templates import defense as D

    mesh = passing.mesh_concept()
    mesh.render().save("mesh.svg")
    jet = mesh.adjust(A.MOTION("Z", "jet"), A.PROTECTION("Slide Rt"))

    iz = SR.inside_zone_series()
    script = iz.to_script(reps=2).with_looks([D.NICKEL_425(), D.FOUR_THREE_OVER()])
    print(script.table())

Documentation: https://github.com/matthewbakerthompson/chalktalk#readme
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

__version__ = "0.13.0"
DOCS_URL = "https://github.com/matthewbakerthompson/chalktalk#readme"
