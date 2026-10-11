"""
chalktalk command line — browse the catalog, render plays, and plan and print a
playbook without writing any Python.

    chalk list plays
    chalk render mesh_concept -o out/mesh.svg
    chalk design week3.json                       # draw it in the browser
    chalk book week3.json --sheet wristband --size teen
    chalk next week3.json --down 3 --distance 8 --at "opp 40" --look "Cover 3"
    chalk scout week3.json                        # the halftime report
    chalk check week3.json                        # what a coordinator would flag
    chalk demo --out out/demo
"""
from __future__ import annotations
import argparse
import inspect
import os
import sys
from typing import Callable, Optional

from . import __version__
from . import catalog as _catalog
from .catalog import series as series_catalog, systems as systems_catalog
from .templates import (blocking as BL, coverages as CV, defense as D,
                        formations as F, qb as QB, routes as R, schemes as SC)
from .models.play import Play, Playbook


# ── Registries ────────────────────────────────────────────────────────────────

def _uppercase(module) -> dict[str, Callable]:
    return {k: v for k, v in _public_callables(module).items() if k.isupper()}


def _public_callables(module) -> dict[str, Callable]:
    return {
        name: fn for name, fn in inspect.getmembers(module, inspect.isfunction)
        if not name.startswith("_") and fn.__module__ == module.__name__
    }


def play_registry() -> dict[str, Callable[[], Play]]:
    return _catalog.play_builders()


def formation_registry() -> dict[str, Callable]:
    return {k: v for k, v in _public_callables(F).items() if k.isupper()}


def defense_registry() -> dict[str, Callable]:
    return {k: v for k, v in _public_callables(D).items() if k.isupper()}


def route_registry() -> dict[str, Callable]:
    return {k: v for k, v in _public_callables(R).items() if k.isupper()}


def _resolve(reg: dict, key: str, kind: str):
    if key in reg:
        return reg[key]
    matches = [k for k in reg if key.lower() in k.lower()]
    if len(matches) == 1:
        return reg[matches[0]]
    if not matches:
        raise SystemExit(f"unknown {kind} '{key}'. Try: chalk list {kind}s")
    raise SystemExit(f"ambiguous {kind} '{key}': {', '.join(sorted(matches))}")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    what = args.what
    if what in ("plays", "play"):
        reg = play_registry()
        for name in sorted(reg):
            play = reg[name]()
            print(f"  {name:<22} {play.play_type.value:<7} {play.formation.name}")
        print(f"\n{len(reg)} plays")
    elif what in ("formations", "formation"):
        reg = formation_registry()
        for name in sorted(reg):
            f = reg[name]()
            print(f"  {name:<28} {f.personnel:<4} {f.name}")
        print(f"\n{len(reg)} formations")
    elif what in ("defenses", "defense", "defence"):
        reg = defense_registry()
        for name in sorted(reg):
            d = reg[name]()
            print(f"  {name:<22} {d.front:<14} {d.coverage or ''}")
        print(f"\n{len(reg)} defensive looks")
    elif what in ("routes", "route"):
        reg = route_registry()
        print("  " + "  ".join(sorted(reg)))
        print(f"\n{len(reg)} routes")
    elif what in ("schemes", "scheme", "blocking"):
        for name, fn in SC.SCHEMES.items():
            blocks = fn(1) if name not in ("big_on_big",) else fn()
            kind = "protection" if name in SC.PROTECTIONS else "run"
            line = " ".join(f"{k}:{v.kind.value}" for k, v in blocks.items())
            print(f"  {name:<14} {kind:<11} {line}")
        print(f"{chr(10)}{len(SC.SCHEMES)} schemes")
    elif what in ("blocks",):
        for name in sorted(_uppercase(BL)):
            print(f"  {name}")
        print(f"{chr(10)}{len(_uppercase(BL))} block types")
    elif what in ("coverages", "coverage"):
        for name, fn in {**CV.COVERAGES, **CV.FRONTS}.items():
            look = fn(D.NICKEL_425(), F.SHOTGUN_TRIPS_RIGHT())
            kind = ("front" if name in CV.FRONTS
                    else "pressure" if name in CV.PRESSURES else "coverage")
            calls = " ".join(f"{p.label}:{p.assignment.describe()}"
                             for p in look.players
                             if p.assignment and not p.is_dl)
            print(f"  {name:<12} {kind:<9} {calls}")
        print(f"{chr(10)}{len(CV.COVERAGES)} coverages, {len(CV.FRONTS)} fronts")
    elif what in ("qb", "quarterback"):
        for name, fn in QB.ACTIONS.items():
            plan = fn()
            mesh = "mesh" if plan.mesh_point else "    "
            print(f"  {name:<12} {mesh}  {plan.rule or ''}")
        print(f"{chr(10)}{len(QB.ACTIONS)} quarterback actions")
    elif what in ("systems", "system", "sets"):
        for key, fn in systems_catalog.ALL_SYSTEMS.items():
            s_ = fn()
            b = s_.balance()
            print(f"  {key:<16} {b['series']} series  {b['plays']:>3} plays  "
                  f"{b['run_pct']:>3}% run  {len(s_.gaps())} gaps   {s_.name}")
        print(f"{chr(10)}{len(systems_catalog.ALL_SYSTEMS)} systems")
    elif what in ("series",):
        for key, fn in series_catalog.ALL_SERIES.items():
            s = fn()
            print(f"  {key:<16} {len(s):>2} plays   {s.name}")
        print(f"\n{len(series_catalog.ALL_SERIES)} series")
    else:
        raise SystemExit("list what? plays | formations | defenses | routes | "
                         "series | systems | schemes | blocks | "
                         "coverages | qb")
    return 0


