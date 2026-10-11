"""
Where a coach's playbooks live: one folder, `Documents/chalktalk`, unless they
say otherwise (`chalk design --folder`, or the CHALKTALK_FOLDER variable).

The designer's Open dialog lists the playbooks here and opens them by their
real path, so Save writes back to the same file; Show in folder opens the
system's file manager on it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

#: How deep the Open dialog looks under the folder, and how many files it lists.
_DEPTH = 2
_LIMIT = 300


# Windows' known folders, which can live elsewhere (OneDrive moves Documents and
# the Desktop): (Data1, Data2, Data3, Data4) of each folder's id.
_DOCUMENTS = (0xFDD39AD0, 0x238F, 0x46AF, (0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
_DESKTOP = (0xB4BFCC3A, 0xDB2C, 0x424C, (0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
_PROGRAMS = (0xA77F5D77, 0x2E2B, 0x44C3, (0xA6, 0xA2, 0xAB, 0xA6, 0x01, 0x05, 0x4A, 0x51))


def known_folder(folder_id: tuple) -> Optional[Path]:
    """Where Windows keeps one of its known folders, or None off Windows or on failure."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

        d1, d2, d3, d4 = folder_id
        guid = GUID(d1, d2, d3, (ctypes.c_ubyte * 8)(*d4))
        found = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None,
                                                      ctypes.byref(found)) != 0:
            return None
        try:
            return Path(found.value)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(found)
    except (OSError, AttributeError, ValueError):
        return None


def documents() -> Path:
    """The user's Documents folder, wherever the system keeps it (OneDrive included)."""
    found = known_folder(_DOCUMENTS)
    if found:
        return found
    home = Path.home()
    return home / "Documents" if (home / "Documents").is_dir() else home


def default_folder() -> Path:
    """Documents/chalktalk, or CHALKTALK_FOLDER when it is set."""
    chosen = os.environ.get("CHALKTALK_FOLDER")
    return Path(chosen).expanduser() if chosen else documents() / "chalktalk"


def _peek(path: Path) -> Optional[dict]:
    """What the Open dialog shows for a file, or None when it isn't a play or a playbook."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("plays"), list):
        return {"kind": "book", "title": str(data.get("name") or path.stem), "plays": len(data["plays"])}
    if "assignments" in data and "formation" in data:
        return {"kind": "play", "title": str(data.get("name") or path.stem), "plays": 1}
    return None


def describe(path: Path, root: Path) -> Optional[dict]:
    """One file for the Open dialog: its name relative to the folder, when it was saved, what it holds."""
    info = _peek(path)
    if info is None:
        return None
    try:
        rel = path.resolve().relative_to(root.resolve())
        name = str(rel)
    except ValueError:
        name = str(path)
    return {"path": str(path.resolve()), "name": name,
            "modified": path.stat().st_mtime_ns // 1_000_000, **info}


def playbooks(root: Path) -> tuple[list[dict], bool]:
    """Every play and playbook under the folder, newest first, and whether there were more."""
    found: list[dict] = []
    if not root.is_dir():
        return found, False
    for folder, dirs, files in os.walk(root):
        depth = len(Path(folder).relative_to(root).parts)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")) if depth < _DEPTH else []
        for f in files:
            if f.lower().endswith(".json") and not f.startswith("."):
                entry = describe(Path(folder) / f, root)
                if entry:
                    found.append(entry)
    found.sort(key=lambda e: e["modified"], reverse=True)
    return found[:_LIMIT], len(found) > _LIMIT


def recent(paths: Iterable[str], root: Path) -> list[dict]:
    """The recent files the page remembers that are still there, in its order."""
    out = []
    for p in paths:
        if isinstance(p, str) and p:
            entry = describe(Path(p), root) if Path(p).is_file() else None
            if entry:
                out.append(entry)
    return out


def reveal(path: Path) -> None:
    """Open the system's file manager on a file (selected) or a folder."""
    path = path.resolve()
    if sys.platform == "win32":
        if path.is_file():
            subprocess.Popen(["explorer", f"/select,{path}"])
        else:
            os.startfile(str(path))                              # noqa: S606 - a folder the coach owns
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)] if path.is_file() else ["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent if path.is_file() else path)])


__all__ = ["documents", "default_folder", "playbooks", "recent", "describe", "reveal"]
