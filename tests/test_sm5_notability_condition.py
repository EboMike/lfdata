from lfdata.model.gametypes.sm5_notability_condition import (
    Sm5NotabilityCondition,
)


def test_sm5_notability_conditions_count_and_priorities() -> None:
    conditions = list(Sm5NotabilityCondition)
    assert len(conditions) == 12

    priorities = [c.priority for c in conditions]
    assert priorities == list(range(1, 13))


def test_sm5_notability_condition_descriptions() -> None:
    draw = Sm5NotabilityCondition.DRAW
    assert draw.priority == 1
    assert 'draw' in draw.description.lower()

    high_med = Sm5NotabilityCondition.HIGH_MEDIC_HITS
    assert high_med.priority == 5
    assert '9' in high_med.description

    medic_vs_medic = Sm5NotabilityCondition.MEDIC_ZAPPED_MEDIC
    assert medic_vs_medic.priority == 10
    assert 'medic' in medic_vs_medic.description.lower()

    never_zapped = Sm5NotabilityCondition.NEVER_ZAPPED
    assert never_zapped.priority == 11

    low_zapped = Sm5NotabilityCondition.LOW_TIMES_ZAPPED
    assert low_zapped.priority == 12
