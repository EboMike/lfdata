"""Scoreboard constant definitions and visibility enumerations.

This module defines configuration options for displaying additional stats
in game scoreboards (such as accuracy, hit ratio, nukes, and medic hits).

Usage example:
    from lfdata.model.constants.scoreboard import ScoreboardAdditionalStats

    mode = ScoreboardAdditionalStats.from_str('after_game')
    print(mode == ScoreboardAdditionalStats.AFTER_GAME)
"""

import enum


class ScoreboardAdditionalStats(enum.Enum):
    """Configuration options for showing additional stats on scoreboards.

    Attributes:
        NEVER: Additional stats are never displayed.
        AFTER_GAME: Additional stats are displayed after the game finishes.
        ALWAYS: Additional stats are displayed at all times during playback.
    """

    NEVER = 'never'
    AFTER_GAME = 'after_game'
    ALWAYS = 'always'

    @classmethod
    def from_str(cls, value: str | None) -> 'ScoreboardAdditionalStats':
        """Parses a string into a ScoreboardAdditionalStats member.

        Normalizes spaces and underscores and matches case-insensitively.
        Defaults to AFTER_GAME if value is empty or not recognized.

        Args:
            value: Configuration string ('never', 'after_game', 'always').

        Returns:
            ScoreboardAdditionalStats: The resolved enum member.
        """
        if not value:
            return cls.AFTER_GAME

        cleaned = str(value).strip().lower().replace(' ', '_')
        for member in cls:
            if member.value == cleaned:
                return member
        return cls.AFTER_GAME


# Alias for backward compatibility
ScoreboardAdditionalValues = ScoreboardAdditionalStats


