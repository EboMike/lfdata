import dataclasses

import pytest

from lfdata.model.gametypes.laserball_notability_condition import (
    LaserballNotabilityCondition,
)
from lfdata.model.gametypes.laserball_notability_result import (
    LaserballNotabilityResult,
)


def test_laserball_notability_result_dataclass() -> None:
    result = LaserballNotabilityResult(
        condition=LaserballNotabilityCondition.GOALS,
        tagline='2 goals, 25 blocks',
        details={'goals': 2, 'blocks': 25},
    )
    assert result.condition == LaserballNotabilityCondition.GOALS
    assert result.tagline == '2 goals, 25 blocks'
    assert result.details['goals'] == 2
    assert result.details['blocks'] == 25

    # Verify immutability (frozen dataclass)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.tagline = 'Changed'  # type: ignore[misc]


def test_laserball_notability_result_none_condition() -> None:
    result = LaserballNotabilityResult(
        condition=None,
        tagline='Laserball game',
    )
    assert result.condition is None
    assert result.tagline == 'Laserball game'
    assert result.details == {}
