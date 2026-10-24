from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, LFGame, PlayerMissilesHistory


def test_create_player_missiles_history() -> None:
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

        missiles_entry = PlayerMissilesHistory(
            game_id='test_game_123',
            time=12500,
            entity_id='#0101',
            missiles=4,
        )
        session.add(missiles_entry)
        session.commit()

        retrieved = (
            session.query(PlayerMissilesHistory)
            .filter_by(game_id='test_game_123', entity_id='#0101')
            .first()
        )
        assert retrieved is not None
        assert retrieved.time == 12500
        assert retrieved.entity_id == '#0101'
        assert retrieved.missiles == 4
        assert retrieved.game.game_id == 'test_game_123'
        assert repr(retrieved) == (
            "PlayerMissilesHistory(id=1, entity_id='#0101', missiles=4)"
        )
