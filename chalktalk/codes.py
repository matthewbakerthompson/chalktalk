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
    dummy: Optional[str] = None  # where the signal hides a digit that means nothing
    live: Optional[int] = None   # which of the signals shown each snap is real


class CodeSheet(BaseModel):
    game: str
    fingerprint: str
    style: str = "number"        # "number" (47) or "letter" (B7)
    plays: list[str]             # the plays on the card, in call-sheet order
    cards: list[CodeCard]


# ── the format of a signal ───────────────────────────────────────────────────
# chalktalk is open to read, so a team that also uses it knows every format
# there is. What it can't know is the one in use: whatever the coach leaves to
# the key is drawn from the secret, per game (the style of the codes, the
# symbols on a board) or per period (where the dummy digit hides, which of the
# signals is live), and never the same two periods running.
LETTERS = "ABCDEFGHJK"           # ten letters, no I or O to read as digits


def _space(style: str, digits: int) -> list[str]:
    """Every code a card can use: 10-99 or 100-999, or A0-K9 or A00-K99."""
    if style == "letter":
        return [f"{c}{n:0{digits - 1}d}" for c in LETTERS for n in range(10 ** (digits - 1))]
    low, high = (10, 99) if digits == 2 else (100, 999)
    return [str(c) for c in range(low, high + 1)]


def _code_order(code: str) -> tuple:
    return (0, int(code), "") if code.isdigit() else (1, 0, code)


def _pick(stream: "_Stream", options: list, last=None):
    """One of the options, never the one used last period."""
    choices = [o for o in options if o != last] or list(options)
    return choices[stream.below(len(choices))]


def code_style(key: bytes, game: str, style: str) -> str:
    return ("number", "letter")[_Stream(key, f"{game}|style").below(2)] if style == "key" else style


def _signal_rules(key: bytes, game: str, calls) -> dict[str, tuple[Optional[str], Optional[int]]]:
    """Per period: where the dummy digit goes, and which signal is live."""
    stream = _Stream(key, f"{game}|signals")
    rules, last_dummy, last_live = {}, None, None
    for period in PERIODS[calls.rotate]:
        dummy = None if calls.dummy_digit == "none" else calls.dummy_digit
        if dummy == "key":
            dummy = last_dummy = _pick(stream, ["first", "middle", "last"], last_dummy)
        live = None
        if calls.signals > 1:
            live = last_live = _pick(stream, list(range(1, calls.signals + 1)), last_live)
        rules[period] = (dummy, live)
    return rules


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
    style = code_style(key, game, calls.code_style)
    space = _space(style, calls.digits)
    need = len(plays) + len(top) * calls.extra_codes + calls.dead_codes
    if need > len(space):
        raise ValueError(f"{need} codes needed but {calls.digits} digits give only "
                         f"{len(space)}: use 3 digits, or fewer extra and dead codes.")
    wanted = plays + [pid for _ in range(calls.extra_codes) for pid in top]
    rules = _signal_rules(key, game, calls)
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
        dummy, live = rules[period]
        cards.append(CodeCard(period=period,
                              codes=dict(sorted(codes.items(), key=lambda kv: _code_order(kv[0]))),
                              dead=sorted(dead, key=_code_order), dummy=dummy, live=live))
        before = codes
    return CodeSheet(game=game, fingerprint=fingerprint(key, game), style=style,
                     plays=plays, cards=cards)


