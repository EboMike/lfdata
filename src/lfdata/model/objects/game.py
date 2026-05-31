"""SQLAlchemy model for LF games."""

from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base


class LFGame(Base):
    """Represents a LF game session.

    This class corresponds to the game data imported from TDF files,
    including metadata such as duration, centre, and versions.
    """

    __tablename__ = 'lf_games'

    game_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    game_type: Mapped[str] = mapped_column(String(50))
    start: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    program_version: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    centre: Mapped[str | None] = mapped_column(String(100), nullable=True)
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

    def __repr__(self) -> str:
        """Returns a string representation of the game.

        Returns:
            str: The string representation.
        """
        return f"LFGame(game_id='{self.game_id}', game_type='{self.game_type}')"
