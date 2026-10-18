from pathlib import Path
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from lfdata.color_correction.color_analysis_types import (
    CorrectionNeedLevel,
    FrameLuminanceSample,
    LuminanceMetrics,
    TemporalLuminanceMetrics,
)
from lfdata.color_correction.color_analyzer import (
    DEFAULT_ANALYSIS_DOWNSAMPLE_WIDTH,
    DEFAULT_ANALYSIS_MAX_FRAMES,
    DEFAULT_ANALYSIS_SAMPLE_INTERVAL_MS,
    ColorAnalyzer,
)


def test_color_analyzer_init_defaults() -> None:
    analyzer = ColorAnalyzer()
    assert analyzer.sample_interval_ms == DEFAULT_ANALYSIS_SAMPLE_INTERVAL_MS
    assert analyzer.max_frames == DEFAULT_ANALYSIS_MAX_FRAMES
    assert analyzer.downsample_width == DEFAULT_ANALYSIS_DOWNSAMPLE_WIDTH


def test_color_analyzer_init_custom() -> None:
    analyzer = ColorAnalyzer(
        sample_interval_ms=500, max_frames=50, downsample_width=160
    )
    assert analyzer.sample_interval_ms == 500
    assert analyzer.max_frames == 50
    assert analyzer.downsample_width == 160


def test_color_analyzer_file_not_found() -> None:
    analyzer = ColorAnalyzer()
    with pytest.raises(FileNotFoundError, match='Video file not found'):
        analyzer.analyze(video_path='non_existent_video_path.mp4')


def test_color_analyzer_invalid_video(tmp_path: Path) -> None:
    invalid_file = tmp_path / 'corrupt.mp4'
    invalid_file.write_text('not a video file', encoding='utf-8')

    analyzer = ColorAnalyzer()
    with pytest.raises(ValueError, match='Could not open video file'):
        analyzer.analyze(video_path=invalid_file)


def test_read_video_metadata_invalid_properties() -> None:
    analyzer = ColorAnalyzer()
    mock_cap = MagicMock()
    mock_cap.get.side_effect = lambda prop: {
        cv2.CAP_PROP_FPS: 0.0,
        cv2.CAP_PROP_FRAME_COUNT: 0,
        cv2.CAP_PROP_FRAME_WIDTH: 1920,
        cv2.CAP_PROP_FRAME_HEIGHT: 1080,
    }.get(prop, 0.0)

    with pytest.raises(ValueError, match='Invalid video container properties'):
        analyzer._read_video_metadata(cap=mock_cap)


def test_read_video_metadata_zero_duration() -> None:
    analyzer = ColorAnalyzer()
    mock_cap = MagicMock()
    mock_cap.get.side_effect = lambda prop: {
        cv2.CAP_PROP_FPS: 100000.0,
        cv2.CAP_PROP_FRAME_COUNT: 1,
        cv2.CAP_PROP_FRAME_WIDTH: 1920,
        cv2.CAP_PROP_FRAME_HEIGHT: 1080,
    }.get(prop, 0.0)

    with pytest.raises(ValueError, match='Calculated video duration is 0 ms'):
        analyzer._read_video_metadata(cap=mock_cap)


def test_build_sample_indices_fewer_than_max_frames() -> None:
    analyzer = ColorAnalyzer(sample_interval_ms=1000, max_frames=10)
    samples = analyzer._build_sample_indices(
        duration_ms=4000, fps=30.0, total_frames=120
    )
    # Expected steps: 0, 1000, 2000, 3000, 4000
    times = [s[0] for s in samples]
    assert times == [0, 1000, 2000, 3000, 4000]
    indices = [s[1] for s in samples]
    assert indices == [0, 30, 60, 90, 119]


def test_build_sample_indices_more_than_max_frames() -> None:
    analyzer = ColorAnalyzer(sample_interval_ms=100, max_frames=4)
    samples = analyzer._build_sample_indices(
        duration_ms=10000, fps=10.0, total_frames=100
    )
    assert len(samples) == 4
    assert samples[0] == (0, 0)
    assert samples[-1][1] == 99


