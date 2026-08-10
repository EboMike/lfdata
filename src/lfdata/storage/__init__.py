"""Database storage and retrieval for LF game data.

This module provides SQL database persistence and retrieval (`DatabaseStorage`) for
parsed `LFGame` objects and associated player, team, event, and stat tables.

Usage example:
    from lfdata.storage import DatabaseStorage

    db = DatabaseStorage('sqlite:///games.db')
    db.save_game(game)
    retrieved_game = db.get_game('game_123')
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, selectinload

from lfdata.model import Base, GameEntity, LFGame, Player


class DatabaseStorage:
    """SQL database manager for persisting and loading LF game objects.

    Attributes:
        connection_string: The database connection URL string.
        engine: SQLAlchemy Engine instance.
    """

    def __init__(self, connection_string: str = 'sqlite:///lfdata.db'):
        """Initializes the database engine and creates all tables.

        Args:
            connection_string: The connection URL for the database.
        """
        self.connection_string = connection_string
        self.engine = create_engine(connection_string)
        Base.metadata.create_all(self.engine)

    def save_game(self, game: LFGame) -> bool:
        """Saves a LFGame and all related components to the database.

        Resolves global player codenames to avoid duplicates.

        Args:
            game: The game data object.

        Returns:
            bool: True if the save was successful, False otherwise.
        """
        try:
            with Session(self.engine) as session:
                for entity in game.entities:
                    if entity.player:
                        existing_player = (
                            session.query(Player)
                            .filter_by(codename=entity.player.codename)
                            .first()
                        )
                        if existing_player:
                            entity.player = existing_player
                            entity.player_id = existing_player.id
                session.add(game)
                session.commit()
            return True
        except Exception:
            return False

    def get_game(self, game_id: str) -> LFGame | None:
        """Retrieves a LFGame from the database with related data.

        Eagerly loads all relationships to allow safe usage after session close.

        Args:
            game_id: The ID of the game.

        Returns:
            LFGame | None: The game data object, or None if not found.
        """
        with Session(self.engine) as session:
            game = (
                session.query(LFGame)
                .options(
                    selectinload(LFGame.teams),
                    selectinload(LFGame.entities).selectinload(
                        GameEntity.player
                    ),
                    selectinload(LFGame.events),
                    selectinload(LFGame.sm5_stats),
                    selectinload(LFGame.score_history),
                    selectinload(LFGame.state_history),
                )
                .filter_by(game_id=game_id)
                .first()
            )
            return game
