"""HUD video merging module for lfdata.

This module provides functionality to combine a base video (e.g. GoPro footage)
with HUD color and alpha mask overlay videos, handling resolution scaling,
duration synchronization, and audio/video fade-out.

Usage example:
    from pathlib import Path
    from lfdata.video.hud_merger import HudMerger, HudMergeOptions

    options = HudMergeOptions(
        gopro_path=Path('gopro.mp4'),
        hud_path=Path('hud.mp4'),
        hud_alpha_path=Path('hud_alpha.mp4'),
        output_path=Path('merged.mp4'),
    )
    merger = HudMerger()
    merger.merge(options)
"""

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


@dataclass
class VideoMetadata:
    """Stores metadata probed from a video container and streams.

    Public attributes:
        width: Video width in pixels.
        height: Video height in pixels.
        duration_ms: Duration in milliseconds.
        has_audio: True if the file contains an audio stream.
    """

    width: int
    height: int
    duration_ms: int
    has_audio: bool


@dataclass
class HudMergeOptions:
    """Configuration options for merging HUD and base videos.

    Public attributes:
        gopro_path: Path to the base video file.
        hud_path: Path to the color HUD video file.
        hud_alpha_path: Path to the alpha mask HUD video file.
        output_path: Path to the output video file.
        fade_duration_ms: Duration of fade out in milliseconds.
        crf: Constant rate factor for libx264 encoding.
        preset: Encoding preset for libx264.
        overwrite: Whether to overwrite existing output files.
    """

    gopro_path: Path
    hud_path: Path
    hud_alpha_path: Path
    output_path: Path
    fade_duration_ms: int = 5000
    crf: int = 18
    preset: str = 'medium'
    overwrite: bool = True


