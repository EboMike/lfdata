from lfdata.model.gametypes.laserball_events import (
    LASERBALL_EVENT_ASSIST,
    LASERBALL_EVENT_BLOCK,
    LASERBALL_EVENT_CLEAR,
    LASERBALL_EVENT_GETS_BALL,
    LASERBALL_EVENT_GOAL,
    LASERBALL_EVENT_PASS,
    LASERBALL_EVENT_ROUND_END,
    LASERBALL_EVENT_ROUND_START,
    LASERBALL_EVENT_STEAL,
)
from lflive.constants import (
    DATA_TYPE_BALL_CARRIER,
    DATA_TYPE_PLAYER_ASSISTS,
    DATA_TYPE_PLAYER_BLOCKS,
    DATA_TYPE_PLAYER_GOALS,
    DATA_TYPE_PLAYER_STATE,
    DATA_TYPE_PLAYER_STEALS,
    DATA_TYPE_ROUND_BEGINS,
    DATA_TYPE_ROUND_END,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.emitter import OutputEmitter
from lflive.laserball_event_handler import LaserballEventHandler
from lflive.state.game_state import LiveGameState


def test_laserball_event_handler() -> None:
    state = LiveGameState(game_type='Laserball')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Earth', color='Green', rgb='#00ff00')

    p1 = state.add_player(
        player_id=1,
        entity_id='#P1',
        name='Ace',
        team_id=1,
        role='',
    )
    p2 = state.add_player(
        player_id=2,
        entity_id='#P2',
        name='Boba',
        team_id=2,
        role='',
    )
    p3 = state.add_player(
        player_id=3,
        entity_id='#P3',
        name='Charlie',
        team_id=1,
        role='',
    )

    emitter = OutputEmitter()
    handler = LaserballEventHandler(game_state=state, emitter=emitter)

    assert handler._colored_player(p1) == '<font color="#ff0000">Ace</font>'
    assert handler._colored_player(None) == 'Unknown'

    # Round start & end
    handler.handle_event(5000, LASERBALL_EVENT_ROUND_START, [])
    assert state.is_in_round is True
    assert f'{DATA_TYPE_ROUND_BEGINS}\t5000' in emitter.emitted_lines

    handler.handle_event(60000, LASERBALL_EVENT_ROUND_END, [])
    assert state.is_in_round is False
    assert state.round_number == 2
    assert f'{DATA_TYPE_ROUND_END}\t60000' in emitter.emitted_lines

    # Possession
    handler.handle_event(65000, LASERBALL_EVENT_GETS_BALL, ['#P1'])
    assert state.ball_carrier_id == 1
    assert f'{DATA_TYPE_BALL_CARRIER}\t65000\t1' in emitter.emitted_lines

    handler.handle_event(
        70000, LASERBALL_EVENT_PASS, ['#P1', 'passes to', '#P3']
    )
    assert state.ball_carrier_id == 3
    assert f'{DATA_TYPE_BALL_CARRIER}\t70000\t3' in emitter.emitted_lines

    # Scoring
    handler.handle_event(75000, LASERBALL_EVENT_GOAL, ['#P3'])
    assert p3.goals == 1
    assert state.ball_carrier_id is None
    assert f'{DATA_TYPE_PLAYER_GOALS}\t75000\t3\t1' in emitter.emitted_lines
    assert f'{DATA_TYPE_BALL_CARRIER}\t75000\t0' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_SCORE}\t75000\t1\t1' in emitter.emitted_lines

    handler.handle_event(75001, LASERBALL_EVENT_ASSIST, ['#P1'])
    assert p1.assists == 1
    assert f'{DATA_TYPE_PLAYER_ASSISTS}\t75001\t1\t1' in emitter.emitted_lines

    # Contests: block, steal, clear
    handler.handle_event(80000, LASERBALL_EVENT_BLOCK, ['#P2', 'blocks', '#P1'])
    assert p2.blocks == 1
    assert p1.state == 3
    assert f'{DATA_TYPE_PLAYER_BLOCKS}\t80000\t2\t1' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_STATE}\t80000\t1\t3' in emitter.emitted_lines

    handler.handle_event(
        85000, LASERBALL_EVENT_STEAL, ['#P1', 'steals from', '#P2']
    )
    assert p1.steals == 1
    assert state.ball_carrier_id == 1
    assert p2.state == 3
    assert f'{DATA_TYPE_PLAYER_STEALS}\t85000\t1\t1' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_STATE}\t85000\t2\t3' in emitter.emitted_lines

    handler.handle_event(
        90000, LASERBALL_EVENT_CLEAR, ['#P1', 'clears to', '#P3']
    )
    assert p1.clears == 1
    assert state.ball_carrier_id == 3


def test_laserball_event_handler_with_ranking_manager() -> None:
    from lflive.constants import (
        DATA_TYPE_PLAYER_RANKING,
        DATA_TYPE_TEAM_RANKING,
    )
    from lflive.ranking_manager import RankingManager

    state = LiveGameState(game_type='Laserball')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Earth', color='Green', rgb='#00ff00')
    state.add_player(1, '#P1', 'Ace', 1)
    state.add_player(2, '#P2', 'Boba', 2)

    emitter = OutputEmitter()
    ranking_mgr = RankingManager(game_state=state, emitter=emitter)
    handler = LaserballEventHandler(
        game_state=state, emitter=emitter, ranking_manager=ranking_mgr
    )

    handler.handle_event(5000, LASERBALL_EVENT_ROUND_START, [])
    assert f'{DATA_TYPE_PLAYER_RANKING}\t5000\t1,2' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_RANKING}\t5000\t1,2' in emitter.emitted_lines

    emitter.clear()
    handler.handle_event(7000, LASERBALL_EVENT_GOAL, ['#P2'])
    # Player 2 scores goal -> leads player ranking and team ranking
    assert f'{DATA_TYPE_PLAYER_RANKING}\t7000\t2,1' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_RANKING}\t7000\t2,1' in emitter.emitted_lines
