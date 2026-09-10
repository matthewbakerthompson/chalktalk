"""
Example: a full game week, end to end.

    stock series  ->  install plan  ->  practice script  ->  call sheet
                                                          ->  wristband
                                                          ->  playbook PDF

Everything below is generated from the same play objects, so the numbers on
the wristband always match the numbers the coordinator is reading.

Run:  python examples/game_week.py
Out:  output/week3/
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chalktalk import adjustments as A
from chalktalk.callsheet import CallSheet, Wristband
from chalktalk.catalog import passing, series as SR
from chalktalk.models import Playbook
from chalktalk.models import situation as S
from chalktalk.script import PracticeScript, Script
from chalktalk.templates import defense as D

TEAM = "Riverside HS"
OPPONENT = "Central"
OUT = os.path.join(os.path.dirname(__file__), "..", "output", "week3")

# What the opponent lines up in — scout looks we want to see all week.
SCOUT_LOOKS = [D.FOUR_THREE_OVER(), D.NICKEL_425(), D.FIRE_ZONE(), D.COVER_2_TAMPA()]


# ── 1. Pick this week's series ────────────────────────────────────────────────

run_game = SR.inside_zone_series()
gap_game = SR.power_counter_series()
third_down = SR.mesh_series()
red_zone = SR.red_zone_series()
two_minute = SR.two_minute_series()

week = [run_game, gap_game, third_down, red_zone, two_minute]


# ── 2. Openers — the first 15, scripted before kickoff ────────────────────────

openers = (
    Script(name="Opening Script", opponent=OPPONENT)
    .add(run_game.base, S.FIRST_TEN, looks=SCOUT_LOOKS,
         note="Set the edge, find out how they fit the front")
    .add(third_down.base, S.Situation(down=2, distance=6), looks=SCOUT_LOOKS)
    .add(gap_game.base, S.FIRST_TEN, looks=SCOUT_LOOKS)
    .add(run_game.by_role(run_game.entries[1].role)[0], S.Situation(down=2, distance=5),
         looks=SCOUT_LOOKS, note="Constraint — check the backside linebacker")
    .add(passing.four_verticals().adjust(A.PLAY_ACTION("RB")), S.FIRST_TEN,
         looks=SCOUT_LOOKS, note="Shot play off run action")
    .alternate_hashes()
)

print(openers.table())
print()
print("Balance:", openers.balance())


# ── 3. Tuesday practice ───────────────────────────────────────────────────────

practice = (
    PracticeScript(name="Tuesday Practice", team=TEAM, opponent=OPPONENT,
                   date="2026-09-08")
    .add_period("Inside Run", run_game.to_script().with_looks(SCOUT_LOOKS),
                minutes=12, focus="Double team to the second level")
    .add_period("Gap Scheme", gap_game.to_script().with_looks(SCOUT_LOOKS),
                minutes=10, focus="Puller tracks")
    .add_period("7-on-7", third_down.to_script(reps=2), minutes=15,
                focus="Third-down conversion")
    .add_period("Team Red Zone", red_zone.to_script().with_looks(SCOUT_LOOKS),
                minutes=15, focus="Score from the 15 in")
    .add_period("Two Minute", two_minute.to_script(), minutes=8,
                focus="Clock and sideline discipline")
)

print()
print(practice.table())


# ── 4. Call sheet + wristband ─────────────────────────────────────────────────

playbook = Playbook(name=f"{TEAM} — Week 3", team=TEAM, season=2026,
                    plays=[p for s in week for p in s.plays])

sheet = (
    CallSheet.from_playbook(playbook, name="Week 3 Call Sheet")
    .note("Openers 1-5 are scripted — do not deviate",
          "Check the boundary safety before any shot play",
          "Two-point chart: go from the 2 if down by 2, 5, or 10")
    .number()
)
sheet = sheet.model_copy(update={"opponent": OPPONENT, "team": TEAM,
                                 "date": "2026-09-11"})

band = Wristband.from_call_sheet(sheet, columns=3)

print()
print(sheet.table())


# ── 5. Print everything ───────────────────────────────────────────────────────

os.makedirs(OUT, exist_ok=True)
sheet.save_html(os.path.join(OUT, "call_sheet.html"))
band.save_html(os.path.join(OUT, "wristband.html"))
with open(os.path.join(OUT, "practice.html"), "w", encoding="utf-8") as fh:
    fh.write(practice.to_html())
with open(os.path.join(OUT, "openers.html"), "w", encoding="utf-8") as fh:
    fh.write(openers.to_html())
practice.save_csv(os.path.join(OUT, "practice.csv"))
playbook.save_html(os.path.join(OUT, "playbook.html"), columns=2)
playbook.save_pdf(os.path.join(OUT, "playbook.pdf"), plays_per_page=4)
playbook.save(os.path.join(OUT, "playbook.json"))

print(f"\n{len(playbook)} plays -> {os.path.abspath(OUT)}")
for name in sorted(os.listdir(OUT)):
    print(f"  {name}")
