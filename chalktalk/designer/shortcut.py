"""
`chalk shortcut`: a Chalktalk icon where the system keeps them, so a coach
opens the designer with a double-click and never sees a terminal.

    Windows   Desktop and Start menu shortcuts, run without a console window
    macOS     ~/Applications/Chalktalk.app
    Linux     a launcher in ~/.local/share/applications, and one on the Desktop

Each runs `python -m chalktalk design --quiet` with the Python chalktalk is
installed in: the designer opens in the browser, a second double-click opens
the same page again, and it stops a little after the page is closed.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

from . import home
from .icon import ico, png

NAME = "Chalktalk"
_DESCRIPTION = "Draw, plan and print football plays"


def data_dir() -> Path:
    """Where chalktalk keeps its own files (the shortcut's icon), never the coach's."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "chalktalk"


def _python(windowless: bool) -> str:
    """The Python chalktalk runs in; on Windows its no-console twin when asked."""
    exe = Path(sys.executable)
    if windowless and sys.platform == "win32" and exe.with_name("pythonw.exe").exists():
        return str(exe.with_name("pythonw.exe"))
    return str(exe)


def _arguments(folder: Optional[str]) -> list[str]:
    args = ["-m", "chalktalk", "design", "--quiet"]
    if folder:
        args += ["--folder", str(Path(folder).expanduser().resolve())]
    return args


def places() -> list[Path]:
    """Where this system keeps launchers, for create() and remove()."""
    if sys.platform == "win32":
        desktop = home.known_folder(home._DESKTOP) or Path.home() / "Desktop"
        programs = (home.known_folder(home._PROGRAMS)
                    or data_dir().parent / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        return [desktop / f"{NAME}.lnk", programs / f"{NAME}.lnk"]
    if sys.platform == "darwin":
        return [Path.home() / "Applications" / f"{NAME}.app"]
    out = [Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
           / "applications" / "chalktalk.desktop"]
    if (Path.home() / "Desktop").is_dir():
        out.append(Path.home() / "Desktop" / "chalktalk.desktop")
    return out


# ── Windows: .lnk files, written by the shell's own shortcut object ──────────

_LNK = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:CT_LNK); "
        "$s.TargetPath = $env:CT_TARGET; $s.Arguments = $env:CT_ARGS; "
        "$s.WorkingDirectory = $env:CT_DIR; $s.IconLocation = $env:CT_ICON; "
        "$s.Description = $env:CT_DESC; $s.Save()")


def _windows(targets: list[Path], folder: Optional[str]) -> None:
    icon = data_dir() / "chalktalk.ico"
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_bytes(ico())
    workdir = str(Path(folder).expanduser().resolve()) if folder else str(home.default_folder())
    for lnk in targets:
        lnk.parent.mkdir(parents=True, exist_ok=True)
        # Everything goes through the environment, so no path needs quoting.
        env = {**os.environ, "CT_LNK": str(lnk), "CT_TARGET": _python(windowless=True),
               "CT_ARGS": subprocess.list2cmdline(_arguments(folder)), "CT_DIR": workdir,
               "CT_ICON": f"{icon},0", "CT_DESC": _DESCRIPTION}
        done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _LNK],
                              env=env, capture_output=True, text=True)
        if done.returncode != 0 or not lnk.exists():
            raise RuntimeError(done.stderr.strip() or f"PowerShell couldn't write {lnk}")


# ── macOS: a tiny app bundle that runs the designer ──────────────────────────

_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>{name}</string>
  <key>CFBundleDisplayName</key><string>{name}</string>
  <key>CFBundleIdentifier</key><string>io.github.matthewbakerthompson.chalktalk</string>
  <key>CFBundleExecutable</key><string>{name}</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
"""


def _mac(app: Path, folder: Optional[str]) -> None:
    macos = app / "Contents" / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)
    (app / "Contents" / "Info.plist").write_text(_PLIST.format(name=NAME), encoding="utf-8")
    run = macos / NAME
    command = " ".join(shlex.quote(a) for a in [_python(windowless=False), *_arguments(folder)])
    run.write_text(f"#!/bin/sh\nexec {command}\n", encoding="utf-8")
    run.chmod(0o755)


# ── Linux: a desktop entry ───────────────────────────────────────────────────

def _desktop_quote(arg: str) -> str:
    """An Exec argument, quoted the way the desktop-entry spec asks."""
    if not any(c in arg for c in ' \t"`$\\'):
        return arg
    return '"' + arg.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$") + '"'


def _linux(targets: list[Path], folder: Optional[str]) -> None:
    icon = data_dir() / "chalktalk.png"
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_bytes(png(256))
    exec_line = " ".join(_desktop_quote(a) for a in [_python(windowless=False), *_arguments(folder)])
    entry = (f"[Desktop Entry]\nType=Application\nName={NAME}\nComment={_DESCRIPTION}\n"
             f"Exec={exec_line}\nIcon={icon}\nTerminal=false\nCategories=Education;Sports;\n")
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry, encoding="utf-8")
        path.chmod(0o755)


def create(folder: Optional[str] = None, targets: Optional[Iterable[Path]] = None) -> list[Path]:
    """Make the launchers (or the ones named in `targets`) and return where they are."""
    targets = list(targets) if targets is not None else places()
    if sys.platform == "win32":
        _windows(targets, folder)
    elif sys.platform == "darwin":
        for app in targets:
            _mac(app, folder)
    else:
        _linux(targets, folder)
    return targets


def remove(targets: Optional[Iterable[Path]] = None) -> list[Path]:
    """Take the launchers away again; returns the ones that were there."""
    gone = []
    for path in (list(targets) if targets is not None else places()):
        if path.is_dir():
            shutil.rmtree(path)
            gone.append(path)
        elif path.exists():
            path.unlink()
            gone.append(path)
    return gone


__all__ = ["create", "remove", "places", "data_dir", "NAME"]
