# chalktalk

**Design football plays in a browser. Keep them as code.**

A visual play designer and a Python library that share one file format. Drag
players and draw routes on screen, or generate a hundred variants in a loop —
either way you get the same JSON, and the same diagrams, call sheets, practice
scripts and wristbands come out the other end.

The designer is a single HTML file — `docs/index.html` in this repo. Open it
locally, or serve `docs/` with GitHub Pages for a live version.

```bash
chalk design                 # open the designer
chalk demo --out out/        # one of everything: playbook, call sheet, wristband
```

```python
from chalktalk import adjustments as A
from chalktalk.catalog import passing
from chalktalk.templates import routes as R

mesh = passing.mesh_concept()
mesh.render(level="hs").save("mesh.svg")     # high school hashes

# Alts are data, not clicks
third_down = mesh.adjust(
    A.PROTECTION("Slide Rt"),
    A.MOTION("Z", "jet"),
    A.TAG("Y", R.CORNER()),
    A.ALERT("Alert Fade vs press"),
)
print(third_down.call)
# Shotgun Trips Right Mesh Concept Slide Rt Z Jet Y Corner
```

---

## Why

Every football design tool on the market is closed and rented: Hudl Play Tools
($199 on top of a ~$900 video subscription), FirstDown PlayBook (~$60–80/mo),
Pro Quick Draw ($199+/yr), Just Play (enterprise quote). They draw plays well.
None of them let you *program* your playbook, and none of them let you own the file.

The open-source side is nearly empty — one Qt desktop app, and analytics libraries
that read play-by-play data but can't draw a play.

`chalktalk` fills that gap, and covers the parts coaches actually spend Sunday
night on: **scripted series, install plans, practice scripts, call sheets, and
wristbands** — generated from the same source of truth so the numbers always agree.

---

## Install

```bash
git clone https://github.com/matthewbakerthompson/chalktalk
cd chalktalk
pip install -e .
```

Requires Python 3.10+. Two dependencies: `pydantic` and `reportlab` (PDF export).
The designer has none — it is one HTML file with no network calls.

---

## What's in the box

| | |
|---|---|
| **32 formations** | Shotgun, pistol, I-form, empty, bunch, trips, quads, wildcat, jumbo, goal line |
| **23 defensive looks** | 4-3, 3-4, nickel, dime, quarter, bear, 46, fire zone, cover-2 Tampa, goal line |
| **30 named routes** | Full route tree plus red-zone specialties (fade, back-shoulder, sail, bubble) |
| **37 stock plays** | Mesh, smash, flood, levels, snag, four verts, inside/outside zone, power, counter, RPOs |
| **6 scripted series** | Inside zone, power/counter, mesh, sprint-out, red zone, two-minute |
| **12 quarterback actions** | Drops, play action, boot, sprint, mesh, handoff, draw, pitch, option, keep, sneak — with read progressions |
| **10 coverages + fronts** | Cover 0-6, Tampa 2, fire zone, zero blitz, line games — with zone drops, man match-ups and blitz paths |
| **14 blocking schemes** | Inside/outside zone, power, counter, trap, iso, plus slide, half-slide, big-on-big, sprint and boot protections |
| **12 adjustment types** | Motion, shift, tag, flip, formation, protection, tempo, alert, max protect, release, play action, personnel |
| **3 field levels** | NFL, college and high school hashes — switchable everywhere |
| **Visual designer** | Single-file browser app: drag players, draw routes, round-trips the same JSON |
| **Renderers** | SVG, multi-page PDF playbooks, printable HTML call sheets / scripts / wristbands, CSV |

---

## The four building blocks

### 1. Formations and plays

```python
from chalktalk.catalog import passing, running, redzone
from chalktalk.templates import formations as F

iz = running.inside_zone()                              # stock play
iz_gun = running.inside_zone(formation=F.GUN_DOUBLES()) # same concept, new look
smash_left = passing.smash().mirror()
```

Or build your own with the fluent builder:

