"""
chalktalk.paper — every sheet a staff prints, from one playbook.

    from chalktalk import paper

    paper.KINDS                                   # what there is to print
    html = paper.render("callsheet", book, columns=3)
    html = paper.render("qbcard", book, key="K7QM-2XRA-9FPD-HW4C", size="teen")
    paper.info("script", book, reps=2)            # ("24 reps · 50% run · 50% pass", "")

Every page is one self-contained HTML file in the paper look; open it in a
browser and print, or Save as PDF. The coded sheets (game plan, QB card, sign
boards) take the staff's key and print its fingerprint, never the key.
`chalk design` prints through here too.
"""
from __future__ import annotations

import functools
from typing import Optional, Sequence

from .callsheet import CallSheet, Wristband
from .models.play import Playbook
from .renderer import plan_sheets as PS
from .renderer import sheets as SH

#: name -> (title, what it is), in the order the designer offers them.
KINDS: dict[str, tuple[str, str]] = {
    "playbook": ("Playbook", "Every play with its diagram"),
    "callsheet": ("Call sheet", "Calls grouped by situation and numbered"),
    "wristband": ("Wristband", "The numbered grid for the forearm"),
    "script": ("Practice script", "The book as a script with looks and reps"),
    "install": ("Install book", "Plays grouped by install day"),
    "drivecards": ("Drive cards", "First calls from each start, and what follows"),
    "gameplan": ("Game plan", "The staff's master: numbers, words, codes"),
    "qbcard": ("QB card", "Coded wristband and line calls"),
    "boards": ("Sign boards", "The rack, the players' key, the signaler's sheet"),
    "scout": ("Halftime sheet", "What the log says: the numbers, the tendencies, what is left"),
}

_KEYED = {"gameplan", "qbcard", "boards"}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def call_sheet(book: Playbook) -> CallSheet:
    """The book bucketed by situation, numbered unless its plays carry numbers already."""
    sheet = CallSheet.from_playbook(book)
    return sheet if any(p.call_number for p in book.plays) else sheet.number()


def call_order(book: Playbook) -> list[str]:
    """Play ids in call-sheet order: the numbers to write into the plays."""
    return [p.id for p in CallSheet.from_playbook(book).plays]


def _script(book: Playbook, reps: int = 1, hashes: bool = False):
    from .script import Script
    script = Script(name=book.name, notes="Practice script").add_all(book.plays, reps=reps)
    return script.alternate_hashes() if hashes else script


@functools.lru_cache(maxsize=8)
def _key_bytes(secret: str) -> bytes:
    from .codes import key_bytes
    return key_bytes(secret)                      # stretched on purpose: slow, so cached


def _coded(book: Playbook, key: Optional[str]):
    """What the key draws for this game: (codes, lines, boards), each None when not in use."""
    from . import codes as K
    from .planner import plan_of
    plan = plan_of(book)
    methods = plan.calls.methods
    if not key:
        return None, None, None
    return (K.wristband(book, key, plan.name) if "wristband" in methods else None,
            K.line_calls(book, key, plan.name) if "words" in methods else None,
            K.boards(book, key, plan.name) if "boards" in methods else None)


