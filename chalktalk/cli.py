"""
chalktalk command line — browse the catalog and render plays without writing
any Python.

    chalk list plays
    chalk render mesh_concept -o out/mesh.svg
    chalk series mesh --out out/mesh_series
    chalk script inside_zone --reps 2
    chalk callsheet inside_zone mesh red_zone -o out/week3.html
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
from .catalog import series as series_catalog
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
    elif what in ("series",):
        for key, fn in series_catalog.ALL_SERIES.items():
            s = fn()
            print(f"  {key:<16} {len(s):>2} plays   {s.name}")
        print(f"\n{len(series_catalog.ALL_SERIES)} series")
    else:
        raise SystemExit("list what? plays | formations | defenses | routes | "
                         "series | schemes | blocks | coverages | qb")
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
    if out.endswith(".pdf"):
        Playbook(name=play.name, plays=[play]).save_pdf(out, level=args.level)
        print(f"Saved: {os.path.abspath(out)}")
    elif out.endswith(".json"):
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(play.to_json())
        print(f"Saved: {os.path.abspath(out)}")
    else:
        play.render(scale=args.scale, level=args.level).save(out)
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


def cmd_design(args: argparse.Namespace) -> int:
    """Open the visual designer, optionally on an existing play."""
    from .designer import open_in_browser, write

    play = None
    if args.play:
        if os.path.exists(args.play):
            with open(args.play, encoding="utf-8") as fh:
                play = Play.from_json(fh.read())
        else:
            play = _build_play(args.play, args.formation, args.defense, args.flip,
                               getattr(args, "coverage", None))

    out = args.out or os.path.join("output", "designer.html")
    path = write(out, play=play, level=args.level)
    print(f"Designer: {path}")
    if play is not None:
        print(f"Loaded:   {play.call}")
    if not args.no_open:
        open_in_browser(path)
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
    book.save_html(os.path.join(out, "playbook.html"))
    book.save(os.path.join(out, "playbook.json"))
    book.save_pdf(os.path.join(out, "playbook.pdf"), plays_per_page=4)

    sheet = CallSheet.from_playbook(book, name="Game Plan").number()
    sheet.save_html(os.path.join(out, "call_sheet.html"))
    Wristband.from_call_sheet(sheet).save_html(os.path.join(out, "wristband.html"))

    practice = PracticeScript(name="Tuesday Practice", team=args.team)
    for s in all_series[:3]:
        practice = practice.add_period(s.name, s.to_script(), minutes=12)
    with open(os.path.join(out, "practice.html"), "w", encoding="utf-8") as fh:
        fh.write(practice.to_html())
    practice.save_csv(os.path.join(out, "practice.csv"))

    from .designer import write as write_designer
    write_designer(os.path.join(out, "designer.html"), level=args.level)

    print(f"{len(plays)} plays across {len(all_series)} series -> {os.path.abspath(out)}")
    for f in sorted(os.listdir(out)):
        print(f"  {f}")
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
                          "schemes | blocks | coverages | qb")
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

    cs = sub.add_parser("callsheet", help="build a call sheet from series")
    cs.add_argument("series", nargs="+")
    cs.add_argument("--name", default="Call Sheet")
    cs.add_argument("--team")
    cs.add_argument("--opponent")
    cs.add_argument("-o", "--out", help="output .html")
    cs.add_argument("--wristband", help="also write a wristband .html")
    cs.set_defaults(func=cmd_callsheet)

    des = sub.add_parser("design", help="open the visual play designer")
    des.add_argument("play", nargs="?",
                     help="a saved play .json, or a catalog play name")
    des.add_argument("-o", "--out", help="where to write the designer HTML")
    des.add_argument("-f", "--formation", help="override the formation")
    des.add_argument("-d", "--defense", help="draw a defensive look")
    des.add_argument("--flip", action="store_true")
    des.add_argument("--coverage", help="a coverage call, e.g. cover_3")
    des.add_argument("--level", default="nfl", choices=["nfl", "ncaa", "hs"])
    des.add_argument("--no-open", action="store_true",
                     help="write the file without launching a browser")
    des.set_defaults(func=cmd_design)

    dem = sub.add_parser("demo", help="generate a full example package")
    dem.add_argument("--out", default="output/demo")
    dem.add_argument("--team")
    dem.add_argument("--level", default="nfl", choices=["nfl", "ncaa", "hs"])
    dem.set_defaults(func=cmd_demo)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
