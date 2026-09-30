from lfdata.model.gametypes.laserball_events import (
    LaserballEvent,
    LaserballEventInfo,
)


def test_laserball_event_info() -> None:
    info = LaserballEventInfo(
        event_id='1101', name='GOAL', description='Scores'
    )
    assert info.event_id == '1101'
    assert info.name == 'GOAL'
    assert info.description == 'Scores'


def test_laserball_event_members() -> None:
    goal = LaserballEvent.GOAL
    assert goal.event_id == '1101'
    assert goal.display_name == 'GOAL'
    assert 'scores' in goal.description.lower()

    steal = LaserballEvent.STEAL
    assert steal.event_id == '1103'
    assert steal.display_name == 'STEAL'

    block = LaserballEvent.BLOCK
    assert block.event_id == '1104'
    assert block.display_name == 'BLOCK'


def test_laserball_event_from_id() -> None:
    assert LaserballEvent.from_id('1100') == LaserballEvent.PASS
    assert LaserballEvent.from_id('1101') == LaserballEvent.GOAL
    assert LaserballEvent.from_id('1102') == LaserballEvent.ASSIST
    assert LaserballEvent.from_id('1103') == LaserballEvent.STEAL
    assert LaserballEvent.from_id('1104') == LaserballEvent.BLOCK
    assert LaserballEvent.from_id('1105') == LaserballEvent.ROUND_START
    assert LaserballEvent.from_id('1106') == LaserballEvent.ROUND_END
    assert LaserballEvent.from_id('1107') == LaserballEvent.GETS_BALL
    assert LaserballEvent.from_id('1109') == LaserballEvent.CLEAR
    assert LaserballEvent.from_id('110A') == LaserballEvent.FAIL_CLEAR
    assert LaserballEvent.from_id('110a') == LaserballEvent.FAIL_CLEAR
    assert LaserballEvent.from_id('110B') == LaserballEvent.RESET_ON_BASE
    assert LaserballEvent.from_id('110b') == LaserballEvent.RESET_ON_BASE
    assert LaserballEvent.from_id('0100') is None
    assert LaserballEvent.from_id('unknown') is None


def test_laserball_event_is_laserball_event() -> None:
    assert LaserballEvent.is_laserball_event('1100') is True
    assert LaserballEvent.is_laserball_event('1101') is True
    assert LaserballEvent.is_laserball_event('110b') is True
    assert LaserballEvent.is_laserball_event('0205') is False
    assert LaserballEvent.is_laserball_event('9999') is False
