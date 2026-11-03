from lflive.constants import (
    DATA_TYPE_PLAYER_ASSISTS,
    DATA_TYPE_PLAYER_BLOCKS,
    DATA_TYPE_PLAYER_GOALS,
    DATA_TYPE_PLAYER_HITPOINTS,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_PLAYER_STEALS,
)
from lflive.dummy_player_manager import DummyPlayerManager
from lflive.emitter import OutputEmitter
from lflive.state.game_state import LiveGameState


def test_dummy_player_initialization() -> None:
    state = LiveGameState(game_type='SM5')
    team1 = state.add_team(
        team_id=1, name='Fire Team', color='Red', rgb='#ff0000'
    )
    assert team1.dummy_player_id == 101
    assert 1 in state.dummy_players
    dummy = state.dummy_players[1]
    assert dummy.player_id == 101
    assert dummy.team_id == 1
    assert dummy.name == 'Fire Team (Totals)'
    assert dummy.lives == 0
    assert dummy.score == 0


def test_dummy_player_stat_aggregation_via_emitter() -> None:
    state = LiveGameState(game_type='SM5')
    emitter = OutputEmitter()
    manager = DummyPlayerManager(game_state=state, emitter=emitter)
    emitter.add_listener(manager.on_line_emitted)

    team = state.add_team(
        team_id=1, name='Fire', color='Red', rgb='#ff0000', dummy_player_id=101
    )
    p1 = state.add_player(1, '#P1', 'Ace', 1, 'commander')
    p2 = state.add_player(2, '#P2', 'Bob', 1, 'heavy')

    # Initial lives
    p1.lives = 15
    emitter.emit(DATA_TYPE_PLAYER_LIVES, 0, p1.player_id, 15)
    assert state.dummy_players[1].lives == 15
    assert f'{DATA_TYPE_PLAYER_LIVES}\t0\t101\t15' in emitter.emitted_lines

    p2.lives = 10
    emitter.emit(DATA_TYPE_PLAYER_LIVES, 0, p2.player_id, 10)
    assert state.dummy_players[1].lives == 25
    assert f'{DATA_TYPE_PLAYER_LIVES}\t0\t101\t25' in emitter.emitted_lines

    # Score update
    p1.score = 100
    emitter.emit(DATA_TYPE_PLAYER_SCORE, 1000, p1.player_id, 100)
    assert state.dummy_players[1].score == 100
    assert f'{DATA_TYPE_PLAYER_SCORE}\t1000\t101\t100' in emitter.emitted_lines

    p2.score = 50
    emitter.emit(DATA_TYPE_PLAYER_SCORE, 2000, p2.player_id, 50)
    assert state.dummy_players[1].score == 150
    assert f'{DATA_TYPE_PLAYER_SCORE}\t2000\t101\t150' in emitter.emitted_lines

    # Shots and missiles
    p1.shots = 100
    emitter.emit(DATA_TYPE_PLAYER_SHOTS, 500, p1.player_id, 100)
    p2.shots = 50
    emitter.emit(DATA_TYPE_PLAYER_SHOTS, 600, p2.player_id, 50)
    assert state.dummy_players[1].shots == 150
    assert f'{DATA_TYPE_PLAYER_SHOTS}\t600\t101\t150' in emitter.emitted_lines

    p1.missiles = 5
    emitter.emit(DATA_TYPE_PLAYER_MISSILES, 700, p1.player_id, 5)
    p2.missiles = 3
    emitter.emit(DATA_TYPE_PLAYER_MISSILES, 800, p2.player_id, 3)
    assert state.dummy_players[1].missiles == 8
    assert f'{DATA_TYPE_PLAYER_MISSILES}\t800\t101\t8' in emitter.emitted_lines

    # Special points and hitpoints
    p1.special_points = 20
    emitter.emit(DATA_TYPE_PLAYER_SPECIAL_POINTS, 900, p1.player_id, 20)
    assert state.dummy_players[1].special_points == 20
    assert (
        f'{DATA_TYPE_PLAYER_SPECIAL_POINTS}\t900\t101\t20'
        in emitter.emitted_lines
    )

    p1.hitpoints = 2
    emitter.emit(DATA_TYPE_PLAYER_HITPOINTS, 950, p1.player_id, 2)
    assert state.dummy_players[1].hitpoints == 3
    assert f'{DATA_TYPE_PLAYER_HITPOINTS}\t950\t101\t3' in emitter.emitted_lines

    p2.hitpoints = 3
    emitter.emit(DATA_TYPE_PLAYER_HITPOINTS, 960, p2.player_id, 3)
    assert state.dummy_players[1].hitpoints == 5
    assert f'{DATA_TYPE_PLAYER_HITPOINTS}\t960\t101\t5' in emitter.emitted_lines

    assert manager.is_dummy_player(team.dummy_player_id) is True
    assert manager.is_dummy_player(999) is False


