from pathlib import Path

import pytest

from lfdata.color_correction.color_analysis_types import (
    ColorAnalysisResult,
    CorrectionNeedLevel,
    CorrectionRecommendations,
    LuminanceMetrics,
    TemporalLuminanceMetrics,
)
from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.suggested_lut import (
    DEFAULT_SUGGESTED_LUT_SIZE,
    DEFAULT_SUGGESTED_LUT_TITLE,
    create_suggested_lut,
    save_suggested_lut,
)


def _sample_recommendations() -> CorrectionRecommendations:
    return CorrectionRecommendations(
        need_level=CorrectionNeedLevel.HIGH,
        recommended_shadow_lift=0.45,
        recommended_gamma=1.25,
        recommended_highlight_rolloff=0.35,
        recommended_brightness=0.02,
        recommended_contrast=1.10,
        summary_notes=['Sample recommendation'],
    )


def test_create_suggested_lut_invalid_size() -> None:
    recs = _sample_recommendations()
    with pytest.raises(ValueError, match='LUT dimension size must be >= 2'):
        create_suggested_lut(recommendations=recs, lut_size=1)


def test_create_suggested_lut_parameters() -> None:
    recs = _sample_recommendations()
    lut = create_suggested_lut(
        recommendations=recs,
        lut_size=17,
        title='Custom Test Grade',
    )
    assert lut.size == 17
    assert lut.title == 'Custom Test Grade'
    assert lut.shadows == 0.45
    assert lut.gamma == 1.25
    assert lut.highlight_rolloff == 0.35
    assert lut.brightness == 0.02
    assert lut.contrast == 1.10
    assert len(lut.table) == 17 * 17 * 17 * 3


def test_create_suggested_lut_defaults() -> None:
    recs = _sample_recommendations()
    lut = create_suggested_lut(recommendations=recs)
    assert lut.size == DEFAULT_SUGGESTED_LUT_SIZE
    assert lut.title == DEFAULT_SUGGESTED_LUT_TITLE


def test_save_suggested_lut_invalid_size(tmp_path: Path) -> None:
    recs = _sample_recommendations()
    target = tmp_path / 'out.cube'
    with pytest.raises(ValueError, match='LUT dimension size must be >= 2'):
        save_suggested_lut(
            recommendations=recs,
            file_path=target,
            lut_size=0,
        )


def test_save_suggested_lut_file_created(tmp_path: Path) -> None:
    recs = _sample_recommendations()
    cube_path = tmp_path / 'my_grade.cube'
    saved_path = save_suggested_lut(
        recommendations=recs,
        file_path=cube_path,
        lut_size=5,
        title='Arena Test LUT',
    )
    assert saved_path == cube_path
    assert cube_path.exists()

    content = cube_path.read_text(encoding='utf-8')
    assert 'TITLE "Arena Test LUT"' in content
    assert 'LUT_3D_SIZE 5' in content
    assert 'DOMAIN_MIN 0.0 0.0 0.0' in content
    assert 'DOMAIN_MAX 1.0 1.0 1.0' in content

    # Verify that the created file can be loaded back into Lut3D
    loaded_lut = Lut3D()
    loaded_lut.load_cube(cube_path)
    assert loaded_lut.size == 5
    assert loaded_lut.title == 'Arena Test LUT'


def test_save_suggested_lut_default_title(tmp_path: Path) -> None:
    recs = _sample_recommendations()
    cube_path = tmp_path / 'arena_match.cube'
    save_suggested_lut(
        recommendations=recs,
        file_path=cube_path,
        lut_size=5,
    )
    content = cube_path.read_text(encoding='utf-8')
    assert 'TITLE "Suggested Arena Grade - arena_match"' in content


def test_color_analysis_result_to_lut3d() -> None:
    recs = _sample_recommendations()
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
    result = ColorAnalysisResult(
        video_path='match_clip.mp4',
        duration_ms=5000,
        fps=30.0,
        frame_count=150,
        width=1280,
        height=720,
        sample_interval_ms=1000,
        global_metrics=metrics,
        temporal_metrics=temporal,
        recommendations=recs,
    )

    lut = result.to_lut3d(lut_size=17)
    assert lut.size == 17
    assert 'match_clip' in lut.title
    assert lut.shadows == recs.recommended_shadow_lift
