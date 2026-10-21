"""Data models and enums for video luminance and color analysis.

This module defines the data structures used by the color analysis utility,
including luminance metrics, temporal statistics, correction recommendations,
and result containers.

Usage example:
    from lfdata.color_correction.color_analysis_types import (
        ColorAnalysisResult,
        CorrectionNeedLevel,
        LuminanceMetrics,
    )
"""

from __future__ import annotations

import dataclasses
import enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lfdata.color_correction.lut import Lut3D


class CorrectionNeedLevel(str, enum.Enum):
    """Categorical level indicating how much color correction is needed.

    Attributes:
        NONE: Video already has well-balanced exposure and contrast.
        LOW: Minor adjustments recommended to improve visibility.
        MODERATE: Noticeable darkness; shadow lift and gamma needed.
        HIGH: Heavy underexposure typical of laser tag arena footage.
        SEVERE: Extremely dark footage requiring aggressive shadow lifting.
    """

    NONE = 'none'
    LOW = 'low'
    MODERATE = 'moderate'
    HIGH = 'high'
    SEVERE = 'severe'


class AnalysisOutputFormat(str, enum.Enum):
    """Supported output formats for color analysis reporting.

    Attributes:
        TEXT: Human-readable formatted text report.
        JSON: Machine-readable JSON output.
    """

    TEXT = 'text'
    JSON = 'json'

    @classmethod
    def from_str(cls, value: str) -> AnalysisOutputFormat:
        """Parses a string into an AnalysisOutputFormat enum value.

        Args:
            value: String format identifier ('text' or 'json').

        Returns:
            AnalysisOutputFormat: The matching enum member.

        Raises:
            ValueError: If the input string is not recognized.

        Usage example:
            fmt = AnalysisOutputFormat.from_str('json')
        """
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(
            f'Unknown output format: {value}. Expected text or json.'
        )


@dataclasses.dataclass(frozen=True)
class FrameLuminanceSample:
    """Luminance metrics for a single sampled video frame.

    Attributes:
        timestamp_ms: Time offset into the video in milliseconds.
        frame_index: Sequential zero-based frame index.
        mean_luminance: Average Rec. 709 luminance in range [0.0, 1.0].
        median_luminance: Median Rec. 709 luminance in range [0.0, 1.0].
        min_luminance: Minimum observed luminance in the frame.
        max_luminance: Maximum observed luminance in the frame.
        shadow_fraction: Fraction of pixels below shadow threshold (<0.15).
        highlight_fraction: Fraction of pixels in highlight range (>=0.70).
    """

    timestamp_ms: int
    frame_index: int
    mean_luminance: float
    median_luminance: float
    min_luminance: float
    max_luminance: float
    shadow_fraction: float
    highlight_fraction: float

    def to_dict(self) -> dict[str, float | int]:
        """Serializes the frame sample to a dictionary.

        Returns:
            dict[str, float | int]: Dictionary representation of sample.

        Usage example:
            data = sample.to_dict()
        """
        return {
            'timestamp_ms': self.timestamp_ms,
            'frame_index': self.frame_index,
            'mean_luminance': round(self.mean_luminance, 4),
            'median_luminance': round(self.median_luminance, 4),
            'min_luminance': round(self.min_luminance, 4),
            'max_luminance': round(self.max_luminance, 4),
            'shadow_fraction': round(self.shadow_fraction, 4),
            'highlight_fraction': round(self.highlight_fraction, 4),
        }