def test_compute_frame_luminance_rec709() -> None:
    analyzer = ColorAnalyzer(downsample_width=64)

    # Pure black frame
    black = np.zeros((32, 64, 3), dtype=np.uint8)
    lum_black = analyzer._compute_frame_luminance(frame=black)
    assert lum_black.shape == (32, 64)
    assert np.allclose(lum_black, 0.0)

    # Pure white frame
    white = np.full((32, 64, 3), 255, dtype=np.uint8)
    lum_white = analyzer._compute_frame_luminance(frame=white)
    assert np.allclose(lum_white, 1.0, atol=1e-3)

    # Pure Green in BGR is [0, 255, 0] -> Rec. 709 coeff 0.7152
    green = np.zeros((32, 64, 3), dtype=np.uint8)
    green[:, :, 1] = 255
    lum_green = analyzer._compute_frame_luminance(frame=green)
    assert np.allclose(lum_green, 0.7152, atol=1e-3)

    # Large frame downsampling test (e.g. 1920x1080 to downsample_width 64)
    large = np.zeros((1080, 1920, 3), dtype=np.uint8)
    lum_large = analyzer._compute_frame_luminance(frame=large)
    assert lum_large.shape[1] == 64
    assert lum_large.shape[0] == 36


def test_create_frame_sample() -> None:
    analyzer = ColorAnalyzer()
    lum_vals = np.array([0.02, 0.04, 0.10, 0.30, 0.85, 0.99], dtype=np.float32)
    sample = analyzer._create_frame_sample(
        timestamp_ms=3000, frame_idx=90, flat_lum=lum_vals
    )
    assert sample.timestamp_ms == 3000
    assert sample.frame_index == 90
    assert pytest.approx(sample.mean_luminance, rel=1e-3) == float(
        np.mean(lum_vals)
    )
    assert pytest.approx(sample.median_luminance, rel=1e-3) == float(
        np.median(lum_vals)
    )
    assert pytest.approx(sample.min_luminance) == 0.02
    assert pytest.approx(sample.max_luminance) == 0.99
    # Shadows (<0.15): 0.02, 0.04, 0.10 -> 3/6 = 0.5
    assert pytest.approx(sample.shadow_fraction) == 0.5
    # Highlights (>=0.70): 0.85, 0.99 -> 2/6 = 0.3333
    assert pytest.approx(sample.highlight_fraction, rel=1e-2) == 0.3333


def test_calculate_luminance_metrics_empty() -> None:
    analyzer = ColorAnalyzer()
    empty_arr = np.array([], dtype=np.float32)
    metrics = analyzer._calculate_luminance_metrics(lum_array=empty_arr)
    assert metrics.mean_luminance == 0.0
    assert metrics.shadow_fraction == 1.0
    assert metrics.deep_shadow_fraction == 1.0


def test_calculate_luminance_metrics_populated() -> None:
    analyzer = ColorAnalyzer()
    lum_vals = np.linspace(0.0, 1.0, 101, dtype=np.float32)
    metrics = analyzer._calculate_luminance_metrics(lum_array=lum_vals)

    assert pytest.approx(metrics.mean_luminance, abs=0.01) == 0.5
    assert pytest.approx(metrics.median_luminance, abs=0.01) == 0.5
    assert pytest.approx(metrics.min_luminance, abs=1e-4) == 0.0
    assert pytest.approx(metrics.max_luminance, abs=1e-4) == 1.0
    assert pytest.approx(metrics.p10, abs=0.02) == 0.10
    assert pytest.approx(metrics.p95, abs=0.02) == 0.95
    assert pytest.approx(metrics.deep_shadow_fraction, abs=0.02) == 0.05
    assert pytest.approx(metrics.shadow_fraction, abs=0.02) == 0.15
    assert pytest.approx(metrics.highlight_fraction, abs=0.02) == 0.30
    assert pytest.approx(metrics.blown_fraction, abs=0.02) == 0.06
    assert pytest.approx(metrics.dynamic_range, abs=0.03) == 0.85


