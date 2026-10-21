"""Tests for VideoExporter FFmpeg export helper."""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.video_exporter import VideoExporter


def test_video_exporter_init() -> None:
    exporter = VideoExporter(ffmpeg_bin='my_ffmpeg', ffprobe_bin='my_ffprobe')
    assert exporter.ffmpeg_bin == 'my_ffmpeg'
    assert exporter.ffprobe_bin == 'my_ffprobe'


def test_probe_has_audio_file_not_found(tmp_path: Path) -> None:
    exporter = VideoExporter()
    non_existent = tmp_path / 'non_existent.mp4'
    with pytest.raises(FileNotFoundError):
        exporter.probe_has_audio(video_path=non_existent)


def test_probe_has_audio_true(tmp_path: Path) -> None:
    exporter = VideoExporter()
    video_file = tmp_path / 'sample.mp4'
    video_file.write_text('dummy')

    fake_output = json.dumps({'streams': [{'codec_type': 'audio'}]})
    mock_res = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=fake_output
    )

    with patch('subprocess.run', return_value=mock_res) as mock_run:
        has_audio = exporter.probe_has_audio(video_path=video_file)
        assert has_audio is True
        mock_run.assert_called_once()


def test_probe_has_audio_false(tmp_path: Path) -> None:
    exporter = VideoExporter()
    video_file = tmp_path / 'sample.mp4'
    video_file.write_text('dummy')

    fake_output = json.dumps({'streams': []})
    mock_res = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=fake_output
    )

    with patch('subprocess.run', return_value=mock_res):
        has_audio = exporter.probe_has_audio(video_path=video_file)
        assert has_audio is False


def test_probe_has_audio_error_handling(tmp_path: Path) -> None:
    exporter = VideoExporter()
    video_file = tmp_path / 'sample.mp4'
    video_file.write_text('dummy')

    with patch(
        'subprocess.run',
        side_effect=subprocess.CalledProcessError(1, 'ffprobe'),
    ):
        assert exporter.probe_has_audio(video_path=video_file) is False


def test_build_filter_complex_empty_ranges() -> None:
    exporter = VideoExporter()
    with pytest.raises(ValueError, match='At least one TimeRange'):
        exporter.build_filter_complex(ranges=[])


def test_build_filter_complex_single_range_no_audio() -> None:
    exporter = VideoExporter()
    ranges = [TimeRange(start_ms=1500, end_ms=4500)]
    fc = exporter.build_filter_complex(ranges=ranges, has_audio=False)

    assert '[0:v]trim=start=1.500:end=4.500,setpts=PTS-STARTPTS[v0]' in fc
    assert '[0:a]' not in fc
    assert '[v0]concat=n=1:v=1:a=0[outv]' in fc


def test_build_filter_complex_multiple_ranges_with_audio() -> None:
    exporter = VideoExporter()
    ranges = [
        TimeRange(start_ms=1000, end_ms=3000),
        TimeRange(start_ms=6500, end_ms=9250),
    ]
    fc = exporter.build_filter_complex(ranges=ranges, has_audio=True)

    assert '[0:v]trim=start=1.000:end=3.000,setpts=PTS-STARTPTS[v0]' in fc
    assert '[0:a]atrim=start=1.000:end=3.000,asetpts=PTS-STARTPTS[a0]' in fc
    assert '[0:v]trim=start=6.500:end=9.250,setpts=PTS-STARTPTS[v1]' in fc
    assert '[0:a]atrim=start=6.500:end=9.250,asetpts=PTS-STARTPTS[a1]' in fc
    assert '[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]' in fc


def test_build_filter_complex_with_lut_and_noise() -> None:
    exporter = VideoExporter()
    ranges = [TimeRange(start_ms=500, end_ms=2500)]
    fc = exporter.build_filter_complex(
        ranges=ranges,
        has_audio=False,
        apply_filters=True,
        lut_path='C:/test/custom.cube',
        noise_reduction_filter='hqdn3d=4.0:3.0:6.0:4.5',
    )

    assert '[basev]' in fc
    assert "lut3d=file='C\\:/test/custom.cube'" in fc
    assert 'hqdn3d=4.0:3.0:6.0:4.5' in fc
    assert '[outv]' in fc


