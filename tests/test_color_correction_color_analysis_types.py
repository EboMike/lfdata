import pytest

from lfdata.color_correction.color_analysis_types import (
    AnalysisOutputFormat,
    ColorAnalysisResult,
    CorrectionNeedLevel,
    CorrectionRecommendations,
    FrameLuminanceSample,
    LuminanceMetrics,
    TemporalLuminanceMetrics,
)


def test_correction_need_level_values() -> None:
    assert CorrectionNeedLevel.NONE.value == 'none'
    assert CorrectionNeedLevel.LOW.value == 'low'
    assert CorrectionNeedLevel.MODERATE.value == 'moderate'
    assert CorrectionNeedLevel.HIGH.value == 'high'
    assert CorrectionNeedLevel.SEVERE.value == 'severe'


def test_analysis_output_format_from_str() -> None:
    assert AnalysisOutputFormat.from_str('text') == AnalysisOutputFormat.TEXT
    assert AnalysisOutputFormat.from_str('TEXT') == AnalysisOutputFormat.TEXT
    assert AnalysisOutputFormat.from_str('json') == AnalysisOutputFormat.JSON
    assert (
        AnalysisOutputFormat.from_str('  JSON  ') == AnalysisOutputFormat.JSON
    )

    with pytest.raises(ValueError, match='Unknown output format'):
        AnalysisOutputFormat.from_str('invalid_format')


def test_frame_luminance_sample_to_dict() -> None:
    sample = FrameLuminanceSample(
        timestamp_ms=2500,
        frame_index=75,
        mean_luminance=0.08234,
        median_luminance=0.04126,
        min_luminance=0.0012,
        max_luminance=0.9854,
        shadow_fraction=0.7812,
        highlight_fraction=0.0345,
    )
    assert sample.timestamp_ms == 2500
    assert sample.frame_index == 75

    data = sample.to_dict()
    assert data['timestamp_ms'] == 2500
    assert data['frame_index'] == 75
    assert data['mean_luminance'] == 0.0823
    assert data['median_luminance'] == 0.0413
    assert data['min_luminance'] == 0.0012
    assert data['max_luminance'] == 0.9854
    assert data['shadow_fraction'] == 0.7812
    assert data['highlight_fraction'] == 0.0345


def test_luminance_metrics_to_dict() -> None:
    metrics = LuminanceMetrics(
        mean_luminance=0.1256,
        median_luminance=0.0654,
        p10=0.0123,
        p25=0.0345,
        p75=0.1567,
        p90=0.3123,
        p95=0.5678,
        p99=0.8912,
        min_luminance=0.0,
        max_luminance=1.0,
        std_luminance=0.1432,
        deep_shadow_fraction=0.4512,
        shadow_fraction=0.6823,
        midtone_fraction=0.2812,
        highlight_fraction=0.0365,
        blown_fraction=0.0054,
        dynamic_range=0.5555,
    )
    data = metrics.to_dict()
    assert data['mean_luminance'] == 0.1256
    assert data['median_luminance'] == 0.0654
    assert data['p10'] == 0.0123
    assert data['p25'] == 0.0345
    assert data['p75'] == 0.1567
    assert data['p90'] == 0.3123
    assert data['p95'] == 0.5678
    assert data['p99'] == 0.8912
    assert data['min_luminance'] == 0.0
    assert data['max_luminance'] == 1.0
    assert data['std_luminance'] == 0.1432
    assert data['deep_shadow_fraction'] == 0.4512
    assert data['shadow_fraction'] == 0.6823
    assert data['midtone_fraction'] == 0.2812
    assert data['highlight_fraction'] == 0.0365
    assert data['blown_fraction'] == 0.0054
    assert data['dynamic_range'] == 0.5555


def test_temporal_luminance_metrics_to_dict() -> None:
    temporal = TemporalLuminanceMetrics(
        frames_analyzed=45,
        mean_frame_mean=0.1122,
        std_frame_mean=0.0234,
        min_frame_mean=0.0678,
        max_frame_mean=0.1654,
        temporal_variation=0.2085,
        is_temporally_stable=True,
    )
    data = temporal.to_dict()
    assert data['frames_analyzed'] == 45
    assert data['mean_frame_mean'] == 0.1122
    assert data['std_frame_mean'] == 0.0234
    assert data['min_frame_mean'] == 0.0678
    assert data['max_frame_mean'] == 0.1654
    assert data['temporal_variation'] == 0.2085
    assert data['is_temporally_stable'] is True


