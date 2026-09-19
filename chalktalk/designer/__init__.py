"""
chalktalk.designer — the visual play designer.

Builds a single self-contained HTML file: the app template with the whole
catalog (formations, routes, defensive looks, stock plays, field specs) inlined
as JSON. No server, no build step, no network. Open it and drag players.

The designer reads and writes the exact `Play` schema the Python side uses, so
a play drawn in the browser loads straight back:

    chalk design                       # open the designer
    chalk design mesh.json             # open it on an existing play
    chalk design book.json             # or on a whole playbook
    chalk design --out docs/index.html --no-open

    >>> Play.from_json(open("mesh.json").read())
"""
from __future__ import annotations

import inspect
import json
import os
from typing import Optional

from ..models.play import Play, Playbook
from ..models.situation import Hash

_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.html")

DEFAULT_FORMATION = "SHOTGUN_TRIPS_RIGHT"


def _uppercase_builders(module) -> dict:
    return {
        name: fn for name, fn in inspect.getmembers(module, inspect.isfunction)
        if name.isupper() and fn.__module__ == module.__name__
    }


def catalog() -> dict:
    """Everything the browser app needs, as plain JSON-able data."""
    from .. import catalog as play_catalog
    from ..models.field import FIELDS
    from ..templates import (blocking as BL, coverages as CV, defense as D,
                             formations as F, qb as QB, routes as R,
                             schemes as SC)
    from ..models.defense import DefensiveRole, Zone, _ZONE_GEOMETRY
    from ..adjustments import _MOTION_PRESETS
    from ..renderer.theme import LAYERS, themes_json
    from ..renderer.sheets import _CSS as SHEET_CSS
    from ..callsheet import STANDARD_BUCKETS
    from .. import codes as K, difficulty as DF, planner as PL
    from ..models import gameplan as GP

    plays = {name: play.model_dump(mode="json")
             for name, play in play_catalog.all_plays().items()}

    return {
        "fields": {
            level.value: {
                "name": spec.name,
                "hash_from_center": round(spec.hash_from_center, 3),
                "hash_separation": round(spec.hash_separation, 3),
                "numbers_from_sideline": spec.numbers_from_sideline,
                "width": round(spec.width, 3),
                "boundary": round(spec.boundary_width(Hash.LEFT), 2),
                "field_side": round(spec.field_width(Hash.LEFT), 2),
            }
            for level, spec in FIELDS.items()
        },
        "routes": {name: fn().model_dump(mode="json")
                   for name, fn in _uppercase_builders(R).items()},
        "formations": {name: fn().model_dump(mode="json")
                       for name, fn in _uppercase_builders(F).items()},
        "defenses": {name: fn().model_dump(mode="json")
                     for name, fn in _uppercase_builders(D).items()},
        "plays": plays,
        "blocks": {
            name: {str(d): _block_sample(fn, d).model_dump(mode="json")
                   for d in (1, -1)}
            for name, fn in _uppercase_builders(BL).items()
        },
        "schemes": {
            name: {
                str(d): {label: block.model_dump(mode="json")
                         for label, block in _scheme_for(fn, d).items()}
                for d in (1, -1)
            }
            for name, fn in SC.SCHEMES.items()
        },
        "protections": sorted(SC.PROTECTIONS),
        "coverages": sorted(CV.COVERAGES),
        "fronts": sorted(CV.FRONTS),
        "pressures": sorted(CV.PRESSURES),
        "zones": {
            z.value: {
                "name": z.display,
                "base_x": geom[0], "depth": geom[1],
                "half_w": geom[2], "half_h": geom[3],
                "deep": z.is_deep,
            }
            for z, geom in _ZONE_GEOMETRY.items()
        },
        "def_roles": [r.value for r in DefensiveRole],
        # Coverage calls, precomputed per defensive look. Paths are left out —
        # the browser rebuilds them with the same formulas — and man match-ups
        # are filled in against whatever offense is on the field.
        "coverage_calls": _coverage_calls(),
        "motions": list(_MOTION_PRESETS),
        "qb_actions": {
            name: {str(d): _qb_sample(fn, d).model_dump(mode="json")
                   for d in (1, -1)}
            for name, fn in QB.ACTIONS.items()
        },
        "default_formation": DEFAULT_FORMATION,
        "themes": themes_json(),
        # The browser prints the same sheets Python does: same stylesheet,
        # same situational buckets, in the same order.
        "sheet_css": SHEET_CSS,
        "call_sheet_buckets": [[title, sit.model_dump(mode="json")]
                               for title, sit in STANDARD_BUCKETS.items()],
        # The drive planner's tables, so the browser ranks plays by the same rules.
        "plan": {
            "defaults": GP.GamePlan().model_dump(mode="json"),
            "sections": [s.model_dump(mode="json") for s in GP.DEFAULT_SECTIONS],
            "zones_with_downs": sorted(GP.ZONES_WITH_DOWNS),
            "mode_labels": {k: v.value for k, v in GP.MODE_LABELS.items()},
            "openers_label": GP.OPENERS_LABEL,
            "success_by_level": {k.value: list(v) for k, v in GP.SUCCESS_BY_LEVEL.items()},
            "kind_points": PL.KIND_POINTS,
            "card_starts": [[t, st.model_dump(mode="json")] for t, st in PL.DRIVE_CARD_STARTS],
            "roles": [r.value for r in GP.Role],
        },
        "difficulty": {"rubric": DF.RUBRIC, "tiers": list(DF.TIERS),
                       "tier_names": DF.TIER_NAMES, "team_levels": DF.TEAM_LEVELS},
        "codes": {"alphabet": K.KEY_ALPHABET, "salt": K.SALT.decode(),
                  "iterations": K.ITERATIONS, "periods": K.PERIODS,
                  "board_shapes": K.BOARD_SHAPES, "board_colors": K.BOARD_COLORS,
                  "board_memory": K.BOARD_MEMORY, "live_colors": K.LIVE_COLORS,
                  "words": K.WORDS},
        "layers": list(LAYERS),
    }


