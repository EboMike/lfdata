"""Time conversion and duration constants for millisecond calculations.

This module defines standard time conversion factors between milliseconds,
centiseconds, seconds, and minutes, as well as the game timer display mode
enumeration used across playback, simulation, video, and diagnostics.

Usage example:
    from lfdata.model.constants.time import (
        MS_PER_MINUTE,
        MS_PER_SECOND,
        TimerMode,
    )

    seconds = total_ms / MS_PER_SECOND
    mode = TimerMode.from_str('remaining')
"""

from __future__ import annotations

import enum

MS_PER_CENTISECOND: int = 10
MS_PER_SECOND: int = 1000
SECONDS_PER_MINUTE: int = 60
MS_PER_MINUTE: int = 60000


class TimerMode(enum.Enum):
    """Display modes for the game timer UI element.

    Attributes:
        REMAINING: Counts down from the scheduled game duration to 00:00.
        ELAPSED: Counts up from 00:00 as the game progresses.
    """

    REMAINING = 'remaining'
    ELAPSED = 'elapsed'

    @classmethod
    def from_str(cls, value: str | None) -> 'TimerMode':
        """Parses a string into a TimerMode member.

        Matches case-insensitively after stripping whitespace. Defaults to
        REMAINING if value is empty or not recognized.

        Args:
            value: Configuration string ('remaining' or 'elapsed').

        Returns:
            TimerMode: The resolved enum member.
        """
        if not value:
            return cls.REMAINING

        cleaned = str(value).strip().lower()
        for member in cls:
            if member.value == cleaned:
                return member
        return cls.REMAINING
