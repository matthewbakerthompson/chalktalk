"""
Blocking: the schemes, the geometry, and the rule that keeps a pull pointing
the right way.
"""
import pytest

from chalktalk import adjustments as A
from chalktalk.builder import play as build
from chalktalk.catalog import passing, redzone, running
from chalktalk.models import Play
from chalktalk.models.block import Block, BlockKind
from chalktalk.models.core import Point
from chalktalk.templates import blocking as B, formations as F, routes as R
from chalktalk.templates import schemes as S

LINE = ("LT", "LG", "C", "RG", "RT")


def _kinds(play: Play) -> dict[str, str]:
    return {a.player.label: a.block.kind.value
            for a in play.assignments if a.block}


# ── The model ─────────────────────────────────────────────────────────────────

def test_block_path_is_relative_to_the_blocker():
    block = B.REACH(1)
    assert block.absolute_path(4.5, 0.0)[0] == (4.5, 0.0)
    assert block.absolute_path(4.5, 0.0)[-1][0] > 4.5      # steps to the right


def test_direction_flips_the_path():
    right, left = B.REACH(1), B.REACH(-1)
    assert [p.x for p in right.path] == [-p.x for p in left.path]
    assert [p.y for p in right.path] == [p.y for p in left.path]


def test_pullers_go_behind_the_line_first():
    for block in (B.KICK(1), B.WRAP(1), B.TRAP(1), B.PULL(1)):
        assert block.is_pulling
        assert min(p.y for p in block.path) < 0, block.kind


def test_wrap_and_climb_finish_at_the_second_level():
    assert B.WRAP(1).to_second_level
    assert B.CLIMB(0).path[-1].y > 3.0
    assert not B.BASE().to_second_level


def test_combo_partner_only_climbs_when_asked():
    climber = B.COMBO("RT", 1, target="M")
    holder = B.COMBO("RG", 1, climb=False)
    assert climber.path[-1].y > holder.path[-1].y
    assert climber.combo_with == "RT"


def test_block_describes_itself_for_a_wristband():
    assert B.WRAP(1, target="M").describe() == "Wrap -> M"
    assert B.COMBO("RT", 1, target="S").describe() == "Combo w/ RT -> S"


# ── Blocks are NOT mirrored like routes ───────────────────────────────────────

def test_blocks_ignore_the_left_side_route_convention():
    """
    A route on a left-side player gets mirrored on the way out. A block must
    not — a pull to the right is a pull to the right whoever is doing it.
    """
    scheme = S.power(1)
    lt = build(F.I_FORM_PRO_RIGHT()).scheme(scheme).build().assignment("LG")
    assert lt.player.is_left_side              # LG is at x = -2
    # the wrap still travels to the offense's right
    assert lt.block.absolute_path(lt.player.x, lt.player.y)[-1][0] > lt.player.x


def test_mirroring_a_play_mirrors_its_blocks():
    right = build(F.I_FORM_PRO_RIGHT()).scheme(S.power(1)).build()
    left = right.mirror()
    puller_r = right.assignment("LG").block.absolute_path(-2.0, 0.0)[-1][0]
    puller_l = left.assignment("LG").block.absolute_path(2.0, 0.0)[-1][0]
    assert puller_r > -2.0        # pulls right
    assert puller_l < 2.0         # after the flip, pulls left


def test_block_mirrored_is_reversible():
    block = B.WRAP(1, target="M")
    assert block.mirrored().mirrored().path == block.path


# ── Schemes ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", sorted(S.SCHEMES))
def test_every_scheme_covers_the_whole_line(name):
    blocks = S.SCHEMES[name](1) if name != "big_on_big" else S.big_on_big()
    for label in LINE:
        assert label in blocks, f"{name} leaves {label} unblocked"
        assert isinstance(blocks[label], Block)


def test_power_pulls_the_backside_guard_and_kicks_with_the_back():
    blocks = S.power(1, kicker="FB")
    assert blocks["LG"].kind is BlockKind.WRAP
    assert blocks["FB"].kind is BlockKind.KICK
    assert all(blocks[l].kind is BlockKind.DOWN for l in ("RT", "RG", "C"))


def test_counter_swaps_the_kicker_and_the_wrapper():
    power, counter = S.power(1), S.counter(1)
    assert power["LG"].kind is BlockKind.WRAP
    assert counter["LG"].kind is BlockKind.KICK
    assert counter["LT"].kind is BlockKind.WRAP


def test_direction_moves_playside_to_the_other_end_of_the_line():
    right, left = S.power(1), S.power(-1)
    assert right["RT"].kind is BlockKind.DOWN and right["LT"].kind is BlockKind.HINGE
    assert left["LT"].kind is BlockKind.DOWN and left["RT"].kind is BlockKind.HINGE


def test_inside_zone_combos_are_reciprocal():
    blocks = S.inside_zone(1)
    for label, block in blocks.items():
        if block.combo_with:
            partner = blocks[block.combo_with]
            assert partner.combo_with == label, f"{label} combos alone"


