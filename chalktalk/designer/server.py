"""
chalktalk.designer.server — the designer, run on your own machine.

`chalk design` starts this: a small web server on 127.0.0.1 that serves the
designer page and writes the playbook files you name, then opens your browser
on it. It listens on this machine only. The page carries a token, and every
request that does anything has to send it back, so no other site can drive it.

    chalk design week3.json        # edit that file; Save writes it back
    chalk design                   # a blank book; Save asks for a file name

Reload the page to pick up a change made to the file from Python. Work that
hasn't been saved survives a reload as long as the file hasn't changed since.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
import webbrowser
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from ..models.play import Play, Playbook
from . import build

DEFAULT_PORT = 8765
_TRIES = 20                   # ports to try past the default before taking any free one
_MAX_BODY = 32 * 1024 * 1024


class Conflict(Exception):
    """Saving would replace a file the coach didn't say to replace."""


def _mtime(path: str) -> Optional[int]:
    """Milliseconds, so the number survives a trip through JavaScript."""
    try:
        return os.stat(path).st_mtime_ns // 1_000_000
    except OSError:
        return None


def _parse(text: str):
    """A play or a playbook, from its JSON, or ValueError saying which it isn't."""
    data = json.loads(text)
    if isinstance(data, dict) and isinstance(data.get("plays"), list):
        return Playbook.model_validate(data)
    if isinstance(data, dict) and "assignments" in data:
        return Play.model_validate(data)
    raise ValueError("That isn't a play or a playbook")


class Session:
    """One `chalk design` run: the folder it started in, maybe a file, a token."""

    def __init__(self, root: str = ".", file: Optional[str] = None,
                 play: Optional[Play] = None, level: str = "nfl", theme: str = "turf"):
        self.root = os.path.abspath(root)
        if file and os.path.isfile(os.path.join(self.root, file)):
            self.file = os.path.abspath(os.path.join(self.root, file))   # as named, whatever it ends in
        else:
            self.file = self.resolve(file) if file else None
        self.play = play
        self.level = level
        self.theme = theme
        self.token = secrets.token_urlsafe(24)
        self.started = time.monotonic()
        self.seen: Optional[float] = None     # the last time a page asked for anything
        self.bye: Optional[float] = None      # when a page said it was closing
        if self.file and os.path.exists(self.file):
            self.read(self.file)          # fail now, at the prompt, not in the browser

    def resolve(self, path: str) -> str:
        """A name the coach typed, as a full path: relative to the folder, .json added."""
        path = (path or "").strip()
        if not path:
            raise ValueError("Name the file")
        if not path.lower().endswith(".json"):
            path += ".json"
        return os.path.abspath(os.path.join(self.root, os.path.expanduser(path)))

    def name(self, path: str) -> str:
        """How the page shows a file: relative to the folder when it is inside it."""
        rel = os.path.relpath(path, self.root)
        return path if rel.startswith("..") or os.path.isabs(rel) else rel

    @staticmethod
    def read(path: str):
        with open(path, encoding="utf-8") as fh:
            return _parse(fh.read())

    def page(self) -> str:
        """The designer, opened on the session's file when there is one."""
        play, book, kind = self.play, None, "book"
        if self.file and os.path.exists(self.file):
            got = self.read(self.file)
            if isinstance(got, Playbook):
                book, play = got, None
            else:
                play, kind = got, "play"
        file = None
        if self.file:
            file = {"name": self.name(self.file), "path": self.file, "kind": kind,
                    "exists": os.path.exists(self.file), "mtime": _mtime(self.file)}
        return build(play=play, playbook=book, level=self.level, theme=self.theme,
                     server={"token": self.token, "folder": self.root, "file": file})

    def save(self, body: dict) -> dict:
        """Write what the page sends, once it is sure Python can read it back."""
        path = self.resolve(body.get("path", ""))
        text = body.get("text")
        if not isinstance(text, str):
            raise ValueError("Nothing to save")
        _parse(text)
        if os.path.exists(path) and not body.get("overwrite"):
            raise Conflict(f"{self.name(path)} already exists")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
        return {"path": path, "name": self.name(path), "mtime": _mtime(path)}


# ── the book the page sends ──────────────────────────────────────────────────
# Every panel sends the book it is showing, and most ask again about the same
# one: reading a big book back into Python costs more than answering, so the
# last few are kept, by their contents.
_BOOKS: OrderedDict[str, Playbook] = OrderedDict()
_BOOKS_LOCK = threading.Lock()


def _book(body: dict) -> Playbook:
    raw = body.get("book") or {}
    key = hashlib.sha1(json.dumps(raw, separators=(",", ":")).encode("utf-8")).hexdigest()
    with _BOOKS_LOCK:
        if key in _BOOKS:
            _BOOKS.move_to_end(key)
            return _BOOKS[key]
    book = Playbook.model_validate(raw)
    with _BOOKS_LOCK:
        _BOOKS[key] = book
        while len(_BOOKS) > 8:
            _BOOKS.popitem(last=False)
    return book


def _index(body: dict, name: str) -> Optional[int]:
    value = body.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


# ── the panels: what each shows, worked out in Python (views.py) ─────────────

