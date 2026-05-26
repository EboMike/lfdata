import pytest

from lfdata.model import LFRole


def test_lf_role_enum() -> None:
    commander = LFRole.COMMANDER
    assert commander.role_id == 1
    assert commander.display_name == "Commander"
    assert commander.start_lives == 15
    assert commander.start_shots == 30
    assert commander.start_missiles == 5
    assert commander.max_lives == 30
    assert commander.max_shots == 60
    assert commander.medic_lives_gain == 4
    assert commander.ammo_shots_gain == 5


def test_lf_role_from_id() -> None:
    assert LFRole.from_id(1) == LFRole.COMMANDER
    assert LFRole.from_id(4) == LFRole.AMMO
    assert LFRole.from_id(5) == LFRole.MEDIC

    with pytest.raises(ValueError):
        LFRole.from_id(99)
