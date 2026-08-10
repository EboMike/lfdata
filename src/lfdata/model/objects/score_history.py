"""SQLAlchemy model for game score history.

This module defines database ORM models for timestamped entity score delta records
parsed from TDF record type 5.

Usage example:
    from lfdata.model import ScoreHistory

    history = ScoreHistory(game_id='g1', time=5000, entity_id='P1', old_score=0, delta_score=100, new_score=100)
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base


class ScoreHistory(Base):
    """Database model for a timestamped entity score change record.

    Holds time offset in milliseconds, entity ID, old score, delta score change, and new score.
    """

    __tablename__ = 'score_history'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    time: Mapped[int] = mapped_column(Integer)
    entity_id: Mapped[str] = mapped_column(String(50), index=True)
    old_score: Mapped[int] = mapped_column(Integer)
    delta_score: Mapped[int] = mapped_column(Integer)
    new_score: Mapped[int] = mapped_column(Integer)

    # Relationships
    game: Mapped['LFGame'] = relationship(
        'LFGame', back_populates='score_history'
    )

    def __repr__(self) -> str:
        """Returns a string representation of the score history entry.

        Returns:
            str: The string representation.
        """
        return (
            f"ScoreHistory(id={self.id}, entity_id='{self.entity_id}', "
            f'delta_score={self.delta_score}, new_score={self.new_score})'
        )
