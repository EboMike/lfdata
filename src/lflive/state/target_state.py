"""In-memory state container for a target or base in lflive.

This module defines `LiveTargetState`, representing targets and arena bases
with numerical primary keys, entity codes, and RGB colors.

Usage example:
    from lflive.state.target_state import LiveTargetState

    base = LiveTargetState(
        target_id=1,
        entity_id='#010001',
        name='Fire Base',
        rgb='#ff0000',
    )
"""

import dataclasses


@dataclasses.dataclass
class LiveTargetState:
    """In-memory real-time state of a target or arena base.

    Attributes:
        target_id: Numerical primary key sent to consumers.
        entity_id: TDF entity ID string.
        name: Printable target name.
        rgb: Hex RGB color code for rendering.
    """

    target_id: int
    entity_id: str
    name: str
    rgb: str
