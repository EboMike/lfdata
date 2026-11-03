"""Target database model for lflive.

This module defines the persistent target entity (such as bases) for live game
sessions, mapping numerical IDs to entity codes, names, and team RGB colors.

Usage example:
    from lflive.models.target import LiveTarget

    target = LiveTarget(
        target_id=1,
        entity_id='#010001',
        name='Earth Base',
        rgb='#00ff00',
    )
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from lflive.models.base import Base


class LiveTarget(Base):
    """SQLAlchemy model representing a target or base in a live session.

    Attributes:
        id: Primary key identifier.
        target_id: Numerical primary key sent to consumers.
        entity_id: TDF entity ID string.
        name: Name of the target or base.
        rgb: Hex RGB color code for rendering.
    """

    __tablename__ = 'live_targets'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    target_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    entity_id: Mapped[str] = mapped_column(String(32), default='')
    name: Mapped[str] = mapped_column(String(64), default='')
    rgb: Mapped[str] = mapped_column(String(16), default='#ffffff')

