from lfdata.model.gametypes.laserball_notability_condition import (
    LaserballNotabilityCondition,
)


def test_laserball_notability_conditions_count_and_priorities() -> None:
    conditions = list(LaserballNotabilityCondition)
    assert len(conditions) == 6

    priorities = [c.priority for c in conditions]
    assert priorities == list(range(1, 7))


def test_laserball_notability_condition_descriptions() -> None:
    goals = LaserballNotabilityCondition.GOALS
    assert goals.priority == 1
    assert 'goal' in goals.description.lower()

    assists = LaserballNotabilityCondition.ASSISTS
    assert assists.priority == 2
    assert 'assist' in assists.description.lower()

    steals = LaserballNotabilityCondition.STEALS
    assert steals.priority == 3
    assert 'steal' in steals.description.lower()

    high_hit_diff = LaserballNotabilityCondition.HIGH_HIT_DIFF
    assert high_hit_diff.priority == 4
    assert '1.4' in high_hit_diff.description

    clears = LaserballNotabilityCondition.CLEARS
    assert clears.priority == 5
    assert 'clear' in clears.description.lower()

    blocks = LaserballNotabilityCondition.BLOCKS_SUMMARY
    assert blocks.priority == 6
    assert 'block' in blocks.description.lower()