def test_dummy_player_laserball_stats() -> None:
    state = LiveGameState(game_type='Laserball')
    emitter = OutputEmitter()
    manager = DummyPlayerManager(game_state=state, emitter=emitter)
    emitter.add_listener(manager.on_line_emitted)

    state.add_team(
        team_id=1, name='Ice', color='Blue', rgb='#0000ff', dummy_player_id=101
    )
    p1 = state.add_player(1, '#P1', 'Striker', 1)

    p1.goals = 2
    emitter.emit(DATA_TYPE_PLAYER_GOALS, 3000, p1.player_id, 2)
    p1.assists = 1
    emitter.emit(DATA_TYPE_PLAYER_ASSISTS, 3100, p1.player_id, 1)
    p1.blocks = 4
    emitter.emit(DATA_TYPE_PLAYER_BLOCKS, 3200, p1.player_id, 4)
    p1.steals = 3
    emitter.emit(DATA_TYPE_PLAYER_STEALS, 3300, p1.player_id, 3)

    dummy = state.dummy_players[1]
    assert dummy.goals == 2
    assert dummy.assists == 1
    assert dummy.blocks == 4
    assert dummy.steals == 3
    assert f'{DATA_TYPE_PLAYER_GOALS}\t3000\t101\t2' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_ASSISTS}\t3100\t101\t1' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_BLOCKS}\t3200\t101\t4' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_STEALS}\t3300\t101\t3' in emitter.emitted_lines


def test_dummy_player_recalculate_all_and_reset() -> None:
    state = LiveGameState(game_type='SM5')
    emitter = OutputEmitter()
    manager = DummyPlayerManager(game_state=state, emitter=emitter)

    state.add_team(
        team_id=1, name='Fire', color='Red', rgb='#ff0000', dummy_player_id=101
    )
    p1 = state.add_player(1, '#P1', 'Ace', 1, 'commander')
    p1.score = 250
    p1.lives = 8

    manager.recalculate_all(time_ms=5000)
    assert state.dummy_players[1].score == 250
    assert state.dummy_players[1].lives == 8
    assert f'{DATA_TYPE_PLAYER_SCORE}\t5000\t101\t250' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_LIVES}\t5000\t101\t8' in emitter.emitted_lines

    manager.reset()
    state.reset()
    assert len(state.dummy_players) == 0


def test_dummy_player_state_reconstruction() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(
        team_id=1, name='Fire', color='Red', rgb='#ff0000', dummy_player_id=101
    )
    p1 = state.add_player(1, '#P1', 'Ace', 1)
    p1.lives = 15
    state.record_change(1000, 'player', 1, 'lives', '10')
    p1.lives = 10

    reconstructed = state.get_state_at(time_ms=2000)
    assert 1 in reconstructed.dummy_players
    assert reconstructed.dummy_players[1].player_id == 101
    assert reconstructed.dummy_players[1].lives == 10
