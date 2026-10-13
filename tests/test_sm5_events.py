from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_CLAIM_BEACON,
    SM5_EVENT_DAMAGED_OPPONENT,
    SM5_EVENT_DAMAGED_TEAM,
    SM5_EVENT_DESTROY_BASE,
    SM5_EVENT_DOWNED_OPPONENT,
    SM5_EVENT_DOWNED_TEAM,
    SM5_EVENT_HIT_BASE,
    SM5_EVENT_LOCKING,
    SM5_EVENT_MISSILE_BASE_DAMAGE,
    SM5_EVENT_MISSILE_BASE_DESTROY,
    SM5_EVENT_MISSILE_BASE_MISS,
    SM5_EVENT_MISSILE_DOWN_OPPONENT,
    SM5_EVENT_MISSILE_DOWN_TEAM,
    SM5_EVENT_MISSILE_MISS,
    SM5_EVENT_MISSION_END,
    SM5_EVENT_MISSION_START,
    SM5_EVENT_NUKE_CANCEL,
    SM5_EVENT_PENALTY,
    SM5_EVENT_WARBOT_ZAP,
    SM5Event,
    SM5EventInfo,
)


def test_sm5_event_info() -> None:
    info = SM5EventInfo(
        event_id='0304',
        name='MISSILE_MISS',
        description='Player fires missile and misses.',
    )
    assert info.event_id == '0304'
    assert info.name == 'MISSILE_MISS'
    assert 'misses' in info.description


def test_sm5_event_members() -> None:
    missile_miss = SM5Event.MISSILE_MISS
    assert missile_miss.event_id == SM5_EVENT_MISSILE_MISS
    assert missile_miss.display_name == 'MISSILE_MISS'
    assert 'misses' in missile_miss.description.lower()

    downed_opp = SM5Event.DOWNED_OPPONENT
    assert downed_opp.event_id == SM5_EVENT_DOWNED_OPPONENT
    assert downed_opp.display_name == 'DOWNED_OPPONENT'

    nuke_cancel = SM5Event.NUKE_CANCEL
    assert nuke_cancel.event_id == SM5_EVENT_NUKE_CANCEL
    assert nuke_cancel.display_name == 'NUKE_CANCEL'


def test_sm5_event_from_id() -> None:
    assert SM5Event.from_id(SM5_EVENT_MISSION_START) == SM5Event.MISSION_START
    assert SM5Event.from_id(SM5_EVENT_MISSION_END) == SM5Event.MISSION_END
    assert SM5Event.from_id(SM5_EVENT_HIT_BASE) == SM5Event.HIT_BASE
    assert SM5Event.from_id(SM5_EVENT_DESTROY_BASE) == SM5Event.DESTROY_BASE
    assert (
        SM5Event.from_id(SM5_EVENT_DAMAGED_OPPONENT)
        == SM5Event.DAMAGED_OPPONENT
    )
    assert (
        SM5Event.from_id(SM5_EVENT_DOWNED_OPPONENT) == SM5Event.DOWNED_OPPONENT
    )
    assert SM5Event.from_id(SM5_EVENT_DAMAGED_TEAM) == SM5Event.DAMAGED_TEAM
    assert SM5Event.from_id(SM5_EVENT_DOWNED_TEAM) == SM5Event.DOWNED_TEAM
    assert SM5Event.from_id(SM5_EVENT_WARBOT_ZAP) == SM5Event.WARBOT_ZAP
    assert SM5Event.from_id(SM5_EVENT_LOCKING) == SM5Event.LOCKING
    assert (
        SM5Event.from_id(SM5_EVENT_MISSILE_BASE_MISS)
        == SM5Event.MISSILE_BASE_MISS
    )
    assert (
        SM5Event.from_id(SM5_EVENT_MISSILE_BASE_DAMAGE)
        == SM5Event.MISSILE_BASE_DAMAGE
    )
    assert (
        SM5Event.from_id(SM5_EVENT_MISSILE_BASE_DESTROY)
        == SM5Event.MISSILE_BASE_DESTROY
    )
    assert SM5Event.from_id(SM5_EVENT_MISSILE_MISS) == SM5Event.MISSILE_MISS
    assert (
        SM5Event.from_id(SM5_EVENT_MISSILE_DOWN_OPPONENT)
        == SM5Event.MISSILE_DOWN_OPPONENT
    )
    assert (
        SM5Event.from_id(SM5_EVENT_MISSILE_DOWN_TEAM)
        == SM5Event.MISSILE_DOWN_TEAM
    )
    assert SM5Event.from_id(SM5_EVENT_PENALTY) == SM5Event.PENALTY
    assert SM5Event.from_id(SM5_EVENT_CLAIM_BEACON) == SM5Event.CLAIM_BEACON
    assert SM5Event.from_id(SM5_EVENT_NUKE_CANCEL) == SM5Event.NUKE_CANCEL
    assert SM5Event.from_id('unknown_xyz') is None


def test_sm5_event_is_sm5_event() -> None:
    assert SM5Event.is_sm5_event(SM5_EVENT_MISSILE_MISS) is True
    assert SM5Event.is_sm5_event(SM5_EVENT_DOWNED_OPPONENT) is True
    assert SM5Event.is_sm5_event(SM5_EVENT_NUKE_CANCEL) is True
    assert SM5Event.is_sm5_event('1101') is False
    assert SM5Event.is_sm5_event('9999') is False
