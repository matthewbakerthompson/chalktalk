# Contributing

The fastest way to help is to add football knowledge. A formation, a route, a
play, or a series is one function — no plumbing required.

## Setup

```bash
pip install -e ".[dev]"
python -m pytest
```

## Adding a play

Plays live in `gridiron/catalog/` (`passing.py`, `running.py`, `redzone.py`).
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

`gridiron/templates/formations.py` and `defense.py`. Coordinates are yards:
`x` from the center of the field (positive = offense's right), `y` from the line
of scrimmage (negative = backfield for the offense, positive = downfield for the
defense). Every formation needs exactly 11 players with unique labels and 5 linemen.

## Adding a series

`gridiron/catalog/series.py`. A series is a base play plus the calls that punish
over-reaction to it. Always fill in `tell=` — the defensive reaction that makes
the call right. That field is the whole point of a series.

## Adding an adjustment

`gridiron/adjustments.py`. Add a value to `AdjustmentKind`, an `_apply_<kind>`
method on `Adjustment`, and a factory helper. Adjustments must be:

- **serializable** — data only, no callables;
- **immutable** — return a new `Play`, never mutate the input;
- **self-describing** — set a `name` that reads like a real call.

Set `stamp_name=False` if the adjustment writes to a dedicated `Play` field
(protection, tempo, alerts) so it isn't printed twice on the call sheet.

## Style

- Match the surrounding code: type hints, `from __future__ import annotations`,
  pydantic models, no new dependencies without a good reason.
- Terminal output stays ASCII (call sheets get printed on Windows machines in
  press boxes). HTML output can use whatever it likes.
- Football terminology over programmer terminology in anything a coach reads.
