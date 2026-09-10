"""
Example: Red Zone Package (3 plays)

Demonstrates red zone formations, compressed route trees, and new route types.
Also saves individual SVGs for each play.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chalktalk import Play, PlayType, Assignment
from chalktalk.templates import routes as R, formations as F

os.makedirs("output", exist_ok=True)

# ── Play 1: Fade/Corner combo (Red Zone Trips Right) ─────────────────────────

f1 = F.RED_ZONE_TRIPS_RIGHT()
p1 = {p.label: p for p in f1.players}

fade_corner = Play(
    name="Fade / Corner",
    formation=f1,
    play_type=PlayType.PASS,
    assignments=[
        Assignment(player=p1["LT"], route=R.BLOCK()),
        Assignment(player=p1["LG"], route=R.BLOCK()),
        Assignment(player=p1["C"],  route=R.BLOCK()),
        Assignment(player=p1["RG"], route=R.BLOCK()),
        Assignment(player=p1["RT"], route=R.BLOCK()),
        Assignment(player=p1["Y"],  route=R.SEAM(depth=8)),      # TE seam up the hash
        Assignment(player=p1["X"],  route=R.FADE(depth=9)),      # back-shoulder fade left
        Assignment(player=p1["Z"],  route=R.CORNER_ENDZONE()),   # corner to end zone right
        Assignment(player=p1["H"],  route=R.FLAT()),             # high-low flat
        Assignment(player=p1["QB"]),
        Assignment(player=p1["RB"], route=R.ANGLE()),            # angle checkdown
    ],
    description="Classic red zone concept — fade + corner stress the back defender, seam over the middle.",
    tags=["red-zone", "fade", "11-personnel", "trips"],
)

fade_corner.render().save("output/rz_fade_corner.svg")
print(fade_corner.describe())

# ── Play 2: Bunch End Zone (Red Zone Bunch Right) ────────────────────────────

f2 = F.RED_ZONE_BUNCH_RIGHT()
p2 = {p.label: p for p in f2.players}

bunch_rubs = Play(
    name="Bunch Rub Routes",
    formation=f2,
    play_type=PlayType.PASS,
    assignments=[
        Assignment(player=p2["LT"], route=R.BLOCK()),
        Assignment(player=p2["LG"], route=R.BLOCK()),
        Assignment(player=p2["C"],  route=R.BLOCK()),
        Assignment(player=p2["RG"], route=R.BLOCK()),
        Assignment(player=p2["RT"], route=R.BLOCK()),
        Assignment(player=p2["Y"],  route=R.SEAM(depth=7)),      # TE seam off the bunch
        Assignment(player=p2["X"],  route=R.CORNER_ENDZONE()),   # corner left
        Assignment(player=p2["Z"],  route=R.OUT(stem=4, depth=6)),  # quick out (uses rub)
        Assignment(player=p2["H"],  route=R.DRAG(depth=4, cross=10)),  # drag off the bunch
        Assignment(player=p2["QB"]),
        Assignment(player=p2["RB"], route=R.FLAT()),             # flat right
    ],
    description="Three-man bunch creates natural rubs. Z uses the H drag as a pick on the corner.",
    tags=["red-zone", "bunch", "rub", "11-personnel"],
)

bunch_rubs.render().save("output/rz_bunch_rubs.svg")
print(bunch_rubs.describe())

# ── Play 3: Power Run (Goal Line Heavy) ──────────────────────────────────────

f3 = F.GOAL_LINE_HEAVY()
p3 = {p.label: p for p in f3.players}

power_run = Play(
    name="Power Right",
    formation=f3,
    play_type=PlayType.RUN,
    assignments=[
        Assignment(player=p3["LT"],  route=R.BLOCK()),
        Assignment(player=p3["LG"],  route=R.BLOCK()),
        Assignment(player=p3["C"],   route=R.BLOCK()),
        Assignment(player=p3["RG"],  route=R.BLOCK()),
        Assignment(player=p3["RT"],  route=R.BLOCK()),
        Assignment(player=p3["Y"],   route=R.BLOCK()),    # TE base block
        Assignment(player=p3["TE"],  route=R.BLOCK()),    # backside cutoff
        Assignment(player=p3["TE2"], route=R.BLOCK()),    # wing kick-out
        Assignment(player=p3["X"],   route=R.BLOCK()),    # crack/stalk
        Assignment(player=p3["QB"]),
        Assignment(player=p3["FB"],  route=R.RUN(dx=2, dy=3)),   # FB lead
        Assignment(
            player=p3["RB"],
            route=R.RUN(dx=3, dy=6),
            is_ball_carrier=True,
        ),
    ],
    description="Goal line power — double-tight, FB lead, RB follows through the B-gap.",
    tags=["goal-line", "run", "power", "22-personnel"],
)

power_run.render().save("output/rz_power_run.svg")
print(power_run.describe())

print("\nAll 3 red zone plays saved to output/")
