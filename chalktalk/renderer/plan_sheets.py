"""
The game plan on paper: drive cards, the staff's master, the quarterback's
card, sign boards and the halftime sheet.

Each takes a playbook with its `GamePlan` and returns one printable HTML page
in the same look as the rest of `sheets.py`. The coded sheets also take what
`codes` drew from the staff's key; the key itself is never printed.

    from chalktalk import codes, planner
    from chalktalk.renderer import plan_sheets as PS

    PS.drive_cards_html(book)
    PS.game_plan_html(book, codes=codes.wristband(book, key, "Wk 3 vs Central"))
    PS.halftime_html(book)
"""
from __future__ import annotations

import html
from typing import TYPE_CHECKING, Optional

from .sheets import (INSERT_SIZES, _footer, _header, _insert, _list_body, _page,
                     band_layout, short_call)

if TYPE_CHECKING:
    from ..codes import BoardSheet, CodeCard, CodeSheet, LineSheet
    from ..models.gameplan import DriveScript, GamePlan
    from ..models.play import Play, Playbook

_INSERT_FOOT = "Print at actual size (100%) and cut on the dashed lines."
_ORDINALS = ["", "1st", "2nd", "3rd"]


def _e(text) -> str:
    return html.escape(str(text)) if text is not None else ""


def plan_title(plan: "GamePlan") -> str:
    """'Wk 3 vs Central', without saying the opponent twice."""
    name = plan.name if plan.name and plan.name != "Game plan" else ""
    opp = (plan.opponent or "").strip()
    vs = f"vs {opp}" if opp and opp.lower() not in name.lower() else ""
    return " ".join(b for b in (name, vs) if b) or "Game plan"


def _role_words(role) -> str:
    return str(getattr(role, "value", role) or "").replace("_", " ")


def _by_id(book: "Playbook") -> dict[str, "Play"]:
    return {p.id: p for p in book.plays}


# ── drive cards ───────────────────────────────────────────────────────────────

_PATH_ORDER = [[], ["on"], ["on", "on"], ["on", "off"], ["off"], ["off", "on"], ["off", "off"]]


def _path_words(path: list[str]) -> str:
    if not path:
        return "the first call"
    return ", then ".join("on schedule" if s == "on" else "off schedule" for s in path)


def _script_card(book: "Playbook", script: "DriveScript") -> str:
    from .. import planner
    by_id = _by_id(book)
    lines = []
    for path in _PATH_ORDER:
        state = planner.script_state(script, path)
        if path and (state.over or state.down == 1):
            continue                                   # the drive moved on: nothing to script
        node = planner.script_node(script, path)
        play = by_id.get(node.play) if node and node.play else None
        why = f"<div class=\"why\">{_e(_path_words(path))}</div>" if path else ""
        lines.append(f"<li style=\"padding-left:{len(path) * 14}px\">"
                     f"<span class=\"num\">{_e(state.label().split(',')[0])}</span>"
                     f"<span><b>{_e(play.call) if play else '—'}</b>{why}</span></li>")
    return (f"<div class=\"dcardp\"><h2>{_e(script.name)}</h2>"
            f"<div class=\"note\">{_e(script.start.label())}</div><ol>{''.join(lines)}</ol></div>")