class HudMerger:
    """Merges a base video with color and alpha HUD overlays using FFmpeg.

    Probes video metadata, calculates synchronized durations, generates
    composite filtergraphs with scaling and fade-outs, and executes FFmpeg.

    Public attributes:
        ffprobe_bin: Name or path of the ffprobe executable.
        ffmpeg_bin: Name or path of the ffmpeg executable.
    """

    ffprobe_bin: str
    ffmpeg_bin: str

    def __init__(
        self,
        ffprobe_bin: str = 'ffprobe',
        ffmpeg_bin: str = 'ffmpeg',
    ) -> None:
        """Initialize the HudMerger instance.

        Args:
            ffprobe_bin: Executable name or path for ffprobe.
            ffmpeg_bin: Executable name or path for ffmpeg.
        """
        self.ffprobe_bin = ffprobe_bin
        self.ffmpeg_bin = ffmpeg_bin

    def probe_video(self, file_path: Path) -> VideoMetadata:
        """Probe a video file to retrieve dimensions, duration, and audio.

        Args:
            file_path: Path to the media file to probe.

        Returns:
            VideoMetadata containing probed attributes.

        Raises:
            FileNotFoundError: If the specified video file does not exist.
            RuntimeError: If ffprobe fails or output cannot be parsed.
        """
        if not file_path.exists():
            raise FileNotFoundError(f'Video file not found: {file_path}')

        cmd = [
            self.ffprobe_bin,
            '-v',
            'error',
            '-show_entries',
            'stream=codec_type,width,height,duration',
            '-show_entries',
            'format=duration',
            '-of',
            'json',
            str(file_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                f'Failed to probe video file {file_path}: {e}'
            ) from e

        return self._parse_probe_json(raw_json=result.stdout)

    def _parse_probe_json(self, raw_json: str) -> VideoMetadata:
        """Parse the JSON output from ffprobe into a VideoMetadata object.

        Args:
            raw_json: Raw JSON string from ffprobe.

        Returns:
            Parsed VideoMetadata instance.

        Raises:
            RuntimeError: If no valid video stream is found in the probe data.
        """
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f'Invalid ffprobe JSON output: {e}') from e

        streams = data.get('streams', [])
        format_info = data.get('format', {})

        video_stream: dict | None = None
        has_audio = False

        for stream in streams:
            codec_type = stream.get('codec_type')
            if codec_type == 'video' and video_stream is None:
                video_stream = stream
            elif codec_type == 'audio':
                has_audio = True

        if not video_stream:
            raise RuntimeError('No video stream found in probe output.')

        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        duration_ms = self._extract_duration_ms(
            stream_info=video_stream,
            format_info=format_info,
        )

        return VideoMetadata(
            width=width,
            height=height,
            duration_ms=duration_ms,
            has_audio=has_audio,
        )

    def _extract_duration_ms(
        self,
        stream_info: dict,
        format_info: dict,
    ) -> int:
        """Extract video duration in milliseconds from stream or format data.

        Args:
            stream_info: Video stream dictionary from ffprobe.
            format_info: Container format dictionary from ffprobe.

        Returns:
            Duration in milliseconds.
        """
        duration_str = stream_info.get('duration')
        if not duration_str or duration_str == 'N/A':
            duration_str = format_info.get('duration')

        if not duration_str or duration_str == 'N/A':
            return 0

        try:
            duration_sec = float(duration_str)
            return int(round(duration_sec * 1000.0))
        except (ValueError, TypeError):
            return 0

    def calculate_sync_parameters(
        self,
        gopro_duration_ms: int,
        hud_duration_ms: int,
        requested_fade_duration_ms: int,
    ) -> tuple[int, int, int]:
        """Calculate effective final duration, fade duration, and fade start.

        Args:
            gopro_duration_ms: Duration of GoPro video in ms.
            hud_duration_ms: Duration of HUD video in ms.
            requested_fade_duration_ms: Requested fade out duration in ms.

        Returns:
            Tuple of (final_duration_ms, fade_duration_ms, fade_start_ms).
        """
        final_duration_ms = min(gopro_duration_ms, hud_duration_ms)
        fade_duration_ms = min(requested_fade_duration_ms, final_duration_ms)
        fade_start_ms = max(0, final_duration_ms - fade_duration_ms)
        return final_duration_ms, fade_duration_ms, fade_start_ms

    def build_filter_complex(
        self,
        gopro_meta: VideoMetadata,
        hud_meta: VideoMetadata,
        final_duration_ms: int,
        fade_duration_ms: int,
        fade_start_ms: int,
    ) -> str:
        """Build the FFmpeg filter_complex graph string.

        Args:
            gopro_meta: Probed GoPro video metadata.
            hud_meta: Probed HUD video metadata.
            final_duration_ms: Total duration of final output in ms.
            fade_duration_ms: Duration of fade out in ms.
            fade_start_ms: Start time for fade out in ms.

        Returns:
            FFmpeg filter complex string.
        """
        filters: list[str] = []
        final_s = final_duration_ms / 1000.0
        fade_dur_s = fade_duration_ms / 1000.0
        fade_st_s = fade_start_ms / 1000.0

        diff_res = (
            hud_meta.width != gopro_meta.width
            or hud_meta.height != gopro_meta.height
        )

        if diff_res:
            filters.append(
                f'[1:v]scale={gopro_meta.width}:{gopro_meta.height}[hud_sc]'
            )
            filters.append(
                f'[2:v]scale={gopro_meta.width}:{gopro_meta.height}[alpha_sc]'
            )
            filters.append('[hud_sc][alpha_sc]alphamerge[ovr]')
        else:
            filters.append('[1:v][2:v]alphamerge[ovr]')

        filters.append('[0:v][ovr]overlay=shortest=0[merged_v]')

        fade_filter = (
            f'[merged_v]trim=duration={final_s:.3f},'
            f'fade=t=out:st={fade_st_s:.3f}:d={fade_dur_s:.3f}[outv]'
        )
        filters.append(fade_filter)

        if gopro_meta.has_audio:
            afade_filter = (
                f'[0:a]atrim=duration={final_s:.3f},'
                f'afade=t=out:st={fade_st_s:.3f}:d={fade_dur_s:.3f}[outa]'
            )
            filters.append(afade_filter)

        return ';'.join(filters)

    def build_ffmpeg_command(
        self,
        options: HudMergeOptions,
        gopro_meta: VideoMetadata,
        hud_meta: VideoMetadata,
    ) -> list[str]:
        """Construct the complete FFmpeg command line arguments list.

        Args:
            options: Merge options configuration.
            gopro_meta: Probed GoPro metadata.
            hud_meta: Probed HUD metadata.

        Returns:
            List of command line argument strings for FFmpeg.
        """
        final_ms, fade_dur_ms, fade_st_ms = self.calculate_sync_parameters(
            gopro_duration_ms=gopro_meta.duration_ms,
            hud_duration_ms=hud_meta.duration_ms,
            requested_fade_duration_ms=options.fade_duration_ms,
        )

        filter_complex = self.build_filter_complex(
            gopro_meta=gopro_meta,
            hud_meta=hud_meta,
            final_duration_ms=final_ms,
            fade_duration_ms=fade_dur_ms,
            fade_start_ms=fade_st_ms,
        )

        cmd: list[str] = [
            self.ffmpeg_bin,
            '-y' if options.overwrite else '-n',
            '-i',
            str(options.gopro_path),
            '-i',
            str(options.hud_path),
            '-i',
            str(options.hud_alpha_path),
            '-filter_complex',
            filter_complex,
            '-map',
            '[outv]',
        ]

        if gopro_meta.has_audio:
            cmd.extend(['-map', '[outa]', '-c:a', 'aac'])

        cmd.extend(
            [
                '-c:v',
                'libx264',
                '-crf',
                str(options.crf),
                '-preset',
                options.preset,
                '-pix_fmt',
                'yuv420p',
                str(options.output_path),
            ]
        )
        return cmd

    def merge(self, options: HudMergeOptions) -> None:
        """Perform the complete HUD and base video merge process.

        Probes input videos, computes duration/fade sync, constructs FFmpeg
        arguments, and runs the FFmpeg process.

        Args:
            options: Configuration options for the merge.

        Raises:
            FileNotFoundError: If any input video file does not exist.
            RuntimeError: If FFmpeg execution encounters an error.
        """
        gopro_meta = self.probe_video(file_path=options.gopro_path)
        hud_meta = self.probe_video(file_path=options.hud_path)

        cmd = self.build_ffmpeg_command(
            options=options,
            gopro_meta=gopro_meta,
            hud_meta=hud_meta,
        )

        options.output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f'FFmpeg merge failed with code {e.returncode}'
            ) from e