def test_calculate_temporal_metrics_empty() -> None:
    analyzer = ColorAnalyzer()
    temporal = analyzer._calculate_temporal_metrics(frame_samples=[])
    assert temporal.frames_analyzed == 0
    assert temporal.mean_frame_mean == 0.0
    assert temporal.is_temporally_stable is True


def test_calculate_temporal_metrics_stable_and_unstable() -> None:
    analyzer = ColorAnalyzer()
    # Stable samples (very small frame variance)
    stable_samples = [
        FrameLuminanceSample(
            timestamp_ms=i * 1000,
            frame_index=i * 30,
            mean_luminance=0.10 + (0.005 * (i % 2)),
            median_luminance=0.08,
            min_luminance=0.0,
            max_luminance=0.9,
            shadow_fraction=0.7,
            highlight_fraction=0.02,
        )
        for i in range(5)
    ]
    stable_res = analyzer._calculate_temporal_metrics(
        frame_samples=stable_samples
    )
    assert stable_res.frames_analyzed == 5
    assert stable_res.is_temporally_stable is True

    # Unstable samples (large variance across time)
    unstable_samples = [
        FrameLuminanceSample(
            timestamp_ms=0,
            frame_index=0,
            mean_luminance=0.02,
            median_luminance=0.01,
            min_luminance=0.0,
            max_luminance=0.1,
            shadow_fraction=0.99,
            highlight_fraction=0.0,
        ),
        FrameLuminanceSample(
            timestamp_ms=1000,
            frame_index=30,
            mean_luminance=0.60,
            median_luminance=0.55,
            min_luminance=0.1,
            max_luminance=1.0,
            shadow_fraction=0.05,
            highlight_fraction=0.4,
        ),
    ]
    unstable_res = analyzer._calculate_temporal_metrics(
        frame_samples=unstable_samples
    )
    assert unstable_res.is_temporally_stable is False


def test_determine_need_level_all_branches() -> None:
    analyzer = ColorAnalyzer()

    # SEVERE
    severe_m = LuminanceMetrics(
        mean_luminance=0.03,
        median_luminance=0.02,
        p10=0.0,
        p25=0.01,
        p75=0.04,
        p90=0.08,
        p95=0.15,
        p99=0.5,
        min_luminance=0.0,
        max_luminance=0.8,
        std_luminance=0.05,
        deep_shadow_fraction=0.75,
        shadow_fraction=0.88,
        midtone_fraction=0.10,
        highlight_fraction=0.02,
        blown_fraction=0.0,
        dynamic_range=0.15,
    )
    assert (
        analyzer._determine_need_level(metrics=severe_m)
        == CorrectionNeedLevel.SEVERE
    )

    # HIGH
    high_m = LuminanceMetrics(
        mean_luminance=0.08,
        median_luminance=0.06,
        p10=0.01,
        p25=0.03,
        p75=0.12,
        p90=0.25,
        p95=0.5,
        p99=0.9,
        min_luminance=0.0,
        max_luminance=0.95,
        std_luminance=0.09,
        deep_shadow_fraction=0.35,
        shadow_fraction=0.68,
        midtone_fraction=0.28,
        highlight_fraction=0.04,
        blown_fraction=0.003,
        dynamic_range=0.49,
    )
    assert (
        analyzer._determine_need_level(metrics=high_m)
        == CorrectionNeedLevel.HIGH
    )

    # MODERATE
    mod_m = LuminanceMetrics(
        mean_luminance=0.16,
        median_luminance=0.12,
        p10=0.03,
        p25=0.07,
        p75=0.22,
        p90=0.35,
        p95=0.55,
        p99=0.7,
        min_luminance=0.0,
        max_luminance=0.8,
        std_luminance=0.10,
        deep_shadow_fraction=0.15,
        shadow_fraction=0.42,
        midtone_fraction=0.55,
        highlight_fraction=0.03,
        blown_fraction=0.0,
        dynamic_range=0.52,
    )
    assert (
        analyzer._determine_need_level(metrics=mod_m)
        == CorrectionNeedLevel.MODERATE
    )

    # LOW
    low_m = LuminanceMetrics(
        mean_luminance=0.22,
        median_luminance=0.20,
        p10=0.06,
        p25=0.12,
        p75=0.28,
        p90=0.40,
        p95=0.50,
        p99=0.65,
        min_luminance=0.01,
        max_luminance=0.70,
        std_luminance=0.10,
        deep_shadow_fraction=0.05,
        shadow_fraction=0.25,
        midtone_fraction=0.72,
        highlight_fraction=0.03,
        blown_fraction=0.0,
        dynamic_range=0.44,
    )
    assert (
        analyzer._determine_need_level(metrics=low_m) == CorrectionNeedLevel.LOW
    )

    # NONE
    none_m = LuminanceMetrics(
        mean_luminance=0.35,
        median_luminance=0.32,
        p10=0.15,
        p25=0.22,
        p75=0.45,
        p90=0.60,
        p95=0.70,
        p99=0.80,
        min_luminance=0.05,
        max_luminance=0.85,
        std_luminance=0.12,
        deep_shadow_fraction=0.01,
        shadow_fraction=0.10,
        midtone_fraction=0.85,
        highlight_fraction=0.05,
        blown_fraction=0.0,
        dynamic_range=0.55,
    )
    assert (
        analyzer._determine_need_level(metrics=none_m)
        == CorrectionNeedLevel.NONE
    )


