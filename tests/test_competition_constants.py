import pytest

from lfdata.model.constants.competition import (
    DEFAULT_STAGE_INDICATOR,
    STAGE_CODE_GAME,
    STAGE_CODE_HALF,
    STAGE_CODE_OVERTIME,
    StageType,
)


def test_stage_type_values() -> None:
    assert DEFAULT_STAGE_INDICATOR == 'G'
    assert STAGE_CODE_GAME == 'G'
    assert STAGE_CODE_HALF == 'H'
    assert STAGE_CODE_OVERTIME == 'OT'

    assert StageType.GAME.code == 'G'
    assert StageType.GAME.display_name == 'Game'
    assert StageType.HALF.code == 'H'
    assert StageType.HALF.display_name == 'Half'
    assert StageType.OVERTIME.code == 'OT'
    assert StageType.OVERTIME.display_name == 'Overtime'


def test_stage_type_from_code() -> None:
    assert StageType.from_code(code='G') == StageType.GAME
    assert StageType.from_code(code='g') == StageType.GAME
    assert StageType.from_code(code='H') == StageType.HALF
    assert StageType.from_code(code='h') == StageType.HALF
    assert StageType.from_code(code='OT') == StageType.OVERTIME
    assert StageType.from_code(code='ot') == StageType.OVERTIME


def test_stage_type_from_code_invalid() -> None:
    with pytest.raises(ValueError, match='Invalid stage code: INVALID'):
        StageType.from_code(code='INVALID')

