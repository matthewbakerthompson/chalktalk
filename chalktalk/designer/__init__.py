"""
chalktalk.designer — the visual play designer.

Builds a single self-contained HTML file: the app template with the whole
catalog (formations, routes, defensive looks, stock plays, field specs) inlined
as JSON. No server, no build step, no network. Open it and drag players.

The designer reads and writes the exact `Play` schema the Python side uses, so
a play drawn in the browser loads straight back:

    chalk design                       # open the designer
    chalk design mesh.json             # open it on an existing play
    chalk design --out docs/index.html --no-open

    >>> Play.from_json(open("mesh.json").read())
"""
from __future__ import annotations

import inspect
import json
import os
from typing import Optional

from ..models.play import Play
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
    from ..catalog import passing, redzone, running
    from ..models.field import FIELDS
    from ..templates import (blocking as BL, defense as D, formations as F,
                             routes as R, schemes as SC)
    from ..adjustments import _MOTION_PRESETS

    plays: dict[str, dict] = {}
    for module in (passing, running, redzone):
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_") or fn.__module__ != module.__name__:
                continue
            plays[name] = fn().model_dump(mode="json")

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
        "motions": list(_MOTION_PRESETS),
        "default_formation": DEFAULT_FORMATION,
    }


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


def _json_for_script(obj) -> str:
    """JSON safe to inline inside a <script> block."""
    return (json.dumps(obj, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def build(play: Optional[Play] = None, level: str = "nfl") -> str:
    """Return the designer as one self-contained HTML string."""
    with open(_TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    html = html.replace("/*__CATALOG__*/{}", _json_for_script(catalog()), 1)
    if play is not None:
        html = html.replace("/*__PLAY__*/null",
                            _json_for_script(play.model_dump(mode="json")), 1)
    if level != "nfl":
        html = html.replace('let level = "nfl";', f'let level = "{level}";', 1)
    return html


def write(path: str, play: Optional[Play] = None, level: str = "nfl") -> str:
    """Write the designer to `path` and return the absolute path."""
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build(play=play, level=level))
    return path


def open_in_browser(path: str) -> None:
    import webbrowser
    webbrowser.open(f"file:///{os.path.abspath(path).replace(os.sep, '/')}")


__all__ = ["build", "write", "catalog", "open_in_browser", "DEFAULT_FORMATION"]
