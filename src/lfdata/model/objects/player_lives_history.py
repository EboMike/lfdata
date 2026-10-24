"""SQLAlchemy model for player lives history.

This module defines database ORM models for timestamped player lives records
parsed from TDF record type 11.

Usage example:
    from lfdata.model import PlayerLivesHistory

    history = PlayerLivesHistory(
        game_id='g1', time=12000, entity_id='P1', lives=15
    )
"""

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base

if TYPE_CHECKING:
    from lfdata.model.objects.game import LFGame


class PlayerLivesHistory(Base):
    """Database model for a timestamped player lives record.

    Attributes:
        id: Primary key integer ID.
        game_id: Foreign key string referencing parent LFGame.
        time: Millisecond timestamp offset from start of game.
        entity_id: Entity ID string for the player.
        lives: New remaining lives count for the player.
        game: Parent LFGame ORM relationship.
    """

    __tablename__ = 'player_lives_history'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    time: Mapped[int] = mapped_column(Integer)
    entity_id: Mapped[str] = mapped_column(String(50), index=True)
    lives: Mapped[int] = mapped_column(Integer)

    # Relationships
    game: Mapped['LFGame'] = relationship(
        'LFGame', back_populates='lives_history'
    )

    def __repr__(self) -> str:
        """Returns a string representation of the lives history entry.

        Returns:
            str: The string representation.
        """
        return (
            f"PlayerLivesHistory(id={self.id}, entity_id='{self.entity_id}', "
            f'lives={self.lives})'
        )