def _build_play(name: str, formation: Optional[str], defense: Optional[str],
                flip: bool, coverage: Optional[str] = None) -> Play:
    fn = _resolve(play_registry(), name, "play")
    kwargs = {}
    if formation:
        kwargs["formation"] = _resolve(formation_registry(), formation, "formation")()
    play = fn(**kwargs)
    if defense:
        play = play.vs(_resolve(defense_registry(), defense, "defense")())
        if coverage:
            calls = {**CV.COVERAGES, **CV.FRONTS}
            if coverage not in calls:
                raise SystemExit(f"unknown coverage '{coverage}'. "
                                 f"Try: chalk list coverages")
            play = play.with_coverage(calls[coverage])
    if flip:
        from . import adjustments as A
        play = play.adjust(A.FLIP())
    return play


def cmd_render(args: argparse.Namespace) -> int:
    play = _build_play(args.play, args.formation, args.defense, args.flip,
                       getattr(args, "coverage", None))
    out = args.out or f"{args.play}.svg"
    hide = [h.strip() for h in (args.hide or "").split(",") if h.strip()]
    if out.endswith(".pdf"):
        Playbook(name=play.name, plays=[play]).save_pdf(out, level=args.level,
                                                        theme=args.theme)
        print(f"Saved: {os.path.abspath(out)}")
    elif out.endswith(".json"):
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(play.to_json())
        print(f"Saved: {os.path.abspath(out)}")
    else:
        play.render(scale=args.scale, level=args.level, theme=args.theme,
                    hide=hide).save(out)
    if args.describe:
        print()
        print(play.describe())
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    play = _build_play(args.play, args.formation, args.defense, args.flip,
                       getattr(args, "coverage", None))
    print(play.describe())
    if play.defense is not None and play.defense.has_assignments:
        print()
        print(play.defense.describe())
    return 0


def _series_by_key(key: str):
    reg = series_catalog.ALL_SERIES
    if key in reg:
        return reg[key]()
    matches = [k for k in reg if key.lower() in k.lower()]
    if len(matches) == 1:
        return reg[matches[0]]()
    raise SystemExit(f"unknown series '{key}'. Try: chalk list series")


def cmd_series(args: argparse.Namespace) -> int:
    s = _series_by_key(args.name)
    print(s.describe())
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        from .renderer.sheets import series_html
        html_path = os.path.join(args.out, "index.html")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(series_html(s))
        s.render_all(args.out)
        s.to_playbook().save(os.path.join(args.out, "series.json"))
        print(f"\nWrote {len(s)} diagrams + {html_path}")
    return 0


def _system_by_key(key: str):
    reg = systems_catalog.ALL_SYSTEMS
    if key in reg:
        return reg[key]()
    matches = [k for k in reg if key.lower() in k.lower()]
    if len(matches) == 1:
        return reg[matches[0]]()
    raise SystemExit(f"unknown system '{key}'. Try: chalk list systems")


