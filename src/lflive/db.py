"""SQLite database management for lflive game persistence.

This module provides the database manager class (`LiveDatabase`) that creates
SQL tables if they do not exist yet, initializes the schema, and manages
session clearing and persistence operations.

Usage example:
    from lflive.db import LiveDatabase

    db = LiveDatabase('lflive.db')
    db.init_db()
    db.reset_session()
"""

from pathlib import Path
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import Session

from lflive.models import (
    Base,
    LiveGameSession,
    LivePlayer,
    LiveSnapshot,
    LiveTarget,
    LiveTeam,
)


class LiveDatabase:
    """Manages SQLite database connections, schema setup, and session states.

    Attributes:
        db_path: Path to the SQLite database file or :memory:.
        engine: SQLAlchemy Engine instance connected to the SQLite database.
    """

    def __init__(self, db_path: str = 'lflive.db') -> None:
        """Initializes the database manager with a database path.

        Args:
            db_path: Relative file path to the SQLite file, or :memory:.
        """
        self.db_path = db_path
        if db_path != ':memory:':
            parent_dir = Path(db_path).parent
            if parent_dir and not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
            conn_url = f'sqlite:///{db_path}'
        else:
            conn_url = 'sqlite:///:memory:'

        self.engine = create_engine(conn_url)

    def init_db(self) -> None:
        """Creates all database tables if they do not exist yet.

        Usage example:
            db = LiveDatabase('test.db')
            db.init_db()
        """
        Base.metadata.create_all(self.engine)
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Migrates database schema for backward compatibility."""
        with self.engine.connect() as conn:
            try:
                result = conn.execute(
                    text("PRAGMA table_info('live_teams')")
                ).fetchall()
                col_names = {row[1] for row in result}
                if result and 'dummy_player_id' not in col_names:
                    conn.execute(
                        text(
                            'ALTER TABLE live_teams ADD COLUMN dummy_player_id'
                            ' INTEGER DEFAULT 0'
                        )
                    )
                    conn.commit()
            except Exception:
                pass

    def reset_session(self) -> None:
        """Deletes all previously persisted game state for a new session.

        Clears existing player, team, target, snapshot, and session records.

        Usage example:
            db = LiveDatabase('test.db')
            db.init_db()
            db.reset_session()
        """
        self.init_db()
        with Session(self.engine) as session:
            session.execute(delete(LiveSnapshot))
            session.execute(delete(LivePlayer))
            session.execute(delete(LiveTeam))
            session.execute(delete(LiveTarget))
            session.execute(delete(LiveGameSession))
            session.commit()

    def get_session(self) -> Session:
        """Returns a new SQLAlchemy Session instance.

        Returns:
            Session: Active SQLAlchemy Session bound to this engine.

        Usage example:
            with db.get_session() as s:
                ...
        """
        return Session(self.engine)