```python
from chalktalk import build_play
from chalktalk.templates import routes as R, formations as F
from chalktalk.models import PlayType

play = (
    build_play(F.SHOTGUN_TRIPS_RIGHT())
    .block_ol()
    .routes(X=R.FLY(), Y=R.FLAT(), Z=R.MESH(), H=R.MESH(depth=6), RB=R.SWING())
    .name("Mesh").play_type(PlayType.PASS).tag("mesh", "third-down")
    .build()
)
```

### 2. Adjustments — the alts, as data

Every alt is a small serializable object, so a variant is just *base + adjustments*.
It prints itself onto the call sheet and diffs cleanly in git.

```python
from chalktalk import adjustments as A

mesh.adjust(A.MOTION("Z", "jet"))          # jet, orbit, across, return, short, out, in
mesh.adjust(A.SHIFT("Y", -7.0, 0.0))       # trade the tight end
mesh.adjust(A.FLIP())                      # mirror; "Right" becomes "Left"
mesh.adjust(A.MAX_PROTECT("RB"))           # keep the back in
mesh.adjust(A.PLAY_ACTION("RB"))           # add the fake, force max protection
mesh.adjust(A.TEMPO("no_huddle"))

# Generate a whole family at once
A.variants(mesh, A.FLIP(), A.MOTION("Z", "jet"), A.MAX_PROTECT())
A.matrix(mesh, [A.FLIP()], [A.MOTION("Z", "jet"), A.MOTION("H", "orbit")])
```

Motion is drawn on the diagram: a dashed trail from the pre-snap alignment,
a ghosted starting position, and the snap position moved for full-speed motions.

### 3. Scripted series — the way offenses are actually built

A base play plus every call that punishes over-reaction to it. Each entry
records the **tell**: what you see that makes it the right call.

```python
from chalktalk.series import series
from chalktalk.catalog import running, passing

iz = (
    series("Inside Zone Series", "Everything off the same mesh point")
    .base(running.inside_zone(), note="Track the double team")
    .constraint(running.speed_sweep(), tell="Backside LB fast-flowing inside")
    .play_action(passing.y_cross().adjust(A.PLAY_ACTION("RB")),
                 tell="Safeties triggering downhill")
    .shot(passing.four_verticals(), tell="Single high, FS cheating the box")
    .build()
)

print(iz.describe())
iz.install(days=3)          # teaching progression
iz.to_script(reps=2)        # practice script
iz.render_all("out/iz")     # one SVG per play
```

Six stock series ship in `chalktalk.catalog.series`.

### 4. Scripts, call sheets, wristbands

```python
from chalktalk.script import Script, PracticeScript
from chalktalk.callsheet import CallSheet, Wristband
from chalktalk.models import situation as S
from chalktalk.templates import defense as D

openers = (
    Script(name="Opening 15", opponent="Central")
    .add(passing.mesh_concept(), S.FIRST_TEN, looks=[D.NICKEL_425()])
    .add(running.inside_zone(), S.SECOND_MEDIUM)
    .alternate_hashes()
)
print(openers.table())
print(openers.balance())     # run/pass split, personnel distribution

practice = (
    PracticeScript(name="Tuesday", team="Riverside HS")
    .add_period("Inside Run", iz.to_script(), minutes=12, focus="Zone tracks")
    .add_period("7-on-7", mesh_series.to_script(reps=2), minutes=15)
)

sheet = CallSheet.from_playbook(playbook, name="Week 3").number()
band = Wristband.from_call_sheet(sheet)     # numbers match the call sheet
sheet.save_html("out/call_sheet.html")
band.save_html("out/wristband.html")
```

`Situation` models down, distance, field zone, hash, tempo and clock, so plays
bucket themselves onto the sheet:

```python
S.Situation(down=3, distance=5, yard_line=32).describe()
# '3rd & 5, Opp 32'
S.Situation.own(25)      # ball on our 25
S.Situation.opp(8).zone  # FieldZone.LOW_RED
```

---

## Blocking