def render(kind: str, book: Playbook, *, key: Optional[str] = None,
           per_row: int = 2, columns: int = 2, size: str = "adult", copies: int = 1,
           reps: int = 1, hashes: bool = False, level: Optional[str] = None,
           hide: Sequence[str] = ()) -> str:
    """
    One printable page. `per_row` is diagrams across (playbook, install book),
    `columns` the call sheet's, `size` and `copies` the wristband inserts', and
    `reps` and `hashes` the practice script's. `hide` leaves diagram layers out.
    A sheet that needs something the book or the key doesn't have raises
    ValueError saying what.
    """
    if kind == "playbook":
        return SH.playbook_html(book, columns=per_row, level=level, hide=hide)
    if kind == "install":
        return SH.install_book_html(book, columns=per_row, level=level, hide=hide)
    if kind == "callsheet":
        return SH.call_sheet_html(call_sheet(book), columns=columns)
    if kind == "wristband":
        return SH.wristband_html(Wristband.from_call_sheet(call_sheet(book)), size=size, copies=copies)
    if kind == "script":
        return SH.script_html(_script(book, reps, hashes))
    if kind == "drivecards":
        return PS.drive_cards_html(book)
    if kind == "scout":
        return PS.halftime_html(book)
    if kind not in KINDS:
        raise ValueError(f"Nothing called {kind!r} to print; there is {', '.join(KINDS)}")
    from .planner import plan_of
    methods = plan_of(book).calls.methods
    codes, lines, boards = _coded(book, key)
    if kind == "gameplan":
        return PS.game_plan_html(book, codes=codes, boards=boards, lines=lines)
    if kind == "qbcard":
        if not codes and not lines:
            raise ValueError("Set a key first" if ("wristband" in methods or "words" in methods)
                             else "Choose wristband numbers or line calls first")
        return PS.qb_card_html(book, codes=codes, lines=lines, size=size, copies=copies)
    if not boards:
        raise ValueError("Set a key first" if "boards" in methods else "Turn on sign boards first")
    return PS.sign_boards_html(book, boards)


def needs_key(kind: str, book: Playbook) -> bool:
    """Whether this sheet prints codes, words or boards the plan calls with, so a key matters."""
    from .planner import plan_of
    methods = plan_of(book).calls.methods
    if kind == "boards":
        return "boards" in methods
    return kind in ("gameplan", "qbcard") and ("wristband" in methods or "words" in methods)


def info(kind: str, book: Playbook, *, key: Optional[str] = None,
         reps: int = 1, hashes: bool = False) -> tuple[str, str]:
    """A line saying what the sheet will hold, and a hint when something is missing."""
    from . import planner, scout
    summary, hint = _plural(len(book.plays), "play"), ""
    if kind in ("callsheet", "wristband"):
        sheet = CallSheet.from_playbook(book)
        summary = (f"{_plural(len(sheet.plays), 'call')} in "
                   f"{_plural(len(sheet.sections), 'section')}")
        if len(sheet.sections) == 1 and sheet.sections[0].title == "Base":
            hint = ("No play has a situation yet, so every call lands in Base. "
                    "Set down, distance and the ball in the play sheet.")
    elif kind == "script":
        b = _script(book, reps, hashes).balance()
        summary = f"{b['total_reps']} reps · {b['run_pct']}% run · {b['pass_pct']}% pass"
    elif kind == "install":
        days = SH.install_days(book)
        count = sum(1 for d, _ in days if d is not None)
        later = next((plays for d, plays in days if d is None), None)
        summary = _plural(count, "day") + (f" · {len(later)} not scheduled" if later else "")
        if not count:
            hint = "No play has an install day yet. Set it in the play sheet."
    elif kind == "scout":
        r = scout.report(book)
        summary = f"{r.on} of {r.snaps} snaps on schedule" if r.snaps else "nothing logged yet"
        if not r.snaps:
            hint = "Log a drive in the Game panel and the halftime sheet fills itself."
    elif kind == "drivecards":
        summary = f"{len(planner.DRIVE_CARD_STARTS)} starts, three calls each"
        if not planner.openers(book):
            hint = 'No opening script yet: label plays "Openers" in the play sheet.'
    elif kind in _KEYED:
        from .codes import fingerprint
        plan = planner.plan_of(book)
        methods = plan.calls.methods
        summary = _plural(len(planner.numbers(book)), "call")
        if key:
            summary += f" · fingerprint {fingerprint(_key_bytes(key), plan.name)}"
        keyed = needs_key(kind, book)
        if kind == "qbcard" and "wristband" not in methods and "words" not in methods:
            hint = "Choose wristband numbers or line calls in the drive planner, under Calling the plays."
        elif kind == "boards" and "boards" not in methods:
            hint = "Turn on sign boards in the drive planner, under Calling the plays."
        elif keyed and not key:
            hint = "Set a key in the drive planner to print codes. The key is never saved in the playbook."
        elif keyed and (plan.name or "Game plan") == "Game plan":
            hint = "Name the game in the drive planner (Wk 3 vs Central) so each week gets fresh codes."
    return summary, hint


__all__ = ["KINDS", "render", "info", "needs_key", "call_sheet", "call_order"]
