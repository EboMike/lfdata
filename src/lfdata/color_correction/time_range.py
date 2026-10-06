"""Time range representation for reference video clips.

This module defines the `TimeRange` dataclass representing a continuous
span of milliseconds selected within a reference video.

Usage example:
    from lfdata.color_correction.time_range import TimeRange

    clip_range = TimeRange(start_ms=1000, end_ms=5000)
    print(clip_range.display_str())
"""

import dataclasses

from lfdata.model.constants.time import MS_PER_SECOND, SECONDS_PER_MINUTE


@dataclasses.dataclass(frozen=True)
class TimeRange:
    """Represents a continuous millisecond duration within a video.

    Attributes:
        start_ms: Starting timestamp in milliseconds (non-negative).
        end_ms: Ending timestamp in milliseconds (greater or equal to start).
    """

    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        """Validates that start and end timestamps are logically valid.

        Raises:
            ValueError: If start_ms is negative or end_ms is before start_ms.
        """
        if self.start_ms < 0:
            raise ValueError(
                f'start_ms must be non-negative, got {self.start_ms}'
            )
        if self.end_ms < self.start_ms:
            raise ValueError(
                f'end_ms ({self.end_ms}) cannot be before '
                f'start_ms ({self.start_ms})'
            )

    @property
    def duration_ms(self) -> int:
        """Calculates the total duration of the range in milliseconds.

        Returns:
            int: The difference between end_ms and start_ms in milliseconds.
        """
        return self.end_ms - self.start_ms

    @staticmethod
    def format_timestamp_ms(time_ms: int) -> str:
        """Formats a millisecond count into MM:SS.mmm format.

        This utility converts an integer millisecond timestamp into a human
        readable time string showing minutes, seconds, and milliseconds.

        Args:
            time_ms: Timestamp in milliseconds.

        Returns:
            str: Formatted string in MM:SS.mmm representation.

        Usage example:
            formatted = TimeRange.format_timestamp_ms(65432)
        """
        total_seconds = time_ms // MS_PER_SECOND
        minutes = total_seconds // SECONDS_PER_MINUTE
        seconds = total_seconds % SECONDS_PER_MINUTE
        millis = time_ms % MS_PER_SECOND
        return f'{minutes:02d}:{seconds:02d}.{millis:03d}'

    def display_str(self) -> str:
        """Returns a formatted human-readable summary of the range.

        Formats the start and end timestamps alongside the total duration
        in fractional seconds for display in UI lists.

        Returns:
            str: Summary string such as '00:01.000 - 00:05.000 (4.000s)'.

        Usage example:
            text = clip_range.display_str()
        """
        start_formatted = self.format_timestamp_ms(self.start_ms)
        end_formatted = self.format_timestamp_ms(self.end_ms)
        duration_sec = self.duration_ms / MS_PER_SECOND
        return f'{start_formatted} - {end_formatted} ({duration_sec:.3f}s)'
