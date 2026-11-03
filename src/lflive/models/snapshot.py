"""State snapshot database model for lflive.

This module defines timestamped point-in-time state changes stored for
late-joining consumers and historical playback.

Usage example:
    from lflive.models.snapshot import LiveSnapshot

    snapshot = LiveSnapshot(
        time_ms=5000,
        entity_type='player',
        entity_id=1,
        field_name='score',
        value='100',
    )
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from lflive.models.base import Base


class LiveSnapshot(Base):
    """SQLAlchemy model representing a timestamped state change point.

    Attributes:
        id: Primary key identifier.
        time_ms: Elapsed game time in milliseconds when the change occurred.
        entity_type: Category of entity (e.g. player, team, target).
        entity_id: Primary key of the entity whose field was updated.
        field_name: Name of the property updated.
        value: String representation of the updated value.
    """

    __tablename__ = 'live_snapshots'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    time_ms: Mapped[int] = mapped_column(Integer, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    field_name: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(String(256))

