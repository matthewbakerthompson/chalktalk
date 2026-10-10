"""
Python prints every sheet now (chalktalk.paper, tested in test_paper.py). What
the page still does itself is say how a situation reads and which call-sheet
section a play lands in; these run that code in node against Python's.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

from chalktalk import adjustments as A
from chalktalk import designer
from chalktalk.callsheet import STANDARD_BUCKETS, CallSheet, Wristband
from chalktalk.catalog import passing, redzone, running
from chalktalk.models import Playbook
from chalktalk.models import situation as S
from chalktalk.models.situation import Hash, Tempo
from chalktalk.script import Script
from chalktalk.templates import coverages as C, defense as D

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _book() -> Playbook:
    tempo = passing.mesh_concept().model_copy(update={"tempo": Tempo.NO_HUDDLE})
    return Playbook(name="Week 3", team="Owls", plays=[
        passing.mesh_concept().at(S.Situation(down=1, distance=10)),
        running.inside_zone().at(S.Situation(down=3, distance=2, yard_line=45)),
        passing.four_verticals().at(S.Situation(label="Openers")),
        running.power_right(),
        redzone.fade_corner().at(S.Situation(down=2, distance=8, yard_line=15,
                                             hash_mark=Hash.LEFT)),
        passing.mesh_concept().rename("Mesh Goal").at(
            S.Situation(down=1, distance=2, yard_line=2)),
        running.counter_trey().vs(D.NICKEL_425(), C.cover_3).at(
            S.Situation(down=2, distance=1.5)),
        tempo.rename("Mesh Tempo").adjust(A.PROTECTION("Slide Rt"), A.MOTION("Z", "jet"))
             .model_copy(update={"alerts": ["Check to fade vs press"]})
             .at(S.Situation(label="Two Minute", clock="2:00", tempo=Tempo.NO_HUDDLE)),
        redzone.fade_corner().rename("Fade Red").at(S.Situation(yard_line=12)),
        running.inside_zone().rename("Zone Own").at(S.Situation(down=1, distance=10,
                                                                yard_line=95)),
    ])


def _js(book: Playbook, body: str):
    """Run `body` inside the designer's script, with `__book` bound, and return its value."""
    html = designer.build()
    script = html[html.index("<script>") + len("<script>"):html.rindex("</script>")].rstrip()
    assert script.endswith("boot();")
    script = script[:-len("boot();")]
    prelude = ("globalThis.window = globalThis;\n"
               "globalThis.document = {getElementById: () => null, addEventListener() {},"
               " createElement: () => ({})};\n"
               "globalThis.localStorage = {getItem: () => null, setItem() {}, removeItem() {}};\n")
    tail = (f"\n;const __book = normalizeBook({json.dumps(book.model_dump(mode='json'))});\n"
            f"process.stdout.write(JSON.stringify((function () {{ {body} }})()));\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "designer.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(prelude + script + tail)
        run = subprocess.run([NODE, path], capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def _sheet_rows(sheet: CallSheet):
    return [[sec.title, [[p.call_number, p.call] for p in sec.plays]] for sec in sheet.sections]


def test_the_browser_ships_pythons_buckets_in_order():
    buckets = designer.catalog()["call_sheet_buckets"]
    assert [title for title, _ in buckets] == list(STANDARD_BUCKETS)


def test_situations_read_the_same_in_both():
    sits = [
        S.Situation(down=1, distance=10), S.Situation(down=1, distance=10, yard_line=8),
        S.Situation(down=3, distance=2.5, yard_line=45, hash_mark=Hash.RIGHT),
        S.Situation(yard_line=80), S.Situation(yard_line=50), S.Situation(down=4),
        S.Situation(label="Openers"), S.Situation(),
        S.Situation(down=2, distance=6, clock="2:00", tempo=Tempo.NO_HUDDLE),
        S.Situation(down=3, distance=7, label="3rd & long special"),
    ]
    payload = json.dumps([s.model_dump(mode="json") for s in sits])
    js = _js(_book(), f"return {payload}.map(s => [sitDescribe(s), sitShort(s)]);")
    assert js == [[s.describe(), s.short()] for s in sits]


def test_percentages_round_like_python():
    values = [0.5, 1.5, 2.5, 12.5, 13.5, 62.5, 33.3, 66.7]
    js = _js(_book(), f"return {json.dumps(values)}.map(pyRound);")
    assert js == [round(v) for v in values]