def test_correction_recommendations_to_dict() -> None:
    recs = CorrectionRecommendations(
        need_level=CorrectionNeedLevel.HIGH,
        recommended_shadow_lift=0.456,
        recommended_gamma=1.25,
        recommended_highlight_rolloff=0.35,
        recommended_brightness=0.0,
        recommended_contrast=1.1,
        summary_notes=['Dark arena scene', 'High LED contrast'],
    )
    data = recs.to_dict()
    assert data['need_level'] == 'high'
    assert data['recommended_shadow_lift'] == 0.456
    assert data['recommended_gamma'] == 1.25
    assert data['recommended_highlight_rolloff'] == 0.35
    assert data['recommended_brightness'] == 0.0
    assert data['recommended_contrast'] == 1.1
    assert data['summary_notes'] == ['Dark arena scene', 'High LED contrast']


def test_color_analysis_result_to_dict() -> None:
    metrics = LuminanceMetrics(
        mean_luminance=0.1,
        median_luminance=0.05,
        p10=0.01,
        p25=0.02,
        p75=0.15,
        p90=0.3,
        p95=0.5,
        p99=0.8,
        min_luminance=0.0,
        max_luminance=1.0,
        std_luminance=0.12,
        deep_shadow_fraction=0.5,
        shadow_fraction=0.7,
        midtone_fraction=0.25,
        highlight_fraction=0.05,
        blown_fraction=0.01,
        dynamic_range=0.49,
    )
    temporal = TemporalLuminanceMetrics(
        frames_analyzed=10,
        mean_frame_mean=0.1,
        std_frame_mean=0.02,
        min_frame_mean=0.07,
        max_frame_mean=0.13,
        temporal_variation=0.2,
        is_temporally_stable=True,
    )
    recs = CorrectionRecommendations(
        need_level=CorrectionNeedLevel.HIGH,
        recommended_shadow_lift=0.45,
        recommended_gamma=1.25,
        recommended_highlight_rolloff=0.35,
        recommended_brightness=0.0,
        recommended_contrast=1.1,
        summary_notes=['Test note'],
    )
    sample = FrameLuminanceSample(
        timestamp_ms=0,
        frame_index=0,
        mean_luminance=0.1,
        median_luminance=0.05,
        min_luminance=0.0,
        max_luminance=1.0,
        shadow_fraction=0.7,
        highlight_fraction=0.05,
    )
    result = ColorAnalysisResult(
        video_path='test_arena.mp4',
        duration_ms=60000,
        fps=30.0,
        frame_count=1800,
        width=1920,
        height=1080,
        sample_interval_ms=2000,
        global_metrics=metrics,
        temporal_metrics=temporal,
        recommendations=recs,
        frame_samples=[sample],
    )
    data = result.to_dict()
    assert data['video_path'] == 'test_arena.mp4'
    assert data['duration_ms'] == 60000
    assert data['fps'] == 30.0
    assert data['frame_count'] == 1800
    assert data['width'] == 1920
    assert data['height'] == 1080
    assert data['sample_interval_ms'] == 2000
    assert 'global_metrics' in data
    assert 'temporal_metrics' in data
    assert 'recommendations' in data
    assert 'frame_samples' in data
    assert len(data['frame_samples']) == 1


def test_color_analysis_result_to_dict_without_samples() -> None:
    metrics = LuminanceMetrics(
        mean_luminance=0.2,
        median_luminance=0.18,
        p10=0.05,
        p25=0.1,
        p75=0.25,
        p90=0.4,
        p95=0.5,
        p99=0.6,
        min_luminance=0.0,
        max_luminance=0.7,
        std_luminance=0.08,
        deep_shadow_fraction=0.1,
        shadow_fraction=0.3,
        midtone_fraction=0.65,
        highlight_fraction=0.05,
        blown_fraction=0.0,
        dynamic_range=0.45,
    )
    temporal = TemporalLuminanceMetrics(
        frames_analyzed=5,
        mean_frame_mean=0.2,
        std_frame_mean=0.01,
        min_frame_mean=0.19,
        max_frame_mean=0.21,
        temporal_variation=0.05,
        is_temporally_stable=True,
    )
    recs = CorrectionRecommendations(
        need_level=CorrectionNeedLevel.LOW,
        recommended_shadow_lift=0.1,
        recommended_gamma=1.0,
        recommended_highlight_rolloff=0.0,
        recommended_brightness=0.0,
        recommended_contrast=1.0,
        summary_notes=['Balanced'],
    )
    result = ColorAnalysisResult(
        video_path='clip.mp4',
        duration_ms=10000,
        fps=25.0,
        frame_count=250,
        width=1280,
        height=720,
        sample_interval_ms=2000,
        global_metrics=metrics,
        temporal_metrics=temporal,
        recommendations=recs,
        frame_samples=[],
    )
    data = result.to_dict()
    assert 'frame_samples' not in data
