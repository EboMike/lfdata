"""Normalizer for LF game types.

This module provides utilities to map raw, non-standardized game type strings from TDF
header records into canonical, standardized game type names (such as 'SM5' or 'Laserball').

Usage example:
    from lfdata.importer.normalizer import GameTypeNormalizer

    normalizer = GameTypeNormalizer()
    canonical_name = normalizer.normalize('Space Marines 5 Tournament Edition')
    # Returns 'SM5'
"""

import re


class GameTypeNormalizer:
    """Normalizes raw game type strings into standardized game type identifiers.

    Holds compiled regex patterns paired with canonical game type strings,
    and matches raw input strings against those patterns.
    """

    def __init__(self) -> None:
        """Initializes the normalizer with default regex mappings."""
        self._mappings: list[tuple[re.Pattern[str], str]] = [
            (re.compile(r'Space\s*Marines\s*5'), 'SM5'),
            (re.compile(r'SM5'), 'SM5'),
            (re.compile(r'Laser\s*[bB]all'), 'Laserball'),
        ]

    def normalize(self, game_type: str) -> str | None:
        """Derives a normalized game type from the given raw game type.

        Iterates through the compiled regular expression mappings and matches
        against the raw game type string. Returns the first matching normalized
        value.

        Args:
            game_type: The raw game type string to normalize.

        Returns:
            str | None: The normalized game type string, or None if no
                pattern matches.
        """
        for pattern, replacement in self._mappings:
            if pattern.search(game_type):
                return replacement
        return None
