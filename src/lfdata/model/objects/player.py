"""SQLAlchemy model for players.

This module defines database ORM models for individual human players across games,
storing player IDs, codenames, and optional real names.

Usage example:
    from lfdata.model import Player

    player = Player(codename='EboMike', real_name='Michael')
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from lfdata.model.base import Base


class Player(Base):
    """Database model for a persistent human player across games.

    Holds primary key ID, unique codename, and optional real name.
    """

    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(primary_key=True)
    codename: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    real_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        """Returns a string representation of the player.

        Returns:
            str: The string representation.
        """
        return f"Player(id={self.id}, codename='{self.codename}')"
