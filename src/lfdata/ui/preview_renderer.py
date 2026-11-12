"""In-memory and subprocess frame rendering engine for the UI preview panel.

This module provides `PreviewRenderer`, a rendering service that caches
precomputed replay simulation snapshots (`VisualElementGenerator`) to deliver
fast in-memory preview rendering for the active game session, with automatic
fallback to CLI subprocess execution when needed.

Usage example:
    from lfdata.ui.preview_renderer import PreviewRenderer

    renderer = PreviewRenderer()
    image = renderer.render_frame(
        game=game,
        tdf_path=tdf_path,
        time_ms=15000,
        config=config_dict,
        player_name='Alpha',
    )
"""

from pathlib import Path
import subprocess
import tempfile
import threading
import yaml
from PIL import Image

from lfdata.model.objects.game import LFGame
from lfdata.video.constants import DEFAULT_PREGAME_DELAY_MS
from lfdata.video.generator import VisualElementGenerator
from lfdata.video.renderer import VideoGenerator


class PreviewRenderer:
    """Renders video HUD frames with in-memory caching and subprocess fallback.

    Attributes:
        _hud_generators: Dictionary mapping cache keys to precomputed
            VisualElementGenerator instances.
        _video_generators: Dictionary mapping game IDs to VideoGenerator
            instances.
        _lock: Thread synchronization lock for cache operations.
    """

    def __init__(self) -> None:
        """Initializes the preview renderer with empty generator caches."""
        self._hud_generators: dict[
            tuple[int, str | None, int], VisualElementGenerator
        ] = {}
        self._video_generators: dict[int, VideoGenerator] = {}
        self._lock = threading.Lock()

    def get_or_create_generators(
        self,
        game: LFGame,
        player_name: str | None,
        config: dict[str, object],
    ) -> tuple[VisualElementGenerator, VideoGenerator]:
        """Gets cached generators or constructs new ones for the game session.

        Args:
            game: The LFGame data model instance.
            player_name: Optional focused player codename string.
            config: Video layout configuration dictionary.

        Returns:
            tuple: Active VisualElementGenerator and VideoGenerator instances.
        """
        raw_pregame = config.get('pregame_delay_ms', DEFAULT_PREGAME_DELAY_MS)
        pregame_delay_ms = (
            int(raw_pregame)
            if isinstance(raw_pregame, (int, float, str))
            else DEFAULT_PREGAME_DELAY_MS
        )
        norm_player = player_name if player_name != 'None' else None
        cache_key = (id(game), norm_player, pregame_delay_ms)

        with self._lock:
            if cache_key in self._hud_generators:
                hud_gen = self._hud_generators[cache_key]
                vid_gen = self._video_generators[id(game)]
                hud_gen.config = config
                return hud_gen, vid_gen

            vid_gen = self._video_generators.get(id(game))
            if vid_gen is None:
                vid_gen = VideoGenerator(game=game)
                self._video_generators[id(game)] = vid_gen

            hud_gen = VisualElementGenerator(
                game=game,
                player_name=norm_player,
                config=config,
            )
            self._hud_generators[cache_key] = hud_gen
            return hud_gen, vid_gen

    def render_in_memory(
        self,
        game: LFGame,
        time_ms: int,
        config: dict[str, object],
        player_name: str | None = None,
    ) -> Image.Image:
        """Renders a preview frame in-memory using cached generators.

        Args:
            game: The LFGame data model instance.
            time_ms: Timestamp in milliseconds to render.
            config: Video layout configuration dictionary.
            player_name: Optional focused player codename string.

        Returns:
            Image.Image: The rendered PIL image frame.
        """
        hud_gen, vid_gen = self.get_or_create_generators(
            game=game,
            player_name=player_name,
            config=config,
        )
        elements = hud_gen.generate_at(time_ms=time_ms)
        return vid_gen._render_frame(
            elements=elements,
            time_ms=time_ms,
            config=config,
            hud_gen=hud_gen,
        )

    def render_via_subprocess(
        self,
        tdf_path: str,
        time_ms: int,
        config: dict[str, object],
        player_name: str | None,
        base_cmd: list[str],
    ) -> Image.Image:
        """Renders a preview frame by invoking the lfdata CLI executable.

        Args:
            tdf_path: Filesystem path to the input TDF file.
            time_ms: Timestamp in milliseconds to render.
            config: Video layout configuration dictionary.
            player_name: Optional focused player codename string.
            base_cmd: CLI executable prefix command list.

        Returns:
            Image.Image: The rendered PIL image frame loaded from disk.

        Raises:
            FileNotFoundError: If the output image file is not found.
            subprocess.CalledProcessError: If CLI execution fails.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cfg_path = temp_path / 'temp_config.yaml'
            with open(cfg_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, default_flow_style=False)

            cmd = base_cmd + [
                '--input_tdf',
                tdf_path,
                '--config',
                str(cfg_path),
                '--image-outdir',
                str(temp_path),
                '--image-at',
                str(time_ms),
            ]
            if player_name and player_name != 'None':
                cmd.extend(['--video_player', player_name])

            subprocess.run(cmd, check=True, capture_output=True)
            img_file = temp_path / f'image_at_{time_ms}.png'
            if not img_file.exists():
                raise FileNotFoundError(
                    f'Preview file not found: {img_file}'
                )

            with Image.open(img_file) as raw_img:
                return raw_img.copy()

    def render_frame(
        self,
        game: LFGame | None,
        tdf_path: str | None,
        time_ms: int,
        config: dict[str, object],
        player_name: str | None = None,
        base_cmd: list[str] | None = None,
    ) -> Image.Image:
        """Renders a frame using in-memory cache or subprocess fallback.

        Args:
            game: Optional LFGame model instance.
            tdf_path: Optional path to the TDF file.
            time_ms: Timestamp in milliseconds to render.
            config: Video layout configuration dictionary.
            player_name: Optional focused player codename string.
            base_cmd: Optional CLI command prefix list.

        Returns:
            Image.Image: Rendered frame PIL image.

        Raises:
            RuntimeError: If neither game nor TDF path is provided.
        """
        if game is not None:
            try:
                return self.render_in_memory(
                    game=game,
                    time_ms=time_ms,
                    config=config,
                    player_name=player_name,
                )
            except Exception:
                if tdf_path is not None and base_cmd is not None:
                    return self.render_via_subprocess(
                        tdf_path=tdf_path,
                        time_ms=time_ms,
                        config=config,
                        player_name=player_name,
                        base_cmd=base_cmd,
                    )
                raise

        if tdf_path is not None and base_cmd is not None:
            return self.render_via_subprocess(
                tdf_path=tdf_path,
                time_ms=time_ms,
                config=config,
                player_name=player_name,
                base_cmd=base_cmd,
            )

        raise RuntimeError(
            'Cannot render preview: neither LFGame nor TDF path provided.'
        )

    def clear_cache(self) -> None:
        """Clears all cached element and video generator objects."""
        with self._lock:
            self._hud_generators.clear()
            self._video_generators.clear()
