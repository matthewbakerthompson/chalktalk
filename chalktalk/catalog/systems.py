"""
Stock series sets — whole offenses, not single families.

A series answers one question. A system is the set of series you actually
install, in the order you install them, with the balance and the gaps that come
with the choice.

    from chalktalk.catalog import systems

    offense = systems.base_offense()
    print(offense.describe())          # weeks, series, and what is missing
    offense.to_practice(week=1)        # one period per series
    offense.to_call_sheet()            # every play, bucketed by situation
    offense.save_html("out/install.html")
"""
from __future__ import annotations

from ..series import SeriesSet, series_set
from . import series as SR


def base_offense() -> SeriesSet:
    """
    A four-week install that can play a season: two run families, the pass game
    that hangs off them, and the situational work at the end.
    """
    return (
        series_set(
            "Base Offense",
            "Zone and gap up front, the pass game off both, and the "
            "situations that decide games.",
        )
        .add(SR.inside_zone_series(), install_week=1, priority=0,
             note="The spine — everything else is built off this picture")
        .add(SR.mesh_series(), install_week=1, priority=1,
             note="Third down from day one")
        .add(SR.power_counter_series(), install_week=2, priority=0,
             note="The gap answer when they start flowing to zone")
        .add(SR.play_action_series(), install_week=2, priority=1,
             note="Punish the linebackers the run game has been moving")
        .add(SR.short_yardage_series(), install_week=2, priority=2,
             note="The down that decides drives")
        .add(SR.red_zone_series(), install_week=3, priority=0)
        .add(SR.screen_series(), install_week=3, priority=1,
             note="Pressure answers once the schedule gets harder")
        .add(SR.two_minute_series(), install_week=4, priority=0)
        .tag("offense", "full-install")
        .build()
    )


def spread_offense() -> SeriesSet:
    """
    One back, four out, and a quarterback who is a threat to keep it. Built to
    make numbers rather than to win a collision.
    """
    return (
        series_set(
            "Spread Offense",
            "Play fast, throw it to space, and let the run game come from the "
            "numbers instead of from movement.",
        )
        .add(SR.inside_zone_series(), install_week=1, priority=0,
             note="Zone read is the run game")
        .add(SR.mesh_series(), install_week=1, priority=1)
        .add(SR.screen_series(), install_week=2, priority=0,
             note="The extension of the run game")
        .add(SR.sprint_out_series(), install_week=2, priority=1)
        .add(SR.red_zone_series(), install_week=3, priority=0)
        .add(SR.two_minute_series(), install_week=3, priority=1)
        .tag("offense", "spread", "tempo")
        .build()
    )


def pro_style() -> SeriesSet:
    """
    Under center, two backs, play action off a run game that has to be real.
    Heavier install, but the play-action shots are worth more.
    """
    return (
        series_set(
            "Pro Style",
            "Establish the gap scheme, then take the top off with the same "
            "picture.",
        )
        .add(SR.power_counter_series(), install_week=1, priority=0,
             note="The identity — install it until it is boring")
        .add(SR.inside_zone_series(), install_week=1, priority=1)
        .add(SR.play_action_series(), install_week=2, priority=0,
             note="Only as good as the run game in front of it")
        .add(SR.mesh_series(), install_week=2, priority=1)
        .add(SR.short_yardage_series(), install_week=2, priority=2,
             note="Under center means you have to be able to get one yard")
        .add(SR.red_zone_series(), install_week=3, priority=0)
        .add(SR.two_minute_series(), install_week=4, priority=0)
        .tag("offense", "pro-style", "under-center")
        .build()
    )


def game_plan() -> SeriesSet:
    """
    A week, not a season: the three or four families you are actually going to
    call on Friday, installed flat rather than in a progression.
    """
    return (
        series_set(
            "Week Plan",
            "What we are calling this week, and nothing else.",
        )
        .add(SR.inside_zone_series(), install_week=1, priority=0)
        .add(SR.mesh_series(), install_week=1, priority=1)
        .add(SR.red_zone_series(), install_week=1, priority=2)
        .add(SR.two_minute_series(), install_week=1, priority=3)
        .tag("game-plan", "week")
        .build()
    )


ALL_SYSTEMS = {
    "base_offense": base_offense,
    "spread_offense": spread_offense,
    "pro_style": pro_style,
    "game_plan": game_plan,
}


def all_systems() -> list[SeriesSet]:
    """Build every stock system."""
    return [fn() for fn in ALL_SYSTEMS.values()]


__all__ = ["base_offense", "spread_offense", "pro_style", "game_plan",
           "ALL_SYSTEMS", "all_systems"]
