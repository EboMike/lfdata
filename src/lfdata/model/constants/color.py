"""Enums representing LF team colors and metadata.

This module defines team colors, display names, RGB hex values, and TDF color ID
mapping for visual rendering and UI display.

Usage example:
    from lfdata.model import LFTeamColor

    color = LFTeamColor.from_enum(11)
    print(f'Color: {color.display_name}, Hex: {color.rgb}')
"""

import dataclasses
import enum


@dataclasses.dataclass(frozen=True)
class LFTeamColorStats:
    """Metadata for a team color representation.

    Holds the integer color enum from TDF files, human-readable display name,
    and CSS RGB hex code.
    """

    color_enum: int
    display_name: str
    rgb: str


class LFTeamColor(enum.Enum):
    """Enumeration of team colors used in Laserforce games.

    Provides mapping from TDF color code integers to display names and hex values.
    """

    FIRE = LFTeamColorStats(color_enum=11, display_name='Fire', rgb='#FF5000')
    EARTH = LFTeamColorStats(color_enum=13, display_name='Earth', rgb='#A0FF00')
    NONE = LFTeamColorStats(color_enum=0, display_name='None', rgb='#808080')

    def __init__(self, stats: LFTeamColorStats) -> None:
        """Initializes the team color.

        Args:
            stats: The color metadata statistics object.
        """
        self.color_enum = stats.color_enum
        self.display_name = stats.display_name
        self.rgb = stats.rgb

    @classmethod
    def from_enum(cls, color_enum: int) -> 'LFTeamColor':
        """Retrieves a team color by its TDF color code.

        Args:
            color_enum: The color code integer.

        Returns:
            LFTeamColor: The matching color enum.

        Raises:
            ValueError: If the color_enum is not valid.
        """
        for color in cls:
            if color.color_enum == color_enum:
                return color
        raise ValueError(f'Invalid color enum: {color_enum}')
