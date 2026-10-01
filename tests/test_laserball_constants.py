from lfdata.model.gametypes.laserball_constants import (
    LASERBALL_CLEAR_STEAL_SCORE_MULTIPLIER,
    LASERBALL_GOAL_SCORE_MULTIPLIER,
    LASERBALL_STAT_CAP,
)


def test_laserball_constants():
    assert LASERBALL_GOAL_SCORE_MULTIPLIER == 10000
    assert LASERBALL_CLEAR_STEAL_SCORE_MULTIPLIER == 100
    assert LASERBALL_STAT_CAP == 99
