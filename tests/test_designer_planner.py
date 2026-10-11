"""
The planner, the difficulty score and the scout run in Python now (the designer
asks for them; tests/test_designer_views.py). What the page still does itself:
give plays their ids, order reads against a coverage, and stretch the code key.
These run that code in node against Python on the same books.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

from chalktalk import codes as K
from chalktalk.catalog import passing, running
from chalktalk.models import GamePlan, Playbook, Role
from chalktalk.models import situation as S
from chalktalk.models.situation import Hash

from chalktalk import designer

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def tag(play, **kw):
    return play.model_copy(update=kw)


def _book(**plan) -> Playbook:
    plan = {"starters": ["power-right", "stick"], **plan}
    return Playbook(name="Wk 3", game_plan=GamePlan(**plan), plays=[
        tag(running.inside_zone(), series="Zone", role=Role.BASE,
            situation=S.Situation(label="Openers")),
        tag(passing.mesh_concept(), situation=S.Situation(label="Openers", hash_mark=Hash.LEFT)),
        tag(running.speed_sweep(), series="Zone", role=Role.CONSTRAINT,
            tell="Backside LB flowing hard"),
        tag(passing.y_cross(), series="Zone", role=Role.PLAY_ACTION),
        tag(running.power_right(), situation=S.Situation(down=3, distance=2)),
        tag(passing.four_verticals(), series="Zone", role=Role.SHOT, difficulty=3,
            situation=S.Situation(down=3, distance=9)),
        tag(passing.stick(), favorite=True, situation=S.Situation(down=3, distance=5, yard_line=15)),
        tag(passing.smash(), series="Zone", role=Role.TRICK),
        tag(passing.mesh_concept(), situation=S.Situation(label="Two Minute")),
    ]).with_ids()


def _js(book, body: str):
    html = designer.build()
    script = html[html.index("<script>") + len("<script>"):html.rindex("</script>")].rstrip()
    assert script.endswith("boot();")
    script = script[:-len("boot();")]
    prelude = ("globalThis.window = globalThis;\n"
               "globalThis.document = {getElementById: () => null, addEventListener() {},"
               " createElement: () => ({})};\n"
               "globalThis.localStorage = {getItem: () => null, setItem() {}, removeItem() {}};\n")
    data = book if isinstance(book, dict) else book.model_dump(mode="json")
    tail = (f"\n;const __book = ensureIds(normalizeBook({json.dumps(data)}));\n"
            f"process.stdout.write(JSON.stringify((function () {{ {body} }})()));\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "designer.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(prelude + script + tail)
        run = subprocess.run([NODE, path], capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_ids_are_made_the_same_way():
    raw = Playbook(name="x", plays=[passing.mesh_concept(), passing.mesh_concept(),
                                    tag(passing.stick(), id="mesh-concept-2"), running.power_right()])
    # The model fills ids in; hand the browser the book as it was saved, without them.
    data = raw.model_dump(mode="json")
    for p, saved in zip(data["plays"], [None, None, "mesh-concept-2", None]):
        p["id"] = saved
    assert _js(data, "return __book.plays.map(p => p.id);") == [p.id for p in raw.plays]
    assert [p.id for p in raw.plays] == ["mesh-concept", "mesh-concept-3", "mesh-concept-2", "power-right"]


def test_reads_against_a_coverage_match_python():
    from chalktalk.models.qb import QBAction, QBPlan
    plan = QBPlan(action=QBAction.DROPBACK).progression("Z", "H", "RB").progression("H", "Z", vs="Cover 2")
    covs = [None, "Cover 2", "cover 2 ", "Cover 3", ""]
    js = _js(_book(), f"const plan = {plan.model_dump_json()};"
                      f" return {json.dumps(covs)}.map(c => readsAgainst(plan, c));")
    assert js == [plan.reads_against(c) for c in covs]


def test_sha256_hmac_and_key_stretching_match_python():
    import hashlib
    import hmac
    msgs = ["", "abc", "a" * 55, "a" * 56, "a" * 64, "a" * 200, "Wk 3 Central|1st half|wristband|0"]
    js = _js(_book(), f"return {json.dumps(msgs)}.map(m => [hex(sha256(utf8(m))), hex(hmacSha256(utf8('key'), utf8(m)))])"
                      ".concat([[hex(keyBytes('k7qm-2xra 9fpd-hw4c'))]]);")
    for (h, mac), m in zip(js, msgs):
        assert h == hashlib.sha256(m.encode()).hexdigest()
        assert mac == hmac.new(b"key", m.encode(), hashlib.sha256).hexdigest()
    assert js[-1][0] == K.key_bytes("K7QM2XRA9FPDHW4C").hex()