@dataclasses.dataclass(frozen=True)
class LuminanceMetrics:
    """Aggregate Rec. 709 luminance distribution across sampled video frames.

    Attributes:
        mean_luminance: Overall mean luminance across all sampled pixels.
        median_luminance: Overall median luminance (50th percentile).
        p10: 10th percentile luminance (deep shadows).
        p25: 25th percentile luminance (lower midtones / dark regions).
        p75: 75th percentile luminance (upper midtones).
        p90: 90th percentile luminance (bright areas).
        p95: 95th percentile luminance (localized arena lights, LEDs).
        p99: 99th percentile luminance (specular highlights, direct lights).
        min_luminance: Absolute minimum observed luminance.
        max_luminance: Absolute maximum observed luminance.
        std_luminance: Standard deviation of pixel luminances.
        deep_shadow_fraction: Fraction of pixels with luminance < 0.05.
        shadow_fraction: Fraction of pixels with luminance < 0.15.
        midtone_fraction: Fraction of pixels with 0.15 <= luminance < 0.70.
        highlight_fraction: Fraction of pixels with luminance >= 0.70.
        blown_fraction: Fraction of pixels with luminance >= 0.95.
        dynamic_range: Difference between 95th and 10th percentiles.
    """

    mean_luminance: float
    median_luminance: float
    p10: float
    p25: float
    p75: float
    p90: float
    p95: float
    p99: float
    min_luminance: float
    max_luminance: float
    std_luminance: float
    deep_shadow_fraction: float
    shadow_fraction: float
    midtone_fraction: float
    highlight_fraction: float
    blown_fraction: float
    dynamic_range: float

    def to_dict(self) -> dict[str, float]:
        """Serializes the aggregate luminance metrics to a dictionary.

        Returns:
            dict[str, float]: Dictionary representation of aggregate metrics.

        Usage example:
            data = metrics.to_dict()
        """
        return {
            'mean_luminance': round(self.mean_luminance, 4),
            'median_luminance': round(self.median_luminance, 4),
            'p10': round(self.p10, 4),
            'p25': round(self.p25, 4),
            'p75': round(self.p75, 4),
            'p90': round(self.p90, 4),
            'p95': round(self.p95, 4),
            'p99': round(self.p99, 4),
            'min_luminance': round(self.min_luminance, 4),
            'max_luminance': round(self.max_luminance, 4),
            'std_luminance': round(self.std_luminance, 4),
            'deep_shadow_fraction': round(self.deep_shadow_fraction, 4),
            'shadow_fraction': round(self.shadow_fraction, 4),
            'midtone_fraction': round(self.midtone_fraction, 4),
            'highlight_fraction': round(self.highlight_fraction, 4),
            'blown_fraction': round(self.blown_fraction, 4),
            'dynamic_range': round(self.dynamic_range, 4),
        }


@dataclasses.dataclass(frozen=True)
class TemporalLuminanceMetrics:
    """Measures frame-to-frame luminance variation across the video.

    Attributes:
        frames_analyzed: Number of sampled frames used in analysis.
        mean_frame_mean: Mean value of per-frame average luminances.
        std_frame_mean: Standard deviation of per-frame average luminances.
        min_frame_mean: Lowest average luminance observed among frames.
        max_frame_mean: Highest average luminance observed among frames.
        temporal_variation: Coefficient of variation (std / max(1e-4, mean)).
        is_temporally_stable: True if variation is low enough for one setting.
    """

    frames_analyzed: int
    mean_frame_mean: float
    std_frame_mean: float
    min_frame_mean: float
    max_frame_mean: float
    temporal_variation: float
    is_temporally_stable: bool

    def to_dict(self) -> dict[str, float | int | bool]:
        """Serializes temporal metrics to a dictionary.

        Returns:
            dict[str, float | int | bool]: Dictionary of temporal metrics.

        Usage example:
            data = temporal.to_dict()
        """
        return {
            'frames_analyzed': self.frames_analyzed,
            'mean_frame_mean': round(self.mean_frame_mean, 4),
            'std_frame_mean': round(self.std_frame_mean, 4),
            'min_frame_mean': round(self.min_frame_mean, 4),
            'max_frame_mean': round(self.max_frame_mean, 4),
            'temporal_variation': round(self.temporal_variation, 4),
            'is_temporally_stable': self.is_temporally_stable,
        }


