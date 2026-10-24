from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, LFGame, PlayerAmmoHistory


def test_create_player_ammo_history() -> None:
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

        ammo_entry = PlayerAmmoHistory(
            game_id='test_game_123',
            time=12500,
            entity_id='#0101',
            shots=28,
        )
        session.add(ammo_entry)
        session.commit()

        retrieved = (
            session.query(PlayerAmmoHistory)
            .filter_by(game_id='test_game_123', entity_id='#0101')
            .first()
        )
        assert retrieved is not None
        assert retrieved.time == 12500
        assert retrieved.entity_id == '#0101'
        assert retrieved.shots == 28
        assert retrieved.ammo == 28
        assert retrieved.game.game_id == 'test_game_123'
        assert repr(retrieved) == (
            "PlayerAmmoHistory(id=1, entity_id='#0101', shots=28)"
        )
