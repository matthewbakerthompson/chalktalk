"""
A coach's playbooks live in one folder the designer knows (Documents/chalktalk),
open by their real path so Save writes back to them, and a shortcut starts the
designer without a terminal. These cover the folder, the Open dialog's
requests, the quiet designer stopping on its own, and the shortcut.
"""
import json
import sys
import time

import pytest

from chalktalk import cli
from chalktalk.catalog import passing, running
from chalktalk.designer import home, icon, server as S, shortcut
from chalktalk.models import Playbook


def _book(name="Week 3") -> Playbook:
    return Playbook(name=name, plays=[passing.mesh_concept(), running.power_right()])


@pytest.fixture
def folder(tmp_path):
    _book().save(str(tmp_path / "week3.json"))
    time.sleep(0.01)
    (tmp_path / "scout").mkdir()
    _book("Central").save(str(tmp_path / "scout" / "central.json"))
    (tmp_path / "notes.json").write_text('{"not": "a play"}', encoding="utf-8")
    (tmp_path / "broken.json").write_text("{nope", encoding="utf-8")
    (tmp_path / ".hidden").mkdir()
    _book("Hidden").save(str(tmp_path / ".hidden" / "x.json"))
    return tmp_path


# ── the folder ────────────────────────────────────────────────────────────────

def test_the_folder_is_documents_chalktalk_unless_told(monkeypatch, tmp_path):
    monkeypatch.delenv("CHALKTALK_FOLDER", raising=False)
    assert home.default_folder() == home.documents() / "chalktalk"
    monkeypatch.setenv("CHALKTALK_FOLDER", str(tmp_path / "books"))
    assert home.default_folder() == tmp_path / "books"


def test_the_open_dialog_lists_playbooks_newest_first(folder):
    listed, more = home.playbooks(folder)
    assert [(f["name"].replace("\\", "/"), f["title"], f["plays"]) for f in listed] == \
           [("scout/central.json", "Central", 2), ("week3.json", "Week 3", 2)]
    assert not more and all(f["kind"] == "book" for f in listed)


def test_a_play_file_is_listed_as_a_play(tmp_path):
    (tmp_path / "mesh.json").write_text(passing.mesh_concept().to_json(), encoding="utf-8")
    (entry,) = home.playbooks(tmp_path)[0]
    assert entry["kind"] == "play" and entry["title"] == "Mesh Concept"


