"""
Example: Inside Zone (run play)

Formation : I-Form Pro Right (21 personnel)
Concept   : Base inside zone — RB reads backside A-gap, hits wherever the
            double-teams create a crease. OL zone-steps right.

Routes
  X  (split-end left)  → BLOCK (stalk/crack vs. CB)
  Z  (flanker right)   → BLOCK (stalk vs. CB)
  Y  (TE right)        → BLOCK (base block vs. DE)
  FB                   → BLOCK (lead through hole)
  RB                   → RUN   (ball carrier, attacks A/B gap)
  QB                   → hands off
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chalktalk import Play, PlayType, Assignment
from chalktalk.templates import routes as R, formations as F

formation = F.I_FORM_PRO_RIGHT()
players   = {p.label: p for p in formation.players}

assignments = [
    Assignment(player=players["LT"], route=R.BLOCK()),
    Assignment(player=players["LG"], route=R.BLOCK()),
    Assignment(player=players["C"],  route=R.BLOCK()),
    Assignment(player=players["RG"], route=R.BLOCK()),
    Assignment(player=players["RT"], route=R.BLOCK()),
    Assignment(player=players["Y"],  route=R.BLOCK()),
    Assignment(player=players["X"],  route=R.BLOCK()),
    Assignment(player=players["Z"],  route=R.BLOCK()),
    Assignment(player=players["QB"]),
    Assignment(player=players["FB"], route=R.BLOCK()),
    Assignment(
        player=players["RB"],
        route=R.RUN(dx=1.5, dy=7.0),
        is_ball_carrier=True,
    ),
]

play = Play(
    name="Inside Zone",
    formation=formation,
    play_type=PlayType.RUN,
    assignments=assignments,
    description="Base inside zone. RB reads backside A-gap behind OL zone steps.",
    tags=["inside-zone", "run", "21-personnel", "i-form"],
)

print(play.describe())
play.render().save("output/inside_zone.svg")

with open("output/inside_zone.json", "w") as f:
    f.write(play.to_json())
print("JSON saved: output/inside_zone.json")
