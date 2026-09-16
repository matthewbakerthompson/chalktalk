# Contributing

The fastest way to help is to add football knowledge. A formation, a route, a
play, or a series is one function — no plumbing required.

## Licence

chalktalk is released under the PolyForm Noncommercial 1.0.0 licence (see
`LICENSE`). By opening a pull request you agree that your contribution is
licensed to the project under those same terms, and that the project may also
offer it under a commercial licence — that is what lets the software stay free
for everyone who is not selling it.

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

## Adding a blocking scheme

`chalktalk/templates/schemes.py`. A scheme takes a `direction` (+1 right, -1
left) and returns `{label: Block}`. Use `_sides(direction)` to get playside and
backside labels rather than hard-coding `RT`/`LT`, so the scheme flips correctly.

Block paths are **never mirrored** by the renderer — the scheme is responsible
for pointing each path the right way. If you find yourself wanting the renderer
to flip a block, the scheme is wrong.

Both members of a double team carry a `COMBO` block naming each other, and
exactly one of them gets `climb=True`. A test enforces both.

## Adding a quarterback action

`chalktalk/templates/qb.py`. An action takes a `direction` where it matters and
returns a `QBPlan` whose path already points the right way — the renderer never
flips it. Set `mesh_at` when the play has an exchange; that is what draws the
ring, and `mesh_point` reads from it rather than guessing at the path.

Reads are receiver labels in order. A test checks that every read in the catalog
names somebody who is on the field *and* running a route, so a progression can
never point at a blocker.

## Adding a coverage

`chalktalk/templates/coverages.py`. A coverage takes a `DefensiveFormation`,
optionally the offensive `Formation`, and a `strength`, and returns a new look
with **every** defender assigned — a parametrized test runs each coverage
against all 23 defensive fronts and fails if anybody is left standing around.

Sort defenders by role (`defense.corners`, `.safeties`, `.linebackers`) rather
than by label, so the call works from any front. Use `match_man` for man
assignments so match-ups stay consistent with the browser's copy of the rule.

A call that only touches the line is a **front**, not a coverage — put it in
`FRONTS` so it can layer over a coverage instead of replacing one.

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
   `Assignment.absolute_waypoints()`; the JS mirrors it in `wpAbs`/`wpRel`. The
   same duplication exists for motion (`_motion_geometry` ↔ `motionGeometry`),
   blocks (`blockAbs`), the quarterback (`drawQB`/`drawReads`), rush paths
   (`defPath`) and man match-ups (`match_man` ↔ `matchMan`, including the order
   the rat is picked in). If you change one, change the other — the designer
   tests will catch you.
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
