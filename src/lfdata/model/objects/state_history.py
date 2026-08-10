"""SQLAlchemy model for player state history.

This module defines database ORM models for timestamped player status transition events
parsed from TDF record type 9 (active, down, eliminated).

Usage example:
    from lfdata.model import PlayerStateHistory

    history = PlayerStateHistory(game_id='g1', time=12000, entity_id='P1', state=0)
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base


class PlayerStateHistory(Base):
    """Database model for a timestamped player state transition record.

    Attributes:
        id: Primary key integer ID.
        game_id: Foreign key string referencing parent LFGame.
        time: Millisecond timestamp offset from start of game.
        entity_id: Entity ID string for the player.
        state: Numeric player state transition value.
        game: Parent LFGame ORM relationship.
    """

    __tablename__ = 'player_state_history'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    time: Mapped[int] = mapped_column(Integer)
    entity_id: Mapped[str] = mapped_column(String(50), index=True)
    state: Mapped[int] = mapped_column(Integer)

    # Relationships
    game: Mapped['LFGame'] = relationship(
        'LFGame', back_populates='state_history'
    )

    def __repr__(self) -> str:
        """Returns a string representation of the state history entry.

        Returns:
            str: The string representation.
        """
        return (
            f"PlayerStateHistory(id={self.id}, entity_id='{self.entity_id}', "
            f'state={self.state})'
        )
