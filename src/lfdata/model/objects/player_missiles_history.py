"""SQLAlchemy model for player missiles history.

This module defines database ORM models for timestamped player missile records
parsed from TDF record type 13.

Usage example:
    from lfdata.model import PlayerMissilesHistory

    history = PlayerMissilesHistory(
        game_id='g1', time=12000, entity_id='P1', missiles=4
    )
"""

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base

if TYPE_CHECKING:
    from lfdata.model.objects.game import LFGame


class PlayerMissilesHistory(Base):
    """Database model for a timestamped player missiles record.

    Attributes:
        id: Primary key integer ID.
        game_id: Foreign key string referencing parent LFGame.
        time: Millisecond timestamp offset from start of game.
        entity_id: Entity ID string for the player.
        missiles: New remaining missiles count for the player.
        game: Parent LFGame ORM relationship.
    """

    __tablename__ = 'player_missiles_history'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    time: Mapped[int] = mapped_column(Integer)
    entity_id: Mapped[str] = mapped_column(String(50), index=True)
    missiles: Mapped[int] = mapped_column(Integer)

    # Relationships
    game: Mapped['LFGame'] = relationship(
        'LFGame', back_populates='missiles_history'
    )

    def __repr__(self) -> str:
        """Returns a string representation of the missiles history entry.

        Returns:
            str: The string representation.
        """
        return (
            f'PlayerMissilesHistory(id={self.id}, '
            f"entity_id='{self.entity_id}', "
            f'missiles={self.missiles})'
        )
