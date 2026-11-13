import subprocess
from unittest.mock import patch

from lfdata.video.encoder import (
    build_encoder_quality_args,
    get_best_h264_encoder,
    get_encoder_details,
)


def test_get_best_h264_encoder_first_succeeds():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0
        )
        encoder = get_best_h264_encoder()
        assert encoder == 'h264_nvenc'
        assert mock_run.call_count == 1
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == 'ffmpeg'
        assert 'h264_nvenc' in cmd


def test_get_best_h264_encoder_custom_binary():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0
        )
        encoder = get_best_h264_encoder(ffmpeg_bin='my_ffmpeg')
        assert encoder == 'h264_nvenc'
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == 'my_ffmpeg'


def test_get_best_h264_encoder_fallback_on_second_candidate():
    def side_effect(cmd, **kwargs):
        if 'h264_nvenc' in cmd:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    with patch('subprocess.run', side_effect=side_effect) as mock_run:
        encoder = get_best_h264_encoder()
        assert encoder == 'h264_amf'
        assert mock_run.call_count == 2


def test_get_best_h264_encoder_fallback_to_libx264():
    with patch(
        'subprocess.run',
        side_effect=subprocess.SubprocessError('Failed'),
    ) as mock_run:
        encoder = get_best_h264_encoder()
        assert encoder == 'libx264'
        assert mock_run.call_count == 4


def test_get_best_h264_encoder_file_not_found():
    with patch(
        'subprocess.run',
        side_effect=FileNotFoundError('No ffmpeg'),
    ) as mock_run:
        encoder = get_best_h264_encoder()
        assert encoder == 'libx264'
        assert mock_run.call_count == 4


def test_get_encoder_details():
    assert get_encoder_details('h264_nvenc') == (
        'GPU-assisted (NVIDIA NVENC)'
    )
    assert get_encoder_details('h264_amf') == 'GPU-assisted (AMD AMF)'
    assert get_encoder_details('h264_qsv') == (
        'GPU-assisted (Intel Quick Sync Video)'
    )
    assert get_encoder_details('h264_videotoolbox') == (
        'GPU-assisted (Apple VideoToolbox)'
    )
    assert get_encoder_details('hevc_nvenc') == (
        'GPU-assisted (NVIDIA NVENC HEVC)'
    )
    assert get_encoder_details('hevc_amf') == (
        'GPU-assisted (AMD AMF HEVC)'
    )
    assert get_encoder_details('hevc_qsv') == (
        'GPU-assisted (Intel QSV HEVC)'
    )
    assert get_encoder_details('hevc_videotoolbox') == (
        'GPU-assisted (Apple VideoToolbox HEVC)'
    )
    assert get_encoder_details('vp9_nvenc') == (
        'GPU-assisted (NVIDIA NVENC VP9)'
    )
    assert get_encoder_details('vp9_qsv') == 'GPU-assisted (Intel QSV VP9)'
    assert get_encoder_details('custom_nvenc') == 'GPU-assisted'
    assert get_encoder_details('custom_amf') == 'GPU-assisted'
    assert get_encoder_details('libx264') == 'CPU-only'
    assert get_encoder_details('custom_codec') == 'CPU-only'


def test_build_encoder_quality_args_nvenc():
    args = build_encoder_quality_args(
        codec='h264_nvenc', crf=18, preset='fast'
    )
    assert args == ['-c:v', 'h264_nvenc', '-cq', '18', '-preset', 'fast']


def test_build_encoder_quality_args_qsv():
    args = build_encoder_quality_args(
        codec='h264_qsv', crf=20, preset='medium'
    )
    assert args == [
        '-c:v',
        'h264_qsv',
        '-global_quality',
        '20',
        '-preset',
        'medium',
    ]


def test_build_encoder_quality_args_amf():
    args = build_encoder_quality_args(
        codec='h264_amf', crf=22, preset='slow'
    )
    assert args == [
        '-c:v',
        'h264_amf',
        '-rc',
        'cqp',
        '-qp_i',
        '22',
        '-qp_p',
        '22',
        '-quality',
        'slow',
    ]


def test_build_encoder_quality_args_videotoolbox():
    args = build_encoder_quality_args(
        codec='h264_videotoolbox', crf=15, preset='medium'
    )
    assert args == ['-c:v', 'h264_videotoolbox', '-q:v', '15']


def test_build_encoder_quality_args_libx264():
    args = build_encoder_quality_args(
        codec='libx264', crf=18, preset='medium'
    )
    assert args == ['-c:v', 'libx264', '-crf', '18', '-preset', 'medium']
