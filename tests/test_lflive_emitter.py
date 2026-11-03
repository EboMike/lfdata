import pytest
from lflive.constants import (
    DATA_TYPE_BALL_CARRIER,
    DATA_TYPE_BASE_DESCRIPTION,
    DATA_TYPE_CENTER_INFO,
    DATA_TYPE_GAME_START_TIME,
    DATA_TYPE_GAME_TYPE,
    DATA_TYPE_NEW_GAME,
    DATA_TYPE_PLAYER_DESCRIPTION,
    DATA_TYPE_PLAYER_HITPOINTS,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_RANKING,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_PLAYER_STATE,
    DATA_TYPE_PRESYNC_END,
    DATA_TYPE_RAPID_FIRE_STATE,
    DATA_TYPE_TEAM_DESCRIPTION,
    DATA_TYPE_TEAM_RANKING,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.emitter import OutputEmitter, format_colored_name
from lflive.state.game_state import LiveGameState


def test_format_colored_name_with_rgb() -> None:
    res = format_colored_name(name='Shadow', rgb='#00ff00')
    assert res == '<font color="#00ff00">Shadow</font>'


def test_format_colored_name_without_rgb() -> None:
    res = format_colored_name(name='Viper', rgb=None)
    assert res == 'Viper'


def test_emitter_init() -> None:
    emitter = OutputEmitter(log_output=False)
    assert emitter.log_output is False
    assert len(emitter.listeners) == 0
    assert len(emitter.emitted_lines) == 0


def test_emitter_listeners() -> None:
    emitter = OutputEmitter()
    received: list[str] = []

    def callback(line: str) -> None:
        received.append(line)

    emitter.add_listener(callback)
    emitter.add_listener(callback)  # Duplicate ignored
    assert len(emitter.listeners) == 1

    emitter.emit(1, 100, 1, 50)
    assert len(received) == 1
    assert received[0] == '1\t100\t1\t50'

    emitter.remove_listener(callback)
    assert len(emitter.listeners) == 0
    emitter.emit(2, 200, '20261103')
    assert len(received) == 1


def test_emitter_emit_logging(capsys: pytest.CaptureFixture[str]) -> None:
    emitter = OutputEmitter(log_output=True)
    line = emitter.emit(3, 500, 10, 250)
    assert line == '3\t500\t10\t250'
    assert emitter.emitted_lines == ['3\t500\t10\t250']

    captured = capsys.readouterr()
    assert '3\t500\t10\t250\n' in captured.out

    emitter.clear()
    assert len(emitter.emitted_lines) == 0


def test_emitter_generate_presync_events() -> None:
    state = LiveGameState()
    state.game_type = 'SM5'
    state.duration_seconds = 900
    state.start_time = '20261103120000000'
    state.current_time_ms = 45000

    state.add_team(
        team_id=1,
        name='Red Team',
        color='Red',
        rgb='#ff0000',
    )
    state.add_target(
        target_id=1,
        entity_id='target_1',
        name='Red Base',
        rgb='#ff0000',
    )
    p = state.add_player(
        player_id=1,
        entity_id='p_1',
        name='Phoenix',
        team_id=1,
        role='scout',
    )
    p.lives = 12
    p.shots = 40
    p.missiles = 2
    p.special_points = 5
    p.hitpoints = 1
    p.state = 0
    p.score = 600
    p.rapid_fire = True
    state.teams[1].score = 600
    state.ball_carrier_id = 1
    state.center_id = '4-19'
    state.center_name = 'Loveland'

    emitter = OutputEmitter()
    events = emitter.generate_presync_events(game_state=state)

    assert any(ev.startswith(f'{DATA_TYPE_NEW_GAME}\t45000') for ev in events)
    assert any(
        ev.startswith(f'{DATA_TYPE_GAME_TYPE}\t45000\tSM5\t900')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_GAME_START_TIME}\t45000\t20261103120000000')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_CENTER_INFO}\t45000\t4-19\tLoveland')
        for ev in events
    )
    assert any(
        ev.startswith(
            f'{DATA_TYPE_TEAM_DESCRIPTION}\t45000\t1\tRed Team\t#ff0000'
        )
        for ev in events
    )
    assert any(
        ev.startswith(
            f'{DATA_TYPE_BASE_DESCRIPTION}\t45000\t1\tRed Base\t#ff0000'
        )
        for ev in events
    )
    assert any(
        ev.startswith(
            f'{DATA_TYPE_PLAYER_DESCRIPTION}\t45000\t1\tPhoenix\tp_1\t1\tscout'
        )
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_LIVES}\t45000\t1\t12')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_SHOTS}\t45000\t1\t40')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_MISSILES}\t45000\t1\t2')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_SPECIAL_POINTS}\t45000\t1\t5')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_HITPOINTS}\t45000\t1\t1')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_STATE}\t45000\t1\t0') for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_SCORE}\t45000\t1\t600')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_RAPID_FIRE_STATE}\t45000\t1\t1')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_TEAM_SCORE}\t45000\t1\t600') for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_RANKING}\t45000\t1\t1')
        for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_TEAM_RANKING}\t45000\t1') for ev in events
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_BALL_CARRIER}\t45000\t1') for ev in events
    )
    assert events[-1] == f'{DATA_TYPE_PRESYNC_END}\t45000'
