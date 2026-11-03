from sqlalchemy import select
from lflive.db import LiveDatabase
from lflive.models.game_session import LiveGameSession
from lflive.state.game_state import LiveGameState
from lflive.state.game_state_flusher import GameStateFlusher


def test_game_state_flusher(tmp_path: object) -> None:
    db_file = tmp_path / 'test_flusher.db'
    db = LiveDatabase(db_path=str(db_file))
    state = LiveGameState(game_type='SM5', duration_seconds=900)
    state.center_id = '4-19'
    state.center_name = 'Loveland'

    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    p = state.add_player(
        player_id=1,
        entity_id='#P1',
        name='Ace',
        team_id=1,
        role='scout',
    )
    p.score = 500
    state.add_target(
        target_id=1,
        entity_id='@66',
        name='Red Base',
        rgb='#ff0000',
    )
    state.record_change(
        time_ms=1000,
        entity_type='player',
        entity_id=1,
        field_name='score',
        value='500',
    )

    GameStateFlusher.flush(game_state=state, db=db)
    assert state._persisted_snapshot_count == 1

    # Second flush with no new snapshots
    GameStateFlusher.flush(game_state=state, db=db)
    assert state._persisted_snapshot_count == 1

    with db.get_session() as session:
        db_sess = session.scalars(select(LiveGameSession)).first()
        assert db_sess is not None
        assert db_sess.center_id == '4-19'
        assert db_sess.center_name == 'Loveland'