def cmd_system(args: argparse.Namespace) -> int:
    """Describe a series set, and optionally print the whole install."""
    system = _system_by_key(args.name)
    print(system.describe())

    if args.balance:
        b = system.balance()
        print()
        print("Answers off each base")
        for name, answers in b["answers_per_base"].items():
            print(f"  {answers:>2}  {name}")
        print()
        print("Personnel:", ", ".join(f"{k}: {v}"
                                      for k, v in sorted(b["personnel"].items())))

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        system.save_html(os.path.join(args.out, "install.html"))
        system.to_call_sheet().save_html(os.path.join(args.out, "call_sheet.html"))
        with open(os.path.join(args.out, "practice.html"), "w",
                  encoding="utf-8") as fh:
            fh.write(system.to_practice(week=args.week).to_html())
        system.to_playbook().save_pdf(os.path.join(args.out, "playbook.pdf"),
                                      plays_per_page=4)
        system.save(os.path.join(args.out, "system.json"))
        system.render_all(os.path.join(args.out, "diagrams"))
        print(f"{chr(10)}Wrote the install to {os.path.abspath(args.out)}")
    return 0


def cmd_script(args: argparse.Namespace) -> int:
    s = _series_by_key(args.name)
    script = s.to_script(reps=args.reps)
    if args.looks:
        looks = [_resolve(defense_registry(), lk, "defense")() for lk in args.looks]
        script = script.with_looks(looks)
    if args.hashes:
        script = script.alternate_hashes()
    print(script.table())
    if args.out:
        if args.out.endswith(".csv"):
            script.save_csv(args.out)
        else:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(script.to_html())
        print(f"\nSaved: {os.path.abspath(args.out)}")
    return 0


def cmd_callsheet(args: argparse.Namespace) -> int:
    from .callsheet import CallSheet, Wristband
    plays: list[Play] = []
    for key in args.series:
        plays.extend(_series_by_key(key).plays)
    book = Playbook(name=args.name, team=args.team, plays=plays)
    sheet = CallSheet.from_playbook(book, name=args.name).number()
    sheet = sheet.model_copy(update={"opponent": args.opponent})
    print(sheet.table())
    if args.out:
        sheet.save_html(args.out)
        print(f"\nSaved: {os.path.abspath(args.out)}")
        if args.wristband:
            Wristband.from_call_sheet(sheet).save_html(args.wristband)
            print(f"Saved: {os.path.abspath(args.wristband)}")
    return 0


# Terminal output stays ASCII: call sheets get printed on press-box machines.
_ASCII = str.maketrans({"·": "-", "—": "-", "–": "-", "’": "'", "‘": "'", "“": '"',
                        "”": '"', "…": "...", "★": "*", "→": "->", "×": "x"})


def _plain(text) -> str:
    return str(text).translate(_ASCII).encode("ascii", "replace").decode("ascii")


def _load_book(path: str) -> Playbook:
    """A playbook file, or a play file as a book of one; a plain exit when it is neither."""
    import json
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("plays"), list):
            return Playbook.model_validate(data)
        play = Play.model_validate(data)
        return Playbook(name=play.name, plays=[play])
    except FileNotFoundError:
        raise SystemExit(f"no such file: {path}")
    except ValueError as e:                 # bad JSON, or not a play (ValidationError is one)
        raise SystemExit(f"{path} isn't a play or a playbook: {str(e).splitlines()[0]}")


def cmd_book(args: argparse.Namespace) -> int:
    """Turn a playbook file — from the designer or from Python — into pages."""
    book = _load_book(args.file)
    stem = os.path.splitext(args.file)[0]
    if args.sheet == "playbook":
        out = args.out or stem + ".pdf"
        if out.endswith(".html"):
            book.save_html(out, level=args.level, theme=args.theme or "paper")
            print(f"Saved: {os.path.abspath(out)}  ({len(book.plays)} plays)")
        else:                               # the exporter reports its own save
            book.save_pdf(out, plays_per_page=args.per_page, level=args.level,
                          theme=args.theme or "paper")
        return 0

    from . import paper
    key = args.key or os.environ.get("CHALKTALK_KEY") or None
    # Asked for, so it never sits in shell history; only at a terminal (on Windows
    # NUL claims to be one, so the output has to be a terminal too).
    if not key and paper.needs_key(args.sheet, book) and sys.stdin.isatty() and sys.stdout.isatty():
        import getpass
        key = getpass.getpass("The staff key (never saved): ").strip() or None
    try:
        html = paper.render(args.sheet, book, key=key, per_row=args.per_row,
                            columns=args.columns, size=args.size, copies=args.copies,
                            reps=args.reps, hashes=args.hashes, level=args.level)
    except ValueError as e:
        tip = " Pass --key, or set CHALKTALK_KEY." if "key" in str(e) else ""
        raise SystemExit(f"{str(e).rstrip('.')}.{tip}")
    out = args.out or f"{stem}-{args.sheet}.html"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    summary, hint = paper.info(args.sheet, book, key=key, reps=args.reps, hashes=args.hashes)
    print(_plain(f"Saved: {os.path.abspath(out)}  ({summary})"))
    if hint:
        print(_plain(hint))
    return 0


