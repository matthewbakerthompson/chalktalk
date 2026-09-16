"""
HTML renderers for the paper side of coaching: call sheets, practice scripts,
wristbands, and playbook pages with inline diagrams.

Everything is a single self-contained HTML string — no assets, no CDN — so it
opens anywhere and prints straight to a laminator.
"""
from __future__ import annotations
import html
from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from ..callsheet import CallSheet, Wristband
    from ..script import Script, PracticeScript
    from ..models.play import Play, Playbook
    from ..series import Series


_CSS = """
:root {
  --ink: #111111; --muted: #6b6b66; --line: #d4d4d0; --accent: #111111;
  --band: #efefec; --paper: #ffffff;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 18px 20px; background: var(--paper); color: var(--ink);
  font: 13px/1.4 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
h1 { font-size: 19px; margin: 0 0 2px; letter-spacing: -.01em; }
h2 { font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: .09em; }
.sub { color: var(--muted); font-size: 12px; margin-bottom: 14px; }
header { border-bottom: 2px solid var(--ink); padding-bottom: 8px; margin-bottom: 14px;
         display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; }
header .meta { text-align: right; color: var(--muted); font-size: 11px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .07em;
     color: var(--muted); border-bottom: 1px solid var(--line); padding: 4px 6px; }
td { padding: 4px 6px; border-bottom: 1px solid #eef2f7; vertical-align: top; }
tr:nth-child(even) td { background: #f8fafc; }
td.n { width: 26px; color: var(--muted); font-variant-numeric: tabular-nums; }
td.call { font-weight: 600; }
td.sit, td.look { white-space: nowrap; }
td.look { color: var(--muted); }
.note { color: var(--muted); font-size: 11px; font-style: italic; }
.alert { color: #b45309; font-size: 11px; font-weight: 600; }
.cols { column-count: 2; column-gap: 20px; }
.section { break-inside: avoid; margin-bottom: 14px; }
.section h2 { background: var(--band); padding: 3px 6px; border-left: 3px solid var(--accent); }
.section ol { margin: 6px 0 0; padding-left: 0; list-style: none; }
.section li { display: flex; gap: 7px; padding: 2px 6px; border-bottom: 1px dotted #e2e8f0; }
.section li .num { color: var(--accent); font-weight: 700; min-width: 22px;
                   font-variant-numeric: tabular-nums; }
.chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }
.chip { background: var(--band); border-radius: 3px; padding: 1px 6px; font-size: 10px;
        color: var(--muted); }
.period { break-inside: avoid; margin-bottom: 16px; }
.period-head { display: flex; align-items: baseline; gap: 8px;
               border-bottom: 1px solid var(--ink); padding-bottom: 3px; }
.period-head .clock { font-variant-numeric: tabular-nums; color: var(--muted);
                      font-size: 11px; }
.band { display: grid; gap: 4px; }
.band .cell { border: 1px solid var(--ink); border-radius: 3px; padding: 4px 6px;
              min-height: 34px; break-inside: avoid; }
.band .cell .num { font-weight: 800; font-size: 15px; margin-right: 5px; }
.band .cell .txt { font-size: 10px; line-height: 1.25; }
.grp { font-size: 10px; text-transform: uppercase; letter-spacing: .08em;
       color: var(--muted); margin: 10px 0 3px; }
.cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.card { border: 1px solid var(--line); border-radius: 6px; padding: 10px;
        break-inside: avoid; }
.card svg { width: 100%; height: auto; display: block; border-radius: 4px; }
.card .title { font-weight: 700; margin-bottom: 6px; }
.foot { margin-top: 16px; padding-top: 6px; border-top: 1px solid var(--line);
        color: var(--muted); font-size: 10px; display: flex; justify-content: space-between; }
@media print {
  body { padding: 0; }
  .page-break { break-before: page; }
  a { text-decoration: none; color: inherit; }
}
"""


def _e(text) -> str:
    return html.escape(str(text)) if text is not None else ""


def _page(title: str, body: str, extra_css: str = "") -> str:
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        f"<meta charset=\"utf-8\">\n<title>{_e(title)}</title>\n"
        f"<style>{_CSS}{extra_css}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def _header(title: str, left_bits: Sequence[str] = (),
            right_bits: Sequence[str] = ()) -> str:
    left = "".join(f"<div class=\"sub\">{_e(b)}</div>" for b in left_bits if b)
    right = "<br>".join(_e(b) for b in right_bits if b)
    return (f"<header><div><h1>{_e(title)}</h1>{left}</div>"
            f"<div class=\"meta\">{right}</div></header>")


