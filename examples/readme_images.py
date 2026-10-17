"""
Example: the play diagrams in the README

Draws three stock plays with the library and writes them to docs/images/.
Run it from anywhere after changing the renderer or the catalog, and commit
the SVGs it writes:

    python examples/readme_images.py

  flood-vs-cover-3.svg  Flood against a Nickel 4-2-5 playing Cover 3
  inside-zone.svg       Inside Zone against a 4-3 Over front
  counter-trey.svg      Counter Trey against a 4-3 Under front, in the print theme
"""
import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from chalktalk.catalog import passing, running
from chalktalk.templates import coverages as CV, defense as D

OUT = os.path.join(ROOT, "docs", "images")
os.makedirs(OUT, exist_ok=True)

flood = passing.flood().vs(D.NICKEL_425()).with_coverage(CV.COVERAGES["cover_3"])
flood.render().save(os.path.join(OUT, "flood-vs-cover-3.svg"))

iz = running.inside_zone().vs(D.FOUR_THREE_OVER())
iz.render().save(os.path.join(OUT, "inside-zone.svg"))

counter = running.counter_trey().vs(D.FOUR_THREE_UNDER())
counter.render(theme="paper").save(os.path.join(OUT, "counter-trey.svg"))
