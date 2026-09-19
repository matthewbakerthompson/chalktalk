# Changelog

## 0.8.0

**The game plan.** Plan the week and call the game: a step-by-step plan
builder with scripted drive patterns, a Game panel that follows them from each
result, coded ways to get the call in whose format the key can vary, wristband
inserts at their real size, reads by coverage, and a designer that works on a
phone.

### Plan: the week
- The **Plan** button opens the game-plan builder in seven steps:
  - the game;
  - series and roles;
  - situations, as a grid of plays by call-sheet section;
  - the opening script;
  - drive scripts;
  - calling;
  - a check and the paper.
- **Draft the plan from this book** fills only what is blank, from what the
  plays already say about themselves, and lists every decision. It never
  overwrites the coach's own tags, sections or script, and it can be undone.
  In Python it is `planner.draft`.
- **Drive scripts** (`GamePlan.drives`, `DriveScript`, `ScriptCall`): drive
  patterns scripted in the week.
  - A script covers one set of downs: the 1st-down call, the 2nd-down call on
    and off schedule, then 3rd down under each.
  - Each slot shows where it will be called and lists the book in the
    planner's order for that spot, with points.
  - `fill_script` drafts the empty slots, reading the calls above each one as
    the drive so far.
- Plays carry a series, a role, the tell that calls for them, a line word and
  a difficulty override. `Playbook.game_plan` keeps the plan with the book.
- Every play in a book has a stable id. Books saved before ids existed get them
  on load, in Python and in the designer, and in the same order.
- The plan check flags:
  - a constraint with no base play;
  - a play above the team's level;
  - a missing opening script;
  - 3rd and short with no run;
  - more board symbols than players can learn.
- A staff's own call sheet catches a play added later in Base.
- **Favorites and drive starters.** Star a play (★ beside its name) and the
  planner gives it +2 wherever it fits. Drive starters (`GamePlan.starters`)
  are the go-to first calls of a drive: once the opening script is done they
  get +4 on each drive's first snap.
- Scripts start from any of 13 spots, from backed up on the 3 to the goal line,
  plus two-minute, end of half and four-minute.

### Game: game day
- The **Game** panel (`D`) follows a drive script from each result: "From
  Opening drive: off schedule". The planner's picks sit underneath, and take
  over when the drive leaves the script.
- The planner's picks show their arithmetic:
  - The opening script comes first.
  - A constraint waits until its base play has been shown.
  - A tell the defense showed brings up its answer.
  - A trick is used once.
  - A play that worked gets another look.
- The log marks each snap on or off schedule. The bar is a percent of the
  distance on 1st, 2nd, and 3rd and 4th down:
  - high school 40/50/100
  - college 50/70/100
  - NFL 45/60/100
- Difficulty is an additive score of what a play asks of the players.
  - Tiers: Basic 0-3, Standard 4-7 and Advanced 8+.
  - The planner takes a point off for every point a play scores above what the
    team runs.
  - A tier the coach sets counts as repped.
- Drive cards print the coach's scripts, then the planner's first calls from
  six common starts.

### Calling the plays
- `chalktalk.codes`, twinned in the designer: everything comes from a key
  through HMAC-SHA256, and matching copies print on any machine with a shared
  fingerprint. The key is never saved in the book, the plan or a printout.
- **Wristband numbers:** codes as numbers (47) or a letter and a number (B7).
  Extra codes go to the top calls, dead codes mean "wait", and no code keeps
  its play from one card to the next.
- **Line calls:** a code word per play for the game.
  - The words come from a list (mix, animals, cities, things) or the team's own.
  - A coach can type a word on each play, pick one from the list, or leave it
    to the key.
  - The live signal is a colour, a number or the team's own word, or there is
    none and the key names which of two or three calls counts.
  - Dummy words fill the noise, and burned words become decoys.
- **Sign boards:** one, two or four symbols a board, with one live cell that
  changes every half.
  - The decoys come from the same symbols, and one rack serves the whole game.
  - The symbols are eight outlined shapes in five colour-blind-safe colours.
- **A format the key can vary.** Whatever the coach leaves to the key is drawn
  from the secret, so a team that also uses chalktalk can't assume it:
  - per game: 47 or B7, and two or four symbols a board;
  - per period, never the same twice running: where a dummy digit hides, and
    which of two or three signals is live.
- **Wristbands print as inserts** at the real size of a wrist coach's window
  (youth, teen, adult), with dashed cut lines, capitals, and as many copies as
  players wear.
  - A numbered band fills its inserts in columns under situation headings.
  - A two-character coded band is a grid: first character down the side, last
    digit across the top, blank squares dead.
  - `wristband_html(band, size=..., copies=...)` in Python matches.

### Reads by coverage
- `QBPlan.reads_vs` keeps an order per coverage. `reads_against`,
  `read_order(label, coverage)` and `progression(..., vs=...)` read and set it.
- The designer numbers the reads for the coverage on the field, and so do the
  SVG and the PDF.
