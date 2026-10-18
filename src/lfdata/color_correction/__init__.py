"""Color Correction Editor package for LF video data processing.

This package provides UI tools and data models for loading reference video
footage, inspecting timeline frames, defining range segments, and preparing
color correction adjustments.

Usage example:
    from lfdata.color_correction.editor import ColorCorrectionEditorApp

    app = ColorCorrectionEditorApp()
"""

from lfdata.color_correction.color_analysis_types import (
    AnalysisOutputFormat,
    ColorAnalysisResult,
    CorrectionNeedLevel,
    CorrectionRecommendations,
    FrameLuminanceSample,
    LuminanceMetrics,
    TemporalLuminanceMetrics,
)
from lfdata.color_correction.color_analyzer import ColorAnalyzer
from lfdata.color_correction.color_averages_bar import (
    ColorAveragesBar,
    compute_frame_color_column,
)
from lfdata.color_correction.color_correction_tab import ColorCorrectionTab
from lfdata.color_correction.editor import ColorCorrectionEditorApp
from lfdata.color_correction.noise_reduction import NoiseReductionSettings
from lfdata.color_correction.noise_reduction_tab import NoiseReductionTab
from lfdata.color_correction.reference_video_tab import ReferenceVideoTab
from lfdata.color_correction.suggested_lut import (
    create_suggested_lut,
    save_suggested_lut,
)
from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.timeline_widget import TimelineWidget
from lfdata.color_correction.video_reader import VideoReader

__all__ = [
    'AnalysisOutputFormat',
    'ColorAnalysisResult',
    'ColorAnalyzer',
    'ColorAveragesBar',
    'ColorCorrectionEditorApp',
    'ColorCorrectionTab',
    'CorrectionNeedLevel',
    'CorrectionRecommendations',
    'FrameLuminanceSample',
    'LuminanceMetrics',
    'NoiseReductionSettings',
    'NoiseReductionTab',
    'ReferenceVideoTab',
    'TemporalLuminanceMetrics',
    'TimeRange',
    'TimelineWidget',
    'VideoReader',
    'compute_frame_color_column',
    'create_suggested_lut',
    'save_suggested_lut',
]
