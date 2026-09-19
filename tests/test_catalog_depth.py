"""
Coverage of the catalog itself: does the library actually contain the plays an
offense runs, and does the registry see all of them?
"""
import collections

import pytest

from chalktalk import catalog
from chalktalk.catalog import playaction, rpo, screens
from chalktalk.models.play import PlayType
from chalktalk.models.qb import QBAction
from chalktalk.templates import formations as F

PLAYS = catalog.all_plays()


# ── The registry ──────────────────────────────────────────────────────────────

def test_play_names_are_unique_across_modules():
    """
    Two modules both exporting `bubble` silently lost one of them from the CLI
    and the designer, because both key plays by bare name.
    """
    seen: dict[str, str] = {}
    clashes = []
    for module in catalog.PLAY_MODULES:
        import inspect
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_") or fn.__module__ != module.__name__:
                continue
            if name in seen:
                clashes.append(f"{name}: {seen[name]} and {module.__name__}")
            seen[name] = module.__name__
    assert not clashes, clashes


def test_the_registry_finds_every_module():
    assert len(PLAYS) == sum(
        1 for module in catalog.PLAY_MODULES
        for name, fn in __import__("inspect").getmembers(module,
                                                         callable)
        if not name.startswith("_") and getattr(fn, "__module__", None) == module.__name__
    )


def test_the_cli_and_the_designer_see_the_same_plays():
    from chalktalk.cli import play_registry
    from chalktalk import designer
    assert set(play_registry()) == set(PLAYS)
    assert set(designer.catalog()["plays"]) == set(PLAYS)


# ── What an offense actually needs ────────────────────────────────────────────

def test_the_catalog_covers_every_play_type():
    kinds = {p.play_type for p in PLAYS.values()}
    assert kinds >= {PlayType.PASS, PlayType.RUN, PlayType.RPO, PlayType.SCREEN}


def test_there_is_a_play_action_game():
    pa = [n for n, p in PLAYS.items()
          if p.qb.action in (QBAction.PLAY_ACTION, QBAction.BOOT)]
    assert len(pa) >= 5, pa


def test_there_is_a_screen_game():
    assert len([p for p in PLAYS.values()
                if p.play_type is PlayType.SCREEN]) >= 5


def test_there_is_a_movement_game():
    moving = [p for p in PLAYS.values()
              if p.qb.action in (QBAction.BOOT, QBAction.SPRINT)]
    assert len(moving) >= 4


def test_the_rpo_family_reads_different_defenders():
    keys = {p.qb.key for p in PLAYS.values() if p.play_type is PlayType.RPO}
    assert len(keys) >= 4, f"every RPO reads the same man: {keys}"


def test_the_catalog_is_not_all_dropback():
    actions = collections.Counter(p.qb.action for p in PLAYS.values())
    assert actions[QBAction.DROPBACK] < len(PLAYS) * 0.5


# ── Play action ───────────────────────────────────────────────────────────────

def test_play_action_sells_the_run():
    """A fake nobody blocks for is not a fake."""
    for name in ("pa_boot", "pa_waggle", "naked", "pa_keeper"):
        play = getattr(playaction, name)()
        assert play.qb.mesh_with, name
        assert play.qb.action is QBAction.BOOT, name


def test_boots_go_away_from_the_run_action():
    play = playaction.pa_boot()
    assert play.qb.direction == -1          # quarterback leaves to the left
    assert play.qb.mesh_at.x > 0            # after faking to the right


def test_the_shot_play_keeps_everybody_in():
    play = playaction.pa_shot()
    blocking = [a.player.label for a in play.assignments if a.is_blocking]
    assert len(blocking) >= 7, "a shot play protects with more than five"
    assert len(play.qb.reads) <= 3


def test_naked_has_no_protection_behind_it():
    assert "Naked" in (playaction.naked().protection or "")


# ── Screens ───────────────────────────────────────────────────────────────────

