"""Video generation and visualization for LF games."""

import colorsys
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont

from lfdata.model import LFGame
from lfdata.video.element import (
    LFScoreboardPlayerData,
    LFScoreboardTeamData,
    LFScoreboardTeamTotals,
    UIElement,
)
from lfdata.video.generator import VisualElementGenerator
from lfdata.video.helpers import (
    DEFAULT_CONFIG,
    _merge_configs,
    apply_animation,
    hex_to_rgb,
    parse_color_with_alpha,
    resolve_animated_value,
    resolve_config_dict,
)

IMAGE_TAG_PATTERN = re.compile(r'\[img:([^\]]+)\]')

_local_vg: 'VideoGenerator | None' = None
_local_hud_gen: VisualElementGenerator | None = None


def _init_renderer_process(
    vg: 'VideoGenerator',
    hud_gen: VisualElementGenerator,
) -> None:
    """Initializes global worker state in a child process.

    Args:
        vg: The VideoGenerator instance.
        hud_gen: The VisualElementGenerator instance.
    """
    global _local_vg, _local_hud_gen
    _local_vg = vg
    _local_hud_gen = hud_gen


def _render_frame_worker(
    frame_idx: int,
    time_ms: int,
    temp_path: Path,
    config: dict[str, Any],
) -> None:
    """Renders a single frame using the process-local generator.

    Args:
        frame_idx: The sequential index of the frame.
        time_ms: The millisecond timestamp.
        temp_path: The directory path to save frame PNGs.
        config: The video styling options.

    Raises:
        RuntimeError: If the worker process is not properly initialized.
    """
    global _local_vg, _local_hud_gen
    if _local_vg is None or _local_hud_gen is None:
        raise RuntimeError('Worker process not properly initialized.')
    _local_vg._render_and_save_frame(
        frame_idx=frame_idx,
        time_ms=time_ms,
        temp_path=temp_path,
        config=config,
        hud_gen=_local_hud_gen,
    )


def _render_frame_bytes_worker(
    time_ms: int,
    config: dict[str, Any],
) -> bytes:
    """Renders a single frame and returns its raw RGBA bytes.

    Args:
        time_ms: The millisecond timestamp.
        config: The video styling options.

    Returns:
        bytes: The raw RGBA bytes of the rendered image.

    Raises:
        RuntimeError: If the worker process is not properly initialized.
    """
    global _local_vg, _local_hud_gen
    if _local_vg is None or _local_hud_gen is None:
        raise RuntimeError('Worker process not properly initialized.')
    return _local_vg._render_frame_bytes(
        time_ms=time_ms,
        config=config,
        hud_gen=_local_hud_gen,
    )


def _get_best_h264_encoder() -> str:
    """Detects and returns the best available H.264 encoder on the system.

    Tries hardware-accelerated encoders (nvenc, amf, qsv, videotoolbox) and
    falls back to libx264 if none are fully functional.

    Returns:
        The name of the best H.264 encoder to use.
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
                'ffmpeg',
                '-y',
                '-f',
                'lavfi',
                '-i',
                'color=c=blue:s=64x64:d=0.01',
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
                timeout=1.0,
                check=True,
            )
            return candidate
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return 'libx264'


def _get_encoder_details(encoder: str) -> str:
    """Returns a user-friendly description of the video encoder capabilities.

    Identifies whether the encoder is GPU-assisted or CPU-only.

    Args:
        encoder: The name of the video encoder.

    Returns:
        A string describing the hardware acceleration details.
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
    if any(
        suffix in encoder
        for suffix in [
            '_nvenc',
            '_amf',
            '_qsv',
            '_videotoolbox',
        ]
    ):
        return 'GPU-assisted'
    return 'CPU-only'


