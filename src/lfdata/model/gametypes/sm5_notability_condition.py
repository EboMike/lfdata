"""Enumeration of notable game conditions for Space Marines 5 games.

This module defines the Sm5NotabilityCondition enum, listing notable game
outcomes (draws, close games, nuke feats, survival, eliminations, etc.)
in priority order.

Usage example:
    from lfdata.model.gametypes.sm5_notability_condition import (
        Sm5NotabilityCondition,
    )

    condition = Sm5NotabilityCondition.DRAW
    print(condition.priority, condition.description)
"""

import enum


class Sm5NotabilityCondition(enum.Enum):
    """Enumeration of notable game conditions in SM5, in priority order.

    Attributes:
        priority: Relative priority integer (1 is highest).
        description: Readable summary of the notable condition.
    """

    DRAW = (1, 'The game ended in a draw with identical scores.')
    CLOSE_GAME = (2, 'The teams ended within 200 points of each other.')
    COMMANDER_NUKES = (3, 'The focus player was a commander with > 5 nukes.')
    HIGH_HIT_DIFF = (4, 'The focus player had a hit diff of 1.9 or more.')
    HIGH_MEDIC_HITS = (5, 'The focus player had 9 or more medic hits.')
    LONE_SURVIVOR_CRITICAL = (
        6,
        'The focus player was the lone survivor with 1-2 lives.',
    )
    LONE_SURVIVOR = (
        7,
        'The focus player was the only person on the team to survive.',
    )
    FAST_TEAM_ELIMINATION = (8, 'A team was eliminated in less than 8 minutes.')
    ALMOST_ELIMINATED_OPPONENTS = (
        9,
        'The other team had only 1 to 5 combined lives left.',
    )
    MEDIC_ZAPPED_MEDIC = (
        10,
        'The focus player is a medic and zapped the other medic >= 3 times.',
    )
    NEVER_ZAPPED = (11, 'The focus player was never zapped.')
    LOW_TIMES_ZAPPED = (
        12,
        'The focus player was zapped less than 5 times the entire game.',
    )

    def __init__(self, priority: int, description: str) -> None:
        """Initializes the notability condition with metadata.

        Args:
            priority: Priority rank integer (1 is most notable).
            description: Description of the condition.
        """
        self.priority = priority
        self.description = description