def play_view(session: Session, body: dict) -> dict:
    from . import views
    return views.play_view(Play.model_validate(body.get("play") or {}))


def plan_view(session: Session, body: dict) -> dict:
    from . import views
    return views.plan_view(_book(body), _index(body, "script"))


def game_view(session: Session, body: dict) -> dict:
    from ..models import DriveState
    from . import views
    return views.game_view(_book(body), DriveState.model_validate(body.get("state") or {}),
                           _index(body, "script"))


def draft(session: Session, body: dict) -> dict:
    from . import views
    return views.draft(_book(body))


def fill_script(session: Session, body: dict) -> dict:
    from ..models import DriveScript
    from . import views
    return views.fill_script(_book(body), DriveScript.model_validate(body.get("script") or {}))


def advance(session: Session, body: dict) -> dict:
    from ..models import DriveState
    from . import views
    return views.advance(DriveState.model_validate(body.get("state") or {}),
                         str(body.get("outcome", "")), float(body.get("gain") or 0))


# ── the coach's playbooks: the folder, opening by path, the file manager ─────

def files(session: Session, body: dict) -> dict:
    """The Open dialog: the recent files the page remembers, and every playbook in the folder."""
    from . import home
    root = Path(session.root)
    listed, more = home.playbooks(root)
    return {"folder": session.root, "files": listed, "more": more,
            "recent": home.recent(body.get("recent") or [], root)}


def open_file(session: Session, body: dict) -> dict:
    """A play or playbook by its path, so Save writes it back where it came from."""
    path = Path(str(body.get("path") or ""))
    path = (path if path.is_absolute() else Path(session.root) / path).resolve()
    if not path.is_file():
        raise ValueError(f"{path.name} isn't there any more")
    text = path.read_text(encoding="utf-8")
    kind = "book" if isinstance(_parse(text), Playbook) else "play"
    return {"data": json.loads(text), "kind": kind, "path": str(path),
            "name": session.name(str(path)), "mtime": _mtime(str(path))}


def reveal(session: Session, body: dict) -> dict:
    """Show a file in the system's file manager, or the folder when there's no file yet."""
    from . import home
    target = Path(str(body.get("path") or session.root))
    if not target.exists():
        target = Path(session.root)
        target.mkdir(parents=True, exist_ok=True)
    home.reveal(target)
    return {}


# ── the page is still there: what lets a quiet designer stop on its own ──────

def ping(session: Session, body: dict) -> dict:
    session.bye = None
    return {}


def bye(session: Session, body: dict) -> dict:
    session.bye = time.monotonic()
    return {}


# ── printing: the page sends the book it has, Python prints it ───────────────


def _print_args(body: dict) -> tuple[str, dict]:
    """The sheet and its choices, kept to what each choice can be."""
    from .. import paper
    from ..renderer.sheets import INSERT_SIZES
    kind = body.get("kind")
    if kind not in paper.KINDS:
        raise ValueError(f"Nothing called {kind!r} to print")

    def num(name: str, low: int, high: int, default: int) -> int:
        try:
            return min(high, max(low, int(body.get(name, default))))
        except (TypeError, ValueError):
            return default

    return kind, {
        "key": body.get("key") or None,          # used for this sheet, never kept
        "per_row": num("per_row", 1, 2, 2), "columns": num("columns", 1, 3, 2),
        "size": body.get("size") if body.get("size") in INSERT_SIZES else "adult",
        "copies": num("copies", 1, 20, 1), "reps": num("reps", 1, 5, 1),
        "hashes": bool(body.get("hashes")),
        "level": body.get("level") if body.get("level") in ("nfl", "ncaa", "hs") else None,
        "hide": [h for h in body.get("hide") or [] if isinstance(h, str)],
    }


def print_sheet(session: Session, body: dict) -> dict:
    from .. import paper
    kind, opts = _print_args(body)
    return {"html": paper.render(kind, _book(body), **opts)}


def print_info(session: Session, body: dict) -> dict:
    from .. import paper
    kind, opts = _print_args(body)
    summary, hint = paper.info(kind, _book(body), key=opts["key"], reps=opts["reps"],
                               hashes=opts["hashes"])
    return {"summary": summary, "hint": hint}


def call_order(session: Session, body: dict) -> dict:
    from .. import paper
    return {"order": paper.call_order(_book(body))}


#: What the page can ask for, by name: POST /api/<name> with a JSON body.
ROUTES: dict[str, Callable[[Session, dict], dict]] = {
    "save": Session.save,
    "print": print_sheet,
    "print_info": print_info,
    "call_order": call_order,
    "play_view": play_view,
    "plan_view": plan_view,
    "game_view": game_view,
    "draft": draft,
    "fill_script": fill_script,
    "advance": advance,
    "files": files,
    "open": open_file,
    "reveal": reveal,
    "ping": ping,
    "bye": bye,
}


