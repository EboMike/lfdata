"""Scoreboard constant definitions and visibility enumerations.

This module defines configuration options for displaying additional values
in game scoreboards (such as accuracy, hit ratio, nukes, and medic hits).

Usage example:
    from lfdata.model.constants.scoreboard import ScoreboardAdditionalValues

    mode = ScoreboardAdditionalValues.from_str('after_game')
    print(mode == ScoreboardAdditionalValues.AFTER_GAME)
"""

import enum


class ScoreboardAdditionalValues(enum.Enum):
    """Configuration options for showing additional values on scoreboards.

    Attributes:
        NEVER: Additional values are never displayed.
        AFTER_GAME: Additional values are displayed after the game finishes.
        ALWAYS: Additional values are displayed at all times during playback.
    """

    NEVER = 'never'
    AFTER_GAME = 'after_game'
    ALWAYS = 'always'

    @classmethod
    def from_str(cls, value: str | None) -> 'ScoreboardAdditionalValues':
        """Parses a string into a ScoreboardAdditionalValues member.

        Normalizes spaces and underscores and matches case-insensitively.
        Defaults to AFTER_GAME if value is empty or not recognized.

        Args:
            value: Configuration string ('never', 'after_game', 'always').

        Returns:
            ScoreboardAdditionalValues: The resolved enum member.
        """
        if not value:
            return cls.AFTER_GAME

        cleaned = str(value).strip().lower().replace(' ', '_')
        for member in cls:
            if member.value == cleaned:
                return member
        return cls.AFTER_GAME

