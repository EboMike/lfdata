from lflive.constants import (
    DATA_TYPE_PLAYER_RANKING,
    DATA_TYPE_TEAM_RANKING,
)
from lflive.emitter import OutputEmitter
from lflive.ranking_manager import RankingManager
from lflive.state.game_state import LiveGameState


def test_ranking_manager_initial_emission() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(1, 'Red', 'Red', '#ff0000')
    state.add_team(2, 'Blue', 'Blue', '#0000ff')
    state.add_player(1, '#P1', 'Ace', 1)
    state.add_player(2, '#P2', 'Bravo', 2)

    emitter = OutputEmitter()
    ranking_mgr = RankingManager(game_state=state, emitter=emitter)

    # Initial call should emit 26 for each team with players and 27 for teams
    p_changed, t_changed = ranking_mgr.update_rankings(time_ms=0)
    assert p_changed is True
    assert t_changed is True
    assert len(emitter.emitted_lines) == 3
    assert emitter.emitted_lines[0] == f'{DATA_TYPE_PLAYER_RANKING}\t0\t1\t1'
    assert emitter.emitted_lines[1] == f'{DATA_TYPE_PLAYER_RANKING}\t0\t2\t2'
    assert emitter.emitted_lines[2] == f'{DATA_TYPE_TEAM_RANKING}\t0\t1,2'


def test_ranking_manager_no_duplicate_emission() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(1, 'Red', 'Red', '#ff0000')
    state.add_player(1, '#P1', 'Ace', 1)
    state.add_player(2, '#P2', 'Bravo', 1)

    emitter = OutputEmitter()
    ranking_mgr = RankingManager(game_state=state, emitter=emitter)

    ranking_mgr.update_rankings(time_ms=0)
    emitter.clear()

    # Second call without score change does not emit
    p_changed, t_changed = ranking_mgr.update_rankings(time_ms=1000)
    assert p_changed is False
    assert t_changed is False
    assert len(emitter.emitted_lines) == 0


def test_ranking_manager_order_change() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(1, 'Red', 'Red', '#ff0000')
    p1 = state.add_player(1, '#P1', 'Ace', 1)
    p2 = state.add_player(2, '#P2', 'Bravo', 1)

    p1.score = 100
    p2.score = 50

    emitter = OutputEmitter()
    ranking_mgr = RankingManager(game_state=state, emitter=emitter)

    ranking_mgr.update_rankings(time_ms=0)
    assert emitter.emitted_lines[0] == f'{DATA_TYPE_PLAYER_RANKING}\t0\t1\t1,2'
    emitter.clear()

    # Player 2 scores and overtakes player 1 within team 1
    p2.score = 500
    p_changed, t_changed = ranking_mgr.update_rankings(time_ms=5000)
    assert p_changed is True
    assert t_changed is False
    assert len(emitter.emitted_lines) == 1
    assert (
        emitter.emitted_lines[0] == f'{DATA_TYPE_PLAYER_RANKING}\t5000\t1\t2,1'
    )


def test_ranking_manager_reset() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(1, 'Red', 'Red', '#ff0000')
    state.add_player(1, '#P1', 'Ace', 1)

    ranking_mgr = RankingManager(game_state=state)
    ranking_mgr.update_rankings(time_ms=0)
    assert ranking_mgr.last_player_rankings == {1: [1]}
    assert ranking_mgr.last_team_ranking == [1]

    ranking_mgr.reset()
    assert len(ranking_mgr.last_player_rankings) == 0
    assert ranking_mgr.last_team_ranking is None