def drive_cards_html(book: "Playbook") -> str:
    """Your drive scripts, then the planner's first three calls from each common start."""
    from .. import planner
    plan = planner.plan_of(book)
    cards = []
    for title, state, picks in planner.drive_cards(book, 3):
        items = []
        for s in picks:
            why = "".join(f"<div class=\"why\">{_e(r.text)}</div>"
                          for r in [r for r in s.reasons if r.points > 0][:2])
            branches = "".join(f"<div class=\"br\">If {_e(b.when)}: {_e(b.call)}</div>"
                               for b in s.branches)
            items.append(f"<li><span class=\"num\">{s.points}</span>"
                         f"<span><b>{_e(s.call)}</b>{why}{branches}</span></li>")
        cards.append(f"<div class=\"dcardp\"><h2>{_e(title)}</h2>"
                     f"<div class=\"note\">{_e(state.label())}</div><ol>{''.join(items)}</ol></div>")
    scripts = "".join(_script_card(book, s) for s in plan.drives)
    css = (".dcards{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}"
           ".dcardp{border:1px solid var(--line);border-radius:6px;padding:10px;break-inside:avoid}"
           ".dcardp h2{font-size:13px;text-transform:none;letter-spacing:0;margin:0}"
           ".dcardp ol{list-style:none;margin:8px 0 0;padding:0}"
           ".dcardp li{display:flex;gap:8px;padding:4px 0;border-top:1px dotted var(--line)}"
           ".dcardp .num{min-width:22px;color:var(--muted);font-variant-numeric:tabular-nums}"
           ".why{color:var(--muted);font-size:11px}.br{font-size:11px;margin-top:2px}")
    sub = ("Your drive scripts, then the planner's first calls from each start" if scripts
           else "Drive cards: the first calls from each start, and what follows")
    body = (_header(plan_title(plan), [sub], [book.team or "", f"{len(book.plays)} plays"])
            + f"<div class=\"dcards\">{scripts}{''.join(cards)}</div>" + _footer())
    return _page(f"{plan_title(plan)} — Drive cards", body, css)


# ── signals, in the words a card prints ───────────────────────────────────────

def signal_rule(card: "CodeCard") -> str:
    bits = []
    if card.dummy:
        bits.append(f"drop the {card.dummy} digit")
    if card.live:
        bits.append(f"the {_ORDINALS[card.live]} signal is live")
    return " · ".join(bits)


def line_rule(lines: "LineSheet", period: str) -> str:
    if lines.order.get(period):
        return f"say {lines.calls}; the {_ORDINALS[lines.order[period]]} counts"
    return f"live: {lines.live[period]}" if lines.live.get(period) else ""


def _line_periods(lines: "LineSheet") -> list[str]:
    return list(lines.live or lines.order)


# ── sign board symbols ────────────────────────────────────────────────────────

_SYMBOL_PATHS = {
    "circle": '<circle cx="50" cy="50" r="44"/>',
    "square": '<rect x="8" y="8" width="84" height="84"/>',
    "triangle": '<polygon points="50,6 94,90 6,90"/>',
    "diamond": '<polygon points="50,4 96,50 50,96 4,50"/>',
    "star": '<polygon points="50,7 61.2,37.6 93.7,38.8 68.1,58.9 77,90.2 50,72 23,90.2 '
            '31.9,58.9 6.3,38.8 38.8,37.6"/>',
    "plus": '<polygon points="35,6 65,6 65,35 94,35 94,65 65,65 65,94 35,94 35,65 6,65 6,35 35,35"/>',
    "x": '<polygon transform="rotate(45 50 50)" points="36,8 64,8 64,36 92,36 92,64 64,64 '
         '64,92 36,92 36,64 8,64 8,36 36,36"/>',
    "ring": '<path fill-rule="evenodd" d="M6,50a44,44 0 1,0 88,0a44,44 0 1,0 -88,0zM26,50a24,24 '
            '0 1,0 48,0a24,24 0 1,0 -48,0z"/>',
}
_COLOR_WORDS = {"sky": "light blue"}
_CELL_NAMES = {1: ["the board"], 2: ["left", "right"],
               4: ["top left", "top right", "bottom left", "bottom right"]}
# How far a board reads on a 22 x 28 in poster: symbols need about 0.3 in a yard.
_BOARD_REACH = {1: 55, 2: 40, 4: 30}


def symbol_svg(symbol: str, size) -> str:
    """One symbol in a 100 x 100 box: a shape in a colour, outlined in black."""
    from ..codes import BOARD_COLORS
    shape, _, color = symbol.partition("/")
    fill = BOARD_COLORS.get(color, "#000")
    return (f"<svg viewBox=\"-2 -2 104 104\" width=\"{size}\" height=\"{size}\" aria-hidden=\"true\">"
            f"<g fill=\"{fill}\" stroke=\"#000\" stroke-width=\"8\" stroke-linejoin=\"round\">"
            f"{_SYMBOL_PATHS.get(shape, _SYMBOL_PATHS['circle'])}</g></svg>")