def _footer(note: str = "") -> str:
    return (f"<div class=\"foot\"><span>{_e(note)}</span>"
            f"<span>generated with chalktalk</span></div>")


# ── Script ────────────────────────────────────────────────────────────────────

def script_html(script: "Script", show_balance: bool = True) -> str:
    rows = []
    for e in script.entries:
        sit = e.situation.short() if e.situation else ""
        hash_mark = e.hash_mark.value if e.hash_mark else ""
        note = (f"<div class=\"note\">{_e(e.note)}</div>" if e.note else "")
        alerts = "".join(f"<div class=\"alert\">! {_e(a)}</div>" for a in e.play.alerts)
        rows.append(
            f"<tr><td class=\"n\">{e.number}</td>"
            f"<td class=\"sit\">{_e(sit)}</td>"
            f"<td class=\"sit\">{_e(hash_mark)}</td>"
            f"<td class=\"call\">{_e(e.call)}{note}{alerts}</td>"
            f"<td class=\"look\">{_e(e.look_name)}</td>"
            f"<td class=\"n\">{e.reps}</td>"
            f"<td style=\"width:70px;border-bottom:1px solid #94a3b8\">"
            f"{_e(e.result or '')}</td></tr>"
        )
    balance = ""
    if show_balance and script.entries:
        b = script.balance()
        chips = [f"{b['total_reps']} reps", f"{b['run_pct']}% run",
                 f"{b['pass_pct']}% pass"]
        chips += [f"{k} pers: {v}" for k, v in sorted(b["personnel"].items())]
        balance = ("<div class=\"chips\">"
                   + "".join(f"<span class=\"chip\">{_e(c)}</span>" for c in chips)
                   + "</div>")
    body = (
        _header(script.name,
                [script.notes or ""],
                [f"vs {script.opponent}" if script.opponent else "", script.date or ""])
        + "<table><thead><tr><th>#</th><th>Sit</th><th>Ha</th><th>Call</th>"
          "<th>Look</th><th>Rep</th><th>Result</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>" + balance + _footer(script.period_name or "")
    )
    return _page(script.name, body)


def practice_html(practice: "PracticeScript") -> str:
    blocks = []
    clock = 0
    for p in practice.periods:
        rows = []
        for e in p.script.entries:
            sit = e.situation.short() if e.situation else ""
            rows.append(
                f"<tr><td class=\"n\">{e.number}</td>"
                f"<td class=\"sit\">{_e(sit)}</td>"
                f"<td class=\"call\">{_e(e.call)}</td>"
                f"<td class=\"look\">{_e(e.look_name)}</td>"
                f"<td class=\"n\">{e.reps}</td>"
                + (f"<td class=\"note\">{_e(e.note or '')}</td>")
                + "</tr>"
            )
        focus = f"<span class=\"note\">{_e(p.focus)}</span>" if p.focus else ""
        blocks.append(
            f"<div class=\"period\"><div class=\"period-head\">"
            f"<h2>{_e(p.name)}</h2><span class=\"clock\">{clock}' → "
            f"{clock + p.minutes}' ({p.minutes} min · {p.reps} reps)</span>{focus}</div>"
            f"<table><tbody>{''.join(rows)}</tbody></table></div>"
        )
        clock += p.minutes
    body = (
        _header(practice.name,
                [f"{practice.total_minutes} min · {practice.total_reps} reps · "
                 f"{len(practice.periods)} periods"],
                [practice.team or "", f"vs {practice.opponent}" if practice.opponent else "",
                 practice.date or ""])
        + "".join(blocks) + _footer(practice.notes or "")
    )
    return _page(practice.name, body)


# ── Call sheet ────────────────────────────────────────────────────────────────

