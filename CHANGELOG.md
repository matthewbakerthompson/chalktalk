# Changelog

## 0.11.0

**What the half says about you.** The game log now reads back as a self-scout:
the numbers, the tendencies a scout would see, and what the staff has left.

### Self-scout
- `chalktalk.scout.report` counts the log back, with the plan's own thresholds:
  - snaps on schedule, overall and by down, with yards a call;
  - third downs converted;
  - explosive plays, 12 yards running and 16 throwing;
  - what is working, by yards a call;
  - your looks, run against pass.
- A tendency is four calls from one formation with eight in ten the same kind,
  and it is written the way a scout would put it: "From I-Form Pro Right you
  have run 6 of 6: a scout sees it."
- It also lists what is set up and not called (a series whose base has been
  shown), and what is left: the opening script, the drive starters, the
  favorites.
- The **Halftime** section in the Game panel shows it while the half is going
  on, and the **Halftime sheet** prints it in two columns.
- The designer carries a twin, held to Python by a test.

## 0.10.0

**Twenty-four more plays.** The catalog goes from 54 concepts to 78, each one
function, tagged so the plan draft puts it in the right series and on the right
part of the call sheet.

### Catalog
- **Runs:**
  - Duo
  - Split Zone
  - Buck Sweep (both guards pull)
  - Pin Pull
  - Power Read
  - Speed Option, the first stock play with a pitch read
  - QB Counter
  - QB Draw
  - Toss Crack
- **Dropback:**
  - Shallow Cross
  - Dagger
  - China
  - Post Wheel
  - Hank
  - Double Post
  - Seam/Flat
  - Mills
- **Play action:** Post Wheel off power action.
- **Screens:** Swing and Double Screen.
- **RPOs:** Stick and Now, both off inside zone.
- **Scoring zone:**
  - Goal Line Leak (a dive fake with the tight end leaking behind the flow)
  - Fade/Out
- Difficulty across the catalog: 64 Basic and 14 Standard.

## 0.9.0

**Plan the week, call the game.** A step-by-step plan builder with scripted
drive patterns, a Game panel that follows them from each result, coded calls
whose format the key can vary, wristband inserts at their real size, reads by
coverage, favorites, and DIN lettering.

### Plan: the week
- The **Plan** button opens the game-plan builder in seven steps:
  - the game;
  - series and roles;
  - situations, as a grid of plays by call-sheet section;
  - the opening script and the drive starters;
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
  - `fill_script` drafts the empty slots.
  - Scripts start from any of 13 spots, from backed up on the 3 to the goal
    line, plus two-minute, end of half and four-minute.
- **Favorites and drive starters.**
  - Star a play (★ beside its name) and the planner gives it +2 wherever it
    fits.
  - Drive starters (`GamePlan.starters`) are the go-to first calls of a drive.
    Once the opening script is done they get +4 on each drive's first snap.
- A staff's own call sheet puts a play added later in Base.

### Game: game day
- The drawer is now the **Game** panel (`D`). It follows a drive script from
  each result ("From Opening drive: off schedule"), with the planner's picks as
  the other options. `planner.follow` does the same in Python.
- Drive cards print the coach's scripts, then the planner's first calls from
  six common starts.

### Calling the plays
- **A format the key can vary.** Two teams on chalktalk know every format, so
  whatever a coach leaves to the key is drawn from the secret:
  - per game: codes as 47 or B7, and two or four symbols a board;
  - per period, never the same twice running: where a dummy digit hides in
    the signal, and which of two or three signals is live.
- **Line calls from the team's own words.**
  - The words come from a list (mix, animals, cities, things; 144 in all) or
    the team's own.
  - A coach can type each play's word, pick it from the list, or fill the
    blanks from the list.
  - The live signal is a colour, a number or the team's own word, or there is
    none and the key names which of two or three calls counts.
- **Wristbands print as inserts** at the real size of a wrist coach's window
  (youth 3.75 x 2.25 in, teen 5 x 2.75, adult 5.25 x 3.25), with dashed cut
  lines, capitals, and as many copies as players wear.
  - A numbered band fills its inserts in columns under situation headings.
  - A two-character coded band is a grid: first character down the side, last
    digit across the top, blank squares dead.
  - `wristband_html(band, size=..., copies=...)` matches in Python.

### Reads by coverage
- `QBPlan.reads_vs` keeps an order per coverage. `reads_against`,
  `read_order(label, coverage)` and `progression(..., vs=...)` read and set it.
- The designer numbers the reads for the coverage on the field, and so do the
  SVG and the PDF.
- In the play sheet the progression has a coverage picker. **Set reads** on a
  selected quarterback lets the coach tap receivers on the field in order.

