"""SQLAlchemy model for game events.

This module defines database ORM models for timestamped game events parsed from TDF
record type 4 (shots, misses, nukes, penalties, resupplies, eliminations).

Usage example:
    from lfdata.model import GameEvent

    event = GameEvent(game_id='game_1', time=1000, event_type='0100', action='zaps')
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base


class GameEvent(Base):
    """Database model for a timestamped LF game event log line.

    Attributes:
        id: Primary key integer ID.
        game_id: Foreign key string referencing the parent LFGame.
        time: Millisecond timestamp offset from the start of the game.
        event_type: TDF event code string (e.g. '0100', '0405').
        actor_entity_id: Optional entity ID string performing the action.
        target_entity_id: Optional entity ID string targeted by the action.
        action: Human-readable action description string.
        raw_message: Raw tab-separated event line text from TDF file.
        game: Parent LFGame ORM relationship.
    """

    __tablename__ = 'game_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    time: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(10))
    actor_entity_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    target_entity_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100))
    raw_message: Mapped[str] = mapped_column(String(255))

    # Relationships
    game: Mapped['LFGame'] = relationship('LFGame', back_populates='events')

    def __repr__(self) -> str:
        """Returns a string representation of the event.

        Returns:
            str: The string representation.
        """
        return (
            f'GameEvent(id={self.id}, time={self.time}, '
            f"event_type='{self.event_type}', action='{self.action}')"
        )
