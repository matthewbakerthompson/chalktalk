# Changelog

## 0.4.0 — 2026-09-16

### Designer
- Rebuilt as a canvas-first workspace: the field fills the window, a tool rail
  opens formation, line, defense, library and layer popovers (formations and
  looks picked from thumbnails), a dock holds a contextual inspector strip and a
  bench of player tokens, the play sheet is a drawer, and `Ctrl+K` opens a
  command palette over the whole catalog.
- Layers: hide routes, blocks, motion, the quarterback, reads, the defense, its
  assignments, zones or the title. Exports follow the toggles.
- Look toggle (turf / paper), arrow-key nudging, PNG export.

### Diagrams
- One theme table (`chalktalk/renderer/theme.py`) drives the SVG renderer, the
  PDF exporter and the designer. Two themes: `turf` for the screen, `paper` for
  print.
- New ink: chalk circles with a ring on the ball, dark squares for the defense,
  soft zone areas, a solid line of scrimmage, real sidelines with out of bounds,
  a name plate in the corner.
- Once a play has a yard line the five-yard grid is the real one, the tens are
  numbered and the end zone is drawn.
- `render(theme=..., hide=[...])`, `chalk render --theme --hide`,
  `chalk design --theme`. HTML playbook pages default to paper.

### Defense
- Zone landmarks are handed out by rank, so no two defenders drop to the same
  spot; the two deepest safeties always split the field; fire zone sends five.

### Licence
- PolyForm Noncommercial 1.0.0 (was MIT).

## 0.3.0

Adjustments, scripted series, practice scripts, call sheets and wristbands.
