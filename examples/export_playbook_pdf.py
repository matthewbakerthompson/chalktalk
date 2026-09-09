"""
Example: Export a full playbook to PDF (three layout options).

Builds a 7-play sample playbook mixing pass, run, and red zone concepts,
then exports it at all three density levels.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gridiron import Play, PlayType, Assignment, Playbook, PDFExporter
from gridiron.templates import routes as R, formations as F

os.makedirs("output", exist_ok=True)


def _block(players, *labels):
    return [Assignment(player=players[lbl], route=R.BLOCK()) for lbl in labels]


# ── Play 1: Mesh Concept ──────────────────────────────────────────────────────
f = F.SHOTGUN_TRIPS_RIGHT()
p = {pl.label: pl for pl in f.players}
mesh = Play(
    name="Mesh Concept",
    formation=f,
    play_type=PlayType.PASS,
    assignments=[
        *_block(p, "LT","LG","C","RG","RT"),
        Assignment(player=p["X"],  route=R.FLY()),
        Assignment(player=p["Y"],  route=R.FLAT()),
        Assignment(player=p["Z"],  route=R.MESH(depth=5, cross=22)),
        Assignment(player=p["H"],  route=R.MESH(depth=6, cross=22)),
        Assignment(player=p["QB"]),
        Assignment(player=p["RB"], route=R.SWING()),
    ],
    description="Two-man mesh with fly clearout and flat/swing checkdowns.",
    tags=["mesh", "trips", "11-personnel"],
)

# ── Play 2: Curl / Flat ───────────────────────────────────────────────────────
f = F.SHOTGUN_TRIPS_RIGHT()
p = {pl.label: pl for pl in f.players}
curl_flat = Play(
    name="Curl / Flat",
    formation=f,
    play_type=PlayType.PASS,
    assignments=[
        *_block(p, "LT","LG","C","RG","RT"),
        Assignment(player=p["X"],  route=R.CURL()),
        Assignment(player=p["Y"],  route=R.SEAM()),
        Assignment(player=p["Z"],  route=R.OUT()),
        Assignment(player=p["H"],  route=R.CURL(depth=10)),
        Assignment(player=p["QB"]),
        Assignment(player=p["RB"], route=R.FLAT()),
    ],
    description="High-low curl/flat stress on the hook-curl defender.",
    tags=["curl-flat", "trips", "11-personnel"],
)

# ── Play 3: Four Verts ────────────────────────────────────────────────────────
f = F.GUN_DOUBLES()
p = {pl.label: pl for pl in f.players}
four_verts = Play(
    name="Four Verticals",
    formation=f,
    play_type=PlayType.PASS,
    assignments=[
        *_block(p, "LT","LG","C","RG","RT"),
        Assignment(player=p["X"],  route=R.FLY()),
        Assignment(player=p["Y"],  route=R.SEAM()),
        Assignment(player=p["H"],  route=R.SEAM(depth=20)),
        Assignment(player=p["Z"],  route=R.FLY()),
        Assignment(player=p["QB"]),
        Assignment(player=p["RB"], route=R.FLAT()),
    ],
    description="Four verticals — stretch coverage deep, checkdown available.",
    tags=["verticals", "four-verts", "11-personnel"],
)

# ── Play 4: Bunch Rub ─────────────────────────────────────────────────────────
f = F.SHOTGUN_BUNCH_RIGHT()
p = {pl.label: pl for pl in f.players}
bunch_rub = Play(
    name="Bunch — Out / Drag / Seam",
    formation=f,
    play_type=PlayType.PASS,
    assignments=[
        *_block(p, "LT","LG","C","RG","RT"),
        Assignment(player=p["X"],  route=R.POST()),
        Assignment(player=p["Y"],  route=R.SEAM()),
        Assignment(player=p["H"],  route=R.DRAG(depth=4, cross=8)),
        Assignment(player=p["Z"],  route=R.OUT(stem=4, depth=6)),
        Assignment(player=p["QB"]),
        Assignment(player=p["RB"], route=R.ANGLE()),
    ],
    description="Bunch rub — Z uses H drag as a natural pick on the cornerback.",
    tags=["bunch", "rub", "11-personnel"],
)

# ── Play 5: Inside Zone ───────────────────────────────────────────────────────
f = F.I_FORM_PRO_RIGHT()
p = {pl.label: pl for pl in f.players}
inside_zone = Play(
    name="Inside Zone",
    formation=f,
    play_type=PlayType.RUN,
    assignments=[
        *_block(p, "LT","LG","C","RG","RT","Y","X","Z"),
        Assignment(player=p["QB"]),
        Assignment(player=p["FB"], route=R.BLOCK()),
        Assignment(player=p["RB"], route=R.RUN(dx=1.5, dy=7), is_ball_carrier=True),
    ],
    description="Base inside zone — RB reads backside A-gap behind OL zone steps.",
    tags=["inside-zone", "run", "21-personnel", "i-form"],
)

# ── Play 6: Power Right ───────────────────────────────────────────────────────
f = F.I_FORM_STRONG_RIGHT()
p = {pl.label: pl for pl in f.players}
power = Play(
    name="Power Right",
    formation=f,
    play_type=PlayType.RUN,
    assignments=[
        *_block(p, "LT","LG","C","RG","RT","Y","X","Z"),
        Assignment(player=p["QB"]),
        Assignment(player=p["FB"], route=R.RUN(dx=3, dy=4)),  # lead through hole
        Assignment(player=p["RB"], route=R.RUN(dx=3, dy=7), is_ball_carrier=True),
    ],
    description="Power right — FB leads through B-gap, RB follows.",
    tags=["power", "run", "21-personnel", "i-form"],
)

# ── Play 7: Fade / Corner (Red Zone) ─────────────────────────────────────────
f = F.RED_ZONE_TRIPS_RIGHT()
p = {pl.label: pl for pl in f.players}
rz_fade = Play(
    name="Red Zone Fade / Corner",
    formation=f,
    play_type=PlayType.PASS,
    assignments=[
        *_block(p, "LT","LG","C","RG","RT"),
        Assignment(player=p["Y"],  route=R.SEAM(depth=8)),
        Assignment(player=p["X"],  route=R.FADE(depth=9)),
        Assignment(player=p["Z"],  route=R.CORNER_ENDZONE()),
        Assignment(player=p["H"],  route=R.FLAT()),
        Assignment(player=p["QB"]),
        Assignment(player=p["RB"], route=R.ANGLE()),
    ],
    description="Fade + corner stress the back defender in the end zone.",
    tags=["red-zone", "fade", "11-personnel"],
)

# ── Assemble playbook ─────────────────────────────────────────────────────────
playbook = Playbook(
    name="Sample Offensive Playbook",
    team="Gridiron FC",
    season=2026,
    plays=[mesh, curl_flat, four_verts, bunch_rub, inside_zone, power, rz_fade],
)

print(f"Playbook: {playbook.name}  ({len(playbook)} plays)")

# ── Export at all three densities ────────────────────────────────────────────
PDFExporter(playbook, "output/playbook_1up.pdf",  plays_per_page=1).export()
PDFExporter(playbook, "output/playbook_2up.pdf",  plays_per_page=2).export()
PDFExporter(playbook, "output/playbook_4up.pdf",  plays_per_page=4).export()
