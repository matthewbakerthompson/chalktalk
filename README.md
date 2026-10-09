# chalktalk

**Football playbooks as code.**

A Python library for American football plays and everything a staff builds
from them. A play is a model that saves as plain JSON: write one by hand,
generate a hundred variants in a loop, and the same diagrams, playbooks, call
sheets, practice scripts and wristbands come out the other end.

Rather draw? The [chalktalk designer](https://matthewbakerthompson.github.io/chalktalk-designer/)
is a browser app that opens and saves the same JSON ([more below](#the-designer)).

```bash
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

---

## What's in the box

| | |
|---|---|
| **40 formations** | Shotgun, pistol, I-form, empty, bunch, trips, quads, wildcat, jumbo, goal line |
| **23 defensive looks** | 4-3, 3-4, nickel, dime, quarter, bear, 46, fire zone, cover-2 Tampa, goal line |
| **30 named routes** | Full route tree plus red-zone specialties (fade, back-shoulder, sail, bubble) |
| **78 stock plays** | Mesh, smash, flood, levels, snag, dagger, shallow cross, mills; inside/outside zone, duo, split zone, power, counter, buck sweep, speed option |
| **Play action & movement** | Boot, waggle, naked, keeper, dagger, post-wheel off power, and max-protect shot plays |
| **Screen game** | RB slip, swing, double screen, tunnel, bubble, jailbreak, middle, TE leak |
| **RPO family** | Bubble, glance, slant, pop, stick, now, and a gap-scheme arrow — each reading a different defender |
| **9 scripted series** | Inside zone, power/counter, mesh, play action, screens, short yardage, sprint-out, red zone, two-minute |
| **4 series sets** | Whole offenses: install order, one practice script, one call sheet, balance and gap checks |
| **12 quarterback actions** | Drops, play action, boot, sprint, mesh, handoff, draw, pitch, option, keep, sneak — with read progressions |
| **10 coverages + fronts** | Cover 0-6, Tampa 2, fire zone, zero blitz, line games — with zone drops, man match-ups and blitz paths |
| **14 blocking schemes** | Inside/outside zone, power, counter, trap, iso, plus slide, half-slide, big-on-big, sprint and boot protections |
| **12 adjustment types** | Motion, shift, tag, flip, formation, protection, tempo, alert, max protect, release, play action, personnel |
| **3 field levels** | NFL, college and high school hashes — switchable everywhere |
| **Renderers** | SVG, multi-page PDF playbooks, printable HTML call sheets / scripts / wristbands, CSV |

---

## The four building blocks

### 1. Formations and plays

```python
from chalktalk.catalog import passing, running, redzone, playaction, screens, rpo
from chalktalk.templates import formations as F

iz = running.inside_zone()                              # stock play
iz_gun = running.inside_zone(formation=F.GUN_DOUBLES()) # same concept, new look
smash_left = passing.smash().mirror()

boot = playaction.pa_boot()      # zone action right, quarterback out the left
slip = screens.rb_slip()         # let the rush come, throw behind it
glance = rpo.glance()            # read the safety who fills
```

`catalog.all_plays()` hands you every concept at once, keyed by name — that is
what the CLI reads, so anything in the catalog is everywhere.

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

Nine stock series ship in `chalktalk.catalog.series`.

### Series sets

A series answers one question. An offense is several of them, installed in an
order, repped together and called off one sheet — that is a **series set**.

```python
from chalktalk.series import series_set
from chalktalk.catalog import series as SR, systems

system = (
    series_set("Base Offense")
    .add(SR.inside_zone_series(), install_week=1)
    .add(SR.mesh_series(), install_week=1)
    .add(SR.power_counter_series(), install_week=2)
    .add(SR.play_action_series(), install_week=2)
    .team("Riverside HS", 2026)
    .build()
)

system.install(weeks=4)     # bases first, answers as the weeks go on
system.to_practice(week=1)  # one period per series
system.to_call_sheet()      # every play, bucketed by situation
system.balance()            # run/pass, personnel, answers per base
system.gaps()               # what the system cannot answer yet
system.save_html("install.html")
```

```bash
chalk list systems
chalk system pro_style --balance
chalk system base_offense --out out/install
```

`install()` puts **every base in before anybody's constraints** — a constraint
installed before the play it constrains teaches nothing.

`gaps()` is the part worth arguing about. It does not check style; it reports
the holes a defensive coordinator finds on Sunday:

```
Gaps
  - Mesh Series: nothing that goes over the top
  - Two-Minute Series: no constraint on the base
  - the whole set is 23% run / 74% pass
```

Four stock systems ship in `chalktalk.catalog.systems` — base offense, spread,
pro style, and a one-week game plan.

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

The [chalktalk designer](https://matthewbakerthompson.github.io/chalktalk-designer/)
is a browser app for drawing plays by hand: drag players, draw routes, build a
book, set the game plan, print the paper. It works offline and keeps plays on
the coach's own device. It is a separate project,
[frozen](https://github.com/matthewbakerthompson/chalktalk-designer) as it
shipped with chalktalk 0.12.0, and it opens and saves the same JSON this
package reads and writes. A book drawn there prints, plans and scouts here, and
a book built here opens there:

```python
book = Playbook.load("week3.json")          # saved from the designer
book.save_pdf("week3.pdf", plays_per_page=4, theme="paper")
book.save("week3.json")                     # opens in the designer again
```

```bash
chalk book week3.json                       # week3.pdf, two to a page, paper
chalk book week3.json -o week3.html
```

That file format is the one promise the package keeps to the designer. A test
loads a playbook the designer saved (`tests/fixtures/designer_book.json`) and
writes it back without losing a field, so a change to the models can't strand
a book a coach has already drawn.

Routes are stored as if the player is on the right side of the ball and
mirrored for left-side players, by one function,
`Assignment.absolute_waypoints()`. Designer files store routes the same way, so
the convention is part of the format.

---

## Game plans and drives

Two jobs: the plan is the week, the planner is game day. A `GamePlan` rides in
the playbook, so the book and its plan travel as one file.

**The week.** Every play can carry its **series** ("Zone"), its **role** in it
(base, complement, constraint, play-action, shot, trick, answer), the **tell**
that calls for it, a difficulty tier and a **favorite** flag. The plan holds:

- the level and what the team can execute;
- call-sheet **sections** (a play can sit in several; one added later lands in
  Base);
- the **openers**, the opening script in order, and the **drive starters**, the
  go-to first calls for each new drive once the script is done;
- **drive scripts**, the drive patterns scripted in the week: the 1st-down
  call, the 2nd-down call on schedule and off it, then 3rd down under each. A
  script can start anywhere from backed up on the 3 to the goal line, after a
  turnover, in two-minute or in four-minute;
- the **call system**: how calls get in (below).

`planner.draft()` fills what is blank from what the plays already say about
themselves (type, scheme tags, the quarterback's action) and lists every
decision: "Speed Sweep: constraint in Inside Zone". It never overwrites what
you set. `planner.fill_script()` drafts a script's empty calls, and
`planner.check()` flags what a coordinator would.

**Game day, and rehearsal in the week.** `planner.suggest()` ranks the next
call from the book, and every pick shows its arithmetic: "+6 next on the
opening script", "+4 they showed it: backside LB flowing hard", "-4 hold:
Inside Zone hasn't been shown yet". Constraint plays wait until their base has
been shown, a trick is used once, favorites are lifted wherever they fit, and a
play that worked earlier gets another look. Give the state the coverage the
defense is showing and the planner lifts the plays written to beat it, and the
ones the quarterback has his own read order against. `planner.follow()` walks
a drive script and hands back to `suggest()` when the drive leaves it, and
`planner.drive_cards()` gives the first calls from six common starts.

```python
from chalktalk import codes as K, planner as P
from chalktalk.models import (CallSystem, DriveScript, DriveState, GamePlan, Outcome,
                              Playbook, Snap)

book = Playbook.load("week3.json")
book.game_plan = GamePlan(name="Wk 3 vs Central", level="hs", execution=2,
                          calls=CallSystem(methods=["wristband", "words", "boards"]))
state = DriveState()                          # 1st & 10, own 25
for s in P.suggest(book, state):
    print(s.points, s.name, [r.text for r in s.reasons])
state = P.advance(state, Outcome.GAIN, 4)     # 2nd & 6, own 29
P.check(book)                                 # what a coordinator would flag

book = P.draft(book).book                     # series, call sheet and openers, blanks only
script = P.fill_script(book, DriveScript(name="Opening drive"))
first = Snap(before=DriveState(), play=script.first.play, call="IZ", gain=4)
P.follow(book, script, state, [first])        # (["on"], the 2nd-down call on schedule)
```

**On schedule** means gaining enough of the distance for the down. The bar
depends on the level:

| Level | 1st down | 2nd down | 3rd and 4th |
|---|---|---|---|
| High school | 40% | 50% | 100% |
| College | 50% | 70% | 100% |
| NFL | 45% | 60% | 100% |

The high school bar is what high school staffs already chart: 4 yards on 1st &
10, half the distance on 2nd. The college bar is the standard college
definition, and the NFL bar is the DVOA baseline. A plan can set its own. Sacks,
incompletions and turnovers fail. Penalties don't count either way.

**Difficulty.** Every play scores what it asks of the players. Jet and orbit
motion, a mesh or option read, the length of the progression, pullers, screen
timing, tags, alerts and checks at the line each add points, and each group
of points names its reason. The play sheet shows the arithmetic ("Advanced 8:
RB orbit motion (3), mesh read (2), ..."). Plays scoring 0–3 are **Basic**, 4–7
**Standard** and 8 or more **Advanced**. Set what your team runs (youth, varsity or college),
and the planner takes a point off for every point a play scores above that.
Setting a play's tier yourself marks it as repped. The weights are a judgment
from what coaches name as hard, not a published scale; the catalog comes out
64 Basic and 14 Standard.

### Halftime, and what a scout sees

`scout.report()` counts back every snap in the plan's log: how many snaps
stayed on schedule and how that splits by
down, third downs converted, the explosive plays (12 yards running, 16
throwing), what is working by yards a call, and what a scout on the other
sideline sees. It also lists what the staff hasn't used: the rest of the
opening script, the drive starters, the favorites, and the plays a series has
set up but never called.

A scout breaks the half down by what the defense sees before the snap:
- formation;
- personnel;
- down and distance;
- hash;
- where the ball is;
- and any two of those together.

Down and distance and the part of the field use the plan's own sections, so a
tendency points at the part of the call sheet that breaks it. Four calls from
one look with eight in ten the same kind is a tendency.

A look is said only when nothing broader says it already:
- a formation that is the whole of its personnel is one note, not two;
- a half that runs 20 of 24 says so once;
- the one place that half throws is still said: "On 2nd & 7+, from the left
  hash, you have thrown 4 of 4: a scout sees it."

```python
from chalktalk.scout import report

r = report(book)                # or report(book, log)
r.on, r.snaps, r.rate           # 29 of 53, 55%
[n for n in r.notes]            # what a scout sees, in a coordinator's order
[(t.by, t.look, t.runs, t.passes) for t in r.tendencies]   # every look, by dimension
```

### Calling the plays

A plan can use any mix of four ways to get the call in:

- **Verbal**: the call as written.
- **Wristband numbers**: the signal is a code, and the quarterback reads the
  play off his card. Codes are numbers (47) or a letter and a number (B7), two
  or three characters. The top calls get extra codes so no code repeats all
  game. Dead codes mean "wait". The cards change every half, or every quarter
  or every game, and no code keeps its play from one card to the next.
- **Line calls**: what the quarterback can say at the line. Every play gets a
  code word for the game, so the team learns the week's words in practice.
  The words come from a list (a mix, animals, cities, things) or from your
  own. Set a play's `word`, or leave it blank and let the key draw one. At the line he says the live word, then the call,
  twice ("Blue... Tiger, Blue... Tiger"). Only the live word's call is real,
  and the live word changes every half. The live word can be a colour, a
  number, or your own word. It can also be dropped: he makes two or three
  calls and the key names which one counts. Dummy words fill the noise, and a
  word heard on film goes on the burned list: it becomes a decoy and never
  means a play again.
- **Sign boards**: each board carries two or four symbols, and only one cell is
  live; which one changes every half. A symbol means its play (or its whole
  series) for the game. The other cells are decoys drawn from the same symbols,
  so every symbol shows up on many boards and a camera sees a mix, not a code.
  One rack serves the whole game: a board means one call while its top-left
  cell is live, and another after the half. The symbols are eight shapes in
  five colours, outlined in black, that stay apart for colour-blind players. A
  four-cell board on a 22 x 28 in poster reads to about 30 yards, two cells to
  about 40, one to about 55. `boards()` returns the rack, what each symbol
  means and which cell is live each half, and the plan check warns when there
  are more symbols than players can keep (about 12 in high school).

**The format varies too.** Two teams on chalktalk know every format the
package has, so you can leave parts of yours to the key: whether codes are 47
or B7, two or four symbols a board (each game), where a dummy digit hides in
the signal, and which of two or three signals is live (each period, never the
same twice running). An opponent who knows chalktalk still doesn't know your
format.

**Wristbands print as inserts** at the real size of a wrist coach's window
(youth 3.75 x 2.25 in, teen 5 x 2.75, adult 5.25 x 3.25), with dashed cut lines,
in capitals, as many copies as players wear: `band.save_html(path, size="teen",
copies=2)`. A numbered band fills its inserts in columns under situation
headings. Print at actual size.

Codes, words and boards come from a **key** through HMAC-SHA256, so the head
coach and the signaler can make matching copies on different machines and
check the fingerprint on every page. The method is public; only the key is
secret. It's never saved in the playbook, the plan or any printout.

```python
key = K.new_key()                          # "K7QM-2XRA-9FPD-HW4C": write it down
K.wristband(book, key, "Wk 3 vs Central")  # a card per half: code -> play, dead codes
K.line_calls(book, key, "Wk 3 vs Central") # word -> play, dummy words, what's live
K.boards(book, key, "Wk 3 vs Central")     # symbols, the live cell per half, the rack
```

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
chalk book week3.json --level ncaa
```

---

## Themes and layers

Every diagram is ink on a surface, and the ink comes from one table —
`chalktalk/renderer/theme.py` — that the SVG renderer and the PDF exporter both
draw from. Two themes ship:

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
out.

```python
play.render(theme="paper").save("mesh.svg")
play.render(hide=["defense", "zones"]).save("offense_only.svg")
playbook.save_pdf("book.pdf", theme="paper")      # PDFs default to turf
playbook.save_html("book.html")                   # HTML pages are paper already
```

```bash
chalk render mesh_concept --theme paper -o mesh.svg
chalk render mesh_concept -d NICKEL_425 --coverage cover_3 --hide zones,title
```

---

## Command line

```bash
chalk book week3.json                # a playbook file to PDF or HTML
chalk list plays                     # or formations | defenses | routes | series | systems | schemes | blocks | coverages | qb
chalk system base_offense --out out/install   # the whole install book
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

- Tendency breakers in the planner: it lifts the play that breaks
  a tendency the self-scout has found for this down, hash and spot
- A concept taxonomy for the pass game — horizontal, vertical and three-level
  stretches, isolation concepts — so plays are classified by what they attack
  and a call sheet can be checked for the answers it is missing
- Pressure checks and hot answers as first-class objects next to alerts
- Modern two-high defensive structures: coverage checks against trips and
  bunch, the way two-high defenses actually adjust, rather than one call for
  every formation
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
