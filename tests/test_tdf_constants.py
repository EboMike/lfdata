from lfdata.model.constants.tdf import (
    TDF_RECORD_ENTITY_END,
    TDF_RECORD_ENTITY_START,
    TDF_RECORD_EVENT,
    TDF_RECORD_INFO,
    TDF_RECORD_MISSION,
    TDF_RECORD_PLAYER_STATE,
    TDF_RECORD_SCORE,
    TDF_RECORD_STATS,
    TDF_RECORD_TEAM,
    LFPlayerState,
)


def test_tdf_record_constants():
    assert TDF_RECORD_INFO == '0'
    assert TDF_RECORD_MISSION == '1'
    assert TDF_RECORD_TEAM == '2'
    assert TDF_RECORD_ENTITY_START == '3'
    assert TDF_RECORD_EVENT == '4'
    assert TDF_RECORD_SCORE == '5'
    assert TDF_RECORD_ENTITY_END == '6'
    assert TDF_RECORD_STATS == '7'
    assert TDF_RECORD_PLAYER_STATE == '9'


def test_lf_player_state_enum():
    assert LFPlayerState.UP == 0
    assert LFPlayerState.RESETTABLE == 2
    assert LFPlayerState.DOWN == 3
