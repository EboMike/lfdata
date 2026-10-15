"""Enumeration of notable game conditions for Laserball games.

This module defines the LaserballNotabilityCondition enum, listing notable
game conditions (goals, assists, steals, high hit diff, clears, etc.)
in priority order.

Usage example:
    from lfdata.model.gametypes.laserball_notability_condition import (
        LaserballNotabilityCondition,
    )

    condition = LaserballNotabilityCondition.GOALS
    print(condition.priority, condition.description)
"""

import enum


class LaserballNotabilityCondition(enum.Enum):
    """Enumeration of notable game conditions in Laserball, in priority order.

    Attributes:
        priority: Relative priority integer (1 is highest).
        description: Readable summary of the notable condition.
    """

    GOALS = (1, 'The focus player scored at least one goal.')
    ASSISTS = (2, 'The focus player had at least one assist.')
    STEALS = (3, 'The focus player had multiple steals.')
    HIGH_HIT_DIFF = (4, 'The focus player had a hit diff over 1.4.')
    CLEARS = (5, 'The focus player cleared more than once.')
    BLOCKS_SUMMARY = (
        6,
        'Fallback summary of player blocks and times blocked.',
    )

    def __init__(self, priority: int, description: str) -> None:
        """Initializes the notability condition with metadata.

        Args:
            priority: Priority rank integer (1 is most notable).
            description: Description of the condition.
        """
        self.priority = priority
        self.description = description