A route says where a receiver runs; a block says who a lineman has and how he
gets there. They are different shapes — a puller goes backwards before he goes
forwards, a combo is two players on one defender before one climbs — so blocking
is its own model, drawn in playbook notation: a bar across the end of an engaged
block, a curve behind the line for a puller, a bracket under a double team.

```python
from chalktalk.templates import schemes as S, blocking as B

play.with_scheme(S.power(+1), protection="Power Rt")   # whole line at once
play.with_block("LG", B.WRAP(+1, target="M"))          # one man
```

```bash
chalk list schemes
```

Schemes take a direction — `+1` right, `-1` left — and work out playside and
backside for you, so `S.counter(-1)` swaps which guard kicks and which tackle
wraps. Every catalog run play now carries a real scheme, which is why power,
counter and inside zone finally draw as three different plays.

**One rule to know:** routes are authored right-side and mirrored for left-side
players; **block paths are never mirrored**. A pull to the right is a pull to the
right whether the left guard or the right guard is doing it. `Play.mirror()`
flips blocks explicitly through `Block.mirrored()`.

---

## The quarterback

Everyone else had an assignment; he had a dot. Now the play says what he does —
the drop that sets the timing, the mesh point where it gets decided, and the
order he works the progression.

```python
from chalktalk.templates import qb as Q

play.with_qb(Q.GUN(3, reads=["Y", "H", "Z", "RB"],
                   rule="High-low the flat defender, then work the mesh"))
play.with_qb(Q.PLAY_ACTION(+1, back="RB", steps=5))
play.with_qb(Q.MESH(+1, back="RB", key="the backside end"))
play.progression("Z", "Y", "RB")          # reorder without touching the rest
```

```bash
chalk list qb
chalk show mesh_concept
```

Reads are drawn as numbered discs at each route's catch point, so a diagram
shows *1, 2, 3* instead of five routes and no instructions. `play.read_order("Z")`
gives you the same thing as data.

Run actions mark the **mesh point** — the exchange — with a ring, which is what
makes a zone read or an RPO legible: the ride, the ring, and the defender being
read.

Fixed along the way: every under-center formation had the quarterback at
shotgun depth with the backs stacked ten yards deep. He is under center now,
and the backfield sits where it belongs.

---

## Defense

A defensive look used to be eleven dots. Now every defender has a job: a gap to
rush, a receiver to travel with, or a spot on the grass to get to.

```python
from chalktalk.templates import coverages as C, defense as D

play.vs(D.NICKEL_425(), C.cover_3)         # attach a look and a call
play.with_coverage(C.cover_1)              # man, matched to this play's receivers
C.line_game(C.cover_3(look))               # a front layered over a coverage
```

```bash
chalk list coverages
chalk render mesh_concept -d NICKEL_425 --coverage cover_3 -o mesh.svg
```

Zone drops are drawn as a short arrow toward the landmark with the area behind
it; man coverage draws a line to the receiver; rushers get an arrow into the
backfield. **Zones move with the ball** — a landmark is computed from the field
spec and the hash the play is run from, so the boundary flat really is a smaller
area than the field flat.

Man coverage needs to know who is on the field, which is why `with_coverage`
passes the play's own formation: corners take the widest receiver on their own
side, working inside from there, and any spare defender becomes a rat in the
hole (or a rusher, if the call is already a pressure).

Two things worth knowing:

- Defenders get **unique labels**. Playbooks draw two ends as `E E`, but
  assignments are keyed by label, so repeats get an alignment prefix — `LDE`,
  `RDE`, `LCB`, `RCB`. That happens automatically.
- Like blocks, **assignment paths are never mirrored**; `mirror()` flips them
  explicitly, along with the zone `side`.

---

## The designer

```bash
chalk design                          # a blank formation
chalk design mesh_concept             # start from a catalog concept
chalk design my_play.json             # keep editing a saved play
chalk design week3.json               # or a whole playbook
chalk design --level hs --out designer.html --no-open
```

It writes one self-contained HTML file — the whole catalog inlined, no server,
no CDN, no build step — and opens it. The field is the window and the tools float over it. The first time it opens,
a start screen offers four concepts, the whole library, a file, or a blank
formation. Drop a play or playbook `.json` anywhere on the window to open it.

