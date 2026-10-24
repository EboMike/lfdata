from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, LFGame, PlayerLivesHistory


def test_create_player_lives_history() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        game = LFGame(
            game_id='test_game_123',
            timestamp=datetime.now(),
            game_type='SM5',
        )
        session.add(game)
        session.commit()

        lives_entry = PlayerLivesHistory(
            game_id='test_game_123',
            time=12500,
            entity_id='#0101',
            lives=14,
        )
        session.add(lives_entry)
        session.commit()

        retrieved = (
            session.query(PlayerLivesHistory)
            .filter_by(game_id='test_game_123', entity_id='#0101')
            .first()
        )
        assert retrieved is not None
        assert retrieved.time == 12500
        assert retrieved.entity_id == '#0101'
        assert retrieved.lives == 14
        assert retrieved.game.game_id == 'test_game_123'
        assert repr(retrieved) == (
            "PlayerLivesHistory(id=1, entity_id='#0101', lives=14)"
        )
