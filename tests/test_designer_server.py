"""
`chalk design` serves the designer from the coach's own machine and writes the
files they name. These run the real server on a spare port and talk to it the
way the page does.
"""
import http.client
import json
import socket
import threading

import pytest

from chalktalk.catalog import passing, running
from chalktalk.designer import server as S
from chalktalk.models import Playbook


def _book(team="Owls") -> Playbook:
    return Playbook(name="Week 3", team=team, season=2026,
                    plays=[passing.mesh_concept(), running.power_right()])


@pytest.fixture
def served(tmp_path):
    _book().save(str(tmp_path / "week3.json"))
    session = S.Session(str(tmp_path), file="week3.json")
    srv = S.make_server(session, port=0)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _ask(srv, method, path, body=None, token=True, host=None):
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Host": host or f"127.0.0.1:{port}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
        if token:
            headers["X-Chalktalk-Token"] = srv.session.token
    conn.request(method, path, json.dumps(body) if body is not None else None, headers)
    r = conn.getresponse()
    data = r.read().decode("utf-8")
    conn.close()
    return r.status, data


def _save(srv, path, book, **kw):
    status, data = _ask(srv, "POST", "/api/save", {"path": path, "text": book.to_json(), **kw})
    return status, json.loads(data)


def test_the_page_opens_on_the_file(served):
    status, html = _ask(served, "GET", "/")
    assert status == 200
    assert "/*__BOOK__*/null" not in html and "/*__SERVER__*/null" not in html
    assert "Week 3" in html and "Power Right" in html
    assert served.session.token in html


def test_saving_writes_the_file_python_reads(served, tmp_path):
    status, got = _save(served, "week3.json", _book(team="Hawks"), overwrite=True)
    assert status == 200, got
    assert got["name"] == "week3.json" and got["mtime"]
    assert Playbook.load(str(tmp_path / "week3.json")).team == "Hawks"


def test_a_reload_picks_up_a_change_made_in_python(served, tmp_path):
    _book(team="Ravens").save(str(tmp_path / "week3.json"))
    assert "Ravens" in _ask(served, "GET", "/")[1]


def test_saving_needs_the_pages_token(served, tmp_path):
    status, _ = _ask(served, "POST", "/api/save",
                     {"path": "week3.json", "text": _book(team="X").to_json(), "overwrite": True},
                     token=False)
    assert status == 403
    assert Playbook.load(str(tmp_path / "week3.json")).team == "Owls"


def test_another_sites_name_is_turned_away(served):
    """A page that rebinds its own domain to 127.0.0.1 still sends its own name."""
    assert _ask(served, "GET", "/", host="evil.example")[0] == 403
    assert _ask(served, "POST", "/api/save", {"path": "x", "text": "{}"}, host="evil.example")[0] == 403


def test_an_existing_file_is_replaced_only_on_a_yes(served):
    status, got = _save(served, "week3.json", _book(team="X"))
    assert status == 409 and "already exists" in got["error"]


def test_what_python_cant_read_is_never_written(served, tmp_path):
    status, got = _ask(served, "POST", "/api/save",
                       {"path": "bad.json", "text": json.dumps({"name": "B", "plays": [{"name": 3}]})})
    assert status == 400
    assert not (tmp_path / "bad.json").exists()
    assert [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"] == []


def test_a_name_gets_json_and_lands_in_the_folder(served, tmp_path):
    status, got = _save(served, "drives/opening", _book())
    assert status == 200, got
    assert (tmp_path / "drives" / "opening.json").exists()
    assert got["name"].replace("\\", "/") == "drives/opening.json"


def test_a_new_file_waits_for_the_first_save(tmp_path):
    session = S.Session(str(tmp_path), file="new.json")
    page = session.page()
    assert '"exists":false' in page
    assert not (tmp_path / "new.json").exists()
    session.save({"path": "new.json", "text": _book().to_json()})
    assert Playbook.load(str(tmp_path / "new.json")).name == "Week 3"


def test_a_file_that_isnt_a_playbook_stops_at_the_prompt(tmp_path):
    (tmp_path / "notes.json").write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ValueError):
        S.Session(str(tmp_path), file="notes.json")


def test_a_named_port_that_is_taken_is_an_error(tmp_path):
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        with pytest.raises(OSError):
            S.make_server(S.Session(str(tmp_path)), port=busy.getsockname()[1])


def test_the_default_port_moves_over_when_taken(tmp_path, monkeypatch):
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        taken = busy.getsockname()[1]
        monkeypatch.setattr(S, "DEFAULT_PORT", taken)
        srv = S.make_server(S.Session(str(tmp_path)), port=taken)
        try:
            assert srv.server_address[1] != taken
        finally:
            srv.server_close()


def test_chalk_design_opens_a_playbook(tmp_path, monkeypatch, capsys):
    from chalktalk import cli
    _book().save(str(tmp_path / "book.json"))
    monkeypatch.chdir(tmp_path)
    started = {}
    monkeypatch.setattr(S, "serve", lambda session, port, open_browser:
                        started.update(session=session, port=port, open=open_browser))
    assert cli.main(["design", "book.json", "--no-open"]) == 0
    session = started["session"]
    assert session.file == str(tmp_path / "book.json") and started["open"] is False
    assert "Week 3" in session.page()


def test_chalk_design_says_why_a_file_wont_open(tmp_path, monkeypatch, capsys):
    from chalktalk import cli
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["design", "broken.json", "--no-open"]) == 1
    assert "Can't open broken.json" in capsys.readouterr().err
