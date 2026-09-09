"""
Comprehensive demo — exercises all major new features:

  1. Catalog plays (passing, running, red zone)
  2. PlayBuilder fluent API
  3. with_route / with_routes (easy route swap)
  4. mirror() — flip the play
  5. vs() — attach defensive formation
  6. Defensive formations rendered as gray squares
  7. PDF export of a full mixed playbook
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.makedirs("output", exist_ok=True)

from gridiron import PlayType, Playbook, PDFExporter, build_play
from gridiron.catalog import passing, running, redzone
from gridiron.templates import routes as R, formations as F, defense as D

# ─────────────────────────────────────────────────────────────────────────────
# 1. Catalog plays (zero boilerplate)
# ─────────────────────────────────────────────────────────────────────────────
mesh        = passing.mesh_concept()
curl        = passing.curl_flat()
four_verts  = passing.four_verticals()
smash       = passing.smash()
scissors    = passing.scissors()
iz          = running.inside_zone()
oz          = running.outside_zone()
power       = running.power_right()
draw        = running.draw()
fade        = redzone.fade_corner()
gl_power    = redzone.goal_line_power()

print("Catalog plays created:", mesh.name, "|", iz.name, "|", fade.name)

# ─────────────────────────────────────────────────────────────────────────────
# 2. PlayBuilder — concise custom play
# ─────────────────────────────────────────────────────────────────────────────
slant_out = (
    build_play(F.SHOTGUN_TRIPS_RIGHT())
    .block_ol()
    .routes(X=R.SLANT(), Z=R.OUT(), H=R.CURL(), Y=R.SEAM(), RB=R.FLAT())
    .name("Slant / Out Package")
    .play_type(PlayType.PASS)
    .tag("slant", "quick-game", "11-personnel")
    .describe("Slant backside, out/curl frontside. Good vs. man coverage.")
    .build()
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. with_route — easy in-place route replacement
# ─────────────────────────────────────────────────────────────────────────────
slant_post   = slant_out.with_route("X", R.POST())        # swap slant → post
slant_corner = slant_out.with_route("Z", R.CORNER())      # swap out  → corner
slant_double = slant_out.with_routes(X=R.SLANT(), Z=R.SLANT())  # both slants

print("Route swap: slant_out → slant_post (X routes differ):",
      slant_out.assignments[5].route.route_type.value,
      "->",
      slant_post.assignments[5].route.route_type.value)

# ─────────────────────────────────────────────────────────────────────────────
# 4. mirror() — flip the entire play
# ─────────────────────────────────────────────────────────────────────────────
mesh_left  = mesh.mirror()
power_left = power.mirror()

mesh.render().save("output/demo_mesh_right.svg")
mesh_left.render().save("output/demo_mesh_left.svg")

# ─────────────────────────────────────────────────────────────────────────────
# 5. vs() — attach a defensive formation
# ─────────────────────────────────────────────────────────────────────────────
mesh_vs_43   = mesh.vs(D.FOUR_THREE_OVER())
smash_vs_c2  = smash.vs(D.COVER_2_TAMPA())
iz_vs_34     = iz.vs(D.THREE_FOUR_BASE())
fade_vs_gl   = fade.vs(D.GOAL_LINE_55())
blitz        = slant_out.vs(D.ZERO_BLITZ())

mesh_vs_43.render().save("output/demo_mesh_vs_43over.svg")
smash_vs_c2.render().save("output/demo_smash_vs_tampa2.svg")
iz_vs_34.render().save("output/demo_iz_vs_34base.svg")
fade_vs_gl.render().save("output/demo_fade_vs_goalline.svg")
blitz.render().save("output/demo_slant_vs_zero_blitz.svg")

print("Defense diagrams saved (mesh vs 4-3 Over, smash vs Tampa 2, IZ vs 3-4, etc.)")

# ─────────────────────────────────────────────────────────────────────────────
# 6. New formations: Wildcat, Quads, Bunch, Diamond
# ─────────────────────────────────────────────────────────────────────────────
wildcat_sweep = (
    build_play(F.WILDCAT())
    .block_ol().block("Y", "Z", "H")
    .routes(QB=R.BLOCK(), RB=R.RUN(dx=7, dy=4))
    .bc("RB")
    .name("Wildcat Sweep")
    .play_type(PlayType.RUN)
    .tag("wildcat", "sweep", "trick")
    .build()
)

quads_flood = (
    build_play(F.GUN_QUADS_RIGHT())
    .block_ol()
    .routes(
        X=R.POST(),
        Y=R.SEAM(),
        H=R.OUT(stem=6, depth=8),
        Z=R.FLY(),
        RB=R.FLAT(),
    )
    .name("Quads Flood")
    .play_type(PlayType.PASS)
    .tag("quads", "overload", "flood")
    .build()
)

wildcat_sweep.render().save("output/demo_wildcat_sweep.svg")
quads_flood.render().save("output/demo_quads_flood.svg")

# ─────────────────────────────────────────────────────────────────────────────
# 7. PDF playbook export — all the new plays
# ─────────────────────────────────────────────────────────────────────────────
playbook = Playbook(
    name="Comprehensive Playbook v2",
    team="Demo FC",
    season=2026,
    plays=[
        mesh_vs_43,
        curl,
        four_verts,
        smash_vs_c2,
        scissors,
        slant_out,
        slant_post,
        iz_vs_34,
        oz,
        power,
        draw,
        wildcat_sweep,
        quads_flood,
        fade_vs_gl,
        gl_power,
    ],
)

PDFExporter(playbook, "output/comprehensive_playbook.pdf", plays_per_page=1).export()
PDFExporter(playbook, "output/comprehensive_2up.pdf", plays_per_page=2).export()

print(f"\nPlaybook exported: {len(playbook)} plays")
print("Files written to output/")
