"""SQLAlchemy model for LF games.

This module defines database ORM models for Laserforce game session metadata (game ID,
timestamp, game type, duration, centre, arena name) and parent ORM relationships.

Usage example:
    from datetime import datetime
    from lfdata.model import LFGame

    game = LFGame(game_id='g1', timestamp=datetime.now(), game_type='SM5')
"""

from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base


class LFGame(Base):
    """Database model for a Laserforce game session metadata container.

    Attributes:
        game_id: Primary key string identifying the game.
        timestamp: DateTime timestamp when game was parsed/recorded.
        game_type: Raw game type description string from TDF header.
        normalized_game_type: Optional normalized game type string (e.g. 'SM5').
        start: Optional start timestamp string from TDF header.
        file_version: Optional TDF file format version string.
        program_version: Optional Laserforce software version string.
        centre: Optional centre code string (e.g. '4-43').
        arena_name: Optional arena location name string.
        duration: Optional game duration in milliseconds.
        penalty: Optional penalty points value for team eliminations.
        teams: List of GameTeam ORM relationships.
        entities: List of GameEntity ORM relationships.
        events: List of GameEvent ORM relationships.
        sm5_stats: List of Sm5Stats ORM relationships.
        score_history: List of ScoreHistory ORM relationships.
        state_history: List of PlayerStateHistory ORM relationships.
    """

    __tablename__ = 'lf_games'

    game_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    game_type: Mapped[str] = mapped_column(String(50))
    normalized_game_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    start: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    program_version: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    centre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    arena_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    penalty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships using string references to avoid circular imports.
    teams: Mapped[list['GameTeam']] = relationship(
        'GameTeam', back_populates='game', cascade='all, delete-orphan'
    )
    entities: Mapped[list['GameEntity']] = relationship(
        'GameEntity', back_populates='game', cascade='all, delete-orphan'
    )
    events: Mapped[list['GameEvent']] = relationship(
        'GameEvent', back_populates='game', cascade='all, delete-orphan'
    )
    sm5_stats: Mapped[list['Sm5Stats']] = relationship(
        'Sm5Stats', back_populates='game', cascade='all, delete-orphan'
    )
    score_history: Mapped[list['ScoreHistory']] = relationship(
        'ScoreHistory', back_populates='game', cascade='all, delete-orphan'
    )
    state_history: Mapped[list['PlayerStateHistory']] = relationship(
        'PlayerStateHistory',
        back_populates='game',
        cascade='all, delete-orphan',
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initializes a new game session.

        Sets database column attributes from the provided keyword arguments
        and automatically derives the normalized game type if possible.

        Args:
            **kwargs: The column values for the game.
        """
        super().__init__(**kwargs)
        if getattr(self, 'normalized_game_type', None) is None:
            game_type_val = getattr(self, 'game_type', None)
            if game_type_val is not None:
                from lfdata.importer.normalizer import GameTypeNormalizer

                self.normalized_game_type = GameTypeNormalizer().normalize(
                    game_type_val
                )

    def __repr__(self) -> str:
        """Returns a string representation of the game.

        Returns:
            str: The string representation.
        """
        return f"LFGame(game_id='{self.game_id}', game_type='{self.game_type}')"