def symbol_name(symbol: str) -> str:
    shape, _, color = symbol.partition("/")
    return f"{_COLOR_WORDS.get(color, color)} {shape}"


def cell_name(cells: int, i: int) -> str:
    names = _CELL_NAMES.get(cells, [])
    return names[i] if i < len(names) else f"cell {i + 1}"


def cell_map(cells: int, live: int) -> str:
    """A little map of the board with the live cell filled in."""
    cols, rows = (1 if cells == 1 else 2), (2 if cells == 4 else 1)
    w, h = cols * 14 + 2, rows * 10 + 2
    rects = "".join(
        f"<rect x=\"{1 + (i % cols) * 14}\" y=\"{1 + (i // cols) * 10}\" width=\"13\" height=\"9\" "
        f"fill=\"{'#000' if i == live else 'none'}\" stroke=\"#000\" stroke-width=\"1\"/>"
        for i in range(cells))
    return (f"<svg viewBox=\"0 0 {w} {h}\" width=\"{w}\" height=\"{h}\" aria-hidden=\"true\" "
            f"style=\"vertical-align:-3px\">{rects}</svg>")


def _unit_of(book: "Playbook", pid: str) -> str:
    from ..planner import plan_of
    series = (_by_id(book)[pid].series or "").strip()
    return f"series:{series}" if plan_of(book).calls.boards_by == "series" and series else pid


# ── the game plan: the staff's master ─────────────────────────────────────────

def game_plan_html(book: "Playbook", codes: Optional["CodeSheet"] = None,
                   boards: Optional["BoardSheet"] = None,
                   lines: Optional["LineSheet"] = None) -> str:
    """Every section of the plan with its numbers, words, symbols and codes."""
    from .. import planner
    plan = planner.plan_of(book)
    numbers = planner.numbers(book)
    by_id = _by_id(book)
    word_of = {pid: w for w, pid in lines.words.items()} if lines else None
    words = word_of is not None or ("words" in plan.calls.methods and any(p.word for p in book.plays))
    periods = [c.period for c in codes.cards] if codes else []

    def codes_of(pid: str, card) -> str:
        return " ".join(c for c, v in card.codes.items() if v == pid)

    def table(title: str, ids: list[str], sub: str = "") -> str:
        if not ids:
            return ""
        head = ("<tr><th>#</th><th>Call</th>" + ("<th>Word</th>" if words else "")
                + ("<th>Board</th>" if boards else "")
                + "".join(f"<th>{_e(p)}</th>" for p in periods) + "</tr>")
        rows = []
        for pid in ids:
            p = by_id[pid]
            role = " · ".join(b for b in (p.series, _role_words(p.role) if p.role else None) if b)
            cells = [f"<td class=\"n\">{numbers.get(pid, '')}</td>",
                     f"<td class=\"call\">{'★ ' if p.favorite else ''}{_e(p.call)}"
                     + (f"<div class=\"note\">{_e(role)}</div>" if role else "") + "</td>"]
            if words:
                cells.append(f"<td>{_e((word_of.get(pid) if word_of else p.word) or '—')}</td>")
            if boards:
                sym = boards.symbols.get(_unit_of(book, pid))
                cells.append(f"<td>{symbol_svg(sym, 22) if sym else ''}</td>")
            if codes:
                cells += [f"<td class=\"n\">{_e(codes_of(pid, card))}</td>" for card in codes.cards]
            rows.append(f"<tr>{''.join(cells)}</tr>")
        return (f"<div class=\"section\"><h2>{_e(title)}</h2>{sub}"
                f"<table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>")

    live = []                                      # what is live, period by period
    if codes and any(signal_rule(c) for c in codes.cards):
        live.append("Signals: " + " · ".join(
            f"{_e(c.period)} <b>{_e(signal_rule(c) or 'as is')}</b>" for c in codes.cards))
    if lines:
        signals = (f" <span class=\"note\">(signal words: {', '.join(_e(s) for s in lines.signals)})</span>"
                   if lines.signals else "")
        live.append("Line calls: " + " · ".join(
            f"{_e(p)} <b>{_e(line_rule(lines, p))}</b>" for p in _line_periods(lines)) + signals)
    if boards:
        live.append("Live cell: " + " · ".join(
            f"{cell_map(boards.cells, c)} {_e(p)} <b>{_e(cell_name(boards.cells, c))}</b>"
            for p, c in boards.live.items()))
    body = f"<p class=\"note\">{'<br>'.join(live)}</p>" if live else ""
    body += table("Openers", planner.openers(book), "<div class=\"note\">The script, in order</div>")
    body += table("Drive starters", planner.starters(book),
                  "<div class=\"note\">The first call of a new drive</div>")
    for section, ids in planner.sections(book):
        body += table(section.title, ids)
    dead = ""
    if codes:
        dead += ("<div class=\"section\"><h2>Dead codes</h2>"
                 + "".join(f"<div class=\"note\">{_e(c.period)}: {' '.join(c.dead)}</div>"
                           for c in codes.cards) + "</div>")
    if lines and lines.dead:
        dead += (f"<div class=\"section\"><h2>Dummy words</h2><div class=\"note\">"
                 f"{', '.join(_e(w) for w in lines.dead)}</div></div>")
    keyed = codes or boards or lines
    head = _header(plan_title(plan), ["Game plan · staff only"],
                   [book.team or "", f"Fingerprint {keyed.fingerprint}" if keyed else "",
                    f"{len(numbers)} calls"])
    return _page(f"{plan_title(plan)} — Game plan",
                 head + body + dead + _footer("Staff only. The key is not printed." if keyed else ""))