def call_sheet_html(sheet: "CallSheet", columns: int = 2) -> str:
    sections = []
    for sec in sheet.sections:
        items = []
        for p in sec.plays:
            num = f"<span class=\"num\">{p.call_number}</span>" if p.call_number else \
                  "<span class=\"num\">•</span>"
            alerts = "".join(f"<div class=\"alert\">! {_e(a)}</div>" for a in p.alerts)
            items.append(f"<li>{num}<span>{_e(p.call)}{alerts}</span></li>")
        sub = ""
        if sec.situation and not sec.situation.is_wildcard:
            sub = f"<div class=\"note\">{_e(sec.situation.describe())}</div>"
        note = f"<div class=\"note\">{_e(sec.note)}</div>" if sec.note else ""
        sections.append(
            f"<div class=\"section\"><h2>{_e(sec.title)}</h2>{sub}{note}"
            f"<ol>{''.join(items)}</ol></div>"
        )
    notes = ""
    if sheet.notes:
        notes = ("<div class=\"section\"><h2>Notes</h2><ol>"
                 + "".join(f"<li><span class=\"num\">•</span><span>{_e(n)}</span></li>"
                           for n in sheet.notes)
                 + "</ol></div>")
    body = (
        _header(sheet.name, [sheet.team or ""],
                [f"vs {sheet.opponent}" if sheet.opponent else "", sheet.date or "",
                 f"{len(sheet)} calls"])
        + f"<div class=\"cols\" style=\"column-count:{columns}\">"
        + "".join(sections) + notes + "</div>" + _footer()
    )
    return _page(sheet.name, body)


# ── Wristband ─────────────────────────────────────────────────────────────────

def wristband_html(band: "Wristband", cell_height: int = 34) -> str:
    blocks = []
    for group, entries in band.groups().items():
        cells = []
        for e in entries:
            note = f"<div class=\"note\">{_e(e.note)}</div>" if e.note else ""
            cells.append(
                f"<div class=\"cell\"><span class=\"num\">{e.number}</span>"
                f"<span class=\"txt\">{_e(e.call)}</span>{note}</div>"
            )
        blocks.append(
            f"<div class=\"grp\">{_e(group)}</div>"
            f"<div class=\"band\" style=\"grid-template-columns:repeat({band.columns},1fr);"
            f"grid-auto-rows:minmax({cell_height}px,auto)\">{''.join(cells)}</div>"
        )
    body = (_header(band.name, [band.team or ""], [f"{len(band)} calls"])
            + "".join(blocks) + _footer("cut along the outer border"))
    return _page(f"{band.name} — Wristband", body)


# ── Playbook / series pages with diagrams ─────────────────────────────────────

def _play_card(play: "Play", scale: float, extra: str = "",
               level: Optional[str] = None, theme: str = "paper") -> str:
    svg = play.render(scale=scale, level=level, theme=theme).render()
    meta = []
    if play.situation:
        meta.append(play.situation.describe())
    if play.protection:
        meta.append(play.protection)
    meta += list(play.tags[:4])
    chips = "".join(f"<span class=\"chip\">{_e(m)}</span>" for m in meta if m)
    alerts = "".join(f"<div class=\"alert\">! {_e(a)}</div>" for a in play.alerts)
    desc = f"<div class=\"note\">{_e(play.description)}</div>" if play.description else ""
    num = f"{play.call_number}. " if play.call_number else ""
    return (f"<div class=\"card\"><div class=\"title\">{_e(num + play.call)}</div>"
            f"{svg}{extra}{desc}{alerts}<div class=\"chips\">{chips}</div></div>")


def playbook_html(playbook: "Playbook", columns: int = 2, scale: float = 9.0,
                  subtitle: Optional[str] = None,
                  level: Optional[str] = None, theme: str = "paper") -> str:
    cards = "".join(_play_card(p, scale, level=level, theme=theme)
                    for p in playbook.plays)
    body = (
        _header(playbook.name, [subtitle or ""],
                [playbook.team or "", str(playbook.season or ""),
                 f"{len(playbook)} plays"])
        + f"<div class=\"cards\" style=\"grid-template-columns:repeat({columns},1fr)\">"
        + cards + "</div>" + _footer()
    )
    return _page(playbook.name, body)


def series_html(series: "Series", columns: int = 2, scale: float = 9.0,
                level: Optional[str] = None, theme: str = "paper") -> str:
    cards = []
    for entry in series.sorted().entries:
        tell = (f"<div class=\"note\"><b>{_e(entry.role.display)}</b>"
                + (f" — {_e(entry.tell or entry.note)}"
                   if (entry.tell or entry.note) else "") + "</div>")
        cards.append(_play_card(entry.play, scale, extra=tell, level=level,
                                theme=theme))
    body = (
        _header(series.name, [series.description or ""],
                [f"{len(series)} plays"])
        + f"<div class=\"cards\" style=\"grid-template-columns:repeat({columns},1fr)\">"
        + "".join(cards) + "</div>" + _footer()
    )
    return _page(series.name, body)


__all__ = ["script_html", "practice_html", "call_sheet_html", "wristband_html",
           "playbook_html", "series_html"]
