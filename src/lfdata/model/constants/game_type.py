"""Enums and constants representing LF game types and mission types.

This module defines Laserforce game types (such as Space Marines 5 and
Laserball), their canonical names, raw string identifiers, and numeric
mission types parsed from TDF header records.

Usage example:
    from lfdata.model.constants.game_type import LFGameType

    game_type = LFGameType.from_mission_type(5)
    print(f'Game type: {game_type.display_name}')
"""

import dataclasses
import enum

# Mission type integer constants
MISSION_TYPE_SM5: int = 5
MISSION_TYPE_LASERBALL: int = 3
MISSION_TYPE_LASERBALL_ALT: int = 28

# Standardized game type string identifiers
GAME_TYPE_NAME_SM5: str = 'SM5'
GAME_TYPE_NAME_LASERBALL: str = 'Laserball'

# Raw game type string identifiers
RAW_GAME_TYPE_SM5: str = 'space_marines_5'
RAW_GAME_TYPE_LASERBALL: str = 'laserball'


@dataclasses.dataclass(frozen=True)
class LFGameTypeStats:
    """Metadata and statistics for a Laserforce game type.

    Attributes:
        name: Standardized canonical short name (e.g. 'SM5', 'Laserball').
        display_name: Human-readable display name.
        raw_name: Raw lowercase identifier used in internal logic.
        primary_mission_type: Primary integer mission type code.
        mission_types: Tuple of valid integer mission type codes for this game.
    """

    name: str
    display_name: str
    raw_name: str
    primary_mission_type: int
    mission_types: tuple[int, ...]


class LFGameType(enum.Enum):
    """Enumeration of Laserforce game types.

    Attributes:
        name: Standardized canonical short name.
        display_name: Human-readable display name.
        raw_name: Raw lowercase identifier.
        primary_mission_type: Primary integer mission type code.
        mission_types: Tuple of valid integer mission type codes.
    """

    SM5 = LFGameTypeStats(
        name=GAME_TYPE_NAME_SM5,
        display_name='Space Marines 5',
        raw_name=RAW_GAME_TYPE_SM5,
        primary_mission_type=MISSION_TYPE_SM5,
        mission_types=(MISSION_TYPE_SM5,),
    )
    LASERBALL = LFGameTypeStats(
        name=GAME_TYPE_NAME_LASERBALL,
        display_name='Laserball',
        raw_name=RAW_GAME_TYPE_LASERBALL,
        primary_mission_type=MISSION_TYPE_LASERBALL,
        mission_types=(MISSION_TYPE_LASERBALL, MISSION_TYPE_LASERBALL_ALT),
    )

    def __init__(self, stats: LFGameTypeStats) -> None:
        """Initializes the game type enum member.

        Args:
            stats: The game type metadata statistics object.
        """
        self.game_type_name = stats.name
        self.display_name = stats.display_name
        self.raw_name = stats.raw_name
        self.primary_mission_type = stats.primary_mission_type
        self.mission_types = stats.mission_types

    @classmethod
    def from_mission_type(cls, mission_type: int) -> 'LFGameType':
        """Retrieves a game type by its numeric mission type code.

        Args:
            mission_type: The integer mission type code.

        Returns:
            LFGameType: The matching game type enum member.

        Raises:
            ValueError: If the mission_type is not recognized.
        """
        for member in cls:
            if mission_type in member.mission_types:
                return member
        raise ValueError(f'Invalid mission type: {mission_type}')

    @classmethod
    def from_name(cls, name: str) -> 'LFGameType':
        """Retrieves a game type by its canonical or raw name.

        Args:
            name: The name string (e.g. 'SM5', 'Laserball', 'space_marines_5').

        Returns:
            LFGameType: The matching game type enum member.

        Raises:
            ValueError: If the name is not recognized.
        """
        lower = name.lower()
        for member in cls:
            if (
                member.game_type_name.lower() == lower
                or member.raw_name == lower
            ):
                return member
        raise ValueError(f'Invalid game type name: {name}')