class VideoGenerator:
    """Generates visual videos from LF game events and data."""

    def __init__(self, game: LFGame) -> None:
        """Initializes the video generator with game data.

        Args:
            game: The LFGame data object.
        """
        self.game = game
        self._text_cache: dict[tuple, Image.Image] = {}
        self._text_cache_lock = threading.Lock()
        self._downtime_full: Image.Image | None = None
        self._downtime_empty: Image.Image | None = None
        self._downtime_cache_size: tuple[int, int] | None = None
        self._downtime_full_resized: Image.Image | None = None
        self._downtime_empty_resized: Image.Image | None = None
        self._icon_cache: dict[tuple[Any, ...], Image.Image] = {}
        self._icon_cache_lock = threading.Lock()
        self._penalty_card_cache: dict[int, Image.Image] = {}
        self._penalty_card_cache_lock = threading.Lock()
        self._font_cache: dict[tuple, ImageFont.ImageFont] = {}
        self._font_cache_lock = threading.Lock()
        self._fallback_font_cache: dict[
            float | int, list[ImageFont.ImageFont]
        ] = {}
        self._font_notdef_signatures: dict[
            ImageFont.ImageFont,
            tuple[tuple[int, int], list[int]] | None,
        ] = {}
        self._hit_border_img: Image.Image | None = None
        self._hit_border_lock = threading.Lock()

    def __getstate__(self) -> dict[str, Any]:
        """Prepares the object state for serialization.

        Removes non-picklable locks and cache objects prior to pickling.

        Returns:
            dict[str, Any]: The picklable object state.
        """
        state = self.__dict__.copy()
        if '_text_cache_lock' in state:
            del state['_text_cache_lock']
        if '_text_cache' in state:
            del state['_text_cache']
        if '_icon_cache_lock' in state:
            del state['_icon_cache_lock']
        if '_icon_cache' in state:
            del state['_icon_cache']
        if '_penalty_card_cache_lock' in state:
            del state['_penalty_card_cache_lock']
        if '_penalty_card_cache' in state:
            del state['_penalty_card_cache']
        if '_font_cache_lock' in state:
            del state['_font_cache_lock']
        if '_font_cache' in state:
            del state['_font_cache']
        if '_fallback_font_cache' in state:
            del state['_fallback_font_cache']
        if '_font_notdef_signatures' in state:
            del state['_font_notdef_signatures']
        if '_hit_border_lock' in state:
            del state['_hit_border_lock']
        if '_hit_border_img' in state:
            del state['_hit_border_img']
        for key in [
            '_downtime_full',
            '_downtime_empty',
            '_downtime_cache_size',
            '_downtime_full_resized',
            '_downtime_empty_resized',
        ]:
            if key in state:
                del state[key]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restores the object state from serialization.

        Re-initializes the thread lock and text cache for the current process.

        Args:
            state: The serialized state dictionary.
        """
        self.__dict__.update(state)
        self._text_cache = {}
        self._text_cache_lock = threading.Lock()
        self._downtime_full = None
        self._downtime_empty = None
        self._downtime_cache_size = None
        self._downtime_full_resized = None
        self._downtime_empty_resized = None
        self._icon_cache = {}
        self._icon_cache_lock = threading.Lock()
        self._penalty_card_cache = {}
        self._penalty_card_cache_lock = threading.Lock()
        self._font_cache = {}
        self._font_cache_lock = threading.Lock()
        self._fallback_font_cache = {}
        self._font_notdef_signatures = {}
        self._hit_border_img = None
        self._hit_border_lock = threading.Lock()

    def _get_cached_icon(
        self, icon_path: Path, size: int
    ) -> Image.Image | None:
        """Retrieves a cached, resized version of an icon image or loads it.

        Args:
            icon_path: The filesystem path to the icon image.
            size: The target width and height of the icon.

        Returns:
            Image.Image | None: The resized Image object, or None if loading
            failed.
        """
        if not icon_path.exists():
            return None
        cache_key = (str(icon_path), size)
        with self._icon_cache_lock:
            cached = self._icon_cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            with Image.open(icon_path) as raw_img:
                img_rgba = raw_img.convert('RGBA')
                try:
                    resized = img_rgba.resize(
                        (size, size), Image.Resampling.LANCZOS
                    )
                    with self._icon_cache_lock:
                        self._icon_cache[cache_key] = resized
                    return resized
                finally:
                    img_rgba.close()
        except Exception as e:
            print(f'Warning: failed to load/resize icon {icon_path}: {e}')
            return None

    def _get_cached_tinted_icon(
        self,
        icon_path: Path,
        size: int,
        color: tuple[int, int, int, int],
    ) -> Image.Image | None:
        """Retrieves a cached, resized, and tinted version of an icon image.

        Loads the icon from the filesystem if not cached, resizes it to a
        square of the given size, and tints it with the specified color.

        Args:
            icon_path: The filesystem path to the icon image.
            size: The target width and height of the icon.
            color: The RGBA color tuple to tint the icon with.

        Returns:
            Image.Image | None: The tinted Image object, or None if failed.
        """
        if not icon_path.exists():
            return None
        cache_key = (str(icon_path), size, color)
        with self._icon_cache_lock:
            cached = self._icon_cache.get(cache_key)
            if cached is not None:
                return cached

        base_img = self._get_cached_icon(icon_path, size)
        if base_img is None:
            return None

        try:
            solid_tint = Image.new('RGBA', (size, size), color[:3] + (255,))
            try:
                tinted = ImageChops.multiply(base_img, solid_tint)
                if len(color) > 3 and color[3] < 255:
                    r, g, b, a = tinted.split()
                    try:
                        new_a = a.point(lambda val: int(val * color[3] / 255))
                        try:
                            tinted_final = Image.merge('RGBA', (r, g, b, new_a))
                            tinted.close()
                            tinted = tinted_final
                        finally:
                            new_a.close()
                    finally:
                        r.close()
                        g.close()
                        b.close()
                        a.close()
                with self._icon_cache_lock:
                    self._icon_cache[cache_key] = tinted
                return tinted
            finally:
                solid_tint.close()
        except Exception as e:
            print(f'Warning: failed to tint icon {icon_path}: {e}')
            return None

    def _get_cached_penalty_card(self, row_h: int) -> Image.Image | None:
        """Loads and caches the penalty card icon keeping aspect ratio.

        Args:
            row_h: The target row height.

        Returns:
            Image.Image | None: Resized penalty card, or None if failed.
        """
        cache_key = row_h
        with self._penalty_card_cache_lock:
            cached = self._penalty_card_cache.get(cache_key)
            if cached is not None:
                return cached

        icon_path = Path('assets') / 'penalty.png'
        if not icon_path.exists():
            return None

        try:
            with Image.open(icon_path) as raw_img:
                img_rgba = raw_img.convert('RGBA')
                try:
                    card_h = int(row_h * 0.8)
                    card_w = int(card_h * raw_img.width / raw_img.height)
                    resized = img_rgba.resize(
                        (card_w, card_h), Image.Resampling.LANCZOS
                    )
                    with self._penalty_card_cache_lock:
                        self._penalty_card_cache[cache_key] = resized
                    return resized
                finally:
                    img_rgba.close()
        except Exception as e:
            print(
                f'Warning: failed to load/resize penalty card {icon_path}: {e}'
            )
            return None

    def _get_hit_border_image(self) -> Image.Image | None:
        """Loads and caches the raw hit border overlay image.

        Returns:
            Image.Image | None: The loaded Image object, or None if failed.
        """
        with self._hit_border_lock:
            if self._hit_border_img is not None:
                return self._hit_border_img

        path = Path('assets') / 'hit_border.png'
        if not path.exists():
            return None

        try:
            raw_img = Image.open(path).convert('RGBA')
            with self._hit_border_lock:
                self._hit_border_img = raw_img
            return raw_img
        except Exception as e:
            print(f'Warning: failed to load hit border image: {e}')
            return None

    def _determine_video_end_ms(
        self,
        hud_gen: VisualElementGenerator,
        config: dict[str, Any],
        video_end_ms: int | None,
    ) -> int:
        """Determines the end timestamp in milliseconds for video generation.

        Args:
            hud_gen: Precomputed visual element HUD generator.
            config: Styling and configuration options.
            video_end_ms: Optional explicit ending timestamp in milliseconds.

        Returns:
            int: The calculated end timestamp in milliseconds.
        """
        if video_end_ms is not None:
            return video_end_ms

        actual_duration_ms = self.game.duration
        if hud_gen.game_ended_at_ms is not None:
            actual_duration_ms = hud_gen.game_ended_at_ms
        if actual_duration_ms is None:
            actual_duration_ms = 0

        if not self.game.events:
            return 0

        pregame_delay_ms = config.get('pregame_delay_ms', 0)
        extra_footage_ms = config.get('extra_footage_ms', 10000)
        return actual_duration_ms + extra_footage_ms + pregame_delay_ms

    def generate(
        self,
        output_path: str | Path,
        config_path: str | Path | None = None,
        video_start_ms: int = 0,
        video_end_ms: int | None = None,
        video_player: str | None = None,
        fps: int | None = None,
        use_pipe: bool = True,
        alpha_output_path: str | Path | None = None,
        pregame_delay_ms: int | None = None,
    ) -> Path:
        """Generates a video file for the game replay.

        This method compiles all replay events, generates image frames, and
        compiles them into a video file at the specified output path.

        Args:
            output_path: The output file path for the generated video.
            config_path: The optional configuration file path.
            video_start_ms: The starting millisecond timestamp for the video.
            video_end_ms: The ending millisecond timestamp for the video.
            video_player: Optional player name to focus on.
            fps: Optional frame rate override for the video.
            use_pipe: Whether to stream frame bytes via pipe directly to FFmpeg.
            alpha_output_path: Optional path for the alpha channel video.

        Returns:
            Path: The path to the generated video file.

        Raises:
            ValueError: If alpha_output_path is set but use_pipe is False.
        """
        output_path = Path(output_path)
        config = self._load_config(config_path)
        if video_player is not None:
            config['player_name'] = video_player
        if pregame_delay_ms is not None:
            config['pregame_delay_ms'] = pregame_delay_ms

        config_use_pipe = config.get('use_pipe', True)
        final_use_pipe = use_pipe and config_use_pipe

        if alpha_output_path is not None:
            if not final_use_pipe:
                raise ValueError(
                    'Alpha video output is only supported when use_pipe is '
                    'True.'
                )
            alpha_output_path = Path(alpha_output_path)

        hud_gen = VisualElementGenerator(
            self.game, config.get('player_name'), config
        )

        end_ms = self._determine_video_end_ms(hud_gen, config, video_end_ms)
        start_ms = video_start_ms
        fps_val = fps if fps is not None else config.get('fps', 60)

        if final_use_pipe:
            self._generate_video_piped(
                output_path=output_path,
                start_ms=start_ms,
                end_ms=end_ms,
                fps=fps_val,
                config=config,
                hud_gen=hud_gen,
                alpha_output_path=alpha_output_path,
            )
        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                self._generate_frames(
                    temp_path=temp_path,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    fps=fps_val,
                    config=config,
                    hud_gen=hud_gen,
                )
                self._compile_video(temp_path, fps_val, output_path, config)
        return output_path

    def _load_config(self, config_path: str | Path | None) -> dict[str, Any]:
        """Loads and parses the optional YAML configuration file.

        Args:
            config_path: Optional config file path.

        Returns:
            dict[str, Any]: Loaded config dictionary.
        """
        import copy

        base_config = copy.deepcopy(DEFAULT_CONFIG)
        if not config_path:
            return base_config

        import yaml

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    return _merge_configs(base_config, loaded)
        except Exception as e:
            print(f'Warning: failed to load config: {e}')
        return base_config

    def _format_duration(self, seconds: float) -> str:
        """Formats a duration in seconds to a human-readable string.

        Converts the float seconds value into a clean, readable representation
        such as 'Xm Ys', 'Xs', or 'Hh Mm'.

        Args:
            seconds: The duration in seconds.

        Returns:
            str: The formatted duration string.
        """
        sec = int(seconds)
        if sec < 60:
            return f'{sec}s'
        minutes = sec // 60
        sec = sec % 60
        if minutes < 60:
            return f'{minutes}m {sec}s'
        hours = minutes // 60
        minutes = minutes % 60
        return f'{hours}h {minutes}m {sec}s'

    def _render_frame_bytes(
        self,
        time_ms: int,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> bytes:
        """Renders a single frame and returns its raw RGBA bytes.

        Args:
            time_ms: The millisecond timestamp.
            config: The merged video styling options.
            hud_gen: Precomputed visual element HUD generator.

        Returns:
            bytes: The raw RGBA bytes of the rendered image.
        """
        elements = hud_gen.generate_at(time_ms)
        img = self._render_frame(elements, time_ms, config, hud_gen)
        try:
            return img.tobytes()
        finally:
            img.close()

    def _render_and_save_frame(
        self,
        frame_idx: int,
        time_ms: int,
        temp_path: Path,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> None:
        """Renders a single frame and saves it as a PNG image.

        Args:
            frame_idx: The sequential index of the frame.
            time_ms: The millisecond timestamp.
            temp_path: The directory path to save frame PNGs.
            config: The merged video styling options.
            hud_gen: Precomputed visual element HUD generator.
        """
        elements = hud_gen.generate_at(time_ms)
        img = self._render_frame(elements, time_ms, config, hud_gen)
        try:
            img.save(temp_path / f'frame_{frame_idx:05d}.png')
        finally:
            img.close()

    def _generate_frames(
        self,
        temp_path: Path,
        start_ms: int,
        end_ms: int,
        fps: int,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> None:
        """Generates all PNG frame images in parallel and saves them.

        Args:
            temp_path: The directory path to save frame PNGs.
            start_ms: The start timestamp of the video in milliseconds.
            end_ms: The end timestamp of the video in milliseconds.
            fps: The number of frames per second.
            config: The merged video styling and configuration options.
            hud_gen: Precomputed visual element HUD generator.
        """
        frame_step = 1000.0 / fps
        tasks = []
        frame_index = 0
        time_ms = float(start_ms)

        while time_ms <= end_ms:
            tasks.append((frame_index, int(time_ms)))
            frame_index += 1
            time_ms += frame_step
            if frame_step <= 0:
                break

        from concurrent.futures import (
            FIRST_COMPLETED,
            ProcessPoolExecutor,
            wait,
        )

        max_workers = min(16, max(1, os.cpu_count() or 4))
        with ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=_init_renderer_process,
            initargs=(self, hud_gen),
        ) as executor:
            futures = [
                executor.submit(
                    _render_frame_worker,
                    t[0],
                    t[1],
                    temp_path,
                    config,
                )
                for t in tasks
            ]
            total_frames = len(tasks)
            pending = set(futures)
            start_time = time.time()
            last_report_time = start_time

            while pending:
                _, pending = wait(
                    pending,
                    timeout=1.0,
                    return_when=FIRST_COMPLETED,
                )
                current_time = time.time()
                if current_time - last_report_time >= 10.0:
                    completed = total_frames - len(pending)
                    pct = (
                        (completed / total_frames) * 100.0
                        if total_frames > 0
                        else 0.0
                    )
                    elapsed = current_time - start_time
                    elapsed_str = self._format_duration(elapsed)

                    if completed >= 5 and elapsed > 1.0:
                        rate = completed / elapsed
                        rem_frames = total_frames - completed
                        remaining = rem_frames / rate
                        remaining_str = self._format_duration(remaining)
                        msg = (
                            f'Rendered {completed}/{total_frames} '
                            f'frames ({pct:.1f}%) - '
                            f'{elapsed_str} elapsed, '
                            f'{remaining_str} remaining.'
                        )
                    else:
                        msg = (
                            f'Rendered {completed}/{total_frames} '
                            f'frames ({pct:.1f}%) - '
                            f'{elapsed_str} elapsed.'
                        )
                    print(msg)
                    last_report_time = current_time

            # Print a final status report upon completion.
            completed = total_frames
            elapsed = time.time() - start_time
            elapsed_str = self._format_duration(elapsed)
            print(
                f'Rendered {completed}/{total_frames} '
                f'frames (100.0%) - '
                f'{elapsed_str} elapsed.'
            )

            for f in futures:
                f.result()

    def _generate_video_piped(
        self,
        output_path: Path,
        start_ms: int,
        end_ms: int,
        fps: int,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
        alpha_output_path: Path | None = None,
    ) -> None:
        """Generates raw video frames in parallel and pipes them to FFmpeg.

        Args:
            output_path: The target path of the output video.
            start_ms: The start timestamp of the video in milliseconds.
            end_ms: The end timestamp of the video in milliseconds.
            fps: The number of frames per second.
            config: The merged video styling and configuration options.
            hud_gen: Precomputed visual element HUD generator.
            alpha_output_path: Optional path for the alpha channel video.

        Raises:
            RuntimeError: If FFmpeg encoding fails or terminates prematurely.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()

        resolution = config.get('resolution', [1920, 1080])
        ext = output_path.suffix.lower()
        codec: str
        pix_fmt: str
        extra_args: list[str]
        user_codec = config.get('codec')
        if user_codec:
            codec = user_codec
            pix_fmt = 'yuv420p'
            extra_args = []
        elif ext == '.webm':
            codec = 'libvpx-vp9'
            pix_fmt = 'yuva420p'
            extra_args = []
        elif ext == '.mov':
            codec = 'prores_ks'
            pix_fmt = 'yuva444p10le'
            extra_args = ['-profile:v', '4']
        else:
            codec = _get_best_h264_encoder()
            pix_fmt = 'yuv420p'
            extra_args = []

        cmd = [
            'ffmpeg',
            '-y',
            '-loglevel',
            'error',
            '-f',
            'rawvideo',
            '-pix_fmt',
            'rgba',
            '-s',
            f'{resolution[0]}x{resolution[1]}',
            '-framerate',
            str(fps),
            '-i',
            '-',
            '-c:v',
            codec,
        ]
        if config.get('use_left_channel_mono', False):
            cmd.extend(['-af', '"pan=stereo|FL=FL|FR=FL"']) # mono audio
        if extra_args:
            cmd.extend(extra_args)
        cmd.extend(
            [
                '-pix_fmt',
                pix_fmt,
                str(output_path),
            ]
        )

        print(f'Encoding video to {output_path} (direct pipe)...')
        print(f'Using video encoder: {codec} ({_get_encoder_details(codec)})')

        frame_step = 1000.0 / fps
        tasks = []
        frame_index = 0
        time_ms = float(start_ms)

        while time_ms <= end_ms:
            tasks.append((frame_index, int(time_ms)))
            frame_index += 1
            time_ms += frame_step
            if frame_step <= 0:
                break

        from concurrent.futures import (
            ProcessPoolExecutor,
            wait,
        )

        max_workers = min(16, max(1, os.cpu_count() or 4))

        try:
            ffmpeg_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                f'ffmpeg command not found: {e}. '
                'Please ensure FFmpeg is installed.'
            )

        ffmpeg_proc_alpha = None
        if alpha_output_path:
            alpha_output_path.parent.mkdir(parents=True, exist_ok=True)
            alpha_output_path.touch()
            print(
                f'Encoding alpha video to {alpha_output_path} (direct pipe)...'
            )
            print(
                f'Using alpha video encoder: {codec} '
                f'({_get_encoder_details(codec)})'
            )
            cmd_alpha = cmd.copy()
            cmd_alpha[-1] = str(alpha_output_path)
            try:
                ffmpeg_proc_alpha = subprocess.Popen(
                    cmd_alpha,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except FileNotFoundError as e:
                ffmpeg_proc.kill()
                ffmpeg_proc.wait()
                raise RuntimeError(
                    f'ffmpeg command not found: {e}. '
                    'Please ensure FFmpeg is installed.'
                )

        try:
            print(f'Starting process pool with {max_workers} workers...')
            with ProcessPoolExecutor(
                max_workers=max_workers,
                initializer=_init_renderer_process,
                initargs=(self, hud_gen),
            ) as executor:
                total_frames = len(tasks)
                active_futures: dict[int, Any] = {}

                # Submit first batch of tasks up to window size
                window_size = max_workers * 2
                for idx in range(min(total_frames, window_size)):
                    active_futures[idx] = executor.submit(
                        _render_frame_bytes_worker,
                        tasks[idx][1],
                        config,
                    )

                print('First batch of frames submitted. Starting pipeline...')

                start_time = time.time()
                last_report_time = start_time
                write_idx = 0

                while write_idx < total_frames:
                    if ffmpeg_proc.poll() is not None:
                        _, stderr_data = ffmpeg_proc.communicate()
                        err_msg = stderr_data.decode('utf-8', errors='replace')
                        raise RuntimeError(
                            'FFmpeg encoding terminated prematurely:\n'
                            f'{err_msg}'
                        )
                    if (
                        ffmpeg_proc_alpha
                        and ffmpeg_proc_alpha.poll() is not None
                    ):
                        _, stderr_alpha = ffmpeg_proc_alpha.communicate()
                        err_msg_alpha = stderr_alpha.decode(
                            'utf-8', errors='replace'
                        )
                        raise RuntimeError(
                            'FFmpeg alpha encoding terminated '
                            f'prematurely:\n{err_msg_alpha}'
                        )

                    curr_future = active_futures.get(write_idx)
                    if curr_future is None:
                        curr_future = executor.submit(
                            _render_frame_bytes_worker,
                            tasks[write_idx][1],
                            config,
                        )
                        active_futures[write_idx] = curr_future

                    current_time = time.time()
                    if current_time - last_report_time >= 10.0:
                        completed = write_idx
                        pct = (
                            (completed / total_frames) * 100.0
                            if total_frames > 0
                            else 0.0
                        )
                        elapsed = current_time - start_time
                        elapsed_str = self._format_duration(elapsed)

                        if completed >= 5 and elapsed > 1.0:
                            rate = completed / elapsed
                            rem_frames = total_frames - completed
                            remaining = rem_frames / rate
                            remaining_str = self._format_duration(remaining)
                            msg = (
                                f'Rendered {completed}/{total_frames} '
                                f'frames ({pct:.1f}%) - '
                                f'{elapsed_str} elapsed, '
                                f'{remaining_str} remaining.'
                            )
                        else:
                            msg = (
                                f'Rendered {completed}/{total_frames} '
                                f'frames ({pct:.1f}%) - '
                                f'{elapsed_str} elapsed.'
                            )
                        print(msg)
                        last_report_time = current_time

                    if not curr_future.done():
                        wait([curr_future], timeout=0.1)
                        continue

                    frame_bytes = curr_future.result()

                    if ffmpeg_proc_alpha:
                        img = Image.frombytes('RGBA', resolution, frame_bytes)
                        r, g, b, a = img.split()
                        img_main = img.convert('RGB').convert('RGBA')
                        img_alpha = Image.merge('RGB', (a, a, a)).convert(
                            'RGBA'
                        )
                        ffmpeg_proc.stdin.write(img_main.tobytes())
                        ffmpeg_proc_alpha.stdin.write(img_alpha.tobytes())
                        img.close()
                        img_main.close()
                        img_alpha.close()
                    else:
                        ffmpeg_proc.stdin.write(frame_bytes)

                    # Free the future reference and raw bytes immediately
                    del active_futures[write_idx]

                    # Submit the next task
                    next_idx = write_idx + window_size
                    if next_idx < total_frames:
                        active_futures[next_idx] = executor.submit(
                            _render_frame_bytes_worker,
                            tasks[next_idx][1],
                            config,
                        )

                    write_idx += 1

            completed = total_frames
            elapsed = time.time() - start_time
            elapsed_str = self._format_duration(elapsed)
            print(
                f'Rendered {completed}/{total_frames} '
                f'frames (100.0%) - '
                f'{elapsed_str} elapsed.'
            )

            if ffmpeg_proc.stdin:
                ffmpeg_proc.stdin.close()
                ffmpeg_proc.stdin = None
            _, stderr_data = ffmpeg_proc.communicate()

            if ffmpeg_proc.returncode != 0:
                err_msg = stderr_data.decode('utf-8', errors='replace')
                raise RuntimeError(
                    f'FFmpeg encoding failed with exit code '
                    f'{ffmpeg_proc.returncode}:\n{err_msg}'
                )

            if ffmpeg_proc_alpha:
                if ffmpeg_proc_alpha.stdin:
                    ffmpeg_proc_alpha.stdin.close()
                    ffmpeg_proc_alpha.stdin = None
                _, stderr_alpha = ffmpeg_proc_alpha.communicate()
                if ffmpeg_proc_alpha.returncode != 0:
                    err_msg_alpha = stderr_alpha.decode(
                        'utf-8', errors='replace'
                    )
                    raise RuntimeError(
                        f'FFmpeg alpha encoding failed with exit code '
                        f'{ffmpeg_proc_alpha.returncode}:\n{err_msg_alpha}'
                    )

        except BaseException as e:
            ffmpeg_proc.kill()
            ffmpeg_proc.wait()
            if ffmpeg_proc_alpha:
                ffmpeg_proc_alpha.kill()
                ffmpeg_proc_alpha.wait()
            raise e

    def _compile_video(
        self, frames_dir: Path, fps: int, output_path: Path, config: dict[str, Any]
    ) -> None:
        """Compiles PNG frames in a directory into a video using ffmpeg.

        Args:
            frames_dir: The directory containing PNG frames.
            fps: The frames per second.
            output_path: The target path of the output video.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        print(f'Encoding video to {output_path}...')

        ext: str = output_path.suffix.lower()
        codec: str
        pix_fmt: str
        extra_args: list[str]
        if ext == '.webm':
            codec = 'libvpx-vp9'
            pix_fmt = 'yuva420p'
            extra_args = []
        elif ext == '.mov':
            codec = 'prores_ks'
            pix_fmt = 'yuva444p10le'
            extra_args = ['-profile:v', '4']
        else:
            codec = _get_best_h264_encoder()
            pix_fmt = 'yuv420p'
            extra_args = []

        print(f'Using video encoder: {codec} ({_get_encoder_details(codec)})')
        cmd: list[str] = [
            'ffmpeg',
            '-y',
            '-loglevel',
            'error',
            '-framerate',
            str(fps),
            '-i',
            str(frames_dir / 'frame_%05d.png'),
            '-c:v',
            codec
        ]
        if config.get('use_left_channel_mono', False):
            cmd.extend(['-af', '"pan=stereo|FL=FL|FR=FL"']) # mono audio
        if extra_args:
            cmd.extend(extra_args)
        cmd.extend(
            [
                '-pix_fmt',
                pix_fmt,
                str(output_path),
            ]
        )
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f'Warning: ffmpeg video encoding failed/skipped: {e}')
            if hasattr(e, 'stderr') and e.stderr:
                err_str = e.stderr.decode('utf-8', errors='replace')
                print(f'ffmpeg stderr:\n{err_str}')

    def _render_frame(
        self,
        elements: list[UIElement],
        time_ms: int,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> Image.Image:
        """Renders all active UI elements onto an Image object.

        Args:
            elements: The active visual elements to render.
            time_ms: The current millisecond timestamp.
            config: The merged video configuration options.
            hud_gen: Precomputed visual element HUD generator.

        Returns:
            Image.Image: The rendered frame image.
        """
        pregame_delay_ms = config.get('pregame_delay_ms', 0)
        if (
            isinstance(pregame_delay_ms, dict)
            and 'keyframes' in pregame_delay_ms
        ):
            pregame_delay_ms = resolve_animated_value(
                pregame_delay_ms,
                time_ms,
                pregame_delay_ms=0,
                game_duration_ms=hud_gen.game.duration or 0,
            )

        actual_duration_ms = hud_gen.game.duration
        if hud_gen.game_ended_at_ms is not None:
            actual_duration_ms = hud_gen.game_ended_at_ms
        if actual_duration_ms is None:
            actual_duration_ms = 0

        resolved_config = resolve_config_dict(
            config,
            time_ms,
            pregame_delay_ms=pregame_delay_ms,
            game_duration_ms=actual_duration_ms,
        )

        resolution = resolved_config.get('resolution', [1920, 1080])
        bg_hex = resolved_config.get('background_color', '#00000000')

        bg_color = parse_color_with_alpha(bg_hex)
        img = Image.new('RGBA', (resolution[0], resolution[1]), bg_color)

        game_time_ms = max(0, time_ms - pregame_delay_ms)

        self._draw_hit_borders(img, game_time_ms, resolved_config, hud_gen)

        for el in elements:
            if el.element_type == 'scoreboard':
                self._draw_scoreboard(img, el, resolved_config)
            elif el.element_type == 'downtime_bar':
                self._draw_downtime_bar(img, el)
            elif el.element_type == 'counter':
                self._draw_counter(img, el, resolved_config)
            elif el.element_type == 'event_scroller':
                self._draw_event_scroller(
                    img, el, game_time_ms, resolved_config
                )

        self._draw_text_elements(img, elements, resolved_config)

        # Draw screen flash overlays (nukes and player missiled)
        flash_alpha: float = 0.0
        nuke_duration_ms: int = resolved_config.get(
            'nuke_flash_duration_ms', 250
        )
        for start_ms in hud_gen.nuke_flashes:
            if start_ms <= game_time_ms < start_ms + nuke_duration_ms:
                elapsed_ms: int = game_time_ms - start_ms
                alpha: float = 1.0 - (elapsed_ms / nuke_duration_ms)
                if alpha > flash_alpha:
                    flash_alpha = alpha

        missile_flash_alpha: float = 0.0
        missile_duration_ms: int = resolved_config.get(
            'missile_flash_duration_ms', 130
        )
        for start_ms in hud_gen.missile_flashes_ms:
            if start_ms <= game_time_ms < start_ms + missile_duration_ms:
                elapsed_ms: int = game_time_ms - start_ms
                alpha: float = 1.0 - (elapsed_ms / missile_duration_ms)
                if alpha > missile_flash_alpha:
                    missile_flash_alpha = alpha

        total_flash_alpha: float = max(flash_alpha, missile_flash_alpha)
        if total_flash_alpha > 0.0:
            overlay = Image.new(
                'RGBA',
                img.size,
                (255, 255, 255, int(255 * total_flash_alpha)),
            )
            try:
                img.alpha_composite(overlay)
            finally:
                overlay.close()

        return img

    def _draw_hit_borders(
        self,
        image: Image.Image,
        time_ms: int,
        config: dict[str, Any],
        hud_gen: VisualElementGenerator,
    ) -> None:
        """Draws active hit border flashes overlay.

        Args:
            image: The Image canvas to draw on.
            time_ms: The current millisecond timestamp.
            config: Merged video configuration options.
            hud_gen: Precomputed visual element HUD generator.
        """
        if not hasattr(hud_gen, 'hit_borders') or not hud_gen.hit_borders:
            return

        hb_config = config.get('elements', {}).get('hit_border', {})
        enabled = hb_config.get('enabled', True)
        if not enabled:
            return

        w, h = image.size

        active_instances = []
        for hb in hud_gen.hit_borders:
            if hb.start_ms <= time_ms < hb.start_ms + hb.duration_ms:
                active_instances.append(hb)

        if not active_instances:
            return

        raw_border = self._get_hit_border_image()
        if raw_border is None:
            return

        for hb in active_instances:
            elapsed = time_ms - hb.start_ms
            p = elapsed / hb.duration_ms

            fade_alpha = 1.0 - p
            scale = 1.0 + (hb.max_scale - 1.0) * p

            scaled_w = int(w * scale)
            scaled_h = int(h * scale)
            if scaled_w <= 0 or scaled_h <= 0:
                continue

            try:
                scaled_border = raw_border.resize(
                    (scaled_w, scaled_h), Image.Resampling.BILINEAR
                )
                try:
                    tint_rgba = parse_color_with_alpha(hb.tint_hex)
                    tint_rgb = tint_rgba[:3]

                    solid_tint = Image.new(
                        'RGBA',
                        (scaled_w, scaled_h),
                        tint_rgb + (255,),
                    )
                    try:
                        tinted = ImageChops.multiply(scaled_border, solid_tint)
                        try:
                            r, g, b, a = tinted.split()
                            try:
                                new_a = a.point(
                                    lambda val: int(val * fade_alpha)
                                )
                                try:
                                    final_img = Image.merge(
                                        'RGBA', (r, g, b, new_a)
                                    )
                                    try:
                                        x_off = (w - scaled_w) // 2
                                        y_off = (h - scaled_h) // 2
                                        image.paste(
                                            final_img,
                                            (x_off, y_off),
                                            mask=final_img,
                                        )
                                    finally:
                                        final_img.close()
                                finally:
                                    new_a.close()
                            finally:
                                r.close()
                                g.close()
                                b.close()
                                a.close()
                        finally:
                            tinted.close()
                    finally:
                        solid_tint.close()
                finally:
                    scaled_border.close()
            except Exception as e:
                print(f'Warning: failed to draw hit border instance: {e}')

    def _calculate_team_y_positions(
        self,
        teams: list[LFScoreboardTeamData],
        y_start: int,
        spacing: int,
        team_heights: dict[int, int],
    ) -> None:
        """Calculates and assigns y_pos to teams based on visual ranks.

        Args:
            teams: List of team data objects.
            y_start: Starting Y position in pixels.
            spacing: Vertical spacing between teams in pixels.
            team_heights: Precalculated height mapping for each team.
        """
        if len(teams) == 2:
            t0, t1 = teams[0], teams[1]
            h0 = team_heights[t0.team_index]
            h1 = team_heights[t1.team_index]
            t0.y_pos = y_start + (t0.visual_rank - 1.0) * (h1 + spacing)
            t1.y_pos = y_start + (t1.visual_rank - 1.0) * (h0 + spacing)
        else:
            curr_y = y_start
            for t in sorted(teams, key=lambda x: x.visual_rank):
                t.y_pos = curr_y
                curr_y += team_heights[t.team_index] + spacing

    def _resolve_font_path(self, font_name: str) -> str:
        """Resolves a font name to a path in the project's fonts folder.

        If the font file exists in the fonts directory (optionally with a .ttf
        extension), its path is returned. Otherwise, font_name is returned.

        Args:
            font_name: The name or file name of the font.

        Returns:
            str: Resolved font path or original font_name.
        """
        from pathlib import Path

        path = Path('fonts') / font_name
        if path.exists():
            return str(path)

        path_ttf = Path('fonts') / f'{font_name}.ttf'
        if path_ttf.exists():
            return str(path_ttf)

        if font_name == 'Anton':
            path_anton = Path('fonts') / 'GoogleSans-Bold.ttf'
            if path_anton.exists():
                return str(path_anton)

        if font_name == 'D Day Stencil':
            path_dday = Path('fonts') / 'D Day Stencil.ttf'
            if path_dday.exists():
                return str(path_dday)

        return font_name

    def _is_char_supported(self, font: ImageFont.ImageFont, char: str) -> bool:
        """Checks if a character is supported by the given font.

        Compares the character mask size and histogram signature to
        the fallback/notdef glyph.

        Args:
            font: The ImageFont to check.
            char: The single character to inspect.

        Returns:
            bool: True if the character is supported, False otherwise.
        """
        if not hasattr(self, '_font_notdef_signatures'):
            self._font_notdef_signatures = {}
        if font not in self._font_notdef_signatures:
            try:
                m = font.getmask('\uffff')
                self._font_notdef_signatures[font] = (m.size, m.histogram())
            except Exception:
                self._font_notdef_signatures[font] = None

        sig = self._font_notdef_signatures[font]
        if sig is None:
            return True

        try:
            char_mask = font.getmask(char)
            if char_mask.size != sig[0]:
                return True
            return char_mask.histogram() != sig[1]
        except Exception:
            return False

    def _get_fallback_fonts(
        self, size: float | int
    ) -> list[ImageFont.ImageFont]:
        """Loads and returns fallback fonts at the given size.

        Common fallback fonts on Windows are loaded and cached.

        Args:
            size: The font size in pixels.

        Returns:
            list[ImageFont.ImageFont]: List of successfully loaded fonts.
        """
        if not hasattr(self, '_fallback_font_cache'):
            self._fallback_font_cache = {}
        if size not in self._fallback_font_cache:
            fallbacks = []
            paths = [
                r'C:\Windows\Fonts\seguisym.ttf',
                r'C:\Windows\Fonts\seguiemj.ttf',
                r'C:\Windows\Fonts\msyh.ttc',
                r'C:\Windows\Fonts\arial.ttf',
            ]
            for p in paths:
                import os

                if os.path.exists(p):
                    try:
                        fallbacks.append(ImageFont.truetype(p, size))
                    except Exception:
                        pass
            self._fallback_font_cache[size] = fallbacks
        return self._fallback_font_cache[size]

    def _get_text_runs(
        self, text: str, font: ImageFont.ImageFont
    ) -> list[tuple[str, ImageFont.ImageFont]]:
        """Splits text into runs grouped by font support.

        Characters not supported by the primary font are mapped to fallback fonts.

        Args:
            text: The text to split.
            font: The primary font to use.

        Returns:
            list[tuple[str, ImageFont.ImageFont]]: Runs of (run_text, font).
        """
        if not text:
            return []

        runs: list[tuple[str, ImageFont.ImageFont]] = []
        current_text: list[str] = []
        current_font: ImageFont.ImageFont | None = None
        first = True

        for char in text:
            resolved_font = font
            if not self._is_char_supported(font, char):
                for fb_font in self._get_fallback_fonts(font.size):
                    if self._is_char_supported(fb_font, char):
                        resolved_font = fb_font
                        break

            if first:
                current_font = resolved_font
                current_text.append(char)
                first = False
            elif resolved_font == current_font:
                current_text.append(char)
            else:
                runs.append((''.join(current_text), current_font))
                current_font = resolved_font
                current_text = [char]

        if current_text:
            runs.append((''.join(current_text), current_font))

        return runs

    def _measure_text_width_with_fallback(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
    ) -> float:
        """Measures text width using font fallbacks.

        Sum of the width of each resolved text run.

        Args:
            draw: The ImageDraw canvas.
            text: The text to measure.
            font: The primary font.

        Returns:
            float: Total measured width in pixels.
        """
        runs = self._get_text_runs(text, font)
        total_w = 0.0
        for run_text, run_font in runs:
            total_w += draw.textlength(run_text, font=run_font)
        return total_w

    def _measure_text_bbox_with_fallback(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        anchor: str = 'la',
    ) -> tuple[float, float, float, float]:
        """Computes text bounding box using font fallbacks.

        Accumulates horizontal width and calculates min/max vertical bounds.

        Args:
            draw: The ImageDraw canvas.
            text: The text to measure.
            font: The primary font.
            anchor: Bounding box alignment anchor.

        Returns:
            tuple[float, float, float, float]: Bounding box (x0, y0, x1, y1).
        """
        runs = self._get_text_runs(text, font)
        if not runs:
            return (0.0, 0.0, 0.0, 0.0)

        total_w = 0.0
        min_y = 0.0
        max_y = 0.0
        first = True

        for run_text, run_font in runs:
            w = draw.textlength(run_text, font=run_font)
            t_bbox = draw.textbbox(
                (total_w, 0), run_text, font=run_font, anchor=anchor
            )
            if first:
                min_y = t_bbox[1]
                max_y = t_bbox[3]
                first = False
            else:
                if t_bbox[1] < min_y:
                    min_y = t_bbox[1]
                if t_bbox[3] > max_y:
                    max_y = t_bbox[3]
            total_w += w

        return (0.0, min_y, total_w, max_y)

    def _draw_text_with_fallback(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[float, float],
        text: str,
        fill: Any,
        font: ImageFont.ImageFont,
        anchor: str = 'la',
        stroke_width: int = 0,
        stroke_fill: Any = None,
    ) -> None:
        """Draws text on a canvas using font fallbacks.

        Splits text into font-specific runs and renders them sequentially.

        Args:
            draw: The ImageDraw canvas.
            xy: Anchor coordinates (x, y).
            text: The text to render.
            fill: Font color.
            font: The primary font.
            anchor: Text alignment anchor.
            stroke_width: Text outline width.
            stroke_fill: Text outline color.
        """
        runs = self._get_text_runs(text, font)
        if not runs:
            return

        h_anchor = anchor[0] if len(anchor) >= 1 else 'l'
        v_anchor = anchor[1] if len(anchor) >= 2 else 'a'

        total_w = self._measure_text_width_with_fallback(draw, text, font)

        x, y = xy
        if h_anchor == 'm':
            x = x - total_w / 2.0
        elif h_anchor == 'r':
            x = x - total_w

        current_x = x
        for run_text, run_font in runs:
            run_anchor = 'l' + v_anchor
            draw.text(
                (current_x, y),
                run_text,
                fill=fill,
                font=run_font,
                anchor=run_anchor,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
            current_x += draw.textlength(run_text, font=run_font)

    def _load_scoreboard_fonts(
        self,
        font_name: str,
        pixel_size: float | int,
        bold_pixel_size: float | int,
    ) -> tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
        """Loads and returns standard and bold fonts for the scoreboard.

        Args:
            font_name: Font family/file name.
            pixel_size: Standard font size.
            bold_pixel_size: Bold font size.

        Returns:
            tuple[ImageFont.ImageFont, ImageFont.ImageFont]: The loaded fonts.
        """
        if not hasattr(self, '_font_cache'):
            self._font_cache = {}
        if not hasattr(self, '_font_cache_lock'):
            self._font_cache_lock = threading.Lock()

        reg_key = ('scoreboard_regular', font_name, pixel_size)
        bold_key = ('scoreboard_bold', font_name, bold_pixel_size)

        with self._font_cache_lock:
            reg_font = self._font_cache.get(reg_key)
            bold_font = self._font_cache.get(bold_key)

        if reg_font is not None and bold_font is not None:
            return reg_font, bold_font

        resolved_name = self._resolve_font_path(font_name)
        try:
            if reg_font is None:
                reg_font = ImageFont.truetype(resolved_name, pixel_size)
            if bold_font is None:
                bold_font = ImageFont.truetype(resolved_name, bold_pixel_size)
        except OSError:
            if reg_font is None:
                try:
                    reg_font = ImageFont.load_default(size=pixel_size)
                except TypeError:
                    reg_font = ImageFont.load_default()
            if bold_font is None:
                try:
                    bold_font = ImageFont.load_default(size=bold_pixel_size)
                except TypeError:
                    bold_font = ImageFont.load_default()

        with self._font_cache_lock:
            self._font_cache[reg_key] = reg_font
            self._font_cache[bold_key] = bold_font

        return reg_font, bold_font

    def _draw_scoreboard(
        self,
        image: Image.Image,
        el: UIElement,
        config: dict[str, Any],
    ) -> None:
        """Draws the animated scoreboard table onto the image.

        Args:
            image: The Image canvas to draw on.
            el: The scoreboard UIElement containing team details.
            config: The merged video configuration options.
        """
        teams = el.scoreboard_data.teams if el.scoreboard_data else []
        if not teams:
            return

        height = image.height
        font_size = el.style.size or 20
        pixel_size = max(1.0, float(height * font_size / 800))
        bold_pixel_size = max(1.0, float(height * (font_size + 2) / 800))

        header_h = int(pixel_size * (35 / 27))
        row_h = int(pixel_size * (28 / 27))
        totals_h = int(pixel_size * (35 / 27))
        spacing = int(pixel_size * (20 / 27))

        x_config = el.x if el.x is not None else 0.1
        y_config = el.y if el.y is not None else 0.4
        x_start = int(image.width * x_config)
        y_start = int(height * y_config)

        team_heights = {}
        for team in teams:
            p_count = len(team.players)
            team_heights[team.team_index] = (
                header_h + (p_count * row_h) + totals_h
            )

        self._calculate_team_y_positions(teams, y_start, spacing, team_heights)

        font, bold_font = self._load_scoreboard_fonts(
            el.style.font, pixel_size, bold_pixel_size
        )
        header_font_name = (
            'D Day Stencil'
            if el.style.font in ('Anton', 'GoogleSans-Bold')
            else el.style.font
        )
        header_font, _ = self._load_scoreboard_fonts(
            header_font_name, bold_pixel_size, bold_pixel_size
        )

        sb_config = config.get('elements', {}).get('scoreboard', {})
        draw_background = sb_config.get('draw_background', False)
        draw_borders = sb_config.get('draw_borders', False)
        stroke_width = max(1, int(pixel_size * 0.05))

        # Find max player column width (name + penalties + hitpoints)
        # across all teams.
        max_player_w = 0
        max_hp_w = 0
        card_h = int(row_h * 0.8)
        penalty_path = Path('assets') / 'penalty.png'
        aspect_ratio = 0.75
        if penalty_path.exists():
            try:
                with Image.open(penalty_path) as card_img:
                    aspect_ratio = card_img.width / card_img.height
            except Exception:
                pass
        card_w = int(card_h * aspect_ratio)

        temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        try:
            temp_draw = ImageDraw.Draw(temp_img)
            for team in teams:
                for p in team.players:
                    codename = p.codename
                    name_w = self._measure_text_width_with_fallback(
                        temp_draw, codename, font
                    )
                    if not isinstance(name_w, (int, float)):
                        name_w = 0.0
                    num_penalties = p.penalties
                    penalties_w = 0
                    if num_penalties > 0:
                        num_cards = min(3, num_penalties)
                        cards_w = card_w + (num_cards - 1) * (card_w // 2)
                        text_w = 0
                        if num_penalties > 3:
                            text_w = self._measure_text_width_with_fallback(
                                temp_draw, f'x{num_penalties}', font
                            )
                            if not isinstance(text_w, (int, float)):
                                text_w = 0.0
                        scale_factor = pixel_size / 27
                        penalties_w = (
                            cards_w
                            + text_w
                            + int(10 * scale_factor * image.width / 1920)
                        )

                    hp_w = 0
                    if p.max_hp > 1:
                        hp_text = '■' * p.max_hp
                        hp_w = self._measure_text_width_with_fallback(
                            temp_draw, hp_text, font
                        )
                        if not isinstance(hp_w, (int, float)):
                            hp_w = 0.0
                        scale_factor = pixel_size / 27
                        margin = int(5 * scale_factor * image.width / 1920)
                        hp_w += margin
                    if hp_w > max_hp_w:
                        max_hp_w = int(hp_w)

                    total_w = name_w + penalties_w
                    if total_w > max_player_w:
                        max_player_w = int(total_w)
        finally:
            temp_img.close()

        # Add the maximum hitpoints width to the maximum player column width
        # to ensure it expands the column correctly.
        max_player_w += max_hp_w

        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        try:
            for team in teams:
                self._draw_team_table(
                    image=overlay,
                    team=team,
                    th=team_heights[team.team_index],
                    x_start=x_start,
                    font=font,
                    bold_font=bold_font,
                    header_font=header_font,
                    header_h=header_h,
                    row_h=row_h,
                    stroke_width=stroke_width,
                    draw_background=draw_background,
                    draw_borders=draw_borders,
                    max_player_w=max_player_w,
                    pixel_size=pixel_size,
                    max_hp_w=max_hp_w,
                )
            if el.alpha < 1.0:
                r, g, b, a = overlay.split()
                try:
                    new_a = a.point(lambda p: int(p * el.alpha))
                    try:
                        overlay_faded = Image.merge('RGBA', (r, g, b, new_a))
                        try:
                            image.alpha_composite(overlay_faded)
                        finally:
                            overlay_faded.close()
                    finally:
                        new_a.close()
                finally:
                    r.close()
                    g.close()
                    b.close()
                    a.close()
            else:
                image.alpha_composite(overlay)
        finally:
            overlay.close()

    def _calculate_team_colors(
        self, team: LFScoreboardTeamData
    ) -> tuple[
        tuple[int, int, int, int],
        tuple[int, int, int, int],
        tuple[int, int, int, int],
        tuple[int, int, int, int],
    ]:
        """Calculates color constants for rendering a team table.

        Args:
            team: The team data object.

        Returns:
            tuple: bg_fill, text_color, dimmed_color, gray_color.
        """
        color_hex = team.color_rgb
        r_sat, g_sat, b_sat = hex_to_rgb(color_hex)
        h, lightness, s = colorsys.rgb_to_hls(
            r_sat / 255.0, g_sat / 255.0, b_sat / 255.0
        )

        r_semi, g_semi, b_semi = colorsys.hls_to_rgb(h, lightness, s * 0.5)
        bg_fill = (int(r_semi * 255), int(g_semi * 255), int(b_semi * 255), 100)

        r_sat_hls, g_sat_hls, b_sat_hls = colorsys.hls_to_rgb(h, lightness, 1.0)
        text_color = (
            int(r_sat_hls * 255),
            int(g_sat_hls * 255),
            int(b_sat_hls * 255),
            255,
        )
        r_dim, g_dim, b_dim = colorsys.hls_to_rgb(
            h, max(0.0, lightness * 0.8), s * 0.5
        )
        dimmed_color = (
            int(r_dim * 255),
            int(g_dim * 255),
            int(b_dim * 255),
            255,
        )
        gray_color = (128, 128, 128, 255)
        return bg_fill, text_color, dimmed_color, gray_color

    def _draw_table_structure(
        self,
        draw: ImageDraw.ImageDraw,
        x_start: int,
        ty: int,
        table_width: int,
        th: int,
        bg_fill: tuple[int, int, int, int],
        border_color: tuple[int, int, int, int],
        columns: list[str],
        offsets: list[int],
        bold_font: ImageFont.ImageFont,
        header_h: int,
        padding_y: int,
        stroke_width: int,
        draw_background: bool,
        draw_borders: bool,
        max_hp_w: int = 0,
    ) -> int:
        """Draws the outer table rectangle and the header columns.

        Args:
            draw: ImageDraw context.
            x_start: X start coordinate.
            ty: Y start coordinate.
            table_width: Width of the table.
            th: Total table height.
            bg_fill: Background fill color.
            border_color: Border color.
            columns: List of column names.
            offsets: X offsets for each column.
            bold_font: Bold font.
            header_h: Header height.
            padding_y: Vertical padding.
            stroke_width: The text outline stroke width in pixels.
            draw_background: Whether to draw the table background color.
            draw_borders: Whether to draw the table borders and lines.
            max_hp_w: Maximum hitpoints width in pixels.

        Returns:
            int: The Y coordinate starting for player rows.
        """
        if draw_background:
            draw.rectangle(
                [x_start, ty, x_start + table_width, ty + th],
                fill=bg_fill,
                outline=border_color if draw_borders else None,
                width=2,
            )
        elif draw_borders:
            draw.rectangle(
                [x_start, ty, x_start + table_width, ty + th],
                fill=None,
                outline=border_color,
                width=2,
            )

        for col_name, offset in zip(columns, offsets):
            x_pos = offset
            if col_name == 'Player':
                x_pos += max_hp_w

            self._draw_text_with_fallback(
                draw,
                (x_pos, ty + header_h // 2),
                col_name,
                fill=(255, 255, 255, 255),
                font=bold_font,
                anchor='lm',
                stroke_width=stroke_width,
                stroke_fill=(0, 0, 0, 255),
            )

        sep_y = ty + header_h
        if draw_borders:
            draw.line(
                [(x_start, sep_y), (x_start + table_width, sep_y)],
                fill=border_color,
                width=2,
            )
        return sep_y

    def _draw_player_rows(
        self,
        draw: ImageDraw.ImageDraw,
        players: list[LFScoreboardPlayerData],
        columns: list[str],
        offsets: list[int],
        font: ImageFont.ImageFont,
        text_color: tuple[int, int, int, int],
        gray_color: tuple[int, int, int, int],
        dimmed_color: tuple[int, int, int, int],
        y_row: int,
        row_h: int,
        height: int,
        overlay: Image.Image | None,
        stroke_width: int,
        max_hp_w: int = 0,
    ) -> int:
        """Draws individual player rows inside the table.

        Args:
            draw: ImageDraw context.
            players: List of player objects.
            columns: List of columns.
            offsets: List of column offsets.
            font: Standard font.
            text_color: Active player text color.
            gray_color: Eliminated player text color.
            dimmed_color: Down player text color.
            y_row: Current Y position coordinate.
            row_h: Row height.
            height: Image height for scaling padding.
            overlay: The overlay Image for pasting role icons.
            stroke_width: The text outline stroke width in pixels.
            max_hp_w: Maximum hitpoints width in pixels.

        Returns:
            int: The Y coordinate ending after player rows.
        """
        for p in players:
            p_color = text_color
            if p.is_eliminated:
                p_color = gray_color
            elif p.is_down:
                p_color = dimmed_color

            vals = self._compile_player_row_values(p, columns)
            for col, val, offset in zip(columns, vals, offsets):
                if col == 'Role':
                    role_name = p.role_name.lower()
                    icon_path = Path('assets') / 'sm5' / f'{role_name}.png'
                    if icon_path.exists() and overlay is not None:
                        icon_size = int(row_h * 0.8)
                        role_img = self._get_cached_icon(icon_path, icon_size)
                        if role_img is not None:
                            icon_y = y_row + (row_h - icon_size) // 2
                            overlay.paste(role_img, (offset, icon_y), role_img)
                            continue

                stroke_fill = (
                    0,
                    0,
                    0,
                    p_color[3] if len(p_color) > 3 else 255,
                )

                x_pos = offset
                if col == 'Player':
                    x_pos += max_hp_w
                    if p.max_hp > 1:
                        scale = row_h / 28
                        img_w = overlay.width if overlay is not None else 1920
                        margin = int(5 * scale * img_w / 1920)

                        hp_text: str = '■' * p.max_hp
                        total_w_val = self._measure_text_width_with_fallback(
                            draw, hp_text, font
                        )
                        total_w: float = (
                            float(total_w_val)
                            if isinstance(total_w_val, (int, float))
                            else 0.0
                        )

                        char_w: float = total_w / p.max_hp

                        icon_size: int = 15
                        if not (
                            hasattr(draw, 'textbbox')
                            and 'Mock' in type(draw.textbbox).__name__
                        ):
                            bbox = draw.textbbox((0, 0), '■', font=font)
                            icon_size = max(1, int(bbox[3] - bbox[1]))

                        x_start_shield: float = (x_pos - margin) - total_w
                        y_shield: float = (y_row + row_h // 2) - icon_size // 2

                        for i in range(p.max_hp):
                            is_full: bool = i < p.hp
                            asset_name: str = (
                                'shield_full.png'
                                if is_full
                                else 'shield_empty.png'
                            )
                            shield_path: Path = Path('assets') / asset_name
                            shield_img = self._get_cached_tinted_icon(
                                shield_path, icon_size, p_color
                            )
                            if shield_img is not None:
                                shield_x: int = int(
                                    x_start_shield
                                    + i * char_w
                                    + (char_w - icon_size) // 2
                                )
                                overlay.paste(
                                    shield_img,
                                    (shield_x, int(y_shield)),
                                    shield_img,
                                )

                self._draw_text_with_fallback(
                    draw,
                    (x_pos, y_row + row_h // 2),
                    val,
                    fill=p_color,
                    font=font,
                    anchor='lm',
                    stroke_width=stroke_width,
                    stroke_fill=stroke_fill,
                )

                if col == 'Player':
                    num_penalties = p.penalties
                    if num_penalties > 0 and overlay is not None:
                        name_w = self._measure_text_width_with_fallback(
                            draw, val, font
                        )
                        scale = row_h / 28
                        margin = int(5 * scale * overlay.width / 1920)
                        card_x_start = x_pos + name_w + margin
                        card_img = self._get_cached_penalty_card(row_h)
                        if card_img is not None:
                            card_h = card_img.height
                            card_w = card_img.width
                            num_cards = min(3, num_penalties)
                            icon_y = y_row + (row_h - card_h) // 2
                            for i in range(num_cards):
                                card_x = card_x_start + i * (card_w // 2)
                                overlay.paste(
                                    card_img,
                                    (int(card_x), int(icon_y)),
                                    card_img,
                                )
                            if num_penalties > 3:
                                right_edge = (
                                    card_x_start
                                    + (num_cards - 1) * (card_w // 2)
                                    + card_w
                                )
                                text_x = right_edge + margin
                                self._draw_text_with_fallback(
                                    draw,
                                    (text_x, y_row + row_h // 2),
                                    f'x{num_penalties}',
                                    fill=p_color,
                                    font=font,
                                    anchor='lm',
                                    stroke_width=stroke_width,
                                    stroke_fill=stroke_fill,
                                )
            y_row += row_h
        return y_row

    def _draw_totals_row(
        self,
        draw: ImageDraw.ImageDraw,
        totals: dict[str, int],
        columns: list[str],
        offsets: list[int],
        bold_font: ImageFont.ImageFont,
        border_color: tuple[int, int, int, int],
        x_start: int,
        table_width: int,
        y_row: int,
        totals_h: int,
        stroke_width: int,
        draw_borders: bool,
        max_hp_w: int = 0,
    ) -> None:
        """Draws the totals row at the bottom of the table.

        Args:
            draw: ImageDraw context.
            totals: Dict of totals.
            columns: List of columns.
            offsets: List of column offsets.
            bold_font: Bold font.
            border_color: Border color.
            x_start: X start coordinate.
            table_width: Table width.
            y_row: Y coordinate starting the totals row.
            totals_h: Height of the totals row.
            stroke_width: The text outline stroke width in pixels.
            draw_borders: Whether to draw the totals separator line.
            max_hp_w: Maximum hitpoints width in pixels.
        """
        if draw_borders:
            draw.line(
                [(x_start, y_row), (x_start + table_width, y_row)],
                fill=border_color,
                width=2,
            )
        tot_vals = self._compile_totals_row_values(totals, columns)
        for col, val, offset in zip(columns, tot_vals, offsets):
            x_pos: int = offset
            if col == 'Player':
                x_pos += max_hp_w
            self._draw_text_with_fallback(
                draw,
                (x_pos, y_row + totals_h // 2),
                val,
                fill=(255, 255, 255, 255),
                font=bold_font,
                anchor='lm',
                stroke_width=stroke_width,
                stroke_fill=(0, 0, 0, 255),
            )

    def _draw_team_table(
        self,
        image: Image.Image,
        team: LFScoreboardTeamData,
        th: int,
        x_start: int,
        font: ImageFont.ImageFont,
        bold_font: ImageFont.ImageFont,
        header_font: ImageFont.ImageFont,
        header_h: int,
        row_h: int,
        stroke_width: int,
        draw_background: bool,
        draw_borders: bool,
        max_player_w: int | None = None,
        pixel_size: float | int = 27,
        max_hp_w: int = 0,
    ) -> None:
        """Draws a single team's table border, headers, and rows.

        Args:
            image: The Image canvas to draw on.
            team: The team data object.
            th: Total table height in pixels.
            x_start: The absolute starting X coordinate of the table.
            font: Standard size scoreboard text font.
            bold_font: Bold size scoreboard text font.
            header_font: Scoreboard column header font.
            header_h: The scoreboard header height in pixels.
            row_h: The scoreboard player row height in pixels.
            stroke_width: The text outline stroke width in pixels.
            draw_background: Whether to draw the table background color.
            draw_borders: Whether to draw the table borders and lines.
            max_player_w: Maximum player column width in pixels.
            pixel_size: Standard font size in pixels.
            max_hp_w: Maximum hitpoints width in pixels.
        """
        bg_fill, text_color, dimmed_color, gray_color = (
            self._calculate_team_colors(team)
        )
        border_color = text_color

        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        try:
            draw = ImageDraw.Draw(overlay)

            scale = pixel_size / 27
            table_width = int(650 * scale * image.width / 1920)
            ty = int(team.y_pos or 0)

            columns = ['Player']
            is_sm5 = (
                'sm5' in self.game.game_type.lower()
                or 'space marines' in self.game.game_type.lower()
            )
            if is_sm5:
                columns.append('Role')

            default_player_col_w = (
                int(160 * table_width / 650)
                if 'Role' in columns
                else int(210 * table_width / 650)
            )
            excess_w = 0
            if max_player_w is not None and max_player_w > default_player_col_w:
                excess_w = max_player_w - default_player_col_w
            actual_table_width = table_width + excess_w

            columns, offsets = self._resolve_scoreboard_columns(
                x_start, table_width, max_player_w
            )
            padding_y = int(5 * scale * image.height / 1080)

            sep_y = self._draw_table_structure(
                draw=draw,
                x_start=x_start,
                ty=ty,
                table_width=actual_table_width,
                th=th,
                bg_fill=bg_fill,
                border_color=border_color,
                columns=columns,
                offsets=offsets,
                bold_font=header_font,
                header_h=header_h,
                padding_y=padding_y,
                stroke_width=stroke_width,
                draw_background=draw_background,
                draw_borders=draw_borders,
                max_hp_w=max_hp_w,
            )

            y_row = self._draw_player_rows(
                draw=draw,
                players=team.players,
                columns=columns,
                offsets=offsets,
                font=font,
                text_color=text_color,
                gray_color=gray_color,
                dimmed_color=dimmed_color,
                y_row=sep_y,
                row_h=row_h,
                height=image.height,
                overlay=overlay,
                stroke_width=stroke_width,
                max_hp_w=max_hp_w,
            )

            totals_h = int(pixel_size * (35 / 27))
            self._draw_totals_row(
                draw=draw,
                totals=team.totals,
                columns=columns,
                offsets=offsets,
                bold_font=bold_font,
                border_color=border_color,
                x_start=x_start,
                table_width=actual_table_width,
                y_row=y_row,
                totals_h=totals_h,
                stroke_width=stroke_width,
                draw_borders=draw_borders,
                max_hp_w=max_hp_w,
            )

            image.alpha_composite(overlay)
        finally:
            overlay.close()

    def _resolve_scoreboard_columns(
        self,
        x_start: int,
        table_width: int,
        max_player_w: int | None = None,
    ) -> tuple[list[str], list[int]]:
        """Resolves which scoreboard columns to display based on game type.

        Args:
            x_start: Table starting X position.
            table_width: Table width in pixels.
            max_player_w: Maximum player column width in pixels.

        Returns:
            tuple: Active column headers and absolute X coordinates.
        """
        is_sm5 = (
            'sm5' in self.game.game_type.lower()
            or 'space marines' in self.game.game_type.lower()
        )

        columns = ['Player']
        if is_sm5:
            columns.append('Role')
        columns.append('Score')
        if is_sm5:
            columns.extend(['Lives', 'Shots', 'Missiles', 'Spec'])

        col_offset_map = {
            'Player': 20,
            'Role': 180,
            'Score': 230,
            'Lives': 330,
            'Shots': 410,
            'Missiles': 490,
            'Spec': 580,
        }

        default_player_col_w = (
            int(160 * table_width / 650)
            if 'Role' in columns
            else int(210 * table_width / 650)
        )
        excess_w = 0
        if max_player_w is not None and max_player_w > default_player_col_w:
            excess_w = max_player_w - default_player_col_w

        offsets = []
        for col in columns:
            offset_val = x_start + int(col_offset_map[col] * table_width / 650)
            if col != 'Player' and excess_w > 0:
                offset_val += excess_w
            offsets.append(offset_val)
        return columns, offsets

    def _compile_player_row_values(
        self, p: LFScoreboardPlayerData, columns: list[str]
    ) -> list[str]:
        """Compiles values for a player row in column order.

        Args:
            p: The player data object.
            columns: Active column headers.

        Returns:
            list[str]: Player row cell values.
        """
        vals = []
        for col in columns:
            if col == 'Player':
                vals.append(p.codename)
            elif col == 'Role':
                vals.append(p.role_name)
            elif col == 'Score':
                vals.append(str(p.score))
            elif col == 'Lives':
                vals.append(str(p.lives))
            elif col == 'Shots':
                vals.append(str(p.shots))
            elif col == 'Missiles':
                vals.append(str(p.missiles))
            elif col == 'Spec':
                vals.append(str(p.special_points))
        return vals

    def _compile_totals_row_values(
        self, totals: LFScoreboardTeamTotals, columns: list[str]
    ) -> list[str]:
        """Compiles values for the team totals row in column order.

        Args:
            totals: The team totals data object.
            columns: Active column headers.

        Returns:
            list[str]: Totals row cell values.
        """
        vals = []
        for col in columns:
            if col == 'Player':
                vals.append('TOTAL')
            elif col == 'Role':
                vals.append('')
            elif col == 'Score':
                vals.append(str(totals.score))
            elif col == 'Lives':
                vals.append(str(totals.lives))
            elif col == 'Shots':
                vals.append(str(totals.shots))
            elif col == 'Missiles':
                vals.append(str(totals.missiles))
            elif col == 'Spec':
                vals.append(str(totals.special_points))
        return vals

    def _draw_downtime_bar(self, image: Image.Image, el: UIElement) -> None:
        """Draws the downtime bar representing safe and resettable time.

        Args:
            image: The Image canvas to draw on.
            el: The downtime bar UIElement.
        """
        x = el.x if el.x is not None else 0.3
        y = el.y if el.y is not None else 0.3
        ext = el.extents if el.extents is not None else [0.4, 0.05]

        width, height = image.size
        x1 = int(width * x)
        y1 = int(height * y)
        x2 = int(width * (x + ext[0]))
        y2 = int(height * (y + ext[1]))

        W = x2 - x1
        H = y2 - y1
        if W <= 0 or H <= 0:
            return

        safe_ms = el.safe_ms
        resettable_ms = el.resettable_ms
        total_remaining_ms = safe_ms + resettable_ms

        if total_remaining_ms <= 0:
            return

        # Determine elapsed progress (0.0 to 1.0)
        progress = max(0.0, min(1.0, (8000 - total_remaining_ms) / 8000.0))

        path_full = Path('assets') / 'downtime-full.png'
        path_empty = Path('assets') / 'downtime-empty.png'

        if path_full.exists() and path_empty.exists():
            try:
                # Lazily load original images once per process
                if self._downtime_full is None:
                    self._downtime_full = Image.open(path_full).convert('RGBA')
                if self._downtime_empty is None:
                    self._downtime_empty = Image.open(path_empty).convert(
                        'RGBA'
                    )

                # Resize only if bar layout dimensions changed
                if self._downtime_cache_size != (W, H):
                    self._downtime_full_resized = self._downtime_full.resize(
                        (W, H), Image.Resampling.LANCZOS
                    )
                    self._downtime_empty_resized = self._downtime_empty.resize(
                        (W, H), Image.Resampling.LANCZOS
                    )
                    self._downtime_cache_size = (W, H)

                # Composite empty and full parts based on progress
                split_x = int(W * progress)

                combined = Image.new('RGBA', (W, H))
                try:
                    if split_x > 0:
                        left_part = self._downtime_empty_resized.crop(
                            (0, 0, split_x, H)
                        )
                        try:
                            combined.paste(left_part, (0, 0))
                        finally:
                            left_part.close()
                    if split_x < W:
                        right_part = self._downtime_full_resized.crop(
                            (split_x, 0, W, H)
                        )
                        try:
                            combined.paste(right_part, (split_x, 0))
                        finally:
                            right_part.close()

                    if el.alpha < 1.0:
                        r, g, b, a = combined.split()
                        try:
                            new_a = a.point(lambda p: int(p * el.alpha))
                            try:
                                combined_faded = Image.merge(
                                    'RGBA', (r, g, b, new_a)
                                )
                                try:
                                    image.alpha_composite(
                                        combined_faded, dest=(x1, y1)
                                    )
                                finally:
                                    combined_faded.close()
                            finally:
                                new_a.close()
                        finally:
                            r.close()
                            g.close()
                            b.close()
                            a.close()
                    else:
                        image.alpha_composite(combined, dest=(x1, y1))
                finally:
                    combined.close()
            except Exception as e:
                print(f'Warning: failed to composite downtime bar: {e}')

    def _load_text_font(
        self,
        font_file: str,
        style: str | None,
        pixel_size: float | int,
    ) -> ImageFont.ImageFont:
        """Resolves font variants and loads font with error fallback.

        Args:
            font_file: Font family/file name.
            style: Font style (e.g. bold, italic).
            pixel_size: Size of font in pixels.

        Returns:
            ImageFont.ImageFont: The loaded font.
        """
        if not hasattr(self, '_font_cache'):
            self._font_cache = {}
        if not hasattr(self, '_font_cache_lock'):
            self._font_cache_lock = threading.Lock()

        cache_key = ('text', font_file, style, pixel_size)
        with self._font_cache_lock:
            cached = self._font_cache.get(cache_key)
            if cached is not None:
                return cached

        if style == 'bold':
            if font_file.lower() == 'verdana':
                font_file = 'verdanab.ttf'
            elif font_file.lower() == 'arial':
                font_file = 'arialbd.ttf'
        elif style == 'italic':
            if font_file.lower() == 'verdana':
                font_file = 'verdanai.ttf'
            elif font_file.lower() == 'arial':
                font_file = 'ariali.ttf'

        resolved_file = self._resolve_font_path(font_file)
        try:
            font = ImageFont.truetype(resolved_file, pixel_size)
        except OSError:
            try:
                font = ImageFont.load_default(size=pixel_size)
            except TypeError:
                font = ImageFont.load_default()

        with self._font_cache_lock:
            self._font_cache[cache_key] = font
        return font

    def _draw_text_elements(
        self,
        image: Image.Image,
        elements: list[UIElement],
        config: dict[str, Any],
    ) -> None:
        """Draws all text elements onto the image.

        Args:
            image: The Image canvas to draw on.
            elements: The active elements on the frame.
            config: The merged video configuration options.
        """
        width, height = image.size

        anchor_map = {'left': 'la', 'center': 'ma', 'right': 'ra'}

        for el in elements:
            if el.element_type != 'text' or not el.text:
                continue

            x_coord = int(width * (el.x if el.x is not None else 0.5))
            y_coord = int(height * (el.y if el.y is not None else 0.5))
            anchor = anchor_map.get(el.align or 'left', 'la')

            pixel_size = max(1.0, float(height * el.style.size / 800))

            alpha_val = round(el.alpha if el.alpha is not None else 1.0, 2)
            cache_key = (
                el.text,
                el.style.font,
                el.style.style,
                pixel_size,
                el.style.color,
                el.style.background_color,
                height,
                alpha_val,
            )

            with self._text_cache_lock:
                cached_entry = self._text_cache.get(cache_key)

            if cached_entry is None:
                font = self._load_text_font(
                    font_file=el.style.font,
                    style=el.style.style,
                    pixel_size=pixel_size,
                )

                text_color = parse_color_with_alpha(el.style.color, alpha_val)
                bg_color = parse_color_with_alpha(
                    el.style.background_color, alpha_val
                )

                stroke_width = max(1, int(pixel_size * 0.05))
                padding = max(1, int(height * 4 / 800))
                margin = stroke_width + padding

                # Parse text into segments of text and images
                parts = IMAGE_TAG_PATTERN.split(el.text)
                segments = []
                for idx, part in enumerate(parts):
                    if idx % 2 == 1:
                        segments.append(
                            {
                                'type': 'image',
                                'path': Path('assets') / part,
                                'name': part,
                            }
                        )
                    else:
                        if part:
                            if el.player_to_color:
                                sub_segs = self._split_by_player_names(
                                    part, el.player_to_color
                                )
                                for sub_text, color_hex in sub_segs:
                                    segments.append(
                                        {
                                            'type': 'text',
                                            'text': sub_text,
                                            'color': color_hex,
                                        }
                                    )
                            else:
                                segments.append(
                                    {
                                        'type': 'text',
                                        'text': part,
                                    }
                                )

                # Measure dimensions of segments using a temp image
                temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
                try:
                    temp_draw = ImageDraw.Draw(temp_img)

                    # Pre-pass to determine text vertical bounds
                    min_y = 0.0
                    max_y = float(pixel_size)
                    for seg in segments:
                        if seg['type'] == 'text':
                            t_str = seg['text']
                            t_bbox = self._measure_text_bbox_with_fallback(
                                temp_draw, t_str, font=font, anchor='la'
                            )
                            if t_bbox[1] < min_y:
                                min_y = t_bbox[1]
                            if t_bbox[3] > max_y:
                                max_y = t_bbox[3]
                        elif seg['type'] == 'image':
                            img_path = seg['path']
                            if not img_path.exists():
                                fallback_text = f'[img:{seg["name"]}]'
                                t_bbox = self._measure_text_bbox_with_fallback(
                                    temp_draw,
                                    fallback_text,
                                    font=font,
                                    anchor='la',
                                )
                                if t_bbox[1] < min_y:
                                    min_y = t_bbox[1]
                                if t_bbox[3] > max_y:
                                    max_y = t_bbox[3]

                    line_h = max_y - min_y

                    resolved_segments = []
                    total_width = 0.0

                    for seg in segments:
                        if seg['type'] == 'text':
                            t_str = seg['text']
                            w = self._measure_text_width_with_fallback(
                                temp_draw, t_str, font=font
                            )
                            t_bbox = self._measure_text_bbox_with_fallback(
                                temp_draw, t_str, font=font, anchor='la'
                            )
                            t_h = t_bbox[3] - t_bbox[1]
                            resolved_segments.append(
                                {
                                    'type': 'text',
                                    'text': t_str,
                                    'width': w,
                                    'height': t_h,
                                    'bbox': t_bbox,
                                    'color': seg.get('color'),
                                }
                            )
                            total_width += w
                        elif seg['type'] == 'image':
                            img_path = seg['path']
                            if img_path.exists():
                                try:
                                    with Image.open(img_path) as raw_seg_img:
                                        img_rgba = raw_seg_img.convert('RGBA')
                                        bbox = img_rgba.getbbox()
                                        if bbox:
                                            img_w = bbox[2] - bbox[0]
                                            img_h = bbox[3] - bbox[1]
                                        else:
                                            img_w, img_h = img_rgba.size
                                        aspect = img_w / img_h
                                        # Use entire height of the text (line_h)
                                        w = line_h * aspect
                                        resolved_segments.append(
                                            {
                                                'type': 'image',
                                                'path': img_path,
                                                'width': w,
                                                'height': line_h,
                                                'bbox': bbox,
                                            }
                                        )
                                        total_width += w
                                        img_rgba.close()
                                except Exception as e:
                                    print(
                                        'Warning: failed to open image '
                                        f'segment {img_path}: {e}'
                                    )
                            else:
                                # Fallback if image file doesn't exist
                                fallback_text = f'[img:{seg["name"]}]'
                                w = self._measure_text_width_with_fallback(
                                    temp_draw, fallback_text, font=font
                                )
                                t_bbox = self._measure_text_bbox_with_fallback(
                                    temp_draw,
                                    fallback_text,
                                    font=font,
                                    anchor='la',
                                )
                                t_h = t_bbox[3] - t_bbox[1]
                                resolved_segments.append(
                                    {
                                        'type': 'text',
                                        'text': fallback_text,
                                        'width': w,
                                        'height': t_h,
                                        'bbox': t_bbox,
                                    }
                                )
                                total_width += w
                finally:
                    temp_img.close()

                img_w = int(total_width + 2 * margin)
                img_h = int((max_y - min_y) + 2 * margin)

                small_img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(small_img)

                # Draw background rectangle if color is specified
                if bg_color[3] > 0:
                    rect_bbox = (
                        margin,
                        margin,
                        margin + total_width,
                        margin + (max_y - min_y),
                    )
                    padded_rect = (
                        rect_bbox[0] - padding,
                        rect_bbox[1] - padding,
                        rect_bbox[2] + padding,
                        rect_bbox[3] + padding,
                    )
                    draw.rectangle(padded_rect, fill=bg_color)

                # Draw/paste segments
                seg_x = 0.0
                for r_seg in resolved_segments:
                    if r_seg['type'] == 'text':
                        draw_x = seg_x + margin
                        draw_y = -min_y + margin
                        seg_color_hex = r_seg.get('color')
                        if seg_color_hex:
                            seg_color = parse_color_with_alpha(
                                seg_color_hex, alpha_val
                            )
                        else:
                            seg_color = text_color
                        stroke_color = (
                            0,
                            0,
                            0,
                            seg_color[3] if len(seg_color) > 3 else 255,
                        )
                        self._draw_text_with_fallback(
                            draw,
                            (draw_x, draw_y),
                            r_seg['text'],
                            fill=seg_color,
                            font=font,
                            anchor='la',
                            stroke_width=stroke_width,
                            stroke_fill=stroke_color,
                        )
                        seg_x += r_seg['width']
                    elif r_seg['type'] == 'image':
                        draw_x = seg_x + margin
                        draw_y = margin + (line_h - r_seg['height']) / 2
                        try:
                            with Image.open(r_seg['path']) as raw_seg_img:
                                target_w = int(r_seg['width'])
                                target_h = int(r_seg['height'])
                                if target_w > 0 and target_h > 0:
                                    img_rgba = raw_seg_img.convert('RGBA')
                                    bbox = r_seg.get('bbox')
                                    if bbox:
                                        cropped = img_rgba.crop(bbox)
                                    else:
                                        cropped = img_rgba

                                    try:
                                        resized_seg = cropped.resize(
                                            (target_w, target_h),
                                            Image.Resampling.LANCZOS,
                                        )
                                    finally:
                                        if bbox:
                                            cropped.close()
                                        img_rgba.close()

                                    # Handle alpha fading
                                    if el.alpha < 1.0:
                                        r_ch, g_ch, b_ch, a_ch = (
                                            resized_seg.split()
                                        )
                                        try:
                                            new_a_ch = a_ch.point(
                                                lambda p: int(p * el.alpha)
                                            )
                                            try:
                                                faded_seg = Image.merge(
                                                    'RGBA',
                                                    (
                                                        r_ch,
                                                        g_ch,
                                                        b_ch,
                                                        new_a_ch,
                                                    ),
                                                )
                                                try:
                                                    small_img.alpha_composite(
                                                        faded_seg,
                                                        dest=(
                                                            int(draw_x),
                                                            int(draw_y),
                                                        ),
                                                    )
                                                finally:
                                                    faded_seg.close()
                                                new_a_ch.close()
                                            finally:
                                                pass
                                        finally:
                                            r_ch.close()
                                            g_ch.close()
                                            b_ch.close()
                                            a_ch.close()
                                    else:
                                        small_img.alpha_composite(
                                            resized_seg,
                                            dest=(int(draw_x), int(draw_y)),
                                        )
                        except Exception as e:
                            print(
                                f'Warning: failed to composite segment image: {e}'
                            )
                        seg_x += r_seg['width']

                # Compute final paste offsets
                if anchor == 'la':
                    offset_x = -margin
                elif anchor == 'ma':
                    offset_x = -total_width / 2 - margin
                elif anchor == 'ra':
                    offset_x = -total_width - margin
                else:
                    offset_x = -margin

                offset_y = min_y - margin
                cached_entry = (small_img, offset_x, offset_y)

                with self._text_cache_lock:
                    if cache_key not in self._text_cache:
                        if len(self._text_cache) >= 1000:
                            oldest_key = next(iter(self._text_cache))
                            oldest_img, _, _ = self._text_cache.pop(oldest_key)
                            oldest_img.close()
                        self._text_cache[cache_key] = cached_entry

            small_img, offset_x, offset_y = cached_entry
            paste_x = int(x_coord + offset_x)
            paste_y = int(y_coord + offset_y)
            image.alpha_composite(small_img, dest=(paste_x, paste_y))

    def _get_icon_path(self, icon_name: str) -> Path | None:
        """Finds the path to the icon file in the assets directory.

        Args:
            icon_name: Name of the icon (e.g. 'lives').

        Returns:
            Path | None: The path to the icon or None if it does not exist.
        """
        p = Path('assets') / f'{icon_name}.png'
        if p.exists():
            return p
        return None

    def _split_by_player_names(
        self,
        text: str,
        player_to_color: dict[str, str],
    ) -> list[tuple[str, str | None]]:
        """Splits an event description into segments of text and player colors.

        Args:
            text: The event description string.
            player_to_color: Mapping of player names to their hex colors.

        Returns:
            list[tuple[str, str | None]]: List of segments (text, color).
        """
        sorted_names = sorted(player_to_color.keys(), key=len, reverse=True)
        parts: list[tuple[str, str | None]] = [(text, None)]

        for name in sorted_names:
            new_parts: list[tuple[str, str | None]] = []
            for part_text, color in parts:
                if color is not None:
                    new_parts.append((part_text, color))
                    continue

                start = 0
                while True:
                    idx = part_text.find(name, start)
                    if idx == -1:
                        new_parts.append((part_text[start:], None))
                        break
                    if idx > start:
                        new_parts.append((part_text[start:idx], None))
                    new_parts.append((name, player_to_color[name]))
                    start = idx + len(name)
            parts = [p for p in new_parts if p[0]]
        return parts

    def _draw_counter(
        self,
        image: Image.Image,
        el: UIElement,
        config: dict[str, Any],
    ) -> None:
        """Draws a Counter element with a circular arc, icon, and text.

        Args:
            image: The Image canvas to draw on.
            el: The Counter UIElement.
            config: Merged video configuration options.
        """
        current = el.current_value if el.current_value is not None else 0
        maximum = el.max_value if el.max_value is not None else 1

        pct = current / maximum if maximum > 0 else 0.0
        pct = max(0.0, min(1.0, pct))

        if el.icon == 'sp':
            color = (76, 175, 80, 255)
        elif pct < 0.2:
            color = (255, 77, 77, 255)
        elif pct < 0.5:
            color = (255, 235, 59, 255)
        else:
            color = (76, 175, 80, 255)

        width, height = image.size
        ext = el.extents if el.extents is not None else [0.05, 0.05]
        diameter = int(height * ext[1])
        if diameter <= 0:
            return

        x_coord = int(width * (el.x if el.x is not None else 0.2))
        y_coord = int(height * (el.y if el.y is not None else 0.9))

        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        try:
            draw = ImageDraw.Draw(overlay)

            thickness = max(2, int(diameter * 0.1))
            circle_bbox = [
                x_coord,
                y_coord,
                x_coord + diameter,
                y_coord + diameter,
            ]

            if pct > 0.0:
                start_angle: float = 135.0
                end_angle: float = 135.0 + pct * 360.0

                segments: list[tuple[float, float]] = [(start_angle, end_angle)]

                if (
                    el.indicator_interval
                    and el.indicator_interval > 0
                    and maximum > 0
                ):
                    gap_degrees: float = 12.0
                    indicator_values: list[int] = [0]
                    val: int = el.indicator_interval
                    while val < maximum:
                        indicator_values.append(val)
                        val += el.indicator_interval

                    for v in indicator_values:
                        angle_v: float = 135.0 + (v / maximum) * 360.0
                        gap_start: float = angle_v - gap_degrees / 2.0
                        gap_end: float = angle_v + gap_degrees / 2.0

                        new_segments: list[tuple[float, float]] = []
                        for seg_start, seg_end in segments:
                            if gap_end <= seg_start or gap_start >= seg_end:
                                new_segments.append((seg_start, seg_end))
                            else:
                                if gap_start <= seg_start < gap_end < seg_end:
                                    new_segments.append((gap_end, seg_end))
                                elif seg_start < gap_start < seg_end <= gap_end:
                                    new_segments.append((seg_start, gap_start))
                                elif (
                                    seg_start < gap_start and gap_end < seg_end
                                ):
                                    new_segments.append((seg_start, gap_start))
                                    new_segments.append((gap_end, seg_end))
                        segments = new_segments

                for seg_start, seg_end in segments:
                    if seg_end - seg_start >= 0.1:
                        draw.arc(
                            circle_bbox,
                            start=seg_start,
                            end=seg_end,
                            fill=color,
                            width=thickness,
                        )

            if el.icon:
                icon_path = self._get_icon_path(el.icon)
                if icon_path and icon_path.exists():
                    icon_size = int(diameter * 0.55)
                    icon_img = self._get_cached_icon(icon_path, icon_size)
                    if icon_img is not None:
                        cx = x_coord + diameter // 2
                        cy = y_coord + diameter // 2
                        overlay.paste(
                            icon_img,
                            (cx - icon_size // 2, cy - icon_size // 2),
                            icon_img,
                        )

            text_str = f'{current}/{maximum}'
            pixel_size = max(1.0, float(height * el.style.size / 800))
            font = self._load_text_font(
                el.style.font, el.style.style, pixel_size
            )

            spacing = int(diameter * 0.2)
            tx = x_coord + diameter + spacing
            ty = y_coord + diameter // 2

            alpha_color = (
                color[0],
                color[1],
                color[2],
                int(color[3] * el.alpha),
            )
            bg_hex = el.style.background_color
            bg_color = parse_color_with_alpha(bg_hex, el.alpha)

            if bg_color[3] > 0:
                bbox = self._measure_text_bbox_with_fallback(
                    draw, text_str, font=font, anchor='lm'
                )
                padding = max(1, int(height * 4 / 800))
                padded_bbox = (
                    bbox[0] - padding,
                    bbox[1] - padding,
                    bbox[2] + padding,
                    bbox[3] + padding,
                )
                draw.rectangle(padded_bbox, fill=bg_color)

            stroke_color = (0, 0, 0, alpha_color[3])
            self._draw_text_with_fallback(
                draw,
                (tx, ty),
                text_str,
                fill=alpha_color,
                font=font,
                anchor='lm',
                stroke_width=max(1, int(pixel_size * 0.05)),
                stroke_fill=stroke_color,
            )
            if el.alpha < 1.0:
                r, g, b, a = overlay.split()
                try:
                    new_a = a.point(lambda p: int(p * el.alpha))
                    try:
                        overlay_faded = Image.merge('RGBA', (r, g, b, new_a))
                        try:
                            image.alpha_composite(overlay_faded)
                        finally:
                            overlay_faded.close()
                    finally:
                        new_a.close()
                finally:
                    r.close()
                    g.close()
                    b.close()
                    a.close()
            else:
                image.alpha_composite(overlay)
        finally:
            overlay.close()

    def _draw_event_scroller(
        self,
        image: Image.Image,
        el: UIElement,
        time_ms: int,
        config: dict[str, Any],
    ) -> None:
        """Draws a tilted Event Scroller list of game events.

        Args:
            image: The Image canvas to draw on.
            el: The Event Scroller UIElement.
            time_ms: The current millisecond timestamp.
            config: Merged video configuration options.
        """
        events = el.events_data or []
        player_to_color = el.player_to_color or {}

        active_events = [ev for ev in events if ev.time <= time_ms]
        if not active_events:
            return

        width, height = image.size
        ext = el.extents if el.extents is not None else [0.4, 0.4]
        W = int(width * ext[0])
        H = int(height * ext[1])
        if W <= 0 or H <= 0:
            return

        x_coord = int(width * (el.x if el.x is not None else 0.55))
        y_coord = int(height * (el.y if el.y is not None else 0.45))

        pixel_size = max(1.0, float(height * el.style.size / 800))
        font = self._load_text_font(el.style.font, el.style.style, pixel_size)
        row_height = int(pixel_size * 1.4)

        anim = config.get('animation', 'ease-in-out')
        scroll_duration_ms = 500

        idx = len(active_events) - 1
        target_offset = idx * row_height
        t_latest = active_events[-1].time

        prev_idx = -1
        for i in range(len(active_events) - 2, -1, -1):
            if active_events[i].time < t_latest:
                prev_idx = i
                break

        if prev_idx == -1:
            prev_offset = 0.0
        else:
            prev_offset = prev_idx * row_height

        elapsed = time_ms - t_latest
        if elapsed < scroll_duration_ms:
            p = elapsed / scroll_duration_ms
            p_anim = apply_animation(p, anim)
            y_scroll = prev_offset + (target_offset - prev_offset) * p_anim
        else:
            y_scroll = target_offset

        temp_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        try:
            draw_temp = ImageDraw.Draw(temp_img)

            for i, ev in enumerate(active_events):
                y_pos = (H - row_height) + (i * row_height - y_scroll)
                if y_pos < -row_height or y_pos > H:
                    continue

                desc = ev.desc
                segments = self._split_by_player_names(desc, player_to_color)
                x_cursor = 10

                for text_part, color_hex in segments:
                    if color_hex:
                        color = parse_color_with_alpha(color_hex, el.alpha)
                    else:
                        color = parse_color_with_alpha(el.style.color, el.alpha)

                    stroke_color = (
                        0,
                        0,
                        0,
                        color[3] if len(color) > 3 else 255,
                    )
                    self._draw_text_with_fallback(
                        draw_temp,
                        (x_cursor, int(y_pos)),
                        text_part,
                        fill=color,
                        font=font,
                        anchor='la',
                        stroke_width=max(1, int(pixel_size * 0.05)),
                        stroke_fill=stroke_color,
                    )
                    x_cursor += int(
                        self._measure_text_width_with_fallback(
                            draw_temp, text_part, font
                        )
                    )

            # Add fade to the top of the event scroller.
            fade_height = int(H * 0.25)
            if fade_height > 0:
                gradient_1 = Image.new('L', (1, H), 255)
                try:
                    for y in range(fade_height):
                        alpha = int(255 * (y / fade_height))
                        gradient_1.putpixel((0, y), alpha)
                    gradient_resized = gradient_1.resize((W, H))
                finally:
                    gradient_1.close()

                try:
                    r, g, b, a = temp_img.split()
                    try:
                        new_a = ImageChops.multiply(a, gradient_resized)
                        try:
                            faded_img = Image.merge('RGBA', (r, g, b, new_a))
                            temp_img.close()
                            temp_img = faded_img
                        finally:
                            new_a.close()
                    finally:
                        r.close()
                        g.close()
                        b.close()
                        a.close()
                finally:
                    gradient_resized.close()

            el_config = config.get('elements', {}).get('all_game_events', {})
            tilt = el_config.get('tilt', 10.0)

            if tilt != 0.0:
                import math

                dx = H * math.tan(math.radians(tilt))
                dx = max(0.0, min(W * 0.45, dx))

                a = W / (W - 2.0 * dx)
                b = W * dx / (H * (W - 2.0 * dx))
                c = -W * dx / (W - 2.0 * dx)
                d = 0.0
                e = a
                f = 0.0
                g = 0.0
                h = (a - 1.0) / H

                coeffs = (a, b, c, d, e, f, g, h)
                try:
                    transformed_img = temp_img.transform(
                        (W, H),
                        Image.Transform.PERSPECTIVE,
                        coeffs,
                        Image.Resampling.BILINEAR,
                    )
                    temp_img.close()
                    temp_img = transformed_img
                except Exception as e:
                    print(f'Warning: perspective transform failed: {e}')

            image.paste(temp_img, (x_coord, y_coord), temp_img)
        finally:
            temp_img.close()
