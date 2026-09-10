"""
Example: Mesh Concept (pass play)

Formation : Shotgun Trips Right (11 personnel)
Concept   : Classic two-man mesh crossing with flat/fly clearouts.

Routes
  X  (split-end left)  → FLY       — clears the deep middle
  Y  (TE right)        → FLAT      — high-low stress on the flat defender
  Z  (flanker right)   → MESH      — shallow cross, first mesh runner
  H  (slot right)      → MESH      — shallow cross, second mesh runner (deeper)
  RB                   → SWING     — safety valve to the right flat
  QB                   → (passer)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chalktalk import Play, PlayType, Assignment
from chalktalk.templates import routes as R, formations as F

formation = F.SHOTGUN_TRIPS_RIGHT()

# Build a lookup so we can reference players by label
players = {p.label: p for p in formation.players}

assignments = [
    # OL — no routes (they block, renderer skips them)
    Assignment(player=players["LT"], route=R.BLOCK()),
    Assignment(player=players["LG"], route=R.BLOCK()),
    Assignment(player=players["C"],  route=R.BLOCK()),
    Assignment(player=players["RG"], route=R.BLOCK()),
    Assignment(player=players["RT"], route=R.BLOCK()),

    # Skill
    Assignment(player=players["X"],  route=R.FLY()),
    Assignment(player=players["Y"],  route=R.FLAT()),
    Assignment(player=players["Z"],  route=R.MESH(depth=5.0, cross=22.0)),
    Assignment(player=players["H"],  route=R.MESH(depth=6.0, cross=22.0)),
    Assignment(player=players["QB"]),                                       # passer
    Assignment(player=players["RB"], route=R.SWING()),
]

play = Play(
    name="Mesh Concept",
    formation=formation,
    play_type=PlayType.PASS,
    assignments=assignments,
    description="Two-man mesh crossing with fly clearout and flat/swing checkdowns.",
    tags=["mesh", "trips", "11-personnel", "quick-game"],
)

print(play.describe())
play.render().save("output/mesh_concept.svg")

# Also dump the play to JSON to show the data model
with open("output/mesh_concept.json", "w") as f:
    f.write(play.to_json())
print("JSON saved: output/mesh_concept.json")
