from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from lfdata.video.hud_merger import (
    HudMerger,
    HudMergeOptions,
    VideoMetadata,
)


def test_video_metadata_initialization():
    meta = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=60000,
        has_audio=True,
    )
    assert meta.width == 1920
    assert meta.height == 1080
    assert meta.duration_ms == 60000
    assert meta.has_audio is True


def test_hud_merge_options_defaults():
    options = HudMergeOptions(
        gopro_path=Path('gopro.mp4'),
        hud_path=Path('hud.mp4'),
        hud_alpha_path=Path('alpha.mp4'),
        output_path=Path('out.mp4'),
    )
    assert options.fade_duration_ms == 5000
    assert options.crf == 18
    assert options.preset == 'medium'
    assert options.overwrite is True


def test_probe_video_file_not_found():
    merger = HudMerger()
    with pytest.raises(FileNotFoundError):
        merger.probe_video(file_path=Path('non_existent_file.mp4'))


def test_probe_video_ffprobe_error():
    merger = HudMerger()
    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('subprocess.run', side_effect=FileNotFoundError('No ffprobe')),
    ):
        with pytest.raises(RuntimeError, match='Failed to probe video file'):
            merger.probe_video(file_path=Path('test.mp4'))


def test_parse_probe_json_valid_video_and_audio():
    raw_json = """
    {
        "streams": [
            {
                "codec_type": "video",
                "width": 3840,
                "height": 2160,
                "duration": "125.500"
            },
            {
                "codec_type": "audio",
                "duration": "125.500"
            }
        ],
        "format": {
            "duration": "125.500"
        }
    }
    """
    merger = HudMerger()
    meta = merger._parse_probe_json(raw_json=raw_json)
    assert meta.width == 3840
    assert meta.height == 2160
    assert meta.duration_ms == 125500
    assert meta.has_audio is True


def test_parse_probe_json_fallback_format_duration_and_no_audio():
    raw_json = """
    {
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "duration": "N/A"
            }
        ],
        "format": {
            "duration": "45.25"
        }
    }
    """
    merger = HudMerger()
    meta = merger._parse_probe_json(raw_json=raw_json)
    assert meta.width == 1920
    assert meta.height == 1080
    assert meta.duration_ms == 45250
    assert meta.has_audio is False


def test_parse_probe_json_invalid_json():
    merger = HudMerger()
    with pytest.raises(RuntimeError, match='Invalid ffprobe JSON output'):
        merger._parse_probe_json(raw_json='invalid json')


def test_parse_probe_json_no_video_stream():
    raw_json = """
    {
        "streams": [
            {
                "codec_type": "audio"
            }
        ]
    }
    """
    merger = HudMerger()
    with pytest.raises(RuntimeError, match='No video stream found'):
        merger._parse_probe_json(raw_json=raw_json)


def test_extract_duration_ms_missing_and_invalid():
    merger = HudMerger()
    # Missing duration
    assert (
        merger._extract_duration_ms(
            stream_info={},
            format_info={},
        )
        == 0
    )
    # Invalid duration string
    assert (
        merger._extract_duration_ms(
            stream_info={'duration': 'invalid'},
            format_info={},
        )
        == 0
    )


def test_calculate_sync_parameters_gopro_shorter():
    merger = HudMerger()
    final_ms, fade_dur_ms, fade_st_ms = merger.calculate_sync_parameters(
        gopro_duration_ms=60000,
        hud_duration_ms=80000,
        requested_fade_duration_ms=5000,
    )
    assert final_ms == 60000
    assert fade_dur_ms == 5000
    assert fade_st_ms == 55000


def test_calculate_sync_parameters_gopro_longer():
    merger = HudMerger()
    final_ms, fade_dur_ms, fade_st_ms = merger.calculate_sync_parameters(
        gopro_duration_ms=100000,
        hud_duration_ms=75000,
        requested_fade_duration_ms=5000,
    )
    assert final_ms == 75000
    assert fade_dur_ms == 5000
    assert fade_st_ms == 70000


def test_calculate_sync_parameters_short_video():
    merger = HudMerger()
    final_ms, fade_dur_ms, fade_st_ms = merger.calculate_sync_parameters(
        gopro_duration_ms=3000,
        hud_duration_ms=10000,
        requested_fade_duration_ms=5000,
    )
    assert final_ms == 3000
    assert fade_dur_ms == 3000
    assert fade_st_ms == 0


