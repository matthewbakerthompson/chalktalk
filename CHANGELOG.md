# Changelog

## 0.5.0

**Series sets** — several series treated as one offense.

- `SeriesSet` groups series with an install week and a priority, and rolls them
  up: `install()` (every base before anybody's constraints), `to_script()`,
  `to_practice()` (one period per series), `to_call_sheet()`, `to_playbook()`,
  and an install-book HTML export.
- `balance()` reports run/pass, personnel spread, roles, and **answers per
  base**; `gaps()` reports what the system cannot answer yet — a base with no
  constraint, a series with nothing over the top, a one-sided set.
- Three new series: play action, screens, short yardage — the first two cover
  the plays added in 0.4.0, which the series catalog had not caught up with.
- Four stock systems in `catalog.systems`: base offense, spread, pro style and
  a one-week game plan.
- CLI: `chalk list systems`, `chalk system <name> --balance --out <dir>`.

## 0.4.0

**The catalog got the plays it was missing.** 37 concepts → 54.

- **Play action and the movement game** (`catalog.playaction`): boot, waggle,
  naked, keeper, PA cross, PA dagger, and a max-protect shot play. The catalog
  previously contained zero play-action passes despite having the machinery for
  them.
- **The screen game** (`catalog.screens`): RB slip, tunnel, bubble, jailbreak,
  middle, TE leak. `PlayType.SCREEN` existed and was unused.
- **RPOs** (`catalog.rpo`): bubble, glance, slant, pop and a gap-scheme arrow,
  each reading a different defender.
- **Left-handed formations**: eight new ones, built by mirroring rather than
  retyping coordinates, so the two sides cannot drift.
- `Formation.mirror()` and `Formation.player()`; `flip_side_name()` is now the
  one definition of the left/right name swap.
- One catalog registry: `catalog.play_builders()` and `catalog.all_plays()`.
  The CLI, the designer and the test sweep all read through it, so a new module
  is picked up everywhere at once.

Fixed: `screens.bubble` and `rpo.bubble` collided in the registry and silently
lost one of them — plays are keyed by bare name, and a test now enforces that
names are unique across modules. `Q.BOOT` was missing its mesh point.

Moved: `passing.rpo_bubble` → `rpo.bubble`.

## 0.3.x

- **Quarterback**: `QBPlan` with 11 actions, mesh points, and read progressions
  drawn as numbered discs. Fixed under-center formations that had the
  quarterback at shotgun depth with the backs ten yards deep.
- **Defense**: `DefensiveAssignment` with 9 roles and 11 zones, 10 coverages
  and a front, zone landmarks computed from the field spec and the hash. Fixed
  duplicate defensive labels that made label-keyed assignments overwrite each
  other, and two arrowhead markers that were referenced but never defined.
- **Blocking**: `Block` with 15 kinds and 14 whole-line schemes, drawn in
  playbook notation. Before this every lineman got an identical stub the
  renderer then skipped, so power, counter and zone drew as the same diagram.
- **Field levels**: NFL, college and high school hashes, switchable everywhere.
  The renderer had been using the college hash *separation* as a distance from
  the middle of the field.
- **The designer**: a single self-contained HTML file — drag players, draw
  routes, apply schemes and coverages, build progressions.
- Renamed from `gridiron` to `chalktalk` (the PyPI name was squatted).

## 0.1.0

Models, 32 formations, 23 defensive looks, 30 routes, 37 plays, adjustments,
scripted series, practice scripts, call sheets, wristbands, SVG and PDF output.