### On a phone
- The Game panel is the part to use on a phone: it takes the whole screen and
  works one-handed.
- The plan builder works on a phone too. Its wide steps say they are easier on
  a tablet or a laptop, the script tree stacks in reading order, and printing
  points to a computer.

### Lettering
- The designer, the diagrams and the paper letter in DIN, the type of signs
  and scoreboards, in place of Inter. The fonts are ones each platform already
  has: Bahnschrift on Windows, DIN Alternate and DIN Condensed on Apple, and
  Roboto Condensed on Android. Nothing is embedded or fetched. Titles, the
  situation and the big numbers use the condensed cut.

### Fixed
- `Play.with_formation()`, and so `A.FORMATION`, carries every job across by
  player label: blocks, the quarterback's plan, motion and notes as well as
  routes and the ball carrier. It used to keep only routes, so Power from a new
  formation went from nine blocks and a handoff to nothing at all.
- Nothing is left pointing at a player who isn't there. Reads on players the
  new formation doesn't have are dropped, and so is a mesh with a missing back.
  The quarterback's footwork and mesh point stay as drawn.
- Paths go across unchanged. A route is still mirrored when its player lines up
  on the left; a block path never is.
- Motion starts from the player's new spot. It is kept if he lines up where he
  did, a preset (jet, orbit, ...) is run again from his new alignment, and
  anything else (a shift, a hand-placed start) is dropped rather than drawn from
  the old formation.
- The designer's formation picker follows the same rules and no longer drops
  the quarterback's plan. A node test holds it to the Python.

## 0.8.0

**The game plan.** Plays tagged with their jobs, a drive planner to rehearse
with during the week, three coded ways to get the call in, and a designer that
works on a phone.

### Game plan
- Plays carry a series, a role in it (base, complement, constraint,
  play-action, shot, trick, answer), the tell that calls for them, a line word
  and a difficulty override. `Playbook.game_plan` keeps the week's plan with
  the book: the level, what the team runs, the call-sheet sections, the
  opening script, how calls get in, and the drive log.
- Every play in a book has a stable id. Books saved before ids existed get them
  on load, in Python and in the designer, and in the same order.
- `chalktalk.planner` sorts the book into sections (down and distance, field
  zones, two- and four-minute) and checks the plan. It flags a constraint with no
  base play, a play above the team's level, no opening script, 3rd and short
  with no run, and too many board symbols to learn.

### Drive planner
- The Drive tab (`D`) rehearses a drive: set the situation, read the next three
  calls with every point explained, call one, tap what happened. Each call
  says what follows a gain and what follows no gain. The script comes first;
  a constraint waits until its base play has been shown; a tell the defense
  showed brings up its answer; a trick is used once; and a play that worked
  gets another look.
- The log marks each snap on or off schedule. The bar depends on the level:
  high school 40/50/100, college 50/70/100, NFL 45/60/100 (percent of the
  distance on 1st, 2nd, and 3rd and 4th down).
- Difficulty: an additive score from what a play asks of the players (motion,
  reads, progression, pullers, screen timing, tags, alerts, checks at the line),
  with tiers Basic 0-3, Standard 4-7 and Advanced 8+. The planner takes a point
  off for every point a play scores above what the team runs, and a tier the
  coach sets counts as repped.
- Print drive cards (the first calls from six common starts), the staff game
  plan, the QB card and sign boards.

### Calling the plays
- `chalktalk.codes`, twinned in the designer: everything comes from a key
  through HMAC-SHA256, so matching copies print on any machine with a shared
  fingerprint. The key is never saved in the book, the plan or a printout.
- Wristband numbers: fresh cards every half (or quarter, or game), extra codes
  for the top calls, dead codes, and no code keeps its play from one card to
  the next.
- Line calls: a code word per play for the game, a live colour that changes
  every half ("Blue... Tiger": only the live colour's call is real), dummy
  words, and burned words that become decoys.
- Sign boards: two or four symbols a board with one live cell that changes
  every half, decoys from the same symbols, and one rack for the whole game.
  Eight outlined shapes in five colours that stay distinct for colour-blind
  players. Prints the rack, the players' key and the signaler's sheet, with how
  far the boards read.

### On a phone
- The tools move to a tab bar, and each opens as a sheet from the bottom of
  the screen. The playbook, the play sheet and the drive planner take the
  screen, and arrows beside the name turn pages. Under the diagram are the
  description, the reads, each player's coaching point and the tags.
- Tap to draw, drag to move, double-tap to delete a handle, and pinch to zoom
  in on the line. On its side the phone gives the field the height. Hints say
  tap where a mouse would click.
- Exports and paper made on a phone are drawn at desk size.

### Fixed
- The game plan's title no longer names the opponent twice ("Wk 3 vs Central
  vs Central").
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