- **Formation, Line, Defense, Library, Layers** sit on the rail at the left.
  Formations and defensive looks are picked from thumbnails, schemes and
  coverages from a list, concepts from a searchable library.
- **Click a player** on the field or on the bench to select it, **drag** to
  move (snapped to half yards). The strip above the bench edits the selection:
  route, block, target, direction, motion, ball carrier, note.
- **Click the field** to add route points, **drag** the yellow handles to shape
  the route, **double-click** one to delete it. Or pick a stock route. While a
  player is selected a faint line runs from the end of his route to the cursor,
  with the depth of the next point.
- **Arrow keys** nudge the selected player, defender or route point by half a
  yard; hold <kbd>Shift</kbd> for a full yard.
- **Layers** hide whatever you are not working on: routes, blocks, motion, the
  quarterback, reads, the defense, its assignments, zone landmarks, the title.
  Exports follow the toggles.
- The **play sheet** drawer holds the quarterback action and progression
  (click receivers in the order he works them), protection, tempo, alerts,
  tags, the situation and notes.
- <kbd>Ctrl</kbd>+<kbd>K</kbd> opens a command palette: every concept,
  formation, look, coverage and scheme is two keystrokes away. <kbd>F</kbd>
  flips the play, <kbd>Ctrl</kbd>+<kbd>Z</kbd> undoes.
- **Plays** opens the playbook: every page with a live thumbnail. Add a blank
  play or one from the library, duplicate, delete (with undo), drag to reorder,
  <kbd>[</kbd> and <kbd>]</kbd> to turn pages. A concept from the library fills a
  blank page or joins the book as a new one.
- **Save** writes the playbook once it has more than one play, otherwise the
  play; **Export** offers either, plus the SVG, a 2x PNG, and **Print playbook**,
  which lays every page out in the paper look and opens the print dialog.

The file the designer saves is the same JSON Python reads, so a book drawn in
the browser prints from the command line and loads in a script:

```python
book = Playbook.load("week3.json")
book.save_pdf("week3.pdf", plays_per_page=4, theme="paper")
```

```bash
chalk book week3.json                       # week3.pdf, two to a page, paper
chalk book week3.json -o week3.html
```

The browser keeps a working copy of the book, not a document store — save the
file. Opening a different book stashes the old working copy; the command
palette can bring it back.

Routes are authored as if the player is on the right side of the ball and
mirrored for left-side players. The designer and the Python renderer share that
convention through one function, `Assignment.absolute_waypoints()`, and a test
pins the two together — so a route drawn on screen lands exactly there on paper.

---

## Field levels

The field is 53 1/3 yards wide everywhere. The inbound lines are not, and that
one number changes every leverage read in a play:

| Level | Hashes apart | From the middle | On a hash: boundary / field |
|---|---|---|---|
| NFL | 18 ft 6 in | ±3.08 yd | 23.6 / 29.8 |
| College | 40 ft | ±6.67 yd | 20.0 / 33.3 |
| High school | 53 ft 4 in | ±8.89 yd | 17.8 / 35.6 |

A high school hash leaves twice as much grass on the field side as the boundary.
An NFL hash is nearly in the middle. Draw a play on the wrong hashes and the
spacing lies to you.

```python
play.render(level="hs").save("play.svg")
playbook.save_pdf("book.pdf", level="ncaa")
```

```bash
chalk render mesh_concept --level hs -o mesh.svg
chalk design --level ncaa
```

---

## Themes and layers

Every diagram is ink on a surface, and the ink comes from one table —
`chalktalk/renderer/theme.py` — that the SVG renderer, the PDF exporter and the
designer all draw from. Two themes ship:

| Theme | For | Field | Ink |
|---|---|---|---|
| `turf` (default) | the screen | a field under lights | chalk white, defense in coral |
| `paper` | the printer | white | black, defense in red |

The offense is drawn as open circles with a ring on whoever has the ball, the
defense as squares, zone drops as soft areas. Once a play has a situation with
a yard line, the five-yard grid becomes the real one, the tens get numbers, and
the end zone shows up when it is in view.