class _Handler(BaseHTTPRequestHandler):
    server_version = "chalktalk"
    # Keep the connection open between requests: the page asks often, and a new
    # connection to "localhost" can wait on IPv6 before it tries 127.0.0.1.
    protocol_version = "HTTP/1.1"

    def _host_ok(self) -> bool:
        # Only this machine's own names: a page on another site that rebinds
        # its domain to 127.0.0.1 still sends its own name here.
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _send(self, status: int, body: bytes, kind: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj: dict) -> None:
        self._send(status, json.dumps(obj).encode("utf-8"), "application/json")

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json(403, {"error": "Open the designer from the address chalk design printed"})
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            try:
                html = self.server.session.page()
            except (OSError, ValueError, ValidationError) as e:
                return self._send(500, f"Could not open the file: {e}".encode("utf-8"),
                                  "text/plain; charset=utf-8")
            self.server.session.seen = time.monotonic()
            return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/favicon.ico":
            from .icon import png
            return self._send(200, png(32), "image/png")
        if path == "/chalktalk":
            # Who is listening here, so a second launch opens this one instead of
            # starting another. The folder only as a fingerprint: no paths.
            return self._json(200, {"app": "chalktalk", "folder": _fingerprint(self.server.session.root)})
        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def _refuse(self, status: int, error: str) -> None:
        # The body is never read, so this connection can't carry another request.
        self.close_connection = True
        self._json(status, {"error": error})

    def do_POST(self) -> None:
        session: Session = self.server.session
        if not self._host_ok() or not secrets.compare_digest(
                self.headers.get("X-Chalktalk-Token", ""), session.token):
            return self._refuse(403, "Not from this designer")
        route = ROUTES.get(self.path.split("?", 1)[0].removeprefix("/api/"))
        if route is None:
            return self._refuse(404, "No such request")
        length = int(self.headers.get("Content-Length") or 0)
        if length > _MAX_BODY:
            return self._refuse(413, "That is too big to send")
        session.seen = time.monotonic()
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            return self._json(200, route(session, body))
        except Conflict as e:
            return self._json(409, {"error": str(e)})
        except ValidationError as e:
            return self._json(400, {"error": f"Python can't read that back: {e.errors()[0]['msg']}"})
        except (ValueError, OSError) as e:
            return self._json(400, {"error": str(e)})

    def log_message(self, format: str, *args) -> None:   # noqa: A002 - the stdlib's name
        pass                                              # the terminal is for the address


class _Server(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second server share a port that is in use,
    # so a second `chalk design` would answer for the first one.
    allow_reuse_address = os.name != "nt"


def make_server(session: Session, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """
    Bind on 127.0.0.1. The default port is fixed so the browser keeps the same
    working copy from one run to the next; if it is taken, the next free one.
    A port named on the command line is that port or nothing; 0 takes any.
    """
    ports = [DEFAULT_PORT + i for i in range(_TRIES)] + [0] if port == DEFAULT_PORT else [port]
    for p in ports:
        try:
            srv = _Server(("127.0.0.1", p), _Handler)
        except OSError as e:
            failure = e
            continue
        srv.session = session
        return srv
    raise failure


def _fingerprint(folder: str) -> str:
    return hashlib.sha1(os.path.normcase(os.path.abspath(folder)).encode("utf-8")).hexdigest()[:12]


def running_at(port: int = DEFAULT_PORT, folder: Optional[str] = None) -> bool:
    """Whether a chalktalk designer already answers on this port (for `folder`, if named)."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/chalktalk", timeout=1) as r:
            there = json.load(r)
    except (OSError, ValueError):
        return False
    if not isinstance(there, dict) or there.get("app") != "chalktalk":
        return False                                     # something else lives on this port
    return folder is None or there.get("folder") == _fingerprint(folder)


# A quiet designer (the shortcut's) stops on its own: when nobody ever opened it,
# a while after the last page said goodbye (long enough for a reload, or for a
# tab in the background, which may only check in once a minute), or after a
# long silence (a browser that closed without saying so).
_NOBODY_CAME = 120
_AFTER_BYE = 75
_SILENCE = 600


def _should_stop(session: Session, now: float) -> bool:
    if session.seen is None:
        return now - session.started > _NOBODY_CAME
    if session.bye is not None and now - session.bye > _AFTER_BYE:
        return True
    return now - session.seen > _SILENCE


def _watch(srv: ThreadingHTTPServer, every: float = 5.0) -> None:
    while not _should_stop(srv.session, time.monotonic()):
        time.sleep(every)
    srv.shutdown()


def serve(session: Session, port: int = DEFAULT_PORT, open_browser: bool = True,
          quiet: bool = False) -> None:
    """Serve until Ctrl+C, or, `quiet`, until the page has gone."""
    srv = make_server(session, port)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Designer: {url}")
    if session.file:
        print(f"File:     {session.file}"
              + ("" if os.path.exists(session.file) else "  (new: Save creates it)"))
    else:
        print(f"Folder:   {session.root}  (Save asks for a file name)")
    print("Stops a little after you close the page." if quiet else "Press Ctrl+C to stop.",
          flush=True)                                    # before the wait, even when piped
    if quiet:
        threading.Thread(target=_watch, args=(srv,), daemon=True).start()
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        srv.server_close()


__all__ = ["Session", "serve", "make_server", "running_at", "ROUTES", "DEFAULT_PORT"]
