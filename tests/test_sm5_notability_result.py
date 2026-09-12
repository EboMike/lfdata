import dataclasses
import pytest

from lfdata.model.gametypes.sm5_notability_condition import (
    Sm5NotabilityCondition,
)
from lfdata.model.gametypes.sm5_notability_result import Sm5NotabilityResult


def test_sm5_notability_result_dataclass() -> None:
    result = Sm5NotabilityResult(
        condition=Sm5NotabilityCondition.DRAW,
        tagline='Tied game',
        details={'team0_score': 5000, 'team1_score': 5000},
    )
    assert result.condition == Sm5NotabilityCondition.DRAW
    assert result.tagline == 'Tied game'
    assert result.details['team0_score'] == 5000

    # Verify immutability (frozen dataclass)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.tagline = 'Changed'  # type: ignore[misc]


def test_sm5_notability_result_none_condition() -> None:
    result = Sm5NotabilityResult(
        condition=None,
        tagline='15K Commander game',
    )
    assert result.condition is None
    assert result.tagline == '15K Commander game'
    assert result.details == {}
