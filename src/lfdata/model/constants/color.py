"""Enums representing LF team colors and metadata."""

import dataclasses
import enum


@dataclasses.dataclass(frozen=True)
class LFTeamColorStats:
    """Statistics and metadata for a team color.

    Attributes:
        color_enum: The integer ID from TDF files.
        display_name: The display name of the color.
        rgb: The CSS/RGB hex color value.
    """

    color_enum: int
    display_name: str
    rgb: str


class LFTeamColor(enum.Enum):
    """Defines team colors used in LF games with internal name and RGB color code.

    Includes display names and RGB hex values.
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
