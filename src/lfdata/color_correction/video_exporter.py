"""Video exporter utility creating trimmed composite videos using FFmpeg.

This module provides the `VideoExporter` class to probe audio streams, construct
FFmpeg filter_complex commands that combine multiple time ranges from a source
video file, and execute the export process in a thread-safe manner.

Usage example:
    from lfdata.color_correction.time_range import TimeRange
    from lfdata.color_correction.video_exporter import VideoExporter

    exporter = VideoExporter()
    cmd = exporter.build_ffmpeg_command(
        source_path='raw.mp4',
        output_path='test_clip.mp4',
        ranges=[TimeRange(start_ms=1000, end_ms=5000)],
    )
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

from lfdata.color_correction.time_range import TimeRange


class VideoExporter:
    """Manages FFmpeg video export combining multiple reference ranges.

    Attributes:
        ffmpeg_bin: Executable name or path for ffmpeg binary.
        ffprobe_bin: Executable name or path for ffprobe binary.
    """

    ffmpeg_bin: str
    ffprobe_bin: str

    def __init__(
        self,
        ffmpeg_bin: str = 'ffmpeg',
        ffprobe_bin: str = 'ffprobe',
    ) -> None:
        """Initializes VideoExporter with binary executable paths.

        Args:
            ffmpeg_bin: Name or path to the ffmpeg executable (default: ffmpeg).
            ffprobe_bin: Name or path to the ffprobe executable (default: ffprobe).
        """
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin

    def probe_has_audio(self, video_path: str | Path) -> bool:
        """Checks if the specified video file contains an audio stream.

        Args:
            video_path: File system path of the media file to probe.

        Returns:
            bool: True if an audio stream is detected, False otherwise.

        Raises:
            FileNotFoundError: If the specified file does not exist.

        Usage example:
            has_audio = exporter.probe_has_audio(video_path='source.mp4')
        """
        path_obj = Path(video_path)
        if not path_obj.exists():
            raise FileNotFoundError(f'Video file not found: {video_path}')

        cmd: list[str] = [
            self.ffprobe_bin,
            '-v',
            'error',
            '-select_streams',
            'a',
            '-show_entries',
            'stream=codec_type',
            '-of',
            'json',
            str(path_obj),
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(res.stdout)
            streams = data.get('streams', [])
            return len(streams) > 0
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            json.JSONDecodeError,
        ):
            return False

    def build_filter_complex(
        self,
        ranges: list[TimeRange],
        has_audio: bool = True,
        apply_filters: bool = False,
        noise_reduction_filter: str | None = None,
        lut_path: str | Path | None = None,
    ) -> str:
        """Constructs an FFmpeg filter_complex string combining ranges.

        Trims each specified time interval from the video (and audio if
        present), resets timestamps, concatenates them into a continuous
        sequence, and optionally applies color correction or noise reduction.

        Args:
            ranges: List of TimeRange intervals to combine.
            has_audio: True if audio should be trimmed and concatenated.
            apply_filters: Whether to chain video filters on the output.
            noise_reduction_filter: Optional FFmpeg denoising filter expression.
            lut_path: Optional path to Adobe .cube file to apply.

        Returns:
            str: The complete filter_complex string.

        Raises:
            ValueError: If ranges is empty.

        Usage example:
            fc = exporter.build_filter_complex(ranges=selected_ranges)
        """
        if not ranges:
            raise ValueError('At least one TimeRange is required to export.')

        parts: list[str] = []
        num_ranges = len(ranges)

        for i, r in enumerate(ranges):
            start_s = max(0, r.start_ms) / 1000.0
            end_s = max(r.start_ms, r.end_ms) / 1000.0
            parts.append(
                f'[0:v]trim=start={start_s:.3f}:end={end_s:.3f},'
                f'setpts=PTS-STARTPTS[v{i}]'
            )
            if has_audio:
                parts.append(
                    f'[0:a]atrim=start={start_s:.3f}:end={end_s:.3f},'
                    f'asetpts=PTS-STARTPTS[a{i}]'
                )

        # Concat inputs
        concat_inputs: list[str] = []
        for i in range(num_ranges):
            concat_inputs.append(f'[v{i}]')
            if has_audio:
                concat_inputs.append(f'[a{i}]')

        audio_flag = 1 if has_audio else 0
        out_v_tag = '[basev]' if apply_filters else '[outv]'
        out_a_tag = '[outa]' if has_audio else ''

        concat_clause = (
            f'{"".join(concat_inputs)}concat=n={num_ranges}:'
            f'v=1:a={audio_flag}{out_v_tag}{out_a_tag}'
        )
        parts.append(concat_clause)

        if apply_filters:
            v_filters: list[str] = []
            if lut_path is not None:
                escaped_lut = (
                    Path(lut_path)
                    .as_posix()
                    .replace('\\', '/')
                    .replace(':', r'\:')
                    .replace("'", r'\'')
                )
                v_filters.append(f"lut3d=file='{escaped_lut}'")
            if noise_reduction_filter and noise_reduction_filter != 'null':
                v_filters.append(noise_reduction_filter)

            if v_filters:
                filter_chain = ','.join(v_filters)
                parts.append(f'[basev]{filter_chain}[outv]')
            else:
                parts[-1] = parts[-1].replace('[basev]', '[outv]')

        return ';'.join(parts)

    def build_ffmpeg_command(
        self,
        source_path: str | Path,
        output_path: str | Path,
        ranges: list[TimeRange],
        has_audio: bool = True,
        apply_filters: bool = False,
        noise_reduction_filter: str | None = None,
        lut_path: str | Path | None = None,
        overwrite: bool = True,
    ) -> list[str]:
        """Builds command-line argument list for FFmpeg export.

        Args:
            source_path: Source input video file path.
            output_path: Destination output video file path.
            ranges: List of TimeRange intervals to combine.
            has_audio: True if audio should be included in export.
            apply_filters: Whether to chain video filters on the output.
            noise_reduction_filter: Optional FFmpeg denoising filter expression.
            lut_path: Optional path to Adobe .cube file to apply.
            overwrite: True to overwrite destination file if it exists.

        Returns:
            list[str]: Command line arguments for subprocess invocation.

        Raises:
            ValueError: If ranges is empty.

        Usage example:
            cmd = exporter.build_ffmpeg_command(
                source_path='raw.mp4',
                output_path='test.mp4',
                ranges=my_ranges,
            )
        """
        filter_complex = self.build_filter_complex(
            ranges=ranges,
            has_audio=has_audio,
            apply_filters=apply_filters,
            noise_reduction_filter=noise_reduction_filter,
            lut_path=lut_path,
        )

        cmd: list[str] = [
            self.ffmpeg_bin,
            '-y' if overwrite else '-n',
            '-i',
            str(source_path),
            '-filter_complex',
            filter_complex,
            '-map',
            '[outv]',
        ]

        if has_audio:
            cmd.extend(['-map', '[outa]', '-c:a', 'aac', '-b:a', '192k'])

        cmd.extend(
            [
                '-c:v',
                'libx264',
                '-preset',
                'fast',
                '-crf',
                '18',
                '-pix_fmt',
                'yuv420p',
                str(output_path),
            ]
        )

        return cmd

    def export_video(
        self,
        source_path: str | Path,
        output_path: str | Path,
        ranges: list[TimeRange],
        has_audio: bool | None = None,
        apply_filters: bool = False,
        noise_reduction_filter: str | None = None,
        lut_path: str | Path | None = None,
        overwrite: bool = True,
        cancel_event: threading.Event | None = None,
    ) -> None:
        """Executes FFmpeg export combining ranges into destination file.

        Args:
            source_path: Path to the source input video.
            output_path: Path to write the combined test video.
            ranges: Configured TimeRange intervals to export.
            has_audio: Optional audio presence flag (probed if None).
            apply_filters: Whether to apply LUT and noise reduction filters.
            noise_reduction_filter: Optional FFmpeg denoising filter expression.
            lut_path: Optional path to Adobe .cube file to apply.
            overwrite: Whether to overwrite existing destination files.
            cancel_event: Optional threading.Event to cancel running process.

        Raises:
            FileNotFoundError: If source video does not exist.
            ValueError: If ranges list is empty.
            RuntimeError: If FFmpeg execution fails or is cancelled.

        Usage example:
            exporter.export_video(
                source_path='in.mp4',
                output_path='out.mp4',
                ranges=clips,
            )
        """
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f'Source video not found: {source_path}')

        if not ranges:
            raise ValueError('Cannot export video with zero selected ranges.')

        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        audio_present = (
            has_audio
            if has_audio is not None
            else self.probe_has_audio(video_path=src)
        )

        cmd = self.build_ffmpeg_command(
            source_path=src,
            output_path=dest,
            ranges=ranges,
            has_audio=audio_present,
            apply_filters=apply_filters,
            noise_reduction_filter=noise_reduction_filter,
            lut_path=lut_path,
            overwrite=overwrite,
        )

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        while proc.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                proc.kill()
                proc.wait()
                if dest.exists():
                    try:
                        dest.unlink()
                    except OSError:
                        pass
                raise RuntimeError('Video export was cancelled.')
            try:
                proc.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                continue

        _, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f'FFmpeg export failed with code {proc.returncode}:\n{stderr}'
            )
