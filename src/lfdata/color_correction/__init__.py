"""Color Correction Editor package for LF video data processing.

This package provides UI tools and data models for loading reference video
footage, inspecting timeline frames, defining range segments, and preparing
color correction adjustments.

Usage example:
    from lfdata.color_correction.editor import ColorCorrectionEditorApp

    app = ColorCorrectionEditorApp()
"""

from lfdata.color_correction.color_correction_tab import ColorCorrectionTab
from lfdata.color_correction.editor import ColorCorrectionEditorApp
from lfdata.color_correction.reference_video_tab import ReferenceVideoTab
from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.timeline_widget import TimelineWidget
from lfdata.color_correction.video_reader import VideoReader

__all__ = [
    'ColorCorrectionEditorApp',
    'ColorCorrectionTab',
    'ReferenceVideoTab',
    'TimeRange',
    'TimelineWidget',
    'VideoReader',
]