def test_only_one_player_climbs_off_each_combo():
    blocks = S.inside_zone(1)
    pairs: dict[frozenset, int] = {}
    for label, block in blocks.items():
        if block.combo_with:
            pair = frozenset((label, block.combo_with))
            pairs[pair] = pairs.get(pair, 0) + (1 if block.climbs else 0)
    assert pairs and all(count == 1 for count in pairs.values())


def test_half_slide_is_half_slide_and_half_man():
    blocks = S.half_slide(1)
    assert [blocks[l].kind for l in ("C", "RG", "RT")] == [BlockKind.SLIDE] * 3
    assert [blocks[l].kind for l in ("LG", "LT")] == [BlockKind.PASS_SET] * 2


def test_max_protect_keeps_the_back_in():
    blocks = S.max_protect(1, extras=("RB", "Y"))
    assert "RB" in blocks and "Y" in blocks
    assert blocks["RB"].kind is BlockKind.PASS_SET


# ── The builder ───────────────────────────────────────────────────────────────

def test_scheme_ignores_players_who_are_not_on_the_field():
    # GUN_OFFSET_BACK_RIGHT has no fullback; the kick assignment is dropped
    play = build(F.GUN_OFFSET_BACK_RIGHT()).scheme(S.power(1, kicker="FB")).build()
    assert play.assignment("FB") is None
    assert len([a for a in play.assignments if a.block]) == 5


def test_scheme_sets_the_protection_name():
    play = build(F.SHOTGUN_TRIPS_RIGHT()).pass_pro(S.half_slide(1), "Half Slide Rt").build()
    assert play.protection == "Half Slide Rt"


def test_a_player_cannot_block_and_run_a_route():
    play = build(F.SHOTGUN_TRIPS_RIGHT()).pass_pro().build()
    with_route = play.with_route("LT", R.FLAT())
    assert with_route.assignment("LT").block is None
    back_to_blocking = with_route.with_block("LT", B.BASE())
    assert back_to_blocking.assignment("LT").route is None


def test_with_scheme_applies_to_an_existing_play():
    play = passing.mesh_concept().with_scheme(S.slide(1), "Slide Rt")
    assert _kinds(play)["C"] == "slide"
    assert play.protection == "Slide Rt"


# ── The catalog ───────────────────────────────────────────────────────────────

def test_run_plays_no_longer_share_one_diagram():
    """The bug this feature exists to fix: power, counter and zone drew alike."""
    signatures = {
        name: tuple(sorted(_kinds(getattr(running, name)()).items()))
        for name in ("inside_zone", "outside_zone", "power_right",
                     "counter_trey", "trap", "lead_iso", "draw")
    }
    assert len(set(signatures.values())) == len(signatures)


def test_every_run_play_has_a_real_scheme():
    for name in ("inside_zone", "power_right", "counter_trey", "toss_sweep"):
        kinds = set(_kinds(getattr(running, name)()).values())
        assert kinds - {"base"}, f"{name} is still all generic base blocks"


def test_pass_plays_protect():
    for name in ("mesh_concept", "smash", "four_verticals"):
        kinds = _kinds(getattr(passing, name)())
        assert all(kinds[l] == "pass_set" for l in LINE), name


def test_the_rpo_blocks_the_run():
    assert set(_kinds(passing.rpo_bubble()).values()) & {"combo", "scoop"}


def test_goal_line_power_still_kicks_with_the_fullback():
    assert _kinds(redzone.goal_line_power())["FB"] == "kick"


def test_play_action_keeps_the_protection():
    play = running.inside_zone().adjust(A.PLAY_ACTION("RB"))
    assert play.protection


# ── Rendering ─────────────────────────────────────────────────────────────────

def test_every_block_gets_a_path_and_a_cap():
    play = running.power_right()
    svg = play.render().render()
    n_blocks = len([a for a in play.assignments if a.block])
    assert svg.count('stroke="#e5e7eb"') >= n_blocks * 2      # path + cap each


def test_a_double_team_draws_one_bracket_not_two():
    svg = running.inside_zone().render().render()
    assert svg.count('stroke-dasharray="4,3"') == 2          # two combo pairs


def test_pullers_and_base_blocks_look_different():
    power = running.power_right().render().render()
    iso = running.lead_iso().render().render()
    assert power != iso


def test_legacy_block_routes_still_draw():
    """A play saved before blocks existed says 'block' with a route."""
    play = passing.mesh_concept().with_route("LT", R.BLOCK())
    assert play.assignment("LT").block is None
    assert 'stroke="#e5e7eb"' in play.render().render()


def test_blocks_survive_a_json_round_trip():
    play = running.counter_trey()
    assert Play.from_json(play.to_json()) == play


def test_pdf_export_with_blocking(tmp_path):
    from chalktalk.models import Playbook
    path = tmp_path / "blocks.pdf"
    Playbook(name="B", plays=[running.power_right(),
                              running.inside_zone()]).save_pdf(str(path))
    assert path.stat().st_size > 1000


def test_describe_lists_blocking_assignments():
    text = running.power_right().describe()
    assert "Wrap" in text
    assert "Kick" in text
