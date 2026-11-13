from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from lfdata.model.objects.game import LFGame
from lfdata.ui.preview_renderer import PreviewRenderer


def test_preview_renderer_init() -> None:
    renderer = PreviewRenderer()
    assert len(renderer._hud_generators) == 0
    assert len(renderer._video_generators) == 0


def test_preview_renderer_in_memory_render() -> None:
    game = LFGame(game_id='test_game', duration=600000, game_type='SM5')
    renderer = PreviewRenderer()
    config: dict[str, object] = {
        'elements': {
            'time': {'enabled': True, 'x': 0.5, 'y': 0.1},
        },
        'fps': 30,
        'resolution': [640, 360],
    }

    img = renderer.render_in_memory(
        game=game,
        time_ms=5000,
        config=config,
        player_name=None,
    )
    assert isinstance(img, Image.Image)
    assert img.size == (640, 360)


def test_preview_renderer_caches_generator() -> None:
    game = LFGame(game_id='test_game_cache', duration=600000, game_type='SM5')
    renderer = PreviewRenderer()
    config: dict[str, object] = {
        'elements': {},
        'fps': 30,
        'resolution': [640, 360],
    }

    hud_gen1, vid_gen1 = renderer.get_or_create_generators(
        game=game,
        player_name=None,
        config=config,
    )
    hud_gen2, vid_gen2 = renderer.get_or_create_generators(
        game=game,
        player_name=None,
        config=config,
    )

    assert hud_gen1 is hud_gen2
    assert vid_gen1 is vid_gen2


def test_preview_renderer_caches_per_player() -> None:
    game = LFGame(game_id='test_game_players', duration=600000)
    renderer = PreviewRenderer()
    config: dict[str, object] = {'elements': {}}

    hud_p1, _ = renderer.get_or_create_generators(
        game=game,
        player_name='Alpha',
        config=config,
    )
    hud_p2, _ = renderer.get_or_create_generators(
        game=game,
        player_name='Bravo',
        config=config,
    )

    assert hud_p1 is not hud_p2


def test_preview_renderer_clear_cache() -> None:
    game = LFGame(game_id='test_clear', duration=600000)
    renderer = PreviewRenderer()
    config: dict[str, object] = {'elements': {}}

    renderer.get_or_create_generators(
        game=game,
        player_name=None,
        config=config,
    )
    assert len(renderer._hud_generators) == 1
    assert len(renderer._video_generators) == 1

    renderer.clear_cache()
    assert len(renderer._hud_generators) == 0
    assert len(renderer._video_generators) == 0


@patch('subprocess.run')
@patch('PIL.Image.open')
def test_preview_renderer_subprocess_fallback(
    mock_open: MagicMock,
    mock_run: MagicMock,
) -> None:
    mock_img = MagicMock()
    mock_img.copy.return_value = mock_img
    mock_open.return_value.__enter__.return_value = mock_img

    def touch_file(cmd: list[str], **kwargs: object) -> MagicMock:
        out_dir = cmd[cmd.index('--image-outdir') + 1]
        time_at = cmd[cmd.index('--image-at') + 1]
        out_file = Path(out_dir) / f'image_at_{time_at}.png'
        out_file.touch()
        return MagicMock()

    mock_run.side_effect = touch_file

    renderer = PreviewRenderer()
    config: dict[str, object] = {'fps': 30}
    img = renderer.render_frame(
        game=None,
        tdf_path='sample.tdf',
        time_ms=10000,
        config=config,
        player_name='PlayerX',
        base_cmd=['python', '-m', 'lfdata'],
    )

    assert mock_run.called is True
    assert img == mock_img


def test_preview_renderer_missing_sources_raises() -> None:
    renderer = PreviewRenderer()
    with pytest.raises(RuntimeError, match='neither LFGame nor TDF path'):
        renderer.render_frame(
            game=None,
            tdf_path=None,
            time_ms=0,
            config={},
            player_name=None,
            base_cmd=None,
        )


def test_preview_renderer_cancelled_returns_none() -> None:
    game = LFGame(game_id='test_cancel', duration=600000, game_type='SM5')
    renderer = PreviewRenderer()
    config: dict[str, object] = {'elements': {}}

    img = renderer.render_frame(
        game=game,
        tdf_path=None,
        time_ms=5000,
        config=config,
        player_name=None,
        is_cancelled=lambda: True,
    )
    assert img is None


def test_preview_renderer_thread_lock_synchronization() -> None:
    import threading

    game = LFGame(game_id='test_thread_lock', duration=600000, game_type='SM5')
    renderer = PreviewRenderer()
    config: dict[str, object] = {'elements': {}}

    results: list[Image.Image | None] = []

    def worker(time_ms: int) -> None:
        frame = renderer.render_frame(
            game=game,
            tdf_path=None,
            time_ms=time_ms,
            config=config,
            player_name=None,
        )
        results.append(frame)

    t1 = threading.Thread(target=worker, args=(1000,))
    t2 = threading.Thread(target=worker, args=(2000,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    assert all(isinstance(r, Image.Image) for r in results)