def test_screens_release_linemen_downfield():
    """The tell: linemen climbing instead of setting."""
    for name in ("rb_slip", "jailbreak", "middle"):
        play = getattr(screens, name)()
        climbing = [a.player.label for a in play.assignments
                    if a.player.is_ol and a.block and a.block.climbs]
        assert len(climbing) >= 3, f"{name} only releases {climbing}"


def test_every_screen_has_a_ball_carrier():
    for name, play in PLAYS.items():
        if play.play_type is PlayType.SCREEN:
            assert play.ball_carrier is not None, name


def test_quick_screens_get_the_ball_out_immediately():
    for name in ("tunnel", "bubble_screen"):
        play = getattr(screens, name)()
        assert play.qb.depth <= 1.0, f"{name} has the quarterback retreating"


def test_slow_screens_invite_the_rush():
    for name in ("rb_slip", "middle", "jailbreak"):
        play = getattr(screens, name)()
        assert play.qb.action is QBAction.SCREEN
        assert play.qb.depth >= 4.0


# ── RPOs ──────────────────────────────────────────────────────────────────────

def test_every_rpo_rides_the_mesh_and_reads_somebody():
    for name in ("bubble", "glance", "slant", "pop", "arrow"):
        play = getattr(rpo, name)()
        assert play.play_type is PlayType.RPO, name
        assert play.qb.action is QBAction.MESH, name
        assert play.qb.key, f"{name} does not say who is being read"
        assert play.ball_carrier is not None, name


def test_rpos_block_a_run():
    for name in ("bubble", "glance", "slant", "pop", "arrow"):
        play = getattr(rpo, name)()
        kinds = {a.block.kind.value for a in play.assignments if a.block}
        assert kinds - {"pass_set"}, f"{name} is protecting, not run blocking"


def test_the_rpo_throw_goes_to_somebody_running_a_route():
    for name in ("bubble", "glance", "slant", "pop", "arrow"):
        play = getattr(rpo, name)()
        for label in play.qb.reads:
            assert play.assignment(label).route is not None, name


# ── Left-handed formations ────────────────────────────────────────────────────

LEFT_PAIRS = [
    ("I_FORM_PRO_RIGHT", "I_FORM_PRO_LEFT"),
    ("I_FORM_STRONG_RIGHT", "I_FORM_STRONG_LEFT"),
    ("GUN_OFFSET_BACK_RIGHT", "GUN_OFFSET_BACK_LEFT"),
    ("GUN_TREY_RIGHT", "GUN_TREY_LEFT"),
    ("PISTOL_TRIPS_RIGHT", "PISTOL_TRIPS_LEFT"),
    ("RED_ZONE_TRIPS_RIGHT", "RED_ZONE_TRIPS_LEFT"),
    ("SINGLE_BACK_PRO_RIGHT", "SINGLE_BACK_PRO_LEFT"),
    ("GUN_TRIPS_TE_RIGHT", "GUN_TRIPS_TE_LEFT"),
]


@pytest.mark.parametrize("right,left", LEFT_PAIRS)
def test_left_formations_mirror_their_right_hand_twin(right, left):
    r, ell = getattr(F, right)(), getattr(F, left)()
    assert {p.label for p in r.players} == {p.label for p in ell.players}
    for player in r.players:
        assert ell.player(player.label).x == -player.x
        assert ell.player(player.label).y == player.y


@pytest.mark.parametrize("right,left", LEFT_PAIRS)
def test_left_formations_are_named_left(right, left):
    assert "Left" in getattr(F, left)().name


def test_mirroring_a_formation_twice_is_a_round_trip():
    original = F.SHOTGUN_TRIPS_RIGHT()
    assert original.mirror().mirror().model_dump() == original.model_dump()


def test_the_name_flip_is_shared_by_everything_that_flips():
    from chalktalk.models.core import flip_side_name
    assert flip_side_name("Trips Right") == "Trips Left"
    assert flip_side_name("Slide Rt") == "Slide Lt"
    assert flip_side_name("Mesh") == "Mesh"
    assert flip_side_name(None) is None
