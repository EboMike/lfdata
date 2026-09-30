from lfdata.model.gametypes.laserball_stats import LaserballStats


def test_laserball_stats_init() -> None:
    stats = LaserballStats(
        game_id='game_1',
        entity_id='P1',
        goals=2,
        assists=1,
        passes=5,
        steals=3,
        clears=2,
        blocks=10,
        times_blocked=4,
        times_zapped=4,
        penalties=1,
    )
    assert stats.game_id == 'game_1'
    assert stats.entity_id == 'P1'
    assert stats.goals == 2
    assert stats.assists == 1
    assert stats.passes == 5
    assert stats.steals == 3
    assert stats.clears == 2
    assert stats.blocks == 10
    assert stats.times_blocked == 4
    assert stats.times_zapped == 4
    assert stats.penalties == 1


def test_laserball_stats_score_calculation() -> None:
    # 2 goals (20000) + 1 assist (10000) + 3 steals + 2 clears (5 * 100 = 500)
    # + 10 blocks (10)
    stats = LaserballStats(
        game_id='g1',
        entity_id='P1',
        goals=2,
        assists=1,
        steals=3,
        clears=2,
        blocks=10,
    )
    assert stats.score == 30510


def test_laserball_stats_score_capping() -> None:
    # Combined clears and steals = 100, capped at 99 -> 9900
    # Blocks = 120, capped at 99 -> 99
    stats = LaserballStats(
        game_id='g1',
        entity_id='P1',
        goals=1,
        assists=0,
        steals=60,
        clears=40,
        blocks=120,
    )
    # 10000 + 9900 + 99 = 19999
    assert stats.score == 19999


def test_laserball_stats_hit_diff() -> None:
    stats = LaserballStats(
        game_id='g1',
        entity_id='P1',
        blocks=8,
        steals=2,
        times_zapped=5,
    )
    # (8 + 2) / 5 = 2.0
    assert stats.hit_diff == 2.0


def test_laserball_stats_hit_diff_never_zapped() -> None:
    stats = LaserballStats(
        game_id='g1',
        entity_id='P1',
        blocks=5,
        steals=1,
        times_zapped=0,
        times_blocked=0,
    )
    assert stats.hit_diff == 1.0


def test_laserball_stats_hit_diff_uses_times_blocked() -> None:
    stats = LaserballStats(
        game_id='g1',
        entity_id='P1',
        blocks=6,
        steals=0,
        times_blocked=3,
        times_zapped=0,
    )
    assert stats.hit_diff == 2.0


def test_laserball_stats_repr() -> None:
    stats = LaserballStats(
        game_id='g1',
        entity_id='P1',
        goals=1,
        assists=2,
    )
    r = repr(stats)
    assert 'LaserballStats' in r
    assert "game_id='g1'" in r
    assert "entity_id='P1'" in r
