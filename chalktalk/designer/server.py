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

import json
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


# ── printing: the page sends the book it has, Python prints it ───────────────

def _book(body: dict) -> Playbook:
    return Playbook.model_validate(body.get("book") or {})


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
}


class _Handler(BaseHTTPRequestHandler):
    server_version = "chalktalk"

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
            return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        session: Session = self.server.session
        if not self._host_ok() or not secrets.compare_digest(
                self.headers.get("X-Chalktalk-Token", ""), session.token):
            return self._json(403, {"error": "Not from this designer"})
        route = ROUTES.get(self.path.split("?", 1)[0].removeprefix("/api/"))
        if route is None:
            return self._json(404, {"error": "No such request"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > _MAX_BODY:
            return self._json(413, {"error": "That is too big to send"})
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


def serve(session: Session, port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    """Serve until Ctrl+C."""
    srv = make_server(session, port)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Designer: {url}")
    if session.file:
        print(f"File:     {session.file}"
              + ("" if os.path.exists(session.file) else "  (new: Save creates it)"))
    else:
        print(f"Folder:   {session.root}  (Save asks for a file name)")
    print("Press Ctrl+C to stop.", flush=True)    # before the wait, even when piped
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        srv.server_close()


__all__ = ["Session", "serve", "make_server", "ROUTES", "DEFAULT_PORT"]