# ── the quarterback's card ────────────────────────────────────────────────────

def _grid_body(card: "CodeCard", style: str, label) -> str:
    """A coded card as a grid: the first character down the side, the last digit across."""
    from ..codes import LETTERS
    rows = list(LETTERS) if style == "letter" else [str(d) for d in range(1, 10)]
    head = "<tr><th class=\"r\"></th>" + "".join(f"<th>{d}</th>" for d in range(10)) + "</tr>"
    body = "".join(
        f"<tr><th class=\"r\">{r}</th>"
        + "".join(f"<td>{_e(label(card.codes[r + str(d)])) if r + str(d) in card.codes else ''}</td>"
                  for d in range(10)) + "</tr>"
        for r in rows)
    return f"<table class=\"grid\">{head}{body}</table>"


def _strip(left: str, rule: str, right: str) -> str:
    return (f"<span>{_e(left)}</span><span class=\"rule\">{_e(rule)}</span>"
            f"<span class=\"fp\">{_e(right)}</span>")


def qb_card_html(book: "Playbook", codes: Optional["CodeSheet"] = None,
                 lines: Optional["LineSheet"] = None, size: str = "adult", copies: int = 1) -> str:
    """The quarterback's inserts: a coded card for each period, and the line calls."""
    from ..codes import _code_order
    from ..planner import plan_of
    size = size if size in INSERT_SIZES else "adult"
    plan, by_id = plan_of(book), _by_id(book)

    def label(pid: str) -> str:
        return short_call(by_id[pid].call)

    cards = []
    if codes and codes.cards:
        first = codes.cards[0]
        grid = all(len(c) == 2 for c in [*first.codes, *first.dead])
        for card in codes.cards:
            rule = " · ".join(b for b in (signal_rule(card),
                                          line_rule(lines, card.period) if lines else "") if b)
            strip = _strip(card.period, rule, codes.fingerprint)
            if grid:
                cards.append(_insert(size, strip, _grid_body(card, codes.style, label)))
            else:
                rows = [(c, label(pid)) for c, pid in sorted(card.codes.items(),
                                                             key=lambda kv: _code_order(kv[0]))]
                cards += [_insert(size, strip, _list_body(cols, size))
                          for cols in band_layout([("", rows)], size)]
    if lines:
        rule = " · ".join(f"{p}: {line_rule(lines, p)}" for p in _line_periods(lines))
        rows = sorted([(w, label(pid)) for w, pid in lines.words.items()]
                      + [(w, "—") for w in lines.dead], key=lambda r: r[0].lower())
        cards += [_insert(size, _strip("Line calls", rule, lines.fingerprint), _list_body(cols, size))
                  for cols in band_layout([("", rows)], size)]
    how = " ".join(b for b in (
        "A blank square or a number not on the card means wait." if codes else "",
        ("" if not lines else
         f"At the line: {lines.calls} calls; only the one the key names counts." if lines.order
         else "At the line: the live word, then the call, twice. Any other signal word is a dummy."),
    ) if b)
    keyed = codes or lines
    head = _header(plan_title(plan), ["QB wristband" if codes else "Line calls"],
                   [f"Fingerprint {keyed.fingerprint}" if keyed else "", INSERT_SIZES[size]["label"]])
    body = (head + f"<div class=\"inserts\">{''.join(cards) * max(1, copies)}</div>"
            + _footer(f"{how} {_INSERT_FOOT}".strip()))
    return _page(f"{plan_title(plan)} — QB card", body)