def test_recommendations_generation_laser_tag_scenario() -> None:
    analyzer = ColorAnalyzer()
    metrics = LuminanceMetrics(
        mean_luminance=0.06,
        median_luminance=0.03,
        p10=0.005,
        p25=0.015,
        p75=0.08,
        p90=0.20,
        p95=0.92,
        p99=0.99,
        min_luminance=0.0,
        max_luminance=1.0,
        std_luminance=0.12,
        deep_shadow_fraction=0.68,
        shadow_fraction=0.82,
        midtone_fraction=0.15,
        highlight_fraction=0.03,
        blown_fraction=0.015,
        dynamic_range=0.915,
    )
    temporal = TemporalLuminanceMetrics(
        frames_analyzed=20,
        mean_frame_mean=0.06,
        std_frame_mean=0.08,
        min_frame_mean=0.02,
        max_frame_mean=0.22,
        temporal_variation=1.33,
        is_temporally_stable=False,
    )

    recs = analyzer._generate_recommendations(
        metrics=metrics, temporal=temporal
    )
    assert recs.need_level == CorrectionNeedLevel.SEVERE
    assert recs.recommended_shadow_lift >= 0.50
    assert recs.recommended_gamma == 1.35
    assert recs.recommended_highlight_rolloff == 0.50
    assert recs.recommended_contrast == 1.10
    assert len(recs.summary_notes) >= 3


def test_end_to_end_analyze_with_synthetic_video(tmp_path: Path) -> None:
    video_file = tmp_path / 'synthetic_arena.mp4'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(video_file), fourcc, 10.0, (160, 120))

    # Create 10 frames: 8 dark frames with a small bright LED, 2 brighter frames
    for i in range(10):
        frame = np.full((120, 160, 3), 15, dtype=np.uint8)
        if i % 2 == 0:
            # Add bright LED patch in center
            frame[50:60, 70:80] = 255
        out.write(frame)
    out.release()

    analyzer = ColorAnalyzer(
        sample_interval_ms=200, max_frames=10, downsample_width=80
    )
    result = analyzer.analyze(video_path=video_file, include_frame_samples=True)

    assert result.duration_ms == 1000
    assert result.width == 160
    assert result.height == 120
    assert result.fps == 10.0
    assert result.frame_count == 10
    assert len(result.frame_samples) > 0
    assert result.global_metrics.mean_luminance > 0.0
    assert result.recommendations.need_level in (
        CorrectionNeedLevel.SEVERE,
        CorrectionNeedLevel.HIGH,
    )
    assert result.recommendations.recommended_shadow_lift > 0.0