def _coverage_calls() -> dict:
    """
    {defense name: {coverage: {label: assignment}}} with paths stripped.

    Zone landmarks and man match-ups are the parts the browser cannot work out
    for itself; rush and blitz paths are pure formulas, so they are rebuilt on
    the other side rather than shipped eleven times per look.
    """
    from ..templates import coverages as CV, defense as D

    out: dict[str, dict] = {}
    for name, build in _uppercase_builders(D).items():
        look = build()
        calls: dict[str, dict] = {}
        for coverage_name, coverage in {**CV.COVERAGES, **CV.FRONTS}.items():
            assigned = coverage(look)
            calls[coverage_name] = {
                p.label: {
                    k: v for k, v in p.assignment.model_dump(mode="json").items()
                    # Stunt loops are hand-shaped; everything else is a formula.
                    if k != "path" or p.assignment.role.value == "stunt"
                }
                for p in assigned.players if p.assignment
            }
            calls[coverage_name]["__meta__"] = {
                "coverage": assigned.coverage, "pressure": assigned.pressure,
            }
        out[look.name] = calls
    return out


def _qb_sample(fn, direction: int):
    """One quarterback plan per action for the picker."""
    params = inspect.signature(fn).parameters
    kwargs = {}
    if "direction" in params:
        kwargs["direction"] = direction
    return fn(**kwargs)


def _block_sample(fn, direction: int):
    """
    Build one block for the picker. Most constructors take `direction` first,
    but a few (BASE, COMBO) lead with something else.
    """
    params = inspect.signature(fn).parameters
    kwargs = {}
    if "direction" in params:
        kwargs["direction"] = direction
    if "partner" in params:
        kwargs["partner"] = ""
    return fn(**kwargs)


def _scheme_for(fn, direction: int) -> dict:
    """Build a scheme for a direction, tolerating the ones that take no argument."""
    try:
        return fn(direction)
    except TypeError:
        return fn()


def _compact(obj):
    """
    Drop nulls and round the float noise out of the inlined catalog.

    Pydantic fills the defaults back in on the way home, and the browser reads
    everything through optional access, so nothing is lost but bytes — and the
    catalog is most of the file.
    """
    if isinstance(obj, dict):
        return {k: _compact(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_compact(v) for v in obj]
    if isinstance(obj, float):
        rounded = round(obj, 2)
        return int(rounded) if rounded == int(rounded) else rounded
    return obj


def _json_for_script(obj) -> str:
    """JSON safe to inline inside a <script> block."""
    return (json.dumps(_compact(obj), separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def build(play: Optional[Play] = None, level: str = "nfl",
          theme: str = "turf",
          playbook: Optional[Playbook] = None) -> str:
    """
    Return the designer as one self-contained HTML string, optionally opened
    on a play or on a whole playbook.
    """
    with open(_TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    html = html.replace("/*__CATALOG__*/{}", _json_for_script(catalog()), 1)
    if play is not None:
        html = html.replace("/*__PLAY__*/null",
                            _json_for_script(play.model_dump(mode="json")), 1)
    if playbook is not None:
        html = html.replace("/*__BOOK__*/null",
                            _json_for_script(playbook.model_dump(mode="json")), 1)
    if level != "nfl":
        html = html.replace('let level = "nfl";', f'let level = "{level}";', 1)
    if theme != "turf":
        html = html.replace('let look = "turf";', f'let look = "{theme}";', 1)
    return html


def write(path: str, play: Optional[Play] = None, level: str = "nfl",
          theme: str = "turf",
          playbook: Optional[Playbook] = None) -> str:
    """Write the designer to `path` and return the absolute path."""
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build(play=play, level=level, theme=theme, playbook=playbook))
    return path


def open_in_browser(path: str) -> None:
    import webbrowser
    webbrowser.open(f"file:///{os.path.abspath(path).replace(os.sep, '/')}")


__all__ = ["build", "write", "catalog", "open_in_browser", "DEFAULT_FORMATION"]
