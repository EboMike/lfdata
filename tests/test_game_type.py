import pytest

from lfdata.model.constants.game_type import (
    GAME_TYPE_NAME_LASERBALL,
    GAME_TYPE_NAME_SM5,
    MISSION_TYPE_LASERBALL,
    MISSION_TYPE_LASERBALL_ALT,
    MISSION_TYPE_SM5,
    RAW_GAME_TYPE_LASERBALL,
    RAW_GAME_TYPE_SM5,
    LFGameType,
)


def test_game_type_constants():
    assert MISSION_TYPE_SM5 == 5
    assert MISSION_TYPE_LASERBALL == 3
    assert MISSION_TYPE_LASERBALL_ALT == 28
    assert GAME_TYPE_NAME_SM5 == 'SM5'
    assert GAME_TYPE_NAME_LASERBALL == 'Laserball'
    assert RAW_GAME_TYPE_SM5 == 'space_marines_5'
    assert RAW_GAME_TYPE_LASERBALL == 'laserball'


def test_game_type_enum_attributes():
    sm5 = LFGameType.SM5
    assert sm5.game_type_name == 'SM5'
    assert sm5.display_name == 'Space Marines 5'
    assert sm5.raw_name == 'space_marines_5'
    assert sm5.primary_mission_type == 5
    assert sm5.mission_types == (5,)

    lb = LFGameType.LASERBALL
    assert lb.game_type_name == 'Laserball'
    assert lb.display_name == 'Laserball'
    assert lb.raw_name == 'laserball'
    assert lb.primary_mission_type == 3
    assert lb.mission_types == (3, 28)


def test_game_type_from_mission_type():
    assert LFGameType.from_mission_type(5) == LFGameType.SM5
    assert LFGameType.from_mission_type(3) == LFGameType.LASERBALL
    assert LFGameType.from_mission_type(28) == LFGameType.LASERBALL

    with pytest.raises(ValueError, match='Invalid mission type'):
        LFGameType.from_mission_type(999)


def test_game_type_from_name():
    assert LFGameType.from_name('SM5') == LFGameType.SM5
    assert LFGameType.from_name('sm5') == LFGameType.SM5
    assert LFGameType.from_name('space_marines_5') == LFGameType.SM5
    assert LFGameType.from_name('Laserball') == LFGameType.LASERBALL
    assert LFGameType.from_name('laserball') == LFGameType.LASERBALL

    with pytest.raises(ValueError, match='Invalid game type name'):
        LFGameType.from_name('unknown_game')
