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

    Attributes:
        id: Primary key integer ID.
        game_id: Foreign key string referencing the parent LFGame.
        entity_id: Entity ID string for the player.
        shots_hit: Total shots hit count.
        shots_fired: Total shots fired count.
        times_zapped: Times player was zapped.
        times_missiled: Times player was missiled.
        missile_hits: Missile hits count.
        nukes_detonated: Nukes detonated count.
        nukes_activated: Nukes activated count.
        nuke_cancels: Nuke cancels count.
        medic_hits: Medic hits count.
        own_medic_hits: Own medic hits count.
        medic_nukes: Medic nukes count.
        scout_rapid: Scout rapid fire count.
        life_boost: Life boosts count.
        ammo_boost: Ammo boosts count.
        lives_left: Remaining lives at end of game.
        shots_left: Remaining shots at end of game.
        penalties: Penalties count.
        shot3_hit: 3-shot hits count.
        own_nuke_cancels: Own nuke cancels count.
        shot_opponent: Shots hit against opponents count.
        shot_team: Friendly fire shots hit count.
        missiled_opponent: Missiles hit against opponents count.
        missiled_team: Friendly fire missiles hit count.
        game: Parent LFGame ORM relationship.
        hit_diff: Property returning ratio of opponent zaps to times zapped.
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

    @property
    def hit_diff(self) -> float:
        """Returns the player's hit differential (hit diff).

        The hit diff is the number of times the player zapped players on
        other teams divided by the number of times the player got zapped.
        Missiles, nukes, friendly fire, and base hits do not factor into this
        equation. If the player was never zapped, the hit diff is 1.0.

        Returns:
            float: The hit diff ratio, or 1.0 if the player was never zapped.
        """
        if self.times_zapped == 0:
            return 1.0
        return self.shot_opponent / self.times_zapped

    def __repr__(self) -> str:
        """Returns a string representation of the SM5 stats.

        Returns:
            str: The string representation.
        """
        return (
            f"Sm5Stats(id={self.id}, game_id='{self.game_id}', "
            f"entity_id='{self.entity_id}')"
        )
