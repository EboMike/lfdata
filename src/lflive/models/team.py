"""Team database model for lflive.

This module defines the persistent team entity for live game sessions,
storing team names, colors, RGB values, and cumulative scores.

Usage example:
    from lflive.models.team import LiveTeam

    team = LiveTeam(team_id=1, name='Fire Team', color='Red', rgb='#ff0000')
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from lflive.models.base import Base


class LiveTeam(Base):
    """SQLAlchemy model representing a team in a live session.

    Attributes:
        id: Primary key identifier.
        team_id: Numerical primary key sent to consumers.
        name: Display name of the team.
        color: Name of the team color.
        rgb: Hex RGB value of the team color (e.g. #ff0000).
        score: Total team score accumulated during the game.
    """

    __tablename__ = 'live_teams'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    team_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64), default='')
    color: Mapped[str] = mapped_column(String(32), default='')
    rgb: Mapped[str] = mapped_column(String(16), default='#ffffff')
    score: Mapped[int] = mapped_column(Integer, default=0)