- In the play sheet the progression has a coverage picker. **Set reads** on a
  selected quarterback lets the coach tap receivers on the field in order.

### On a phone
- The tools move to a tab bar and open as sheets from the bottom of the
  screen.
- The playbook, the play sheet and the Game panel take the screen, and arrows
  beside the name turn pages.
- Under the diagram are the description, the reads, each player's coaching
  point and the tags.
- Tap to draw, drag to move, double-tap to delete a handle, and pinch to zoom.
- The plan builder works on a phone. Its wide steps say they are easier on a
  tablet or a laptop, and printing points to a computer.
- Exports and paper made on a phone are drawn at desk size.

### Lettering
- The designer, the diagrams and the paper letter in DIN, the type of signs
  and scoreboards. The fonts come from what each platform already has:
  Bahnschrift on Windows, DIN Alternate and DIN Condensed on Apple, and Roboto
  Condensed on Android. Nothing is embedded or fetched. Titles, the situation
  and the big numbers use the condensed cut.

### Fixed
- The game plan's title no longer names the opponent twice.
- Escape closes an open dialog in browsers that don't do it themselves.

## 0.7.0

**The designer goes to the sideline.** An installable web app that opens with
no connection, keeps every play on the coach's own device, and prints the paper
a game needs.

### Web app
- Published at https://matthewbakerthompson.github.io/chalktalk/ by a GitHub Pages workflow. Only
  the built site is public; the repository can stay private.
- `chalk site` (and `chalktalk.designer.site.build_site`) wraps the designer with
  a manifest, generated icons and a service worker for any static host. The
  designer file itself is unchanged and still self-contained.
- Installs from Chrome, Edge, Chromebooks and the iPad home screen, and opens
  offline. A new deploy replaces the cached version from the next launch.

### Your files
- Open and Save work with real files: `Ctrl+O`, `Ctrl+S`, `Ctrl+Shift+S`, a copy
  of one play, or a file dropped on the window. In Chrome, Edge and on
  Chromebooks, Save writes back to the same file, even after a restart. On an
  iPad, Save opens the share sheet; elsewhere it downloads.
- The playbook panel names the file the book belongs to and says whether it
  has unsaved changes; the Save button carries a dot until it's written.

### Paper
- Print (`Ctrl+P`): playbook, call sheet, wristband, practice script and install
  book, built in the browser with Python's stylesheet and call-sheet buckets. A
  test runs the browser's builders in node against `CallSheet`, `Wristband` and
  `Script`.
- The play sheet sets install day, call number and a call-sheet bucket, and the
  situation line names the section the play lands in. Call numbers can be
  written into the plays so every printed sheet agrees.

### Fixed
- Zone drops run to the edge of the zone they own, and each zone carries its
  defender's label, in the SVG, the PDF and the designer. Drops used to stop
  after six yards, which left deep zones floating with no visible owner.

### Licence
- The designer file carries the PolyForm Noncommercial notice, so every copy of
  it carries the terms.

## 0.6.0

**The designer, redrawn.** A canvas-first workspace, playbooks, one theme
table for every diagram, and a noncommercial licence.

### Designer
- Rebuilt as a canvas-first workspace: the field fills the window, a tool rail
  opens formation, line, defense, library and layer popovers (formations and
  looks picked from thumbnails), a dock holds a contextual inspector strip and a
  bench of player tokens, the play sheet is a drawer, and `Ctrl+K` opens a
  command palette over the whole catalog.
- Layers: hide routes, blocks, motion, the quarterback, reads, the defense, its
  assignments, zones or the title. Exports follow the toggles.
- Look toggle (turf / paper), arrow-key nudging, PNG export.
- Playbook mode. The designer holds a book — the same `Playbook` JSON Python
  reads — with a panel of live thumbnails: add, duplicate, delete with undo,
  drag to reorder, `[` and `]` to turn pages. Library concepts fill a blank page
  or join the book. Save writes the book once it has more than one play; Export
  offers the play, the book, and a client-side Print playbook in the paper look.
- Opening a different book stashes the previous working copy; the command
  palette restores it.
- Live route preview: with a player selected, a faint line runs from the end of
  his route to the cursor, labelled with the depth of the next point.
- A start screen on the first open: four featured concepts, the library, a
  file, or a blank formation. `Show the start screen` in the palette brings it back.
- Open a play or playbook file from the start screen, the Import dialog, the
  palette, or by dropping it on the window.
- A quieter bench: the five linemen are one group captioned with their scheme
  ("pass set", "hinge · wrap · down"), and the defense folds into one chip
  naming the look and the call. Opening it is remembered.

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

### Command line
- `chalk design book.json` opens a whole playbook.
- `chalk book book.json` prints a playbook file to PDF or HTML, paper by default.

### Defense
- Zone landmarks are handed out by rank, so no two defenders drop to the same
  spot; the two deepest safeties always split the field; fire zone sends five.

### Licence
- PolyForm Noncommercial 1.0.0 (was MIT).

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
