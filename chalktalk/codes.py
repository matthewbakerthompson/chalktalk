"""
chalktalk.codes — scrambled wristband numbers, line-call words and sign boards.

A wristband is a codebook, and every snap an opponent films hands them one
entry of it. What protects it is not a clever scheme but a short life: fresh
codes each half or quarter, extra codes for the plays called most so no number
repeats, dead codes that mean "wait", and a secret the opponent does not have.
The method is public (chalktalk is open to read); only the key is secret.

Everything comes from a key, the game's name and the period, through HMAC-SHA256,
so the same key prints the same cards on any machine: the head coach and the
signaler can print their copies separately and check the fingerprint. The key
is never stored in the playbook, the plan or any printout.

    key = new_key()                       # "K7QM-2XRA-9FPD-HW4C": write it down
    sheet = wristband(book, key, "Wk 3 Central")
    sheet.fingerprint, sheet.cards[0].codes

The browser designer carries a byte-for-byte twin (a pure JavaScript SHA-256,
so it works from a local file with no network); a test holds the two together.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Iterator, Optional

from pydantic import BaseModel

from .models.play import Playbook
from .planner import numbers, plan_of

# Crockford's base32, without the letters that read like digits.
KEY_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
SALT = b"chalktalk-codes-v1"
ITERATIONS = 100_000

PERIODS = {
    "game": ["Game"],
    "half": ["1st half", "2nd half"],
    "quarter": ["1st quarter", "2nd quarter", "3rd quarter", "4th quarter"],
}


def new_key() -> str:
    """A random key: 16 characters, 80 bits, in groups of four."""
    raw = "".join(secrets.choice(KEY_ALPHABET) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def normalize(secret: str) -> str:
    """Case, spaces and dashes don't matter, so a key read aloud still works."""
    return re.sub(r"[\s\-]+", "", secret or "").upper()


def key_bytes(secret: str) -> bytes:
    """Stretch a key or passphrase so a guessed one costs real time to check."""
    if not normalize(secret):
        raise ValueError("The key is empty")
    return hashlib.pbkdf2_hmac("sha256", normalize(secret).encode("utf-8"),
                               SALT, ITERATIONS, 32)


def _mac(key: bytes, label: str) -> bytes:
    return hmac.new(key, label.encode("utf-8"), hashlib.sha256).digest()


def fingerprint(key: bytes, game: str) -> str:
    """Eight characters every printed card carries, so the staff can check they match."""
    h = _mac(key, f"{game}|fingerprint").hex().upper()
    return f"{h[:4]}-{h[4:8]}"


