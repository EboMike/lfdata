"""Constants for the color correction editor tool.

This module defines graphical colors, sizing dimensions, and styling constants
used across the color correction editor user interface.

Usage example:
    from lfdata.color_correction.constants import (
        DEFAULT_PREVIEW_WIDTH,
        DEFAULT_TIMELINE_HEIGHT,
    )

    width = DEFAULT_PREVIEW_WIDTH
"""

DEFAULT_PREVIEW_WIDTH: int = 640
DEFAULT_PREVIEW_HEIGHT: int = 360
DEFAULT_TIMELINE_HEIGHT: int = 40
DEFAULT_TIMELINE_PAD_X: int = 15
DEFAULT_TIMELINE_TRACK_Y_PAD: int = 8
DEFAULT_COLOR_BAR_UPDATE_INTERVAL_MS: int = 5000
DEFAULT_MAX_COLOR_BAR_SAMPLES: int = 120

COLOR_TRACK_BG: str = '#2d3748'
COLOR_TRACK_BORDER: str = '#4a5568'
COLOR_RANGE_FILL: str = '#3182ce'
COLOR_RANGE_OUTLINE: str = '#63b3ed'
COLOR_SCRUBBER: str = '#e53e3e'
COLOR_TICK: str = '#718096'
