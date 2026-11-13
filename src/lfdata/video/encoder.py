"""Video encoder detection and hardware acceleration utilities.

This module provides detection of GPU hardware-accelerated H.264 video encoders
(NVENC, AMF, QSV, VideoToolbox) with automatic fallback to CPU libx264, along
with helper functions to construct encoder-specific quality parameters.

Usage example:
    from lfdata.video.encoder import (
        build_encoder_quality_args,
        get_best_h264_encoder,
        get_encoder_details,
    )

    encoder = get_best_h264_encoder()
    print(f'Using {encoder}: {get_encoder_details(encoder)}')
    args = build_encoder_quality_args(encoder, crf=18, preset='fast')
"""

import subprocess


def get_best_h264_encoder(ffmpeg_bin: str = 'ffmpeg') -> str:
    """Detects and returns the best available H.264 encoder on the system.

    Probes hardware-accelerated encoders in order (NVENC, AMF, QSV,
    VideoToolbox) by running a minimal 1-frame test through the given FFmpeg
    binary, and falls back to software libx264 if no hardware encoder is
    functional.

    Args:
        ffmpeg_bin: Executable name or filesystem path for FFmpeg.

    Returns:
        str: The selected video encoder codec name.
    """
    candidates = [
        'h264_nvenc',
        'h264_amf',
        'h264_qsv',
        'h264_videotoolbox',
    ]
    for candidate in candidates:
        try:
            cmd = [
                ffmpeg_bin,
                '-hide_banner',
                '-f',
                'lavfi',
                '-i',
                'color=c=black:s=64x64',
                '-frames:v',
                '1',
                '-c:v',
                candidate,
                '-f',
                'null',
                '-',
            ]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
                check=True,
            )
            return candidate
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return 'libx264'


def get_encoder_details(encoder: str) -> str:
    """Returns a user-friendly description of the video encoder capabilities.

    Identifies whether the encoder is GPU-assisted or CPU-only.

    Args:
        encoder: The name of the video encoder codec.

    Returns:
        str: Human-readable hardware acceleration details string.
    """
    gpu_map = {
        'h264_nvenc': 'GPU-assisted (NVIDIA NVENC)',
        'h264_amf': 'GPU-assisted (AMD AMF)',
        'h264_qsv': 'GPU-assisted (Intel Quick Sync Video)',
        'h264_videotoolbox': 'GPU-assisted (Apple VideoToolbox)',
        'hevc_nvenc': 'GPU-assisted (NVIDIA NVENC HEVC)',
        'hevc_amf': 'GPU-assisted (AMD AMF HEVC)',
        'hevc_qsv': 'GPU-assisted (Intel QSV HEVC)',
        'hevc_videotoolbox': 'GPU-assisted (Apple VideoToolbox HEVC)',
        'vp9_nvenc': 'GPU-assisted (NVIDIA NVENC VP9)',
        'vp9_qsv': 'GPU-assisted (Intel QSV VP9)',
    }
    if encoder in gpu_map:
        return gpu_map[encoder]
    gpu_suffixes = (
        '_nvenc',
        '_amf',
        '_qsv',
        '_videotoolbox',
    )
    if any(suffix in encoder for suffix in gpu_suffixes):
        return 'GPU-assisted'
    return 'CPU-only'


def build_encoder_quality_args(
    codec: str,
    crf: int,
    preset: str,
) -> list[str]:
    """Constructs codec-specific quality and preset command arguments.

    Maps constant rate factor and preset values to the correct arguments
    depending on the chosen hardware or software video encoder.

    Args:
        codec: The video encoder codec name.
        crf: Quality factor integer (lower means higher quality).
        preset: Encoding speed/quality preset string.

    Returns:
        list[str]: Command line arguments for FFmpeg video encoding.
    """
    args = ['-c:v', codec]
    if 'nvenc' in codec:
        args.extend(['-cq', str(crf), '-preset', preset])
    elif 'qsv' in codec:
        args.extend(['-global_quality', str(crf), '-preset', preset])
    elif 'amf' in codec:
        args.extend(
            [
                '-rc',
                'cqp',
                '-qp_i',
                str(crf),
                '-qp_p',
                str(crf),
                '-quality',
                preset,
            ]
        )
    elif 'videotoolbox' in codec:
        args.extend(['-q:v', str(crf)])
    else:
        args.extend(['-crf', str(crf), '-preset', preset])
    return args
