"""Player database model for lflive.

This module defines the persistent player entity for live game sessions,
storing player metadata, current operational states, roles, and stats.

Usage example:
    from lflive.models.player import LivePlayer

    player = LivePlayer(
        player_id=1,
        entity_id='#1A2B3C',
        name='Shadow',
        team_id=1,
    )
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from lflive.models.base import Base


class LivePlayer(Base):
    """SQLAlchemy model representing a player in a live session.

    Attributes:
        id: Primary key identifier.
        player_id: Numerical primary key sent to consumers.
        entity_id: TDF entity ID string (e.g. #1A2b3c).
        name: Player codename.
        team_id: Numerical primary key of the player's team.
        role: Player role string (e.g. commander, heavy, scout).
        lives: Current number of lives remaining.
        shots: Current number of shots remaining.
        missiles: Current number of missiles remaining.
        special_points: Current number of special points accumulated.
        hitpoints: Current hitpoints remaining.
        score: Current personal score.
        goals: Number of goals scored in Laserball.
        assists: Number of assists in Laserball.
        blocks: Number of blocks executed in Laserball.
        clears: Number of clears executed in Laserball.
        steals: Number of steals executed in Laserball.
        state: Numerical player state (0=Up, 2=Resettable, 3=Down, 4=Dead).
        rapid_fire: Boolean flag indicating if rapid fire is enabled.
    """

    __tablename__ = 'live_players'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    player_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    entity_id: Mapped[str] = mapped_column(String(32), default='')
    name: Mapped[str] = mapped_column(String(64), default='')
    team_id: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String(32), default='')
    lives: Mapped[int] = mapped_column(Integer, default=0)
    shots: Mapped[int] = mapped_column(Integer, default=0)
    missiles: Mapped[int] = mapped_column(Integer, default=0)
    special_points: Mapped[int] = mapped_column(Integer, default=0)
    hitpoints: Mapped[int] = mapped_column(Integer, default=1)
    score: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    blocks: Mapped[int] = mapped_column(Integer, default=0)
    clears: Mapped[int] = mapped_column(Integer, default=0)
    steals: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[int] = mapped_column(Integer, default=0)
    rapid_fire: Mapped[bool] = mapped_column(Boolean, default=False)