# ── sign boards ───────────────────────────────────────────────────────────────

def sign_boards_html(book: "Playbook", boards: "BoardSheet") -> str:
    """The rack, a board to a page; then the players' key and the signaler's sheet."""
    from ..planner import plan_of
    plan, by_id = plan_of(book), _by_id(book)

    def unit_name(u: str) -> str:
        return f"{u[7:]} series" if u.startswith("series:") else by_id[u].call

    cells = boards.cells
    cols, rows = (1 if cells == 1 else 2), (2 if cells == 4 else 1)
    pages = "".join(
        f"<div class=\"board\"><div class=\"corner\">{i + 1}</div><div class=\"grid\" "
        f"style=\"grid-template-columns:repeat({cols},1fr);grid-template-rows:repeat({rows},1fr)\">"
        + "".join(f"<div class=\"cellb\">{symbol_svg(sym, '100%')}</div>" for sym in row)
        + "</div></div>"
        for i, row in enumerate(boards.boards))
    live_line = " &nbsp; ".join(
        f"{cell_map(cells, c)} {_e(p)}: <b>{_e(cell_name(cells, c))}</b>" for p, c in boards.live.items())
    players = ("<div class=\"section\"><h2>What the symbols mean</h2>"
               f"<p class=\"note\">Read only the live cell. {live_line}</p><table><tbody>"
               + "".join(f"<tr><td style=\"width:44px\">{symbol_svg(boards.symbols[u], 30)}</td>"
                         f"<td>{_e(symbol_name(boards.symbols[u]))}</td>"
                         f"<td class=\"call\">{_e(unit_name(u))}</td></tr>" for u in boards.units)
               + "</tbody></table></div>")
    meanings = set(boards.symbols.values())
    signaler = []
    for period, cell in boards.live.items():
        def board_of(sym: str) -> int:
            return next((i + 1 for i, row in enumerate(boards.boards) if row[cell] == sym), 0)
        dummies = [str(i + 1) for i, row in enumerate(boards.boards) if row[cell] not in meanings]
        signaler.append(
            f"<div class=\"section\"><h2>{_e(period)} · live cell {_e(cell_name(cells, cell))}</h2>"
            "<table><tbody>"
            + "".join(f"<tr><td class=\"n\" style=\"width:44px\">{board_of(boards.symbols[u])}</td>"
                      f"<td class=\"call\">{_e(unit_name(u))}</td></tr>" for u in boards.units)
            + f"</tbody></table><p class=\"note\">Dummy boards: {', '.join(dummies) or 'none'}</p></div>")
    reach = _BOARD_REACH.get(cells, 30)
    css = ("@page{size:landscape;margin:10mm}"
           ".board{height:92vh;position:relative;break-after:page;border:1px solid #000;"
           "background:#fff;box-sizing:border-box;padding:3vh}"
           ".board .grid{display:grid;gap:3vh;height:100%}"
           ".board .cellb{display:flex;align-items:center;justify-content:center;min-height:0}"
           ".board .cellb svg{max-height:100%;max-width:100%}"
           ".board .corner{position:absolute;left:10px;top:6px;font-size:11px;color:#555}"
           ".keypage{break-before:page}")
    fp = [f"Fingerprint {boards.fingerprint}"]
    players_head = _header(plan_title(plan), ["Sign boards · the players' key"], fp)
    signaler_head = _header(plan_title(plan), ["Sign boards · signaler only"], fp)
    body = (pages
            + f"<div class=\"keypage\">{players_head}{players}"
            + _footer(f"On a 22 x 28 in poster these boards read to about {reach} yards; "
                      "letter paper is for practice.") + "</div>"
            + f"<div class=\"keypage\">{signaler_head}{''.join(signaler)}"
            + _footer("Signaler only. The key is not printed.") + "</div>")
    return _page(f"{plan_title(plan)} — Sign boards", body, css)