Each part of the drawing is a layer — `motion`, `blocks`, `qb`, `routes`,
`reads`, `defense`, `coverage`, `zones`, `title` — and any of them can be left
out. The designer's Layers control is the same list, and its exports follow
the toggles.

```python
play.render(theme="paper").save("mesh.svg")
play.render(hide=["defense", "zones"]).save("offense_only.svg")
playbook.save_pdf("book.pdf", theme="paper")      # PDFs default to turf
playbook.save_html("book.html")                   # HTML pages are paper already
```

```bash
chalk render mesh_concept --theme paper -o mesh.svg
chalk render mesh_concept -d NICKEL_425 --coverage cover_3 --hide zones,title
chalk design --theme paper
```

---

## Command line

```bash
chalk design                         # visual play designer
chalk book week3.json                # a designer playbook to PDF or HTML
chalk list plays                     # or formations | defenses | routes | series | schemes | blocks | coverages | qb
chalk render mesh_concept -o out/mesh.svg -d NICKEL_425 --coverage cover_3 --level hs --theme paper
chalk show mesh_concept              # assignments as text
chalk series mesh --out out/mesh_series
chalk script inside_zone --reps 2 --looks NICKEL_425 FIRE_ZONE --hashes
chalk callsheet mesh red_zone -o out/week3.html --wristband out/band.html
chalk demo --out out/demo            # one of everything
```

`chalktalk` works as an alias for `chalk`, and `python -m chalktalk` works
without installing the console script.

---

## Output formats

| Format | How |
|---|---|
| SVG diagram | `play.render(theme="turf", hide=[]).save("play.svg")` |
| PDF playbook (1/2/4-up) | `playbook.save_pdf("book.pdf", plays_per_page=4)` |
| HTML playbook page | `playbook.save_html("book.html")` |
| Call sheet / wristband | `sheet.save_html(...)`, `band.save_html(...)` |
| Practice script | `practice.to_html()`, `practice.save_csv(...)` |
| JSON | `play.to_json()`, `Playbook.load(path)` |

All HTML is single-file and print-ready — no assets, no CDN, no JavaScript.

---

## Examples

```bash
python examples/inside_zone.py        # build a run play from scratch
python examples/mesh_concept.py       # build a pass concept from scratch
python examples/scripted_series.py    # a series, its install plan, and a script
python examples/game_week.py          # series -> practice -> call sheet -> wristband -> PDF
python examples/redzone_package.py
python examples/export_playbook_pdf.py
```

---

## Tests

```bash
python -m pytest
```

The suite checks every stock formation for 11 players and 5 linemen, every
defensive look for 11 defenders, every catalog play for complete assignments and
a clean SVG render, and every adjustment for immutability and JSON round-tripping.

---

## Roadmap

- Self-scout: tendency reports by down, distance, hash, personnel and formation
- A concept taxonomy for the pass game, so a call sheet can be checked for the
  answers it is missing
- Coverage *checks* against trips and bunch, the way modern two-high defenses
  actually adjust, rather than one call for every formation
- A concept taxonomy for the pass game — horizontal, vertical and three-level
  stretches, isolation concepts — so plays are classified by what they attack
- Pressure checks and hot answers as first-class objects next to alerts
- Modern two-high defensive structures: coverage tools and checks against
  trips and bunch, rather than only named base fronts
- Self-scout: tendency reports by down, distance, hash, personnel and formation
- Flag football (5v5, 7v7) field sizes and formation sets
- Special teams: kickoff, punt, field goal, return units
- Import from Hudl / Pro Quick Draw exports

Contributions welcome — the catalog especially. Adding a play is one function.

---

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).

Free to use, study, change and share for any noncommercial purpose — a coach,
a team, a school, a club, a hobbyist, a researcher. What it does not allow is
selling chalktalk, or a product built on it or on a modified copy of it. If
that is what you want to do, ask: matthewbakerthompson@gmail.com.

Your playbook is yours. The licence covers the software, not the plays you
draw with it.