class _Stream:
    """Unsigned 32-bit numbers from HMAC(key, label|block), in order."""

    def __init__(self, key: bytes, label: str):
        self.words = self._words(key, label)

    @staticmethod
    def _words(key: bytes, label: str) -> Iterator[int]:
        block = 0
        while True:
            digest = _mac(key, f"{label}|{block}")
            for i in range(0, 32, 4):
                yield int.from_bytes(digest[i:i + 4], "big")
            block += 1

    def below(self, n: int) -> int:
        """Uniform in [0, n), by rejection, so no code is likelier than another."""
        limit = (2 ** 32 // n) * n
        while True:
            v = next(self.words)
            if v < limit:
                return v % n

    def shuffle(self, items: list) -> list:
        out = list(items)
        for i in range(len(out) - 1, 0, -1):
            j = self.below(i + 1)
            out[i], out[j] = out[j], out[i]
        return out


class CodeCard(BaseModel):
    period: str
    codes: dict[str, str]        # code -> play id
    dead: list[str] = []         # codes that mean "wait for the next signal"


class CodeSheet(BaseModel):
    game: str
    fingerprint: str
    plays: list[str]             # the plays on the card, in call-sheet order
    cards: list[CodeCard]


def wristband(book: Playbook, secret: str, game: str) -> CodeSheet:
    """
    The QB's coded cards for one game, one per period of the plan's rotation.
    Each play gets a code; the plan's top calls get extra codes so the most
    frequent calls don't repeat a number; dead codes fill the rest of the
    signal. No code keeps its play from one period to the next.
    """
    key = key_bytes(secret)
    calls = plan_of(book).calls
    plays = list(numbers(book))
    top = plays[:calls.top_calls]
    low, high = (10, 99) if calls.digits == 2 else (100, 999)
    space = [str(c) for c in range(low, high + 1)]
    need = len(plays) + len(top) * calls.extra_codes + calls.dead_codes
    if need > len(space):
        raise ValueError(f"{need} codes needed but {calls.digits} digits give only "
                         f"{len(space)}: use 3 digits, or fewer extra and dead codes.")
    wanted = plays + [pid for _ in range(calls.extra_codes) for pid in top]
    cards: list[CodeCard] = []
    before: dict[str, str] = {}
    for period in PERIODS[calls.rotate]:
        pool = _Stream(key, f"{game}|{period}|wristband").shuffle(space)
        codes = dict(zip(pool, wanted))
        spare = pool[len(wanted):]
        # No code carries its meaning into the next period: trade it for a spare.
        for code in list(codes):
            if before.get(code) == codes[code]:
                swap = next(c for c in spare if before.get(c) != codes[code])
                spare.remove(swap)
                spare.append(code)
                codes[swap] = codes.pop(code)
        dead = spare[:calls.dead_codes]
        cards.append(CodeCard(period=period,
                              codes=dict(sorted(codes.items(), key=lambda kv: int(kv[0]))),
                              dead=sorted(dead, key=int)))
        before = codes
    return CodeSheet(game=game, fingerprint=fingerprint(key, game), plays=plays, cards=cards)


# ── line calls: what the quarterback says at the line ────────────────────────
# Every play gets a code word for the game, drawn from the key, so the team can
# learn the week's words in practice; a word the coach set on a play stays.
# The quarterback leads each call with a colour, twice ("Blue... Tiger, Blue...
# Tiger"), and only the live colour's call is real: any other colour is a dummy
# and the call already made stands. The live colour changes every period.
# Words heard on film are burned: they become dummies and never mean a play
# again. Words are short, sound unlike each other, and avoid colours, numbers,
# snap words and play names the team might already use.
LIVE_COLORS = ["Red", "Blue", "Green", "White", "Black", "Purple", "Brown", "Silver"]
WORDS = [
    "Tiger", "Falcon", "Badger", "Cobra", "Bison", "Hornet", "Mustang", "Raven",
    "Viper", "Gator", "Rhino", "Jaguar", "Bronco", "Otter", "Moose", "Walrus",
    "Denver", "Dallas", "Memphis", "Tulsa", "Phoenix", "Vegas", "Detroit", "Seattle",
    "Fresno", "Buffalo", "Nashville", "Raleigh", "Boston", "Toledo", "Rocket", "Hammer",
    "Anchor", "Laser", "Magnet", "Thunder", "Blizzard", "Tornado", "Comet", "Canyon",
    "Glacier", "Jungle", "Marble", "Pepper", "Pickle", "Pretzel", "Waffle", "Taco",
    "Yogurt", "Zipper", "Igloo", "Kayak", "Noodle", "Banjo", "Cactus", "Domino",
    "Gumbo", "Hippo", "Mango", "Zebra", "Lemon", "Wizard", "Pirate", "Cowboy",
]


def _word(text: Optional[str]) -> str:
    return " ".join(str(text or "").split())


class LineSheet(BaseModel):
    game: str
    fingerprint: str
    words: dict[str, str]        # word -> play id, for the whole game
    dead: list[str] = []         # words that mean nothing: dummies and burned words
    live: dict[str, str]         # period -> the live colour


def _live_colors(key: bytes, game: str, periods: list[str]) -> dict[str, str]:
    stream, live, last = _Stream(key, f"{game}|live"), {}, None
    for period in periods:
        options = [c for c in LIVE_COLORS if c != last]
        last = live[period] = options[stream.below(len(options))]
    return live


def line_calls(book: Playbook, secret: str, game: str) -> LineSheet:
    """The game's code words, dummy words and the live colour for each period."""
    key = key_bytes(secret)
    calls = plan_of(book).calls
    by_id = {p.id: p for p in book.plays}
    burned = []
    for w in map(_word, calls.burned_words):
        if w and w.lower() not in {b.lower() for b in burned}:
            burned.append(w)
    own = {pid: _word(by_id[pid].word) for pid in numbers(book) if _word(by_id[pid].word)}
    taken = {w.lower() for w in list(own.values()) + burned}
    pool = [w for w in _Stream(key, f"{game}|words").shuffle(WORDS) if w.lower() not in taken]
    words: dict[str, str] = {}
    for pid in numbers(book):
        w = own.get(pid)
        if not w or w.lower() in {x.lower() for x in words}:
            if not pool:
                raise ValueError(f"Only {len(WORDS)} words to draw from: set your own words "
                                 f"on some plays, or burn fewer.")
            w = pool.pop(0)
        words[w] = pid
    dead = pool[:calls.dummy_words] + [w for w in burned if w.lower() not in
                                       {x.lower() for x in words}]
    return LineSheet(game=game, fingerprint=fingerprint(key, game), words=words,
                     dead=sorted(dead, key=str.lower),
                     live=_live_colors(key, game, PERIODS[calls.rotate]))


# ── sign boards ──────────────────────────────────────────────────────────────
# A board carries two or four symbols, and only one cell is live: which one
# changes every period, from the key. What each symbol means holds for the
# game, so players learn one list during the week; the other cells are decoys
# drawn from the same symbols, so every symbol turns up on many boards and a
# camera sees a mix, not a code. One rack of boards serves the whole game: a
# board means one call while its top-left cell is live and another after the
# half, and no board shows a symbol twice.
#
# A symbol is a shape in a colour with a black outline, on white. The five
# colours stay apart under all three kinds of colour blindness, and a meaning
# never rests on colour alone. There's no hexagon or octagon: at a distance
# their corners blur into a circle.
BOARD_SHAPES = ["circle", "square", "triangle", "diamond", "star", "plus", "x", "ring"]
BOARD_COLORS = {
    "black": "#000000", "blue": "#0072B2", "red": "#D55E00",
    "yellow": "#F0E442", "sky": "#56B4E9",
}
# How many symbol meanings players reliably keep in a game, by level.
BOARD_MEMORY = {"hs": 12, "ncaa": 24, "nfl": 24}


def board_units(book: Playbook) -> list[str]:
    """What gets a symbol: each play, or each series when the plan says so."""
    calls = plan_of(book).calls
    by_id = {p.id: p for p in book.plays}
    out: list[str] = []
    for pid in numbers(book):
        series = (by_id[pid].series or "").strip()
        unit = f"series:{series}" if calls.boards_by == "series" and series else pid
        if unit not in out:
            out.append(unit)
    return out


class BoardSheet(BaseModel):
    game: str
    fingerprint: str
    cells: int                   # symbols on each board: 1, 2 or 4
    units: list[str]
    symbols: dict[str, str]      # unit (play id, or "series:<name>") -> "shape/color"
    live: dict[str, int]         # period -> the live cell (0 top left, then across)
    boards: list[list[str]]      # the rack: every board, cell by cell


def boards(book: Playbook, secret: str, game: str) -> BoardSheet:
    """The game's symbols, the live cell for each period, and the rack of boards."""
    key = key_bytes(secret)
    calls = plan_of(book).calls
    symbols = [f"{shape}/{color}" for color in BOARD_COLORS for shape in BOARD_SHAPES]
    units = board_units(book)
    n = len(units) + calls.dummy_boards
    if n > len(symbols):
        raise ValueError(f"{n} boards needed but only {len(symbols)} symbols: "
                         f"use a symbol per series, or fewer dummies.")
    pool = _Stream(key, f"{game}|boards").shuffle(symbols)
    meaning = dict(zip(units, pool))
    blanks = pool[len(units):n]               # the dummies' live cells: they mean nothing
    cells = calls.board_cells

    stream, live, last = _Stream(key, f"{game}|boards|live"), {}, None
    for period in PERIODS[calls.rotate]:
        options = [c for c in range(cells) if c != last] or [0]
        last = live[period] = options[stream.below(len(options))]

    # Every cell that is ever live carries each meaning on exactly one board.
    rack: list[list[Optional[str]]] = [[None] * cells for _ in range(n)]
    for c in sorted(set(live.values())):
        column = _Stream(key, f"{game}|boards|cell{c}").shuffle(list(meaning.values()) + blanks)
        for i in range(n):
            if column[i] in rack[i]:          # no board shows a symbol twice
                j = next((j for j in [*range(i + 1, n), *range(i)]
                          if column[j] not in rack[i] and column[i] not in rack[j]), None)
                if j is not None:
                    column[i], column[j] = column[j], column[i]
        for i in range(n):
            rack[i][c] = column[i]
    # The cells that are never live: decoys from all the symbols.
    stream = _Stream(key, f"{game}|boards|decoys")
    for row in rack:
        for c in range(cells):
            while row[c] is None:
                s = symbols[stream.below(len(symbols))]
                if s not in row:
                    row[c] = s
    return BoardSheet(game=game, fingerprint=fingerprint(key, game), cells=cells, units=units,
                      symbols=meaning, live=live, boards=rack)


__all__ = ["KEY_ALPHABET", "PERIODS", "new_key", "normalize", "key_bytes", "fingerprint",
           "CodeCard", "CodeSheet", "wristband", "LIVE_COLORS", "WORDS", "LineSheet",
           "line_calls", "BOARD_SHAPES", "BOARD_COLORS", "BOARD_MEMORY", "board_units",
           "BoardSheet", "boards"]
