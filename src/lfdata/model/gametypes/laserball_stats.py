"""SQLAlchemy model for Laserball game statistics.

This module defines database ORM models for per-player Laserball end-of-game
performance statistics (goals, assists, clears, steals, blocks, penalties,
etc.).

Usage example:
    from lfdata.model import LaserballStats

    stats = LaserballStats(game_id='g1', entity_id='P1', goals=2, assists=1)
    print(f'Player ranking score: {stats.score}')
"""

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base
from lfdata.model.gametypes.laserball_constants import (
    LASERBALL_CLEAR_STEAL_SCORE_MULTIPLIER,
    LASERBALL_GOAL_SCORE_MULTIPLIER,
    LASERBALL_STAT_CAP,
)

if TYPE_CHECKING:
    from lfdata.model.objects.game import LFGame


class LaserballStats(Base):
    """Database model for Laserball end-of-game player performance statistics.

    Attributes:
        id: Primary key integer ID.
        game_id: Foreign key string referencing the parent LFGame.
        entity_id: Entity ID string for the player.
        goals: Total goals scored count.
        assists: Total assists count.
        passes: Total passes completed count.
        steals: Total ball steals from opponents count.
        clears: Total ball clears count.
        blocks: Total blocks (zaps against enemy players) count.
        times_blocked: Times player was blocked/zapped.
        times_zapped: Alias/mirror for times_blocked.
        penalties: Penalties count.
        game: Parent LFGame ORM relationship.
        score: Computed player ranking score.
        hit_diff: Ratio of opponent hits (blocks + steals) to times zapped.
    """

    __tablename__ = 'laserball_stats'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='CASCADE'), index=True
    )
    entity_id: Mapped[str] = mapped_column(String(50), index=True)

    # Laserball Specific Statistics Columns
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    passes: Mapped[int] = mapped_column(Integer, default=0)
    steals: Mapped[int] = mapped_column(Integer, default=0)
    clears: Mapped[int] = mapped_column(Integer, default=0)
    blocks: Mapped[int] = mapped_column(Integer, default=0)
    times_blocked: Mapped[int] = mapped_column(Integer, default=0)
    times_zapped: Mapped[int] = mapped_column(Integer, default=0)
    penalties: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    game: Mapped['LFGame'] = relationship(
        'LFGame', back_populates='laserball_stats'
    )

    @property
    def score(self) -> int:
        """Returns the calculated ranking score for the player.

        Goals and assists grant 10,000 points each. Clears and steals grant
        100 points each (combined count capped at 99, giving at most 9,900
        points). Blocks grant 1 point each (capped at 99 points).

        Returns:
            int: The computed player ranking score.

        Usage:
            ranking_score = stats.score
        """
        goals_val = self.goals or 0
        assists_val = self.assists or 0
        clears_val = self.clears or 0
        steals_val = self.steals or 0
        blocks_val = self.blocks or 0
        return (
            (goals_val + assists_val) * LASERBALL_GOAL_SCORE_MULTIPLIER
            + min(LASERBALL_STAT_CAP, clears_val + steals_val)
            * LASERBALL_CLEAR_STEAL_SCORE_MULTIPLIER
            + min(LASERBALL_STAT_CAP, blocks_val)
        )

    @property
    def hit_diff(self) -> float:
        """Returns the player's hit differential (hit diff).

        The hit diff is the number of times the player zapped players on
        other teams (blocks and steals) divided by the number of times the
        player was zapped. If the player was never zapped, the hit diff is 1.0.

        Returns:
            float: The hit diff ratio, or 1.0 if never zapped.

        Usage:
            ratio = stats.hit_diff
        """
        zapped = self.times_zapped or self.times_blocked or 0
        if zapped == 0:
            return 1.0
        hits = (self.blocks or 0) + (self.steals or 0)
        return hits / zapped

    def __repr__(self) -> str:
        """Returns a string representation of the Laserball stats.

        Returns:
            str: The string representation.
        """
        return (
            f"LaserballStats(id={self.id}, game_id='{self.game_id}', "
            f"entity_id='{self.entity_id}', goals={self.goals}, "
            f'assists={self.assists}, score={self.score})'
        )