def _spot(text: str) -> int:
    """Where the ball is, as yards to the goal: 'own 25' -> 75, 'opp 32' -> 32, '50' -> 50."""
    import re
    m = re.fullmatch(r"\s*(own|opp)?\s*(\d{1,2})\s*", text.lower())
    n = int(m.group(2)) if m else 0
    if not m or not 1 <= n <= (50 if m.group(1) else 99):
        raise SystemExit(f"--at takes 'own 25', 'opp 32', or yards to the goal (1-99), not {text!r}")
    return 100 - n if m.group(1) == "own" else n


def cmd_next(args: argparse.Namespace) -> int:
    """What the planner would call here, and why: the Game panel, in the terminal."""
    from . import planner as P
    from .models import DriveState
    book = _load_book(args.file)
    try:
        state = DriveState(down=args.down, distance=args.distance, yard_line=_spot(args.at),
                           hash_mark=args.hash, mode=args.mode, look=args.look)
    except ValueError as e:
        raise SystemExit(f"that situation doesn't work: {str(e).splitlines()[0]}")
    picks = P.suggest(book, state, [] if args.fresh else None, k=args.k)
    print(_plain(state.label() + (f" vs {args.look}" if args.look else "")))
    if not picks:
        print("No play in the book fits this situation.")
    for i, s in enumerate(picks, 1):
        print(_plain(f"{i:>2}. {s.call}  ({s.points:+d})"))
        for r in s.reasons:
            print(_plain(f"      {r.points:+d}  {r.text}"))
        for b in s.branches:
            print(_plain(f"      If {b.when}: {b.call}"))
    return 0


def cmd_scout(args: argparse.Namespace) -> int:
    """The halftime report from the book's game log, in the terminal."""
    from . import scout
    from .planner import plan_of
    from .renderer.plan_sheets import plan_title
    book = _load_book(args.file)
    title = plan_title(plan_of(book))
    r = scout.report(book)
    if not r.snaps:
        print(_plain(f"{title}: nothing logged yet. Log snaps in the designer's Game panel."))
        return 0
    print(_plain(f"{title}: {r.on} of {r.snaps} on schedule ({r.rate}%), "
                 f"{r.thirds.on} of {r.thirds.calls} on third down"))

    def per_call(yards: float, calls: int) -> str:
        return format(round(yards / calls * 10) / 10 if calls else 0, "g")

    blocks = [
        ("What a scout sees", list(r.notes)),
        ("By down", [f"{s.label:<10} {s.on} of {s.calls} on schedule, {per_call(s.yards, s.calls)} a call"
                     for s in r.by_down]),
        ("What is working", [f"{per_call(l.yards, l.calls):>5} a call  {l.call} ({l.calls} calls)"
                             for l in r.best]),
        ("Explosives", [f"{per_call(l.yards, l.calls):>5}  {l.call}" for l in r.explosives]),
        ("Set up and not called", list(r.ready)),
        ("Left on the sheet", list(r.unused)),
    ]
    for head, lines in blocks:
        if lines:
            print(f"\n{head}")
            for line in lines:
                print(_plain(f"  {line}"))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """What a coordinator would flag in the book's plan."""
    from . import planner as P
    book = _load_book(args.file)
    notes = P.check(book)
    print(_plain(f"{book.name}: " + (f"{len(notes)} to look at" if notes else "nothing to flag")))
    for note in notes:
        print(_plain(f"  - {note}"))
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    """Fill the plan's blanks from what the plays say about themselves."""
    from . import planner as P
    book = _load_book(args.file)
    d = P.draft(book)
    if not d.notes:
        print("Nothing blank to fill: every play has its series, the call sheet and the script are set.")
        return 0
    for note in d.notes:
        print(_plain(f"  {note}"))
    if args.out:
        d.book.save(args.out)
        print(f"Saved: {os.path.abspath(args.out)}")
    else:
        print(f"\n{len(d.notes)} changes, not saved. Run with -o {args.file} to save them.")
    return 0


