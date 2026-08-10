"""Enums representing LF centres and metadata.

This module defines Laserforce arena centre identifiers, locations, country codes,
and metadata mappings used across TDF importing and game reporting.

Usage example:
    from lfdata.model import LFCentre

    centre = LFCentre.from_code('4-43')
    print(f'Centre arena: {centre.arena_name}')
"""

import dataclasses
import enum


@dataclasses.dataclass(frozen=True)
class LFCentreStats:
    """Statistics and metadata for a Laserforce centre.

    Holds country code, location code, and arena name for a specific venue.
    """

    country_code: int
    location_code: int
    arena_name: str

    @property
    def centre_code(self) -> str:
        """Returns the centre code string (e.g. '4-43')."""
        return f'{self.country_code}-{self.location_code}'


class LFCentre(enum.Enum):
    """Enumeration of known Laserforce arena centres.

    Provides metadata lookup by centre code string or location details.
    """

    BRISBANE = LFCentreStats(1, 1, 'Brisbane')
    ST_GEORGE = LFCentreStats(4, 2, 'St George')
    INVASION = LFCentreStats(4, 43, 'Invasion')
    AUCKLAND_WAIRAU = LFCentreStats(3, 3, 'Auckland Wairau')
    SYRACUSE = LFCentreStats(4, 23, 'Syracuse')
    LOVELAND = LFCentreStats(4, 19, 'Loveland')
    CARMICHAEL = LFCentreStats(4, 3, 'Lasertag of Carmichael')
    ATLANTIS = LFCentreStats(4, 12, 'Atlantis Laser Tag')
    DARMSTADT = LFCentreStats(21, 70, 'LaserTag Darmstadt')
    DETROIT = LFCentreStats(4, 6, 'Detroit')
    AUCKLAND_GAME_OVER = LFCentreStats(3, 7, 'Auckland Game Over')
    HUDDERSFIELD = LFCentreStats(7, 10, 'Huddersfield')
    PETERBOROUGH = LFCentreStats(7, 2, 'Peterborough')
    SYDNEY_UNDERWORLD = LFCentreStats(1, 64, 'Sydney Underworld')
    CHELTANHAM = LFCentreStats(7, 13, 'Cheltanham')

    def __init__(self, stats: LFCentreStats) -> None:
        """Initializes the centre.

        Args:
            stats: The centre metadata statistics object.
        """
        self.country_code = stats.country_code
        self.location_code = stats.location_code
        self.arena_name = stats.arena_name
        self.centre_code = stats.centre_code

    @classmethod
    def from_code(cls, centre_code: str) -> 'LFCentre':
        """Retrieves a centre by its centre code (e.g. '4-43').

        Args:
            centre_code: The centre code string.

        Returns:
            LFCentre: The matching centre enum.

        Raises:
            ValueError: If the centre_code is not valid.
        """
        for centre in cls:
            if centre.centre_code == centre_code:
                return centre
        raise ValueError(f'Invalid centre code: {centre_code}')