# ── halftime ──────────────────────────────────────────────────────────────────

_DIMENSION_NAMES = {"formation": "Formation", "personnel": "Personnel",
                    "down": "Down & distance", "hash": "Hash", "field": "Field"}


def _per_call(yards: float, calls: int) -> float:
    return round(yards / calls * 10) / 10 if calls else 0


def halftime_html(book: "Playbook", log=None) -> str:
    """The numbers, what a scout sees, what is working and what is left."""
    from ..planner import plan_of
    from ..scout import report
    plan, r = plan_of(book), report(book, log)

    def section(title: str, inner: str) -> str:
        return f"<div class=\"section\"><h2>{_e(title)}</h2>{inner}</div>" if inner else ""

    def listed(items: list[str]) -> str:
        return ("<ol>" + "".join(f"<li><span></span><span>{_e(i)}</span></li>" for i in items)
                + "</ol>") if items else ""

    def calls(lines, each: bool) -> str:
        return ("<ol>" + "".join(
            f"<li><span class=\"num\">{_per_call(l.yards, l.calls):g}</span><span>{_e(l.call)}"
            + (f"<div class=\"note\">{l.calls} calls</div>" if each else "") + "</span></li>"
            for l in lines) + "</ol>") if lines else ""

    split = ""
    if r.by_down:
        split = ("<table><thead><tr><th>Down</th><th class=\"n\">Calls</th>"
                 "<th class=\"n\">On schedule</th><th class=\"n\">Yards</th>"
                 "<th class=\"n\">A call</th></tr></thead><tbody>"
                 + "".join(f"<tr><td>{_e(s.label)}</td><td class=\"n\">{s.calls}</td>"
                           f"<td class=\"n\">{s.on} ({s.rate}%)</td><td class=\"n\">{round(s.yards)}</td>"
                           f"<td class=\"n\">{_per_call(s.yards, s.calls):g}</td></tr>" for s in r.by_down)
                 + "</tbody></table>")
    looks = ""
    if r.tendencies:
        rows, last = [], None
        for t in r.tendencies:
            if t.by != last:
                rows.append(f"<tr><th colspan=\"5\">{_DIMENSION_NAMES.get(t.by, t.by)}</th></tr>")
                last = t.by
            rows.append(f"<tr><td>{_e(t.look)}</td><td class=\"n\">{t.calls}</td>"
                        f"<td class=\"n\">{t.runs}</td><td class=\"n\">{t.passes}</td>"
                        f"<td class=\"n\">{t.on}</td></tr>")
        looks = ("<table><thead><tr><th>Look</th><th class=\"n\">Calls</th><th class=\"n\">Run</th>"
                 "<th class=\"n\">Pass</th><th class=\"n\">On schedule</th></tr></thead><tbody>"
                 + "".join(rows) + "</tbody></table>")
    head = _header(plan_title(plan), ["Halftime: what the log says"],
                   [book.team or "", f"{r.on} of {r.snaps} on schedule",
                    f"{r.thirds.on} of {r.thirds.calls} on third down"])
    body = (section("What a scout sees", listed(r.notes))
            + section("By down", split)
            + section("What is working", calls(r.best, True))
            + section("Explosives", calls(r.explosives, False))
            + section("Your looks", looks)
            + section("Set up and not called", listed(r.ready))
            + section("Left on the sheet", listed(r.unused)))
    return _page(f"{plan_title(plan)} - Halftime",
                 head + f"<div class=\"cols\">{body}</div>" + _footer("Counted from the game log."),
                 ".cols{column-count:2;column-gap:20px}")


__all__ = ["plan_title", "drive_cards_html", "game_plan_html", "qb_card_html",
           "sign_boards_html", "halftime_html", "symbol_svg", "signal_rule", "line_rule"]