def _log_without_a_console() -> None:
    """
    Started from the shortcut (pythonw) there is nowhere to print, so a designer
    that won't start would just not appear. Keep what it says in a log instead.
    """
    from .designer.shortcut import data_dir
    try:
        data_dir().mkdir(parents=True, exist_ok=True)
        log = open(data_dir() / "designer.log", "w", encoding="utf-8", buffering=1)
    except OSError:
        log = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = sys.stderr = log


def cmd_design(args: argparse.Namespace) -> int:
    """Run the designer on this machine and open it in the browser."""
    import webbrowser
    from .designer.home import default_folder
    from .designer.server import DEFAULT_PORT, Session, running_at, serve

    file = play = None
    if args.play and (os.path.exists(args.play) or args.play.lower().endswith(".json")):
        file = os.path.abspath(args.play)       # a file to edit, or one Save will create
    elif args.play:
        play = _build_play(args.play, args.formation, args.defense, args.flip,
                           getattr(args, "coverage", None))
    # Where Open looks and Save as starts: --folder, else the file's own folder,
    # else the coach's playbook folder (Documents/chalktalk).
    folder = os.path.expanduser(args.folder) if args.folder else (os.path.dirname(file) if file else None)
    if args.quiet and sys.stdout is None:
        _log_without_a_console()
    if (file is None and play is None and args.port == DEFAULT_PORT
            and running_at(DEFAULT_PORT, folder=folder)):
        url = f"http://127.0.0.1:{DEFAULT_PORT}/"
        print(f"Chalktalk is already running: {url}")   # a second double-click opens it again
        if not args.no_open:
            webbrowser.open(url)
        return 0
    folder = os.path.abspath(os.path.expanduser(folder or str(default_folder())))
    try:
        os.makedirs(folder, exist_ok=True)
        session = Session(folder, file=file, play=play, level=args.level, theme=args.theme)
    except (OSError, ValueError) as e:
        print(f"Can't open {args.play or folder}: {e}", file=sys.stderr)    # as the coach typed it
        return 1
    if play is not None:
        print(f"Loaded:   {play.call}")
    try:
        serve(session, port=args.port, open_browser=not args.no_open, quiet=args.quiet)
    except OSError as e:
        print(f"Can't start the designer on port {args.port}: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_shortcut(args: argparse.Namespace) -> int:
    """Put a Chalktalk icon where this system keeps them, so no terminal is needed."""
    from .designer import shortcut
    if args.remove:
        gone = shortcut.remove()
        print("\n".join(f"Removed:  {p}" for p in gone) or "No Chalktalk shortcuts to remove.")
        return 0
    try:
        made = shortcut.create(folder=args.folder)
    except (OSError, RuntimeError) as e:
        print(f"Couldn't make the shortcut: {e}", file=sys.stderr)
        return 1
    for p in made:
        print(f"Made:     {p}")
    print("Open Chalktalk from there: the designer opens in your browser, and stops a little "
          "after you close it.")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Generate one of everything so you can see what the package does."""
    from .callsheet import CallSheet, Wristband
    from .script import PracticeScript
    from .renderer.sheets import series_html
    out = args.out
    os.makedirs(out, exist_ok=True)

    all_series = series_catalog.all_series()
    plays: list[Play] = []
    for s in all_series:
        plays.extend(s.plays)
        with open(os.path.join(out, f"series_{s.name.split()[0].lower()}.html"),
                  "w", encoding="utf-8") as fh:
            fh.write(series_html(s))

    book = Playbook(name="Demo Playbook", team=args.team, plays=plays)
    book.save_html(os.path.join(out, "playbook.html"), level=args.level)
    book.save(os.path.join(out, "playbook.json"))
    book.save_pdf(os.path.join(out, "playbook.pdf"), plays_per_page=4, level=args.level)

    sheet = CallSheet.from_playbook(book, name="Game Plan").number()
    sheet.save_html(os.path.join(out, "call_sheet.html"))
    Wristband.from_call_sheet(sheet).save_html(os.path.join(out, "wristband.html"))

    practice = PracticeScript(name="Tuesday Practice", team=args.team)
    for s in all_series[:3]:
        practice = practice.add_period(s.name, s.to_script(), minutes=12)
    with open(os.path.join(out, "practice.html"), "w", encoding="utf-8") as fh:
        fh.write(practice.to_html())
    practice.save_csv(os.path.join(out, "practice.csv"))

    print(f"{len(plays)} plays across {len(all_series)} series -> {os.path.abspath(out)}")
    for f in sorted(os.listdir(out)):
        print(f"  {f}")
    print(f"\nOpen the playbook in the designer: chalk design {os.path.join(out, 'playbook.json')}")
    return 0


# ── Parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chalktalk",
        description="Design, script, and print American football plays.")
    p.add_argument("--version", action="version", version=f"chalktalk {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    lst = sub.add_parser("list", help="list catalog contents")
    lst.add_argument("what",
                     help="plays | formations | defenses | routes | series | "
                          "schemes | blocks | coverages | qb | systems")
    lst.set_defaults(func=cmd_list)

    ren = sub.add_parser("render", help="render one play to SVG/PDF/JSON")
    ren.add_argument("play")
    ren.add_argument("-o", "--out", help="output file (.svg, .pdf, .json)")
    ren.add_argument("-f", "--formation", help="override the formation")
    ren.add_argument("-d", "--defense", help="draw a defensive look")
    ren.add_argument("--flip", action="store_true", help="mirror the play")
    ren.add_argument("--coverage", help="a coverage call, e.g. cover_3")
    ren.add_argument("--scale", type=float, default=18.0)
    ren.add_argument("--level", default="nfl", choices=["nfl", "ncaa", "hs"],
                     help="hash marks: nfl | ncaa | hs")
    ren.add_argument("--theme", default="turf", choices=["turf", "paper"],
                     help="turf for the screen, paper for the printer")
    ren.add_argument("--hide", help="layers to leave out, e.g. defense,zones")
    ren.add_argument("--describe", action="store_true")
    ren.set_defaults(func=cmd_render)

    sho = sub.add_parser("show", help="print a play's assignments")
    sho.add_argument("play")
    sho.add_argument("-f", "--formation")
    sho.add_argument("-d", "--defense")
    sho.add_argument("--flip", action="store_true")
    sho.add_argument("--coverage", help="a coverage call, e.g. cover_3")
    sho.set_defaults(func=cmd_show)

    ser = sub.add_parser("series", help="describe / export a scripted series")
    ser.add_argument("name")
    ser.add_argument("--out", help="directory for diagrams + HTML")
    ser.set_defaults(func=cmd_series)

    scr = sub.add_parser("script", help="build a practice script from a series")
    scr.add_argument("name")
    scr.add_argument("--reps", type=int, default=1)
    scr.add_argument("--looks", nargs="*", help="scout looks to cycle through")
    scr.add_argument("--hashes", action="store_true", help="alternate hash marks")
    scr.add_argument("-o", "--out", help="output .html or .csv")
    scr.set_defaults(func=cmd_script)

    sysp = sub.add_parser("system", help="describe or export a series set")
    sysp.add_argument("name")
    sysp.add_argument("--out", help="directory for the install book and sheets")
    sysp.add_argument("--week", type=int, help="only this install week")
    sysp.add_argument("--balance", action="store_true",
                      help="show answers per base and personnel spread")
    sysp.set_defaults(func=cmd_system)

    cs = sub.add_parser("callsheet", help="build a call sheet from series")
    cs.add_argument("series", nargs="+")
    cs.add_argument("--name", default="Call Sheet")
    cs.add_argument("--team")
    cs.add_argument("--opponent")
    cs.add_argument("-o", "--out", help="output .html")
    cs.add_argument("--wristband", help="also write a wristband .html")
    cs.set_defaults(func=cmd_callsheet)

    from .paper import KINDS
    bk = sub.add_parser("book", help="print a playbook .json: the playbook, or any sheet from it")
    bk.add_argument("file", help="a playbook .json saved from the designer or Python")
    bk.add_argument("--sheet", default="playbook", choices=list(KINDS),
                    help="what to print (default: playbook, as PDF unless -o says .html; "
                         "every other sheet is HTML)")
    bk.add_argument("-o", "--out", help="output file; default: next to the input")
    bk.add_argument("--per-page", type=int, default=2, choices=[1, 2, 4],
                    help="plays per PDF page")
    bk.add_argument("--per-row", type=int, default=2, choices=[1, 2],
                    help="diagrams across, for the install book")
    bk.add_argument("--columns", type=int, default=2, choices=[1, 2, 3],
                    help="call sheet columns")
    bk.add_argument("--size", default="adult", choices=["youth", "teen", "adult"],
                    help="wristband insert size")
    bk.add_argument("--copies", type=int, default=1, help="wristband inserts to print")
    bk.add_argument("--reps", type=int, default=1, help="practice script reps per play")
    bk.add_argument("--hashes", action="store_true", help="practice script: alternate L, R, M")
    bk.add_argument("--key", help="the staff key for coded sheets (or set CHALKTALK_KEY; "
                                  "asked for when it's needed and missing)")
    bk.add_argument("--theme", choices=["turf", "paper"],
                    help="default: paper, because it prints")
    bk.add_argument("--level", default="nfl", choices=["nfl", "ncaa", "hs"])
    bk.set_defaults(func=cmd_book)

    nx = sub.add_parser("next", help="what the planner would call next, and why")
    nx.add_argument("file", help="a playbook .json with its game plan")
    nx.add_argument("--down", type=int, default=1, choices=[1, 2, 3, 4])
    nx.add_argument("--distance", type=float, default=10)
    nx.add_argument("--at", default="own 25", help="where the ball is: 'own 25', 'opp 32', or yards to go")
    nx.add_argument("--hash", choices=["L", "M", "R"])
    nx.add_argument("--mode", choices=["two_minute", "four_minute"])
    nx.add_argument("--look", help="the coverage they're showing, e.g. 'Cover 3'")
    nx.add_argument("-k", type=int, default=3, help="how many calls (default 3)")
    nx.add_argument("--fresh", action="store_true",
                    help="ignore the game log (what's been called, shown and worked)")
    nx.set_defaults(func=cmd_next)

    sc = sub.add_parser("scout", help="the halftime report from a playbook's game log")
    sc.add_argument("file")
    sc.set_defaults(func=cmd_scout)

    ck = sub.add_parser("check", help="what a coordinator would flag in a playbook's plan")
    ck.add_argument("file")
    ck.set_defaults(func=cmd_check)

    dr = sub.add_parser("draft", help="fill a plan's blanks: series, call sheet, openers")
    dr.add_argument("file")
    dr.add_argument("-o", "--out", help="where to save the drafted book (nothing is saved without it)")
    dr.set_defaults(func=cmd_draft)

    from .designer.server import DEFAULT_PORT
    des = sub.add_parser("design", help="open the visual play designer in your browser")
    des.add_argument("play", nargs="?",
                     help="a play or playbook .json to edit (Save creates it if it doesn't "
                          "exist yet), or a catalog play name to start from")
    des.add_argument("-f", "--formation", help="override the formation")
    des.add_argument("-d", "--defense", help="draw a defensive look")
    des.add_argument("--flip", action="store_true")
    des.add_argument("--coverage", help="a coverage call, e.g. cover_3")
    des.add_argument("--level", default="nfl", choices=["nfl", "ncaa", "hs"])
    des.add_argument("--theme", default="turf", choices=["turf", "paper"],
                     help="the look the designer opens in")
    des.add_argument("--port", type=int, default=DEFAULT_PORT,
                     help=f"the port on this machine to serve it from (default: {DEFAULT_PORT})")
    des.add_argument("--no-open", action="store_true",
                     help="start the designer without opening a browser")
    des.add_argument("--folder", help="where Open looks and Save as starts "
                                      "(default: the file's folder, else Documents/chalktalk)")
    des.add_argument("--quiet", action="store_true",
                     help="stop a little after the page is closed, rather than at Ctrl+C "
                          "(what the shortcut does)")
    des.set_defaults(func=cmd_design)

    sh = sub.add_parser("shortcut", help="put a Chalktalk icon on the desktop and in the start menu")
    sh.add_argument("--folder", help="the folder the designer keeps playbooks in "
                                     "(default: Documents/chalktalk)")
    sh.add_argument("--remove", action="store_true", help="take the shortcuts away again")
    sh.set_defaults(func=cmd_shortcut)

    dem = sub.add_parser("demo", help="generate a full example package")
    dem.add_argument("--out", default="output/demo")
    dem.add_argument("--team")
    dem.add_argument("--level", default="nfl", choices=["nfl", "ncaa", "hs"],
                     help="hash marks on the playbook pages")
    dem.set_defaults(func=cmd_demo)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
