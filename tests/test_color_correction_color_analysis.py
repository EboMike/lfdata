import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from lfdata.color_correction.color_analysis import (
    build_arg_parser,
    format_json_report,
    format_text_report,
    main,
    run_analysis,
)
from lfdata.color_correction.color_analysis_types import (
    AnalysisOutputFormat,
    ColorAnalysisResult,
    CorrectionNeedLevel,
    CorrectionRecommendations,
    FrameLuminanceSample,
    LuminanceMetrics,
    TemporalLuminanceMetrics,
)


def _create_sample_result() -> ColorAnalysisResult:
    metrics = LuminanceMetrics(
        mean_luminance=0.0823,
        median_luminance=0.0412,
        p10=0.0081,
        p25=0.0182,
        p75=0.0954,
        p90=0.2201,
        p95=0.4102,
        p99=0.8804,
        min_luminance=0.0001,
        max_luminance=0.9982,
        std_luminance=0.1154,
        deep_shadow_fraction=0.582,
        shadow_fraction=0.814,
        midtone_fraction=0.158,
        highlight_fraction=0.028,
        blown_fraction=0.006,
        dynamic_range=0.4021,
    )
    temporal = TemporalLuminanceMetrics(
        frames_analyzed=60,
        mean_frame_mean=0.0823,
        std_frame_mean=0.0182,
        min_frame_mean=0.0451,
        max_frame_mean=0.1254,
        temporal_variation=0.2211,
        is_temporally_stable=True,
    )
    recs = CorrectionRecommendations(
        need_level=CorrectionNeedLevel.HIGH,
        recommended_shadow_lift=0.450,
        recommended_gamma=1.250,
        recommended_highlight_rolloff=0.350,
        recommended_brightness=0.000,
        recommended_contrast=1.100,
        summary_notes=[
            'Dark arena footage',
            'Bright LEDs detected; rolloff advised',
        ],
    )
    sample = FrameLuminanceSample(
        timestamp_ms=2000,
        frame_index=60,
        mean_luminance=0.085,
        median_luminance=0.042,
        min_luminance=0.0,
        max_luminance=0.99,
        shadow_fraction=0.80,
        highlight_fraction=0.03,
    )
    return ColorAnalysisResult(
        video_path='sample_video.mp4',
        duration_ms=120000,
        fps=30.0,
        frame_count=3600,
        width=1920,
        height=1080,
        sample_interval_ms=2000,
        global_metrics=metrics,
        temporal_metrics=temporal,
        recommendations=recs,
        frame_samples=[sample],
    )


def test_build_arg_parser_defaults() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(['my_clip.mp4'])
    assert args.video == 'my_clip.mp4'
    assert args.input_video is None
    assert args.sample_interval_ms == 2000
    assert args.max_frames == 120
    assert args.format == 'text'
    assert args.output is None
    assert args.verbose is False


def test_build_arg_parser_custom_flags() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            '--input',
            'arena.mp4',
            '--sample_interval_ms',
            '1500',
            '--max_frames',
            '50',
            '--format',
            'json',
            '--output',
            'out.json',
            '--verbose',
        ]
    )
    assert args.input_video == 'arena.mp4'
    assert args.sample_interval_ms == 1500
    assert args.max_frames == 50
    assert args.format == 'json'
    assert args.output == 'out.json'
    assert args.verbose is True


def test_format_text_report_non_verbose() -> None:
    result = _create_sample_result()
    report = format_text_report(result=result, verbose=False)
    assert 'COLOR ANALYSIS REPORT: sample_video.mp4' in report
    assert 'Resolution:       1920x1080' in report
    assert 'Duration:         120.0s (120000 ms)' in report
    assert 'Mean Luminance:   0.0823' in report
    assert 'Shadows (<15%):' in report
    assert '81.4%' in report
    assert 'Need Level:       HIGH' in report
    assert 'Shadows Lift:       +0.450' in report
    assert 'Per-Frame Samples:' not in report


def test_format_text_report_verbose() -> None:
    result = _create_sample_result()
    report = format_text_report(result=result, verbose=True)
    assert 'Per-Frame Samples:' in report
    assert 'Timestamp(ms) | FrameIdx | MeanLum | MedianLum | Shadow%' in report
    assert '2000' in report


def test_format_json_report() -> None:
    result = _create_sample_result()
    json_text = format_json_report(result=result)
    parsed = json.loads(json_text)
    assert parsed['video_path'] == 'sample_video.mp4'
    assert parsed['duration_ms'] == 120000
    assert parsed['global_metrics']['mean_luminance'] == 0.0823
    assert parsed['recommendations']['need_level'] == 'high'


def _create_synthetic_test_video(file_path: Path) -> None:
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(file_path), fourcc, 10.0, (80, 60))
    for _ in range(5):
        frame = np.full((60, 80, 3), 20, dtype=np.uint8)
        out.write(frame)
    out.release()


def test_run_analysis_text(tmp_path: Path) -> None:
    video_file = tmp_path / 'test_clip.mp4'
    _create_synthetic_test_video(video_file)

    buf = io.StringIO()
    exit_code = run_analysis(
        video_path=str(video_file),
        sample_interval_ms=200,
        max_frames=5,
        output_format=AnalysisOutputFormat.TEXT,
        output_stream=buf,
        verbose=False,
    )
    assert exit_code == 0
    content = buf.getvalue()
    assert 'COLOR ANALYSIS REPORT' in content
    assert 'Video Properties:' in content


def test_run_analysis_json(tmp_path: Path) -> None:
    video_file = tmp_path / 'test_clip.mp4'
    _create_synthetic_test_video(video_file)

    buf = io.StringIO()
    exit_code = run_analysis(
        video_path=str(video_file),
        sample_interval_ms=200,
        max_frames=5,
        output_format=AnalysisOutputFormat.JSON,
        output_stream=buf,
        verbose=True,
    )
    assert exit_code == 0
    data = json.loads(buf.getvalue())
    assert data['duration_ms'] == 500
    assert 'frame_samples' in data


def test_main_missing_video() -> None:
    with patch.object(sys, 'argv', ['color_analysis']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_invalid_format(tmp_path: Path) -> None:
    video_file = tmp_path / 'dummy.mp4'
    with patch.object(
        sys, 'argv', ['color_analysis', str(video_file), '--format', 'invalid']
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code != 0


def test_main_file_not_found() -> None:
    with patch.object(
        sys, 'argv', ['color_analysis', 'missing_non_existent.mp4']
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_to_output_file(tmp_path: Path) -> None:
    video_file = tmp_path / 'test_clip.mp4'
    _create_synthetic_test_video(video_file)
    out_file = tmp_path / 'report.txt'

    with patch.object(
        sys,
        'argv',
        [
            'color_analysis',
            str(video_file),
            '--output',
            str(out_file),
            '--sample_interval_ms',
            '200',
            '--max_frames',
            '5',
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    assert out_file.exists()
    content = out_file.read_text(encoding='utf-8')
    assert 'COLOR ANALYSIS REPORT' in content
