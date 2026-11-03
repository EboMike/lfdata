"""Game session database model for lflive.

This module defines the persistent game session entity representing an active
or historical live game parsing session.

Usage example:
    from lflive.models.game_session import LiveGameSession

    session = LiveGameSession(game_type='SM5', start_time='20261102235000')
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from lflive.models.base import Base


class LiveGameSession(Base):
    """SQLAlchemy model representing a live game session.

    Attributes:
        id: Primary key identifier.
        game_type: Type of game being played (e.g. SM5, Laserball).
        start_time: Start timestamp of the game in center local time.
        duration_seconds: Maximum length of the game in seconds.
        is_active: Flag indicating whether the session is currently ongoing.
    """

    __tablename__ = 'live_game_sessions'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    game_type: Mapped[str] = mapped_column(String(32), default='SM5')
    start_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=900)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

