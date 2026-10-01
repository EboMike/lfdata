"""Time conversion and duration constants for millisecond calculations.

This module defines standard time conversion factors between milliseconds,
seconds, and minutes used across playback, simulation, video, and diagnostics.

Usage example:
    from lfdata.model.constants.time import MS_PER_MINUTE, MS_PER_SECOND

    seconds = total_ms / MS_PER_SECOND
"""

MS_PER_SECOND: int = 1000
SECONDS_PER_MINUTE: int = 60
MS_PER_MINUTE: int = 60000
