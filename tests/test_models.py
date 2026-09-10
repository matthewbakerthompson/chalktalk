import pytest

from chalktalk.catalog import passing, running
from chalktalk.models import Play, Playbook, PlayType
from chalktalk.models.situation import (
    Situation, FieldZone, Distance, Hash, zone_for, distance_for,
)


# ── Situation ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("yard,zone", [
    (99, FieldZone.BACKED_UP),
    (95, FieldZone.BACKED_UP),
    (75, FieldZone.OWN),
    (50, FieldZone.MIDFIELD),
    (41, FieldZone.MIDFIELD),
    (35, FieldZone.FRINGE),
    (15, FieldZone.RED_ZONE),
    (7,  FieldZone.LOW_RED),
    (2,  FieldZone.GOAL_LINE),
])
def test_zone_boundaries(yard, zone):
    assert zone_for(yard) is zone


@pytest.mark.parametrize("dist,bucket", [
    (1, Distance.SHORT), (3, Distance.SHORT),
    (4, Distance.MEDIUM), (6, Distance.MEDIUM),
    (7, Distance.LONG), (10, Distance.LONG),
    (11, Distance.XLONG),
])
def test_distance_buckets(dist, bucket):
    assert distance_for(dist) is bucket


def test_own_and_opp_constructors():
    assert Situation.own(25).field_position == "Own 25"
    assert Situation.opp(8).field_position == "Opp 8"
    assert Situation.own(50).field_position == "50"


def test_goal_to_go_display():
    assert Situation(down=1, distance=10, yard_line=8).down_distance == "1st & Goal"
    assert Situation(down=1, distance=10, yard_line=40).down_distance == "1st & 10"


def test_short_and_describe():
    s = Situation(down=3, distance=5, yard_line=32, hash_mark=Hash.LEFT)
    assert s.short() == "3&5 O32 L"
    assert "3rd & 5" in s.describe()


def test_matches_treats_unset_as_wildcard():
    third = Situation(down=3)
    assert third.matches(Situation(down=3, distance=12))
    assert not third.matches(Situation(down=2, distance=12))


def test_wildcard_situation_matches_by_label_only():
    openers = Situation(label="Openers")
    assert openers.matches(Situation(label="Openers"))
    assert not openers.matches(Situation(down=1, distance=10))


def test_distance_bucket_matching_is_fuzzy():
    third_medium = Situation(down=3, distance=5)
    assert third_medium.matches(Situation(down=3, distance=6))   # both MEDIUM
    assert not third_medium.matches(Situation(down=3, distance=9))


# ── Play ──────────────────────────────────────────────────────────────────────

def test_play_json_round_trip():
    play = passing.mesh_concept()
    assert Play.from_json(play.to_json()) == play


def test_mirror_negates_x_and_is_reversible():
    play = passing.mesh_concept()
    flipped = play.mirror()
    for a, b in zip(play.assignments, flipped.assignments):
        assert a.player.x == pytest.approx(-b.player.x)
    assert flipped.mirror().model_dump() == play.model_dump()


def test_with_route_is_immutable():
    from chalktalk.templates import routes as R
    play = passing.mesh_concept()
    changed = play.with_route("X", R.POST())
    assert play.assignment("X").route.route_type.value == "fly"
    assert changed.assignment("X").route.route_type.value == "post"


def test_with_formation_transfers_routes_by_label():
    from chalktalk.templates import formations as F
    play = passing.mesh_concept().with_formation(F.GUN_TREY_RIGHT())
    assert play.formation.name == F.GUN_TREY_RIGHT().name
    assert play.assignment("X").route is not None


def test_call_string_includes_formation_and_alts():
    from chalktalk import adjustments as A
    play = passing.mesh_concept().adjust(A.PROTECTION("Slide Rt"),
                                         A.MOTION("Z", "jet"))
    assert "Mesh" in play.call
    assert "Slide Rt" in play.call
    assert "Z Jet" in play.call
    assert play.call.count("Slide Rt") == 1     # protection is not double-printed


def test_ball_carrier_lookup():
    iz = running.inside_zone()
    assert iz.ball_carrier is not None
    assert iz.ball_carrier.is_ball_carrier


# ── Playbook ──────────────────────────────────────────────────────────────────

def test_playbook_add_filter_and_number():
    book = Playbook(name="Test").add(passing.mesh_concept(), running.inside_zone())
    assert len(book) == 2
    assert len(book.filter(play_type=PlayType.RUN)) == 1
    numbered = book.number()
    assert [p.call_number for p in numbered] == [1, 2]


def test_playbook_get_by_substring():
    book = Playbook(name="Test").add(passing.mesh_concept())
    assert book.get("mesh") is not None
    assert book.get("nonexistent") is None


def test_playbook_save_load(tmp_path):
    book = Playbook(name="Test", team="X").add(passing.mesh_concept())
    path = tmp_path / "book.json"
    book.save(str(path))
    assert Playbook.load(str(path)) == book