# ── line calls: what the quarterback says at the line ────────────────────────
# Every play gets a code word for the game, drawn from the key, so the team can
# learn the week's words in practice; a word the coach set on a play stays.
# By default the quarterback leads each call with a colour ("Blue... Tiger")
# and only the live colour's call is real: any other colour is a dummy and the
# call already made stands. The live signal can be a number or the team's own
# words instead, or there can be none: he makes two or three calls and the key
# says which one counts. Whatever is live changes every period.
# Words heard on film are burned: they become dummies and never mean a play
# again. The lists are short words that sound unlike each other, and avoid
# colours, numbers, snap words and the names of plays and coverages.
WORD_LISTS: dict[str, list[str]] = {
    "animals": [
        "Tiger", "Falcon", "Badger", "Cobra", "Bison", "Hornet", "Mustang", "Raven",
        "Viper", "Gator", "Rhino", "Jaguar", "Bronco", "Otter", "Moose", "Walrus",
        "Hippo", "Zebra", "Panther", "Beaver", "Coyote", "Donkey", "Eagle", "Ferret",
        "Gecko", "Heron", "Iguana", "Jackal", "Koala", "Lizard", "Mongoose", "Narwhal",
        "Ocelot", "Pelican", "Puffin", "Rooster", "Parrot", "Toucan", "Turkey", "Weasel",
        "Wombat", "Yak", "Llama", "Camel", "Hyena", "Lobster", "Oyster", "Pigeon",
    ],
    "cities": [
        "Denver", "Dallas", "Memphis", "Tulsa", "Phoenix", "Vegas", "Detroit", "Seattle",
        "Fresno", "Nashville", "Raleigh", "Boston", "Toledo", "Albany", "Chicago", "Cleveland",
        "Dayton", "Eugene", "Fargo", "Houston", "Jackson", "Wichita", "Lincoln", "Madison",
        "Newark", "Orlando", "Portland", "Richmond", "Savannah", "Spokane", "Tacoma", "Tucson",
        "Atlanta", "Buffalo", "Charlotte", "Durham", "Helena", "Juneau", "Laredo", "Macon",
        "Norfolk", "Oakland", "Pueblo", "Salem", "Topeka", "Waco", "Boise", "Akron",
    ],
    "things": [
        "Rocket", "Hammer", "Anchor", "Laser", "Magnet", "Thunder", "Blizzard", "Tornado",
        "Comet", "Canyon", "Glacier", "Jungle", "Marble", "Pepper", "Pickle", "Pretzel",
        "Waffle", "Taco", "Yogurt", "Zipper", "Igloo", "Kayak", "Noodle", "Banjo",
        "Cactus", "Domino", "Gumbo", "Mango", "Lemon", "Wizard", "Pirate", "Cowboy",
        "Bucket", "Candle", "Dragon", "Engine", "Feather", "Guitar", "Jacket", "Kettle",
        "Ladder", "Muffin", "Napkin", "Paddle", "Biscuit", "Tractor", "Violin", "Walnut",
    ],
}
WORD_LISTS["mix"] = [w for trio in zip(*WORD_LISTS.values()) for w in trio]
LIVE_SIGNALS: dict[str, list[str]] = {
    "colors": ["Red", "Blue", "Green", "White", "Black", "Purple", "Brown", "Silver"],
    "numbers": ["Ten", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty"],
}
LIVE_COLORS = LIVE_SIGNALS["colors"]
WORDS = WORD_LISTS["mix"]


def _word(text: Optional[str]) -> str:
    return " ".join(str(text or "").split())


def _words(items: list[str]) -> list[str]:
    """Cleaned, and each word once whatever its case."""
    out: list[str] = []
    for w in map(_word, items):
        if w and w.lower() not in {x.lower() for x in out}:
            out.append(w)
    return out


class LineSheet(BaseModel):
    game: str
    fingerprint: str
    words: dict[str, str]        # word -> play id, for the whole game
    dead: list[str] = []         # words that mean nothing: dummies and burned words
    live: dict[str, str] = {}    # period -> the live signal word
    order: dict[str, int] = {}   # period -> which call counts, when no word marks it
    calls: int = 1               # calls made each snap
    signals: list[str] = []      # every live-signal word, so the staff knows the dummies


def live_words(calls) -> list[str]:
    if calls.live_signal == "own":
        return _words(calls.own_live)
    return LIVE_SIGNALS.get(calls.live_signal, [])


def word_bank(calls) -> list[str]:
    return _words(calls.own_words) if calls.word_list == "own" else WORD_LISTS[calls.word_list]


def line_calls(book: Playbook, secret: str, game: str) -> LineSheet:
    """The game's code words, dummy words, and what is live each period."""
    key = key_bytes(secret)
    calls = plan_of(book).calls
    by_id = {p.id: p for p in book.plays}
    signals = live_words(calls)
    if calls.live_signal != "order" and len(signals) < 2:
        raise ValueError("Give at least two live words, so the others can be dummies.")
    bank, burned = word_bank(calls), _words(calls.burned_words)
    own = {pid: _word(by_id[pid].word) for pid in numbers(book) if _word(by_id[pid].word)}
    taken = {w.lower() for w in list(own.values()) + burned + signals}
    pool = [w for w in _Stream(key, f"{game}|words").shuffle(bank) if w.lower() not in taken]
    words: dict[str, str] = {}
    for pid in numbers(book):
        w = own.get(pid)
        if not w or w.lower() in {x.lower() for x in words}:
            if not pool:
                raise ValueError(f"Not enough words: the list has {len(bank)}. Add words to it, "
                                 f"set your own on some plays, or burn fewer.")
            w = pool.pop(0)
        words[w] = pid
    dead = pool[:calls.dummy_words] + [w for w in burned if w.lower() not in
                                       {x.lower() for x in words}]
    periods = PERIODS[calls.rotate]
    live: dict[str, str] = {}
    order: dict[str, int] = {}
    count = calls.signals
    if calls.live_signal == "order":
        count = max(2, calls.signals)
        stream, last = _Stream(key, f"{game}|order"), None
        for period in periods:
            last = order[period] = _pick(stream, list(range(1, count + 1)), last)
    else:
        stream, last = _Stream(key, f"{game}|live"), None
        for period in periods:
            last = live[period] = _pick(stream, signals, last)
    return LineSheet(game=game, fingerprint=fingerprint(key, game), words=words,
                     dead=sorted(dead, key=str.lower), live=live, order=order,
                     calls=count, signals=signals)


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
    if cells == "key":                        # two or four, from the key, each game
        cells = (2, 4)[_Stream(key, f"{game}|cells").below(2)]

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
           "LETTERS", "code_style", "CodeCard", "CodeSheet", "wristband", "WORD_LISTS",
           "LIVE_SIGNALS", "LIVE_COLORS", "WORDS", "LineSheet", "line_calls", "live_words",
           "word_bank", "BOARD_SHAPES", "BOARD_COLORS", "BOARD_MEMORY", "board_units",
           "BoardSheet", "boards"]