@dataclasses.dataclass(frozen=True)
class CorrectionRecommendations:
    """Recommended global color correction adjustments for the video as a whole.

    Attributes:
        need_level: Assessment category of color correction required.
        recommended_shadow_lift: Recommended Lut3D shadows lift parameter.
        recommended_gamma: Recommended Lut3D gamma parameter.
        recommended_highlight_rolloff: Recommended Lut3D highlight rolloff.
        recommended_brightness: Recommended Lut3D brightness offset.
        recommended_contrast: Recommended Lut3D contrast multiplier.
        summary_notes: List of explanatory observations and rationale.
        recommended_deep_shadows: Recommended Lut3D deep near-black lift.
        recommended_black_level: Recommended Lut3D black pedestal lift/cut.
        recommended_dark_expansion: Recommended Lut3D dark gamma expansion.
    """

    need_level: CorrectionNeedLevel
    recommended_shadow_lift: float
    recommended_gamma: float
    recommended_highlight_rolloff: float
    recommended_brightness: float
    recommended_contrast: float
    summary_notes: list[str]
    recommended_deep_shadows: float = 0.0
    recommended_black_level: float = 0.0
    recommended_dark_expansion: float = 1.0

    def to_dict(self) -> dict[str, float | str | list[str]]:
        """Serializes recommendations to a dictionary.

        Returns:
            dict[str, float | str | list[str]]: Dictionary representation.

        Usage example:
            data = recs.to_dict()
        """
        return {
            'need_level': self.need_level.value,
            'recommended_shadow_lift': round(self.recommended_shadow_lift, 3),
            'recommended_gamma': round(self.recommended_gamma, 3),
            'recommended_highlight_rolloff': round(
                self.recommended_highlight_rolloff, 3
            ),
            'recommended_brightness': round(self.recommended_brightness, 3),
            'recommended_contrast': round(self.recommended_contrast, 3),
            'recommended_deep_shadows': round(self.recommended_deep_shadows, 3),
            'recommended_black_level': round(self.recommended_black_level, 3),
            'recommended_dark_expansion': round(
                self.recommended_dark_expansion, 3
            ),
            'summary_notes': list(self.summary_notes),
        }


@dataclasses.dataclass(frozen=True)
class ColorAnalysisResult:
    """Comprehensive analysis result for a video file.

    Attributes:
        video_path: File system path of the analyzed video.
        duration_ms: Total duration of the video in milliseconds.
        fps: Frame rate of the video.
        frame_count: Total frame count in the video container.
        width: Pixel width of video frames.
        height: Pixel height of video frames.
        sample_interval_ms: Millisecond interval between sampled frames.
        global_metrics: Aggregate luminance metrics across all samples.
        temporal_metrics: Temporal stability metrics across frames.
        recommendations: Recommended global color correction settings.
        frame_samples: Optional list of per-frame sample metrics.
    """

    video_path: str
    duration_ms: int
    fps: float
    frame_count: int
    width: int
    height: int
    sample_interval_ms: int
    global_metrics: LuminanceMetrics
    temporal_metrics: TemporalLuminanceMetrics
    recommendations: CorrectionRecommendations
    frame_samples: list[FrameLuminanceSample] = dataclasses.field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, object]:
        """Serializes complete analysis result to a nested dictionary.

        Returns:
            dict[str, object]: Serialized analysis data suitable for JSON.

        Usage example:
            data = result.to_dict()
        """
        res: dict[str, object] = {
            'video_path': self.video_path,
            'duration_ms': self.duration_ms,
            'fps': round(self.fps, 2),
            'frame_count': self.frame_count,
            'width': self.width,
            'height': self.height,
            'sample_interval_ms': self.sample_interval_ms,
            'global_metrics': self.global_metrics.to_dict(),
            'temporal_metrics': self.temporal_metrics.to_dict(),
            'recommendations': self.recommendations.to_dict(),
        }
        if self.frame_samples:
            res['frame_samples'] = [s.to_dict() for s in self.frame_samples]
        return res

    def to_lut3d(
        self,
        lut_size: int = 33,
        title: str | None = None,
    ) -> Lut3D:
        """Builds a Lut3D instance configured with recommendations.

        Args:
            lut_size: Grid dimension of the 3D LUT (default: 33).
            title: Optional title string to write into metadata header.

        Returns:
            Lut3D: Configured 3D LUT with suggested adjustments applied.

        Usage example:
            lut = result.to_lut3d(lut_size=33)
        """
        from lfdata.color_correction.suggested_lut import create_suggested_lut

        lut_title = (
            title
            if title is not None
            else f'Suggested Grade - {Path(self.video_path).stem}'
        )
        return create_suggested_lut(
            recommendations=self.recommendations,
            lut_size=lut_size,
            title=lut_title,
        )
