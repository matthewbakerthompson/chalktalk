# Contributing

The fastest way to help is to add football knowledge. A formation, a route, a
play, or a series is one function — no plumbing required.

## Setup

```bash
pip install -e ".[dev]"
python -m pytest
```

## Adding a play

Plays live in `chalktalk/catalog/` (`passing.py`, `running.py`, `redzone.py`).
Every entry takes an optional formation override and returns a `Play`:

```python
def dagger(formation: Optional[Formation] = None) -> Play:
    """Dagger — seam clears, dig behind it."""
    f = formation or F.GUN_DOUBLES()
    return (
        _b(f).block_ol()
        .routes(X=R.DIG(stem=12), Y=R.SEAM(), Z=R.FLY(), H=R.CURL(), RB=R.FLAT())
        .name("Dagger")
        .play_type(PlayType.PASS)
        .tag("pass", "dropback", "vertical")
        .describe("Seam runner clears the safety; the dig sits in the vacated window.")
        .build()
    )
```

The test suite picks new plays up automatically and checks that they have 11
assignments, blocking linemen, and render to valid SVG.

## Adding a formation or defensive look

`chalktalk/templates/formations.py` and `defense.py`. Coordinates are yards:
`x` from the center of the field (positive = offense's right), `y` from the line
of scrimmage (negative = backfield for the offense, positive = downfield for the
defense). Every formation needs exactly 11 players with unique labels and 5 linemen.

## Adding a series

`chalktalk/catalog/series.py`. A series is a base play plus the calls that punish
over-reaction to it. Always fill in `tell=` — the defensive reaction that makes
the call right. That field is the whole point of a series.

## Adding an adjustment

`chalktalk/adjustments.py`. Add a value to `AdjustmentKind`, an `_apply_<kind>`
method on `Adjustment`, and a factory helper. Adjustments must be:

- **serializable** — data only, no callables;
- **immutable** — return a new `Play`, never mutate the input;
- **self-describing** — set a `name` that reads like a real call.

Set `stamp_name=False` if the adjustment writes to a dedicated `Play` field
(protection, tempo, alerts) so it isn't printed twice on the call sheet.

## Working on the designer

The designer lives in `chalktalk/designer/app.html`. It is a plain HTML file
with no build step and no dependencies; `chalktalk/designer/__init__.py` inlines
the catalog into it at build time.

```bash
chalk design                                  # build and open it
chalk design --out docs/index.html --no-open  # refresh the demo page
```

Two rules keep it honest:

1. **The browser and Python must agree on geometry.** Routes are stored relative
   to the player and mirrored for left-side players. Python applies that in
   `Assignment.absolute_waypoints()`; the JS mirrors it in `wpAbs`/`wpRel`. Motion
   geometry is duplicated the same way (`_motion_geometry` in
   `chalktalk/adjustments.py`, `motionGeometry` in the app). If you change one,
   change the other — `tests/test_designer_and_field.py` will catch you.
2. **Commit `docs/index.html` when the app changes.** CI rebuilds it and fails if
   it drifts from the source.

The designer must stay a single self-contained file: no CDN, no `fetch`, no
external assets. A test enforces that too.

## Style

- Match the surrounding code: type hints, `from __future__ import annotations`,
  pydantic models, no new dependencies without a good reason.
- Terminal output stays ASCII (call sheets get printed on Windows machines in
  press boxes). HTML output can use whatever it likes.
- Football terminology over programmer terminology in anything a coach reads.
