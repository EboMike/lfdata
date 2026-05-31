from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, LFGame


def test_create_game() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    now = datetime.now()
    with Session(engine) as session:
        game = LFGame(
            game_id='test_game_123',
            timestamp=now,
            game_type='SM5',
            start='20240114205710',
            file_version='2.005',
            program_version='8.503',
            centre='4-43',
            duration=900000,
            penalty=-1000,
        )
        session.add(game)
        session.commit()

        retrieved = (
            session.query(LFGame).filter_by(game_id='test_game_123').first()
        )
        assert retrieved is not None
        assert retrieved.game_id == 'test_game_123'
        assert retrieved.timestamp == now
        assert retrieved.game_type == 'SM5'
        assert retrieved.start == '20240114205710'
        assert retrieved.file_version == '2.005'
        assert retrieved.program_version == '8.503'
        assert retrieved.centre == '4-43'
        assert retrieved.duration == 900000
        assert retrieved.penalty == -1000
        assert repr(retrieved) == (
            "LFGame(game_id='test_game_123', game_type='SM5')"
        )