def test_build_filter_complex_same_resolution_no_audio():
    merger = HudMerger()
    gopro = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=50000,
        has_audio=False,
    )
    hud = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=50000,
        has_audio=False,
    )

    filter_str = merger.build_filter_complex(
        gopro_meta=gopro,
        hud_meta=hud,
        final_duration_ms=50000,
        fade_duration_ms=5000,
        fade_start_ms=45000,
    )

    assert '[1:v][2:v]alphamerge[ovr]' in filter_str
    assert '[0:v][ovr]overlay=shortest=0[merged_v]' in filter_str
    assert (
        '[merged_v]trim=duration=50.000,fade=t=out:st=45.000:d=5.000[outv]'
        in filter_str
    )
    assert 'afade' not in filter_str


def test_build_filter_complex_different_resolution_with_audio():
    merger = HudMerger()
    gopro = VideoMetadata(
        width=3840,
        height=2160,
        duration_ms=60000,
        has_audio=True,
    )
    hud = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=60000,
        has_audio=False,
    )

    filter_str = merger.build_filter_complex(
        gopro_meta=gopro,
        hud_meta=hud,
        final_duration_ms=60000,
        fade_duration_ms=5000,
        fade_start_ms=55000,
    )

    assert '[1:v]scale=3840:2160[hud_sc]' in filter_str
    assert '[2:v]scale=3840:2160[alpha_sc]' in filter_str
    assert '[hud_sc][alpha_sc]alphamerge[ovr]' in filter_str
    assert (
        '[0:a]atrim=duration=60.000,afade=t=out:st=55.000:d=5.000[outa]'
        in filter_str
    )


def test_build_ffmpeg_command():
    merger = HudMerger(ffprobe_bin='ffprobe_custom', ffmpeg_bin='ffmpeg_custom')
    options = HudMergeOptions(
        gopro_path=Path('gopro.mp4'),
        hud_path=Path('hud.mp4'),
        hud_alpha_path=Path('alpha.mp4'),
        output_path=Path('out.mp4'),
        fade_duration_ms=4000,
        crf=20,
        preset='fast',
        overwrite=False,
    )
    gopro = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=40000,
        has_audio=True,
    )
    hud = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=50000,
        has_audio=False,
    )

    cmd = merger.build_ffmpeg_command(
        options=options,
        gopro_meta=gopro,
        hud_meta=hud,
    )

    assert cmd[0] == 'ffmpeg_custom'
    assert '-n' in cmd
    assert '-i' in cmd
    assert 'gopro.mp4' in cmd
    assert 'hud.mp4' in cmd
    assert 'alpha.mp4' in cmd
    assert '-map' in cmd
    assert '[outv]' in cmd
    assert '[outa]' in cmd
    assert '-crf' in cmd
    assert '20' in cmd
    assert '-preset' in cmd
    assert 'fast' in cmd
    assert 'out.mp4' in cmd


def test_merge_success():
    merger = HudMerger()
    options = HudMergeOptions(
        gopro_path=Path('gopro.mp4'),
        hud_path=Path('hud.mp4'),
        hud_alpha_path=Path('alpha.mp4'),
        output_path=Path('merged.mp4'),
    )
    dummy_meta = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=30000,
        has_audio=False,
    )

    with (
        patch.object(merger, 'probe_video', return_value=dummy_meta),
        patch('pathlib.Path.mkdir'),
        patch('subprocess.run') as mock_run,
    ):
        merger.merge(options=options)
        mock_run.assert_called_once()


def test_merge_failure():
    merger = HudMerger()
    options = HudMergeOptions(
        gopro_path=Path('gopro.mp4'),
        hud_path=Path('hud.mp4'),
        hud_alpha_path=Path('alpha.mp4'),
        output_path=Path('merged.mp4'),
    )
    dummy_meta = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=30000,
        has_audio=False,
    )

    with (
        patch.object(merger, 'probe_video', return_value=dummy_meta),
        patch('pathlib.Path.mkdir'),
        patch(
            'subprocess.run',
            side_effect=subprocess.CalledProcessError(1, 'ffmpeg'),
        ),
    ):
        with pytest.raises(RuntimeError, match='FFmpeg merge failed'):
            merger.merge(options=options)