def test_recent_files_keep_their_order_and_drop_the_missing(folder, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "away.json"
    _book("Away").save(str(elsewhere))
    got = home.recent([str(elsewhere), str(folder / "gone.json"), str(folder / "week3.json")], folder)
    assert [f["title"] for f in got] == ["Away", "Week 3"]
    assert got[0]["name"] == str(elsewhere.resolve())          # outside the folder: the full path


# ── the Open dialog's requests ────────────────────────────────────────────────

def test_files_and_open_by_path(folder):
    session = S.Session(str(folder))
    got = S.ROUTES["files"](session, {"recent": [str(folder / "scout" / "central.json")]})
    assert got["folder"] == str(folder) and [f["title"] for f in got["recent"]] == ["Central"]
    opened = S.ROUTES["open"](session, {"path": str(folder / "week3.json")})
    assert opened["kind"] == "book" and opened["data"]["name"] == "Week 3"
    assert opened["path"] == str((folder / "week3.json").resolve()) and opened["mtime"]
    # what was opened by path saves back to the same path
    session.save({"path": opened["path"], "text": _book("Week 3 v2").to_json(), "overwrite": True})
    assert Playbook.load(str(folder / "week3.json")).name == "Week 3 v2"


def test_open_says_when_a_file_is_gone_or_isnt_a_playbook(folder):
    session = S.Session(str(folder))
    with pytest.raises(ValueError, match="isn't there"):
        S.ROUTES["open"](session, {"path": str(folder / "gone.json")})
    with pytest.raises(ValueError):
        S.ROUTES["open"](session, {"path": "notes.json"})


def test_show_in_folder_opens_the_file_manager(folder, monkeypatch):
    shown = []
    monkeypatch.setattr(home, "reveal", shown.append)
    session = S.Session(str(folder))
    S.ROUTES["reveal"](session, {"path": str(folder / "week3.json")})
    S.ROUTES["reveal"](session, {})
    S.ROUTES["reveal"](session, {"path": str(folder / "gone.json")})
    assert shown == [folder / "week3.json", folder, folder]


# ── the quiet designer stops on its own ───────────────────────────────────────

def test_a_quiet_designer_stops_when_the_page_has_gone(tmp_path):
    s = S.Session(str(tmp_path))
    t0 = s.started
    assert not S._should_stop(s, t0 + 60)
    assert S._should_stop(s, t0 + S._NOBODY_CAME + 1)           # nobody ever came
    s.seen = t0 + 10
    assert not S._should_stop(s, t0 + 300)
    assert S._should_stop(s, t0 + 10 + S._SILENCE + 1)           # a long silence
    S.ROUTES["bye"](s, {})
    s.seen = s.bye
    assert not S._should_stop(s, s.bye + 30)                     # long enough for a reload
    assert S._should_stop(s, s.bye + S._AFTER_BYE + 1)
    S.ROUTES["ping"](s, {})                                      # another page spoke up
    assert s.bye is None and not S._should_stop(s, s.seen + 100)


def test_the_designer_says_who_it_is_and_shows_its_icon(tmp_path):
    import threading
    srv = S.make_server(S.Session(str(tmp_path)), port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    try:
        port = srv.server_address[1]
        assert S.running_at(port) and S.running_at(port, folder=str(tmp_path))
        assert not S.running_at(port, folder=str(tmp_path / "elsewhere"))
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/chalktalk", timeout=5) as r:
            assert str(tmp_path) not in r.read().decode("utf-8")     # a fingerprint, not a path
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico", timeout=5) as r:
            assert r.headers["Content-Type"] == "image/png" and r.read() == icon.png(32)
    finally:
        srv.shutdown()
        srv.server_close()
    assert not S.running_at(port)


# ── chalk design: the folder, and a second launch ─────────────────────────────

def test_chalk_design_keeps_playbooks_in_the_coachs_folder(tmp_path, monkeypatch):
    started = {}
    monkeypatch.setenv("CHALKTALK_FOLDER", str(tmp_path / "books"))
    monkeypatch.setattr(S, "running_at", lambda port=None, folder=None: False)
    monkeypatch.setattr(S, "serve", lambda session, port, open_browser, quiet=False:
                        started.update(session=session, quiet=quiet))
    assert cli.main(["design", "--no-open", "--quiet"]) == 0
    assert started["session"].root == str(tmp_path / "books") and started["quiet"]
    assert (tmp_path / "books").is_dir()
    assert cli.main(["design", "--no-open", "--folder", str(tmp_path / "other")]) == 0
    assert started["session"].root == str(tmp_path / "other")


def test_a_second_launch_opens_the_designer_already_running(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHALKTALK_FOLDER", str(tmp_path))
    asked = []
    monkeypatch.setattr(S, "running_at", lambda port=None, folder=None: asked.append(folder) or True)
    monkeypatch.setattr(S, "serve", lambda *a, **k: pytest.fail("started a second designer"))
    opened = []
    import webbrowser
    monkeypatch.setattr(webbrowser, "open", opened.append)
    assert cli.main(["design"]) == 0
    assert "already running" in capsys.readouterr().out and opened == [f"http://127.0.0.1:{S.DEFAULT_PORT}/"]
    # a shortcut made with --folder names it every time: same folder, same designer
    assert cli.main(["design", "--quiet", "--folder", str(tmp_path / "books")]) == 0
    assert asked == [None, str(tmp_path / "books")]


def test_a_designer_started_without_a_console_keeps_a_log(tmp_path, monkeypatch):
    monkeypatch.setattr(shortcut, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(sys, "stdout", None)                     # what pythonw gives
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(S, "running_at", lambda port=None, folder=None: False)
    monkeypatch.setattr(S, "serve", lambda session, port, open_browser, quiet=False:
                        print(f"Folder:   {session.root}"))
    assert cli.main(["design", "--quiet", "--no-open", "--folder", str(tmp_path / "books")]) == 0
    sys.stdout.close()
    assert "Folder:" in (tmp_path / "data" / "designer.log").read_text(encoding="utf-8")


# ── the shortcut ──────────────────────────────────────────────────────────────

def test_the_icon_is_a_real_png_and_ico():
    assert icon.png(16).startswith(b"\x89PNG\r\n\x1a\n")
    ico = icon.ico((16, 32))
    assert ico[:4] == b"\x00\x00\x01\x00" and int.from_bytes(ico[4:6], "little") == 2


def test_the_shortcut_runs_the_quiet_designer(tmp_path, monkeypatch):
    monkeypatch.setattr(shortcut, "data_dir", lambda: tmp_path / "data")
    name = {"win32": "Chalktalk.lnk", "darwin": "Chalktalk.app"}.get(sys.platform, "chalktalk.desktop")
    target = tmp_path / "Desktop" / name
    made = shortcut.create(folder=str(tmp_path / "books"), targets=[target])
    assert made == [target] and target.exists()
    if sys.platform == "darwin":
        script = (target / "Contents" / "MacOS" / "Chalktalk").read_text(encoding="utf-8")
        assert "chalktalk design --quiet" in script and "--folder" in script
    elif sys.platform != "win32":
        entry = target.read_text(encoding="utf-8")
        assert "chalktalk design --quiet" in entry and "Terminal=false" in entry
    assert shortcut.remove([target]) == [target] and not target.exists()
    assert shortcut.remove([target]) == []


def test_chalk_shortcut_says_where_it_put_the_icon(tmp_path, monkeypatch, capsys):
    target = tmp_path / "Chalktalk.lnk"
    monkeypatch.setattr(shortcut, "create", lambda folder=None, targets=None: [target])
    monkeypatch.setattr(shortcut, "remove", lambda targets=None: [target])
    assert cli.main(["shortcut"]) == 0
    assert f"Made:     {target}" in capsys.readouterr().out
    assert cli.main(["shortcut", "--remove"]) == 0
    assert f"Removed:  {target}" in capsys.readouterr().out
