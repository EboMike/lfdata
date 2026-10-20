"""Luminance and color correction analyzer for video footage.

This module provides the `ColorAnalyzer` class to decode sampled video frames,
calculate Rec. 709 luminance statistics, measure temporal lighting consistency,
and determine recommended global color correction parameters.

Usage example:
    from lfdata.color_correction.color_analyzer import ColorAnalyzer

    analyzer = ColorAnalyzer(sample_interval_ms=2000, max_frames=60)
    result = analyzer.analyze(video_path='footage.mp4')
    print(f'Need level: {result.recommendations.need_level}')
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from lfdata.color_correction.color_analysis_types import (
    ColorAnalysisResult,
    CorrectionNeedLevel,
    CorrectionRecommendations,
    FrameLuminanceSample,
    LuminanceMetrics,
    TemporalLuminanceMetrics,
)
from lfdata.model.constants.time import MS_PER_SECOND

# Standard Rec. 709 luminance coefficients for BGR channels in OpenCV
REC709_B_COEFF: float = 0.0722
REC709_G_COEFF: float = 0.7152
REC709_R_COEFF: float = 0.2126

DEFAULT_ANALYSIS_SAMPLE_INTERVAL_MS: int = 2000
DEFAULT_ANALYSIS_MAX_FRAMES: int = 120
DEFAULT_ANALYSIS_DOWNSAMPLE_WIDTH: int = 320


class ColorAnalyzer:
    """Analyzes overall luminance properties of a video file.

    Attributes:
        sample_interval_ms: Millisecond interval between sampled frames.
        max_frames: Upper bound on the number of frames to decode and analyze.
        downsample_width: Width in pixels used to downsample frames for speed.
    """

    sample_interval_ms: int
    max_frames: int
    downsample_width: int

    def __init__(
        self,
        sample_interval_ms: int = DEFAULT_ANALYSIS_SAMPLE_INTERVAL_MS,
        max_frames: int = DEFAULT_ANALYSIS_MAX_FRAMES,
        downsample_width: int = DEFAULT_ANALYSIS_DOWNSAMPLE_WIDTH,
    ) -> None:
        """Initializes a ColorAnalyzer instance with sampling parameters.

        Args:
            sample_interval_ms: Sampling interval in ms (default 2000).
            max_frames: Maximum number of frames to sample (default 120).
            downsample_width: Target frame width for downsampling (default 320).
        """
        self.sample_interval_ms = max(100, sample_interval_ms)
        self.max_frames = max(1, max_frames)
        self.downsample_width = max(32, downsample_width)

    def analyze(
        self,
        video_path: str | Path,
        include_frame_samples: bool = False,
    ) -> ColorAnalysisResult:
        """Analyzes video luminance distribution and produces recommendations.

        Opens the target video file, extracts frame samples across the timeline,
        computes Rec. 709 luminance distributions and temporal consistency,
        and generates recommended color grading adjustments.

        Args:
            video_path: Path to the video file to analyze.
            include_frame_samples: Whether to include per-frame sample objects.

        Returns:
            ColorAnalysisResult: Complete analysis result with recommendations.

        Raises:
            FileNotFoundError: If the specified video file does not exist.
            ValueError: If the video cannot be opened or decoded.

        Usage example:
            result = analyzer.analyze(video_path='clip.mp4')
        """
        path_obj = Path(video_path)
        if not path_obj.exists():
            raise FileNotFoundError(f'Video file not found: {video_path}')

        cap = cv2.VideoCapture(str(path_obj))
        if not cap.isOpened():
            cap.release()
            raise ValueError(f'Could not open video file: {video_path}')

        try:
            fps, frame_count, width, height, duration_ms = (
                self._read_video_metadata(cap=cap)
            )
            sampled_pixels, frame_samples = self._sample_video_frames(
                cap=cap,
                duration_ms=duration_ms,
                fps=fps,
                total_frames=frame_count,
            )
        finally:
            cap.release()

        global_metrics = self._calculate_luminance_metrics(
            lum_array=sampled_pixels
        )
        temporal_metrics = self._calculate_temporal_metrics(
            frame_samples=frame_samples
        )
        recommendations = self._generate_recommendations(
            metrics=global_metrics,
            temporal=temporal_metrics,
        )

        return ColorAnalysisResult(
            video_path=str(path_obj),
            duration_ms=duration_ms,
            fps=fps,
            frame_count=frame_count,
            width=width,
            height=height,
            sample_interval_ms=self.sample_interval_ms,
            global_metrics=global_metrics,
            temporal_metrics=temporal_metrics,
            recommendations=recommendations,
            frame_samples=frame_samples if include_frame_samples else [],
        )

    def _read_video_metadata(
        self, cap: cv2.VideoCapture
    ) -> tuple[float, int, int, int, int]:
        """Extracts and validates basic container metadata from VideoCapture.

        Args:
            cap: An active OpenCV VideoCapture instance.

        Returns:
            tuple[float, int, int, int, int]: Tuple of (fps, frame_count,
            width, height, duration_ms).

        Raises:
            ValueError: If critical video properties cannot be retrieved.
        """
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps <= 0.0 or frame_count <= 0:
            raise ValueError(
                f'Invalid video container properties: fps={fps}, '
                f'frames={frame_count}'
            )

        duration_ms = int((frame_count / fps) * MS_PER_SECOND)
        if duration_ms <= 0:
            raise ValueError('Calculated video duration is 0 ms')

        return fps, frame_count, width, height, duration_ms

    def _build_sample_indices(
        self, duration_ms: int, fps: float, total_frames: int
    ) -> list[tuple[int, int]]:
        """Calculates timestamps and frame indices to sample evenly over time.

        Args:
            duration_ms: Total duration of the video in milliseconds.
            fps: Frame rate of the video.
            total_frames: Total number of frames in the video.

        Returns:
            list[tuple[int, int]]: List of (timestamp_ms, frame_idx) pairs.
        """
        step_ms = self.sample_interval_ms
        num_steps = max(1, duration_ms // step_ms)
        sample_times_ms: list[int]

        if num_steps <= self.max_frames:
            sample_times_ms = [i * step_ms for i in range(num_steps)]
            if (
                duration_ms > 0
                and sample_times_ms
                and sample_times_ms[-1] < duration_ms - (step_ms // 2)
            ):
                sample_times_ms.append(duration_ms)
        else:
            sample_times_ms = [
                round(t) for t in np.linspace(0, duration_ms, self.max_frames)
            ]

        results: list[tuple[int, int]] = []
        for time_ms in sample_times_ms:
            frame_idx = round((time_ms / MS_PER_SECOND) * fps)
            frame_idx = max(0, min(total_frames - 1, frame_idx))
            results.append((time_ms, frame_idx))

        return results

    def _sample_video_frames(
        self,
        cap: cv2.VideoCapture,
        duration_ms: int,
        fps: float,
        total_frames: int,
    ) -> tuple[np.ndarray, list[FrameLuminanceSample]]:
        """Decodes sampled frames from the video and calculates luminance.

        Args:
            cap: An opened VideoCapture object.
            duration_ms: Total length in milliseconds.
            fps: Video frames per second.
            total_frames: Total frames in container.

        Returns:
            tuple[np.ndarray, list[FrameLuminanceSample]]: Flat array of sampled
            pixel luminances and list of frame sample objects.
        """
        targets = self._build_sample_indices(
            duration_ms=duration_ms, fps=fps, total_frames=total_frames
        )
        pixel_chunks: list[np.ndarray] = []
        frame_samples: list[FrameLuminanceSample] = []

        last_frame_idx = -1
        for time_ms, frame_idx in targets:
            if 0 < frame_idx - last_frame_idx <= 5:
                for _ in range(frame_idx - last_frame_idx - 1):
                    cap.grab()
            elif frame_idx != last_frame_idx + 1:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

            success, bgr_frame = cap.read()
            last_frame_idx = frame_idx
            if not success or bgr_frame is None or bgr_frame.size == 0:
                continue

            lum_map = self._compute_frame_luminance(frame=bgr_frame)
            flat_lum = lum_map.ravel()
            pixel_chunks.append(flat_lum)

            sample = self._create_frame_sample(
                timestamp_ms=time_ms,
                frame_idx=frame_idx,
                flat_lum=flat_lum,
            )
            frame_samples.append(sample)

        if not pixel_chunks:
            fallback = np.array([0.0], dtype=np.float32)
            return fallback, []

        return np.concatenate(pixel_chunks), frame_samples

    def _compute_frame_luminance(self, frame: np.ndarray) -> np.ndarray:
        """Calculates normalized Rec. 709 luminance values for a single frame.

        Downsamples the frame horizontally and vertically to optimize
        computation speed while maintaining statistical fidelity.

        Args:
            frame: Raw BGR video frame array of shape (H, W, 3).

        Returns:
            np.ndarray: 2D array of luminance values in range [0.0, 1.0].
        """
        h, w = frame.shape[:2]
        if w > self.downsample_width:
            target_h = max(16, round(h * (self.downsample_width / w)))
            resized = cv2.resize(
                frame,
                (self.downsample_width, target_h),
                interpolation=cv2.INTER_AREA,
            )
        else:
            resized = frame

        # Compute Rec. 709 luminance from BGR channels
        lum = (
            REC709_B_COEFF * resized[:, :, 0]
            + REC709_G_COEFF * resized[:, :, 1]
            + REC709_R_COEFF * resized[:, :, 2]
        ) / 255.0

        return lum.astype(np.float32)

    def _create_frame_sample(
        self,
        timestamp_ms: int,
        frame_idx: int,
        flat_lum: np.ndarray,
    ) -> FrameLuminanceSample:
        """Creates a FrameLuminanceSample dataclass from a flat luminance array.

        Args:
            timestamp_ms: Time offset into video in milliseconds.
            frame_idx: Zero-based frame index.
            flat_lum: 1D array of pixel luminances in range [0.0, 1.0].

        Returns:
            FrameLuminanceSample: Summary statistics for the single frame.
        """
        mean_val = float(np.mean(flat_lum))
        median_val = float(np.median(flat_lum))
        min_val = float(np.min(flat_lum))
        max_val = float(np.max(flat_lum))
        total_pixels = max(1, flat_lum.size)
        shadow_count = int(np.count_nonzero(flat_lum < 0.15))
        highlight_count = int(np.count_nonzero(flat_lum >= 0.70))

        return FrameLuminanceSample(
            timestamp_ms=timestamp_ms,
            frame_index=frame_idx,
            mean_luminance=mean_val,
            median_luminance=median_val,
            min_luminance=min_val,
            max_luminance=max_val,
            shadow_fraction=shadow_count / total_pixels,
            highlight_fraction=highlight_count / total_pixels,
        )

    def _calculate_luminance_metrics(
        self, lum_array: np.ndarray
    ) -> LuminanceMetrics:
        """Calculates global luminance percentiles and tone zone distributions.

        Args:
            lum_array: Flat array of luminance values across all sampled frames.

        Returns:
            LuminanceMetrics: Aggregate luminance metrics.
        """
        if lum_array.size == 0:
            return LuminanceMetrics(
                mean_luminance=0.0,
                median_luminance=0.0,
                p10=0.0,
                p25=0.0,
                p75=0.0,
                p90=0.0,
                p95=0.0,
                p99=0.0,
                min_luminance=0.0,
                max_luminance=0.0,
                std_luminance=0.0,
                deep_shadow_fraction=1.0,
                shadow_fraction=1.0,
                midtone_fraction=0.0,
                highlight_fraction=0.0,
                blown_fraction=0.0,
                dynamic_range=0.0,
            )

        mean_lum = float(np.mean(lum_array))
        std_lum = float(np.std(lum_array))
        min_lum = float(np.min(lum_array))
        max_lum = float(np.max(lum_array))

        percentiles = np.percentile(lum_array, [10, 25, 50, 75, 90, 95, 99])
        p10, p25, median_lum, p75, p90, p95, p99 = [
            float(val) for val in percentiles
        ]

        total_pixels = lum_array.size
        deep_shadow = float(np.count_nonzero(lum_array < 0.05) / total_pixels)
        shadow = float(np.count_nonzero(lum_array < 0.15) / total_pixels)
        highlight = float(np.count_nonzero(lum_array >= 0.70) / total_pixels)
        blown = float(np.count_nonzero(lum_array >= 0.95) / total_pixels)
        midtone = max(0.0, 1.0 - shadow - highlight)
        dyn_range = max(0.0, p95 - p10)

        return LuminanceMetrics(
            mean_luminance=mean_lum,
            median_luminance=median_lum,
            p10=p10,
            p25=p25,
            p75=p75,
            p90=p90,
            p95=p95,
            p99=p99,
            min_luminance=min_lum,
            max_luminance=max_lum,
            std_luminance=std_lum,
            deep_shadow_fraction=deep_shadow,
            shadow_fraction=shadow,
            midtone_fraction=midtone,
            highlight_fraction=highlight,
            blown_fraction=blown,
            dynamic_range=dyn_range,
        )

    def _calculate_temporal_metrics(
        self, frame_samples: list[FrameLuminanceSample]
    ) -> TemporalLuminanceMetrics:
        """Measures frame-to-frame luminance variation across the video timeline.

        Evaluates whether luminance is uniform across time so a single color
        correction setting can be applied reliably to the whole video.

        Args:
            frame_samples: List of per-frame sample metrics.

        Returns:
            TemporalLuminanceMetrics: Temporal consistency statistics.
        """
        if not frame_samples:
            return TemporalLuminanceMetrics(
                frames_analyzed=0,
                mean_frame_mean=0.0,
                std_frame_mean=0.0,
                min_frame_mean=0.0,
                max_frame_mean=0.0,
                temporal_variation=0.0,
                is_temporally_stable=True,
            )

        means = np.array([s.mean_luminance for s in frame_samples])
        mean_mean = float(np.mean(means))
        std_mean = float(np.std(means))
        min_mean = float(np.min(means))
        max_mean = float(np.max(means))
        temporal_var = float(std_mean / max(1e-4, mean_mean))

        # A video is stable if std deviation of frame means is small
        is_stable = bool(std_mean < 0.06 or temporal_var < 0.35)

        return TemporalLuminanceMetrics(
            frames_analyzed=len(frame_samples),
            mean_frame_mean=mean_mean,
            std_frame_mean=std_mean,
            min_frame_mean=min_mean,
            max_frame_mean=max_mean,
            temporal_variation=temporal_var,
            is_temporally_stable=is_stable,
        )

    def _determine_need_level(
        self, metrics: LuminanceMetrics
    ) -> CorrectionNeedLevel:
        """Determines categorical color correction need level from metrics.

        Args:
            metrics: Aggregate video luminance metrics.

        Returns:
            CorrectionNeedLevel: Determined need category.
        """
        if (
            metrics.shadow_fraction >= 0.80
            or metrics.median_luminance < 0.04
            or metrics.deep_shadow_fraction >= 0.65
        ):
            return CorrectionNeedLevel.SEVERE

        if metrics.shadow_fraction >= 0.60 or metrics.median_luminance < 0.08:
            return CorrectionNeedLevel.HIGH

        if metrics.shadow_fraction >= 0.35 or metrics.median_luminance < 0.16:
            return CorrectionNeedLevel.MODERATE

        if metrics.shadow_fraction >= 0.20 or metrics.median_luminance < 0.22:
            return CorrectionNeedLevel.LOW

        return CorrectionNeedLevel.NONE

    def _calculate_shadow_lift(
        self, need: CorrectionNeedLevel, metrics: LuminanceMetrics
    ) -> float:
        """Calculates recommended Lut3D shadow lift parameter.

        Args:
            need: Categorical correction need level.
            metrics: Video luminance metrics.

        Returns:
            float: Recommended shadow adjustment in range [0.0, 1.0].
        """
        if need == CorrectionNeedLevel.SEVERE:
            return min(0.85, 0.60 + (metrics.shadow_fraction * 0.25))
        if need == CorrectionNeedLevel.HIGH:
            return min(0.70, 0.45 + (metrics.shadow_fraction * 0.25))
        if need == CorrectionNeedLevel.MODERATE:
            return min(0.50, 0.25 + (metrics.shadow_fraction * 0.25))
        if need == CorrectionNeedLevel.LOW:
            return 0.20
        return 0.0

    def _calculate_gamma(
        self, need: CorrectionNeedLevel, metrics: LuminanceMetrics
    ) -> float:
        """Calculates recommended Lut3D gamma power curve multiplier.

        Args:
            need: Categorical correction need level.
            metrics: Video luminance metrics.

        Returns:
            float: Recommended gamma value (neutral 1.0).
        """
        if need == CorrectionNeedLevel.SEVERE:
            if metrics.median_luminance < 0.03:
                return 1.85
            return 1.70
        if need == CorrectionNeedLevel.HIGH:
            if metrics.median_luminance < 0.06:
                return 1.60
            return 1.50
        if need == CorrectionNeedLevel.MODERATE:
            return 1.35
        if need == CorrectionNeedLevel.LOW:
            return 1.15
        return 1.0

    def _calculate_highlight_rolloff(self, metrics: LuminanceMetrics) -> float:
        """Calculates recommended Lut3D highlight rolloff parameter.

        Ensures bright LEDs and laser pack targets do not harshly clip
        when shadow lifting and gamma adjustments are applied.

        Args:
            metrics: Video luminance metrics.

        Returns:
            float: Recommended highlight rolloff in range [0.0, 1.0].
        """
        if metrics.blown_fraction >= 0.005 or metrics.p99 >= 0.96:
            return 0.60
        if metrics.blown_fraction >= 0.001 or metrics.p95 >= 0.80:
            return 0.45
        if metrics.highlight_fraction >= 0.03 or metrics.p95 >= 0.65:
            return 0.30
        if metrics.p95 >= 0.50:
            return 0.15
        return 0.0

    def _generate_recommendations(
        self,
        metrics: LuminanceMetrics,
        temporal: TemporalLuminanceMetrics,
    ) -> CorrectionRecommendations:
        """Produces color grading recommendations based on arena constraints.

        Args:
            metrics: Aggregate luminance metrics across the video.
            temporal: Temporal consistency metrics across sampled frames.

        Returns:
            CorrectionRecommendations: Recommended parameters and notes.
        """
        need_level = self._determine_need_level(metrics=metrics)
        shadow_lift = self._calculate_shadow_lift(
            need=need_level, metrics=metrics
        )
        gamma = self._calculate_gamma(need=need_level, metrics=metrics)
        rolloff = self._calculate_highlight_rolloff(metrics=metrics)

        # Brightness: keep neutral if bright lights exist to prevent washed-out
        # arena blacks and highlight blowouts; slight lift if highlights are absent
        if metrics.p95 < 0.35 and need_level in (
            CorrectionNeedLevel.SEVERE,
            CorrectionNeedLevel.HIGH,
        ):
            brightness = 0.04
        else:
            brightness = 0.0

        # Contrast: boost to recover punch and avoid washed-out look from aggressive lift
        contrast = (
            1.15
            if shadow_lift >= 0.45
            else (1.08 if shadow_lift >= 0.20 else 1.0)
        )

        notes = self._build_recommendation_notes(
            need_level=need_level,
            metrics=metrics,
            temporal=temporal,
            rolloff=rolloff,
        )

        return CorrectionRecommendations(
            need_level=need_level,
            recommended_shadow_lift=shadow_lift,
            recommended_gamma=gamma,
            recommended_highlight_rolloff=rolloff,
            recommended_brightness=brightness,
            recommended_contrast=contrast,
            summary_notes=notes,
        )

    def _build_recommendation_notes(
        self,
        need_level: CorrectionNeedLevel,
        metrics: LuminanceMetrics,
        temporal: TemporalLuminanceMetrics,
        rolloff: float,
    ) -> list[str]:
        """Creates human-readable rationale notes for the recommendations.

        Args:
            need_level: Categorical need level.
            metrics: Aggregate luminance metrics.
            temporal: Temporal consistency metrics.
            rolloff: Recommended highlight rolloff.

        Returns:
            list[str]: Bullet-point rationale notes.
        """
        notes: list[str] = []
        shadow_pct = metrics.shadow_fraction * 100.0
        median_lum = metrics.median_luminance

        if need_level in (CorrectionNeedLevel.SEVERE, CorrectionNeedLevel.HIGH):
            notes.append(
                f'Laser tag arena footage is predominantly dark ({shadow_pct:.1f}% '
                f'shadows, median luminance {median_lum:.3f}). Aggressively lifting '
                'shadows and expanding dark-region gamma reveals otherwise '
                'imperceptible arena features, obstacles, and players.'
            )
        elif need_level == CorrectionNeedLevel.MODERATE:
            notes.append(
                f'Footage has notable shadow content ({shadow_pct:.1f}% shadows). '
                'Noticeable shadow lifting will improve player and arena visibility.'
            )
        else:
            notes.append(
                'Footage has balanced luminance distribution. Little or no '
                'color correction is required.'
            )

        if rolloff > 0.0:
            blown_pct = metrics.blown_fraction * 100.0
            notes.append(
                f'Bright localized lights detected (p95={metrics.p95:.2f}, '
                f'blown pixels={blown_pct:.2f}%). Highlight rolloff is recommended '
                'to prevent LED pack lights and laser beams from harsh clipping.'
            )

        if not temporal.is_temporally_stable:
            notes.append(
                f'High temporal lighting variation detected (std={temporal.std_frame_mean:.3f}). '
                'Because a single global correction applies to the whole video, '
                'adjustments should remain conservative to avoid overexposing brighter scenes.'
            )
        else:
            notes.append(
                'Temporal lighting profile is stable across the video; the recommended '
                'single setting will apply consistently throughout.'
            )

        return notes
