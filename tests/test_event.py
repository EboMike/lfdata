from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, GameEvent, LFGame
from lfdata.model.gametypes.sm5_events import SM5_EVENT_RESUPPLY_LIVES


def test_create_event() -> None:
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

        event = GameEvent(
            game_id='test_game_123',
            time=224,
            event_type=SM5_EVENT_RESUPPLY_LIVES,
            actor_entity_id='#ciufC',
            target_entity_id='#7ghHvV',
            action='resupplies',
            raw_message='#ciufC\tresupplies\t#7ghHvV',
        )
        session.add(event)
        session.commit()

        retrieved = (
            session.query(GameEvent)
            .filter_by(game_id='test_game_123', time=224)
            .first()
        )
        assert retrieved is not None
        assert retrieved.event_type == SM5_EVENT_RESUPPLY_LIVES
        assert retrieved.actor_entity_id == '#ciufC'
        assert retrieved.target_entity_id == '#7ghHvV'
        assert retrieved.action == 'resupplies'
        assert retrieved.raw_message == '#ciufC\tresupplies\t#7ghHvV'
        assert retrieved.game.game_id == 'test_game_123'
        assert repr(retrieved) == (
            f"GameEvent(id=1, time=224, event_type='{SM5_EVENT_RESUPPLY_LIVES}',"
            " action='resupplies')"
        )
