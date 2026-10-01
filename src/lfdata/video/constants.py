"""Constants for video generation, layouts, dimensions, and timing.

This module defines common default values for video rendering pipelines,
including frame rates, extra end footage, pregame delays, standard canvas
resolutions, time unit conversions, HUD merger defaults, chapter generator
thresholds, and audio matching parameters.

Usage example:
    from lfdata.video.constants import DEFAULT_FPS, DEFAULT_EXTRA_FOOTAGE_MS

    print(f'Default FPS: {DEFAULT_FPS}, Extra: {DEFAULT_EXTRA_FOOTAGE_MS} ms')
"""

from lfdata.model.constants.time import (
    MS_PER_MINUTE,
    MS_PER_SECOND,
    SECONDS_PER_MINUTE,
)

__all__ = [
    'CHAPTER_GETTING_READY_THRESHOLD_MS',
    'CHAPTER_MULTI_NUKE_WINDOW_MS',
    'CHAPTER_SPAN_THRESHOLD_MS',
    'DEFAULT_AUDIO_THRESHOLD',
    'DEFAULT_AUDIO_TOLERANCE_MS',
    'DEFAULT_EXTRA_FOOTAGE_MS',
    'DEFAULT_FADE_DURATION_S',
    'DEFAULT_FPS',
    'DEFAULT_FRAME_HEIGHT',
    'DEFAULT_FRAME_WIDTH',
    'DEFAULT_HOP_LENGTH',
    'DEFAULT_HUD_MERGE_CRF',
    'DEFAULT_HUD_MERGE_FADE_DURATION_MS',
    'DEFAULT_HUD_MERGE_PRESET',
    'DEFAULT_MAX_CHAPTERS',
    'DEFAULT_N_FFT',
    'DEFAULT_PREGAME_DELAY_MS',
    'DEFAULT_RESOLUTION',
    'DEFAULT_SAMPLE_RATE_HZ',
    'MS_PER_MINUTE',
    'MS_PER_SECOND',
    'SECONDS_PER_MINUTE',
]

# Default framerate and timing offsets
DEFAULT_FPS: int = 60
DEFAULT_EXTRA_FOOTAGE_MS: int = 10000
DEFAULT_PREGAME_DELAY_MS: int = 0
DEFAULT_FADE_DURATION_S: float = 1.0

# Standard display resolution dimensions
DEFAULT_FRAME_WIDTH: int = 1920
DEFAULT_FRAME_HEIGHT: int = 1080
DEFAULT_RESOLUTION: tuple[int, int] = (
    DEFAULT_FRAME_WIDTH,
    DEFAULT_FRAME_HEIGHT,
)

# HUD video merger defaults
DEFAULT_HUD_MERGE_FADE_DURATION_MS: int = 5000
DEFAULT_HUD_MERGE_CRF: int = 18
DEFAULT_HUD_MERGE_PRESET: str = 'medium'

# Chapter generator limits and thresholds
DEFAULT_MAX_CHAPTERS: int = 20
CHAPTER_SPAN_THRESHOLD_MS: int = 10000
CHAPTER_MULTI_NUKE_WINDOW_MS: int = 15000
CHAPTER_GETTING_READY_THRESHOLD_MS: int = 20000

# Audio matching defaults
DEFAULT_SAMPLE_RATE_HZ: int = 22050
DEFAULT_HOP_LENGTH: int = 256
DEFAULT_N_FFT: int = 1024
DEFAULT_AUDIO_THRESHOLD: float = 0.2
DEFAULT_AUDIO_TOLERANCE_MS: int = 500
