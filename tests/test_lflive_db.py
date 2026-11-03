from pathlib import Path
from sqlalchemy import select
from lflive.db import LiveDatabase
from lflive.models import (
    LiveGameSession,
    LivePlayer,
    LiveSnapshot,
    LiveTarget,
    LiveTeam,
)


def test_db_init_memory() -> None:
    db = LiveDatabase(':memory:')
    db.init_db()
    with db.get_session() as session:
        session.add(
            LiveTeam(
                team_id=1,
                name='Fire Team',
                color='Red',
                rgb='#ff0000',
                score=100,
            )
        )
        session.commit()
        teams = session.scalars(select(LiveTeam)).all()
        assert len(teams) == 1
        assert teams[0].name == 'Fire Team'


def test_db_reset_session() -> None:
    db = LiveDatabase(':memory:')
    db.init_db()
    with db.get_session() as session:
        session.add(
            LiveTeam(
                team_id=1, name='Fire', color='Red', rgb='#ff0000', score=100
            )
        )
        session.add(LivePlayer(player_id=1, name='Ace', team_id=1))
        session.add(LiveTarget(target_id=1, name='Base', rgb='#ff0000'))
        session.add(
            LiveSnapshot(
                time_ms=100,
                entity_type='player',
                entity_id=1,
                field_name='score',
                value='10',
            )
        )
        session.add(LiveGameSession(game_type='SM5'))
        session.commit()

    db.reset_session()

    with db.get_session() as session:
        assert len(session.scalars(select(LiveTeam)).all()) == 0
        assert len(session.scalars(select(LivePlayer)).all()) == 0
        assert len(session.scalars(select(LiveTarget)).all()) == 0
        assert len(session.scalars(select(LiveSnapshot)).all()) == 0
        assert len(session.scalars(select(LiveGameSession)).all()) == 0


def test_db_creates_parent_dir(tmp_path: Path) -> None:
    nested_path = tmp_path / 'subdir' / 'live.db'
    db = LiveDatabase(str(nested_path))
    db.init_db()
    assert nested_path.exists()
