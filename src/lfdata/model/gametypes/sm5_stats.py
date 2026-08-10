"""SQLAlchemy model for SM5 game statistics.

This module defines database ORM models for per-player Space Marines 5 end-of-game
performance statistics (shots hit/fired, zaps, missiles, nukes, medic/ammo boosts, etc.).

Usage example:
    from lfdata.model import Sm5Stats

    stats = Sm5Stats(game_id='game_1', entity_id='P1', shots_hit=50)
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base


class Sm5Stats(Base):
    """Database model for Space Marines 5 end-of-game player performance statistics.

    Holds detailed post-game metrics parsed from TDF record type 7 for a specific entity.
    """

    __tablename__ = 'sm5_stats'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    entity_id: Mapped[str] = mapped_column(String(50), index=True)

    # SM5 Specific Statistics Columns
    shots_hit: Mapped[int] = mapped_column(Integer, default=0)
    shots_fired: Mapped[int] = mapped_column(Integer, default=0)
    times_zapped: Mapped[int] = mapped_column(Integer, default=0)
    times_missiled: Mapped[int] = mapped_column(Integer, default=0)
    missile_hits: Mapped[int] = mapped_column(Integer, default=0)
    nukes_detonated: Mapped[int] = mapped_column(Integer, default=0)
    nukes_activated: Mapped[int] = mapped_column(Integer, default=0)
    nuke_cancels: Mapped[int] = mapped_column(Integer, default=0)
    medic_hits: Mapped[int] = mapped_column(Integer, default=0)
    own_medic_hits: Mapped[int] = mapped_column(Integer, default=0)
    medic_nukes: Mapped[int] = mapped_column(Integer, default=0)
    scout_rapid: Mapped[int] = mapped_column(Integer, default=0)
    life_boost: Mapped[int] = mapped_column(Integer, default=0)
    ammo_boost: Mapped[int] = mapped_column(Integer, default=0)
    lives_left: Mapped[int] = mapped_column(Integer, default=0)
    shots_left: Mapped[int] = mapped_column(Integer, default=0)
    penalties: Mapped[int] = mapped_column(Integer, default=0)
    shot3_hit: Mapped[int] = mapped_column(Integer, default=0)
    own_nuke_cancels: Mapped[int] = mapped_column(Integer, default=0)
    shot_opponent: Mapped[int] = mapped_column(Integer, default=0)
    shot_team: Mapped[int] = mapped_column(Integer, default=0)
    missiled_opponent: Mapped[int] = mapped_column(Integer, default=0)
    missiled_team: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    game: Mapped['LFGame'] = relationship('LFGame', back_populates='sm5_stats')

    def __repr__(self) -> str:
        """Returns a string representation of the SM5 stats.

        Returns:
            str: The string representation.
        """
        return (
            f"Sm5Stats(id={self.id}, game_id='{self.game_id}', "
            f"entity_id='{self.entity_id}')"
        )
