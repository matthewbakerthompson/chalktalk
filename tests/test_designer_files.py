"""
The one promise the package keeps to the browser designer.

The designer left the package and is frozen at
https://github.com/matthewbakerthompson/chalktalk-designer. It opens and saves
the same Playbook JSON the package reads and writes, so a coach can draw a book
there and print, plan or scout it here. The fixture was saved by that designer:
five plays (one flipped, one with a defensive look, one route drawn by hand), a
drafted game plan and two snaps logged in its Game drawer. If a change to the
models breaks a test here, it breaks every book a coach has already saved.
"""
import json
from pathlib import Path

import pytest

from chalktalk import planner, scout
from chalktalk.models import DriveState, Playbook

FIXTURE = Path(__file__).parent / "fixtures" / "designer_book.json"


@pytest.fixture
def book() -> Playbook:
    return Playbook.load(str(FIXTURE))


def test_a_book_saved_by_the_designer_loads(book):
    assert (book.name, book.team, book.season) == ("Contract book", "Chalktalk", 2026)
    assert [p.name for p in book.plays] == [
        "Power Left", "Four Verticals", "Mesh Concept", "Inside Zone", "Buck Sweep"]
    assert [p.id for p in book.plays] == [
        "power-left", "four-verticals", "mesh-concept", "inside-zone", "buck-sweep"]


def test_what_the_coach_drew_lands_where_he_drew_it(book):
    verts = book.plays[1]                       # flipped in the designer
    z = next(a for a in verts.assignments if a.player.label == "Z")
    assert z.player.x == -20                    # the flip put Z on the left
    # stored as if he were on the right, mirrored on the way out
    assert z.absolute_waypoints() == [(-20.0, -1.0), (-20.0, 5.0), (-24.0, 9.0)]
    mesh = book.plays[2]
    assert mesh.defense.name == "Tampa 2" and len(mesh.defense.players) == 11
    power = book.plays[0]
    assert next(a for a in power.assignments if a.player.label == "RG").block.kind == "wrap"


def test_the_designers_game_plan_drives_the_planner_and_the_scout(book):
    plan = book.game_plan
    assert [s.title for s in plan.sections][:2] == ["1st & 10", "2nd & 1-3"]
    assert plan.openers[0] == "power-left"
    assert [snap.play for snap in plan.log] == ["inside-zone", "four-verticals"]
    calls = planner.suggest(book, DriveState(down=3, distance=8, yard_line=40))
    assert calls and calls[0].play == "mesh-concept"      # the 3rd & 7+ call in its plan
    assert scout.report(book).snaps == 2


def test_every_play_in_it_renders(book, tmp_path):
    for play in book.plays:
        assert "<svg" in play.render().render()
    book.save_html(str(tmp_path / "book.html"))
    assert (tmp_path / "book.html").read_text(encoding="utf-8").count("<svg") == 5


def test_the_package_writes_it_back_without_losing_anything(book, tmp_path):
    """A book saved here has to open in the designer again."""
    path = tmp_path / "again.json"
    book.save(str(path))
    assert Playbook.load(str(path)) == book

    def keys(node, at=""):
        if isinstance(node, dict):
            for k, v in node.items():
                yield f"{at}.{k}"
                yield from keys(v, f"{at}.{k}")
        elif isinstance(node, list):
            for v in node:
                yield from keys(v, f"{at}[]")

    drawn = set(keys(json.loads(FIXTURE.read_text(encoding="utf-8"))))
    written = set(keys(json.loads(path.read_text(encoding="utf-8"))))
    assert not drawn - written, sorted(drawn - written)
