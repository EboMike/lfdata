from lfdata.model.gametypes.laserball_events import LASERBALL_EVENT_GOAL
from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_ACTIVATE_RAPID_FIRE,
    SM5_EVENT_MISSION_END,
    SM5_EVENT_MISSION_START,
)
from lflive.constants import (
    DATA_TYPE_EVENT_SCROLLER,
    DATA_TYPE_GAME_OVER,
    DATA_TYPE_PLAYER_GOALS,
    DATA_TYPE_RAPID_FIRE_STATE,
)
from lflive.emitter import OutputEmitter
from lflive.game_event_handler import GameEventHandler
from lflive.state.game_state import LiveGameState


def test_game_event_handler_coordination() -> None:
    state = LiveGameState(game_type='Laserball')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    p1 = state.add_player(
        player_id=1, entity_id='#P1', name='Ace', team_id=1, role=''
    )

    emitter = OutputEmitter()
    handler = GameEventHandler(game_state=state, emitter=emitter)

    # Mission lifecycle
    handler.handle_event(1000, SM5_EVENT_MISSION_START, [])
    assert (
        f'{DATA_TYPE_EVENT_SCROLLER}\t1000\t* Mission Start *'
        in emitter.emitted_lines
    )

    # Laserball event delegation
    handler.handle_event(5000, LASERBALL_EVENT_GOAL, ['#P1'])
    assert p1.goals == 1
    assert f'{DATA_TYPE_PLAYER_GOALS}\t5000\t1\t1' in emitter.emitted_lines

    # SM5 event delegation
    handler.handle_event(8000, SM5_EVENT_ACTIVATE_RAPID_FIRE, ['#P1'])
    assert p1.rapid_fire is True
    assert f'{DATA_TYPE_RAPID_FIRE_STATE}\t8000\t1\t1' in emitter.emitted_lines

    # Mission end
    handler.handle_event(900000, SM5_EVENT_MISSION_END, [])
    assert state.is_game_over is True
    assert (
        f'{DATA_TYPE_EVENT_SCROLLER}\t900000\t* Mission End *'
        in emitter.emitted_lines
    )
    assert f'{DATA_TYPE_GAME_OVER}\t900000' in emitter.emitted_lines


def test_game_event_handler_with_ranking_manager() -> None:
    from lflive.constants import (
        DATA_TYPE_PLAYER_RANKING,
        DATA_TYPE_TEAM_RANKING,
    )
    from lflive.ranking_manager import RankingManager

    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    state.add_player(1, '#P1', 'Ace', 1)

    emitter = OutputEmitter()
    ranking_mgr = RankingManager(game_state=state, emitter=emitter)
    handler = GameEventHandler(
        game_state=state, emitter=emitter, ranking_manager=ranking_mgr
    )

    handler.handle_event(1000, SM5_EVENT_MISSION_START, [])
    assert f'{DATA_TYPE_PLAYER_RANKING}\t1000\t1' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_RANKING}\t1000\t1' in emitter.emitted_lines
