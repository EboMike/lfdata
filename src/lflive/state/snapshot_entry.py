"""Historical snapshot delta entry model for live game state tracking.

This module defines `SnapshotEntry`, which records a timestamped property
mutation on a player, team, or target entity.

Usage example:
    from lflive.state.snapshot_entry import SnapshotEntry

    entry = SnapshotEntry(
        time_ms=1000,
        entity_type='player',
        entity_id=1,
        field_name='score',
        value='100',
    )
"""

import dataclasses


@dataclasses.dataclass
class SnapshotEntry:
    """Represents a single timestamped property mutation for an entity.

    Attributes:
        time_ms: Elapsed game time in milliseconds when the change occurred.
        entity_type: Category of entity (player, team, target).
        entity_id: Primary key of the entity.
        field_name: Name of the property that was mutated.
        value: Serialized string value of the new property state.
    """

    time_ms: int
    entity_type: str
    entity_id: int
    field_name: str
    value: str

