"""
Example: a scripted series — one base play and everything that punishes a
defense for over-playing it.

A series is the unit coaches actually think in. Each entry carries the *tell*:
what you see on film that makes it the right call this week.

Run:  python examples/scripted_series.py
Out:  output/series/  (one SVG per play, plus a printable HTML page)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gridiron import adjustments as A
from gridiron.catalog import passing, running
from gridiron.models import situation as S
from gridiron.renderer.sheets import series_html
from gridiron.series import series
from gridiron.templates import defense as D, routes as R

OUT = os.path.join(os.path.dirname(__file__), "..", "output", "series")


# ── Build the series ──────────────────────────────────────────────────────────

split_zone = (
    series(
        "Split Zone Series",
        "Inside zone with a backside H-back kick-out. Every call starts with "
        "the same first two steps.",
    )
    .base(
        running.inside_zone(),
        note="Track the play-side double team, cut off the backside 3-tech",
        situation=S.FIRST_TEN,
    )
    .constraint(
        running.speed_sweep().adjust(A.MOTION("Z", "jet")),
        tell="Backside linebacker fast-flowing inside on the first step",
        situation=S.Situation(down=2, distance=6),
    )
    .constraint(
        running.qb_keeper().adjust(A.MOTION("H", "orbit")),
        tell="Unblocked end crashing down on the mesh point",
        situation=S.Situation(down=2, distance=3),
    )
    .play_action(
        passing.y_cross().adjust(A.PLAY_ACTION("RB"), A.PROTECTION("Slide Rt")),
        tell="Safeties triggering downhill the moment they see zone action",
        situation=S.Situation(down=2, distance=4),
    )
    .shot(
        passing.four_verticals().adjust(A.PLAY_ACTION("RB"),
                                        A.TAG("Z", R.POST(), name="Z Post")),
        tell="Single high with the free safety cheating into the box",
        situation=S.FIRST_TEN,
    )
    .answer(
        passing.rpo_bubble(),
        tell="Overhang defender aligned inside the slot with no leverage",
        situation=S.FIRST_TEN,
    )
    .tag("run", "zone", "install-week-1")
    .build()
)

print(split_zone.describe())


# ── Teach it: split the series across an install progression ──────────────────

print("\nInstall progression")
print("-------------------")
for day, plays in split_zone.install(days=3).items():
    print(f"  Day {day}: " + ", ".join(p.name for p in plays))


# ── Rep it: turn the series into a practice script ────────────────────────────

script = (
    split_zone.to_script(reps=2, period="Team")
    .with_looks([D.FOUR_THREE_OVER(), D.NICKEL_425(), D.FIRE_ZONE()])
    .alternate_hashes()
)

print()
print(script.table())


# ── Print it ──────────────────────────────────────────────────────────────────

os.makedirs(OUT, exist_ok=True)
split_zone.render_all(OUT)
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(series_html(split_zone))
script.save_csv(os.path.join(OUT, "script.csv"))
split_zone.to_playbook(team="Example HS").save(os.path.join(OUT, "series.json"))

print(f"\nWrote {len(split_zone)} diagrams + index.html to {os.path.abspath(OUT)}")
