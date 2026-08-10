"""SQLAlchemy model for game entities.

This module defines database ORM models for Laserforce game participants and arena objects
(including human players, referees, targets, and generator bases).

Usage example:
    from lfdata.model import GameEntity

    entity = GameEntity(game_id='game_1', entity_id='P1', type='player', desc='Alpha')
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base


class GameEntity(Base):
    """Database model for a Laserforce game entity participant or target object.

    Holds entity registration details, description, team assignment, category,
    battlesuit ID, and final score.
    """

    __tablename__ = 'game_entities'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    entity_id: Mapped[str] = mapped_column(String(50), index=True)
    type: Mapped[str] = mapped_column(String(50))
    desc: Mapped[str] = mapped_column(String(100))
    team_index: Mapped[int] = mapped_column(Integer)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[int | None] = mapped_column(Integer, nullable=True)
    battlesuit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    end_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey('players.id', ondelete='SET NULL'), nullable=True
    )

    # Relationships
    game: Mapped['LFGame'] = relationship('LFGame', back_populates='entities')
    player: Mapped['Player | None'] = relationship('Player')

    def __repr__(self) -> str:
        """Returns a string representation of the entity.

        Returns:
            str: The string representation.
        """
        return (
            f"GameEntity(id={self.id}, entity_id='{self.entity_id}', "
            f"type='{self.type}', desc='{self.desc}')"
        )