def test_build_filter_complex_apply_filters_empty() -> None:
    exporter = VideoExporter()
    ranges = [TimeRange(start_ms=500, end_ms=2500)]
    fc = exporter.build_filter_complex(
        ranges=ranges,
        has_audio=False,
        apply_filters=True,
        lut_path=None,
        noise_reduction_filter=None,
    )
    assert '[outv]' in fc
    assert '[basev]' not in fc


def test_build_ffmpeg_command() -> None:
    exporter = VideoExporter()
    ranges = [TimeRange(start_ms=1000, end_ms=2000)]
    cmd = exporter.build_ffmpeg_command(
        source_path='raw.mp4',
        output_path='out.mp4',
        ranges=ranges,
        has_audio=True,
        overwrite=True,
    )

    assert cmd[0] == 'ffmpeg'
    assert '-y' in cmd
    assert '-i' in cmd
    assert 'raw.mp4' in cmd
    assert '-filter_complex' in cmd
    assert '-map' in cmd
    assert '[outv]' in cmd
    assert '[outa]' in cmd
    assert 'out.mp4' in cmd


def test_export_video_file_not_found(tmp_path: Path) -> None:
    exporter = VideoExporter()
    non_existent = tmp_path / 'missing.mp4'
    ranges = [TimeRange(start_ms=100, end_ms=500)]
    with pytest.raises(FileNotFoundError):
        exporter.export_video(
            source_path=non_existent,
            output_path=tmp_path / 'out.mp4',
            ranges=ranges,
        )


def test_export_video_empty_ranges(tmp_path: Path) -> None:
    exporter = VideoExporter()
    source = tmp_path / 'source.mp4'
    source.write_text('dummy')
    with pytest.raises(ValueError, match='zero selected ranges'):
        exporter.export_video(
            source_path=source,
            output_path=tmp_path / 'out.mp4',
            ranges=[],
        )


def test_export_video_success(tmp_path: Path) -> None:
    exporter = VideoExporter()
    source = tmp_path / 'source.mp4'
    source.write_text('dummy')
    output = tmp_path / 'out.mp4'
    ranges = [TimeRange(start_ms=1000, end_ms=2000)]

    mock_proc = MagicMock()
    mock_proc.poll.side_effect = [0]
    mock_proc.communicate.return_value = ('', '')
    mock_proc.returncode = 0

    with (
        patch('subprocess.Popen', return_value=mock_proc) as mock_popen,
        patch.object(exporter, 'probe_has_audio', return_value=False),
    ):
        exporter.export_video(
            source_path=source,
            output_path=output,
            ranges=ranges,
        )
        mock_popen.assert_called_once()


def test_export_video_failure(tmp_path: Path) -> None:
    exporter = VideoExporter()
    source = tmp_path / 'source.mp4'
    source.write_text('dummy')
    output = tmp_path / 'out.mp4'
    ranges = [TimeRange(start_ms=1000, end_ms=2000)]

    mock_proc = MagicMock()
    mock_proc.poll.side_effect = [0]
    mock_proc.communicate.return_value = ('', 'Encoding error')
    mock_proc.returncode = 1

    with (
        patch('subprocess.Popen', return_value=mock_proc),
        patch.object(exporter, 'probe_has_audio', return_value=False),
        pytest.raises(RuntimeError, match='FFmpeg export failed with code 1'),
    ):
        exporter.export_video(
            source_path=source,
            output_path=output,
            ranges=ranges,
        )


def test_export_video_cancellation(tmp_path: Path) -> None:
    exporter = VideoExporter()
    source = tmp_path / 'source.mp4'
    source.write_text('dummy')
    output = tmp_path / 'out.mp4'
    output.write_text('partial data')
    ranges = [TimeRange(start_ms=1000, end_ms=2000)]

    cancel_event = threading.Event()
    cancel_event.set()

    mock_proc = MagicMock()
    mock_proc.poll.return_value = None

    with (
        patch('subprocess.Popen', return_value=mock_proc),
        patch.object(exporter, 'probe_has_audio', return_value=False),
        pytest.raises(RuntimeError, match='Video export was cancelled'),
    ):
        exporter.export_video(
            source_path=source,
            output_path=output,
            ranges=ranges,
            cancel_event=cancel_event,
        )
        mock_proc.kill.assert_called_once()
        assert not output.exists()
