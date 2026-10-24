"""SQLAlchemy model for player ammo history.

This module defines database ORM models for timestamped player ammo records
parsed from TDF record type 12.

Usage example:
    from lfdata.model import PlayerAmmoHistory

    history = PlayerAmmoHistory(
        game_id='g1', time=12000, entity_id='P1', shots=30
    )
"""

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base

if TYPE_CHECKING:
    from lfdata.model.objects.game import LFGame


class PlayerAmmoHistory(Base):
    """Database model for a timestamped player ammo record.

    Attributes:
        id: Primary key integer ID.
        game_id: Foreign key string referencing parent LFGame.
        time: Millisecond timestamp offset from start of game.
        entity_id: Entity ID string for the player.
        shots: New remaining shots count for the player.
        ammo: Property alias returning shots count.
        game: Parent LFGame ORM relationship.
    """

    __tablename__ = 'player_ammo_history'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    time: Mapped[int] = mapped_column(Integer)
    entity_id: Mapped[str] = mapped_column(String(50), index=True)
    shots: Mapped[int] = mapped_column(Integer)

    # Relationships
    game: Mapped['LFGame'] = relationship(
        'LFGame', back_populates='ammo_history'
    )

    @property
    def ammo(self) -> int:
        """Alias property for shots count.

        Returns:
            int: The remaining shots count.
        """
        return self.shots

    def __repr__(self) -> str:
        """Returns a string representation of the ammo history entry.

        Returns:
            str: The string representation.
        """
        return (
            f"PlayerAmmoHistory(id={self.id}, entity_id='{self.entity_id}', "
            f'shots={self.shots})'
        )
