"""Tests for the ImagePreview class."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import pytest


class DummyDoubleVar:
    """Mock DoubleVar for testing."""

    def __init__(self, value: float = 0.0) -> None:
        self._val = float(value)

    def get(self) -> float:
        return self._val

    def set(self, value: float) -> None:
        self._val = float(value)


class DummyWidget:
    """Mocked Tkinter widget to prevent library/display dependencies."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._state: str = 'normal'
        self.image: Any = None
        self.text: str = ''
        self._items: list[str] = []
        self._selection: list[int] = []

    def grid(self, *args: Any, **kwargs: Any) -> None:
        pass

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def place(self, *args: Any, **kwargs: Any) -> None:
        pass

    def pack_propagate(self, *args: Any, **kwargs: Any) -> None:
        pass

    def grid_propagate(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, *args: Any, **kwargs: Any) -> None:
        pass

    def grid_columnconfigure(self, *args: Any, **kwargs: Any) -> None:
        pass

    def grid_rowconfigure(self, *args: Any, **kwargs: Any) -> None:
        pass

    def rowconfigure(self, *args: Any, **kwargs: Any) -> None:
        pass

    def columnconfigure(self, *args: Any, **kwargs: Any) -> None:
        pass

    def winfo_children(self) -> list[Any]:
        return []

    def __setitem__(self, key: str, value: Any) -> None:
        if key == 'state':
            self._state = value
        elif key == 'text':
            self.text = str(value)
        elif key == 'image':
            self.image = value

    def config(self, *args: Any, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)
        if 'image' in kwargs:
            self.image = kwargs['image']
        if 'text' in kwargs:
            self.text = kwargs['text']

    def configure(self, *args: Any, **kwargs: Any) -> None:
        self.config(*args, **kwargs)

    def update_idletasks(self) -> None:
        pass

    def update(self) -> None:
        pass

    def after(self, *args: Any, **kwargs: Any) -> str:
        if len(args) > 1 and callable(args[1]):
            self._scheduled = args[1]
        return 'timer_1'

    def after_cancel(self, *args: Any, **kwargs: Any) -> None:
        self._scheduled = None

    def title(self, *args: Any, **kwargs: Any) -> None:
        pass

    def geometry(self, *args: Any, **kwargs: Any) -> None:
        pass

    def minsize(self, *args: Any, **kwargs: Any) -> None:
        pass

    def destroy(self) -> None:
        pass

    def add(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set(self, *args: Any, **kwargs: Any) -> None:
        pass

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return ''

    # Listbox methods
    def delete(self, start: int, end: Any = None) -> None:
        self._items = []

    def insert(self, index: Any, item: str) -> None:
        self._items.append(item)

    def curselection(self) -> list[int]:
        return self._selection

    def selection_clear(self, *args: Any) -> None:
        self._selection = []

    def selection_set(self, index: int) -> None:
        self._selection = [index]

    def see(self, index: int) -> None:
        pass

    def yview(self, *args: Any, **kwargs: Any) -> None:
        pass


# Directly monkeypatch variables & widgets
import tkinter  # noqa: E402
import tkinter.ttk  # noqa: E402

tkinter.DoubleVar = DummyDoubleVar
tkinter.StringVar = MagicMock
tkinter.ttk.LabelFrame = DummyWidget
tkinter.ttk.Frame = DummyWidget
tkinter.ttk.Label = DummyWidget
tkinter.ttk.Combobox = DummyWidget
tkinter.ttk.Scale = DummyWidget
tkinter.ttk.Button = DummyWidget

from lfdata.ui.preview import ImagePreview  # noqa: E402
from lfdata.ui.config_manager import UIConfigManager  # noqa: E402


@pytest.fixture
def manager() -> UIConfigManager:
    """Fixture returning a fresh config manager.

    Returns:
        UIConfigManager: The configuration manager.
    """
    cm = UIConfigManager()
    cm.tdf_path = 'dummy.tdf'
    cm.players = ['Player1', 'Player2']
    return cm


@patch('subprocess.run')
@patch('PIL.Image.open')
@patch('PIL.ImageTk.PhotoImage')
def test_preview_update(
    mock_photo: MagicMock,
    mock_open: MagicMock,
    mock_run: MagicMock,
    manager: UIConfigManager,
) -> None:
    """Tests preview rendering invokes the lfdata CLI with correct params."""
    # Setup mock image size and PhotoImage
    mock_img = MagicMock()
    mock_img.size = (1920, 1080)
    mock_img.copy.return_value = mock_img
    mock_img.resize.return_value = mock_img
    mock_open.return_value.__enter__.return_value = mock_img
    mock_photo.return_value = 'mock_photo_image'

    # side effect to create the empty file inside temp directory
    def touch_file(cmd: list[str], **kwargs: Any) -> MagicMock:
        out_dir = cmd[cmd.index('--image-outdir') + 1]
        time_at = cmd[cmd.index('--image-at') + 1]
        out_file = Path(out_dir) / f'image_at_{time_at}.png'
        out_file.touch()
        return MagicMock()

    mock_run.side_effect = touch_file

    parent = MagicMock()
    preview = ImagePreview(parent, manager)
    preview.current_time_ms = 15000
    preview.player_var.get = MagicMock(return_value='Player1')

    # Trigger update
    preview.update_preview()

    # Verify subprocess called with expected CLI args
    assert mock_run.called is True
    args = mock_run.call_args[0][0]
    assert '--input_tdf' in args
    assert 'dummy.tdf' in args
    assert '--image-at' in args
    assert '15000' in args
    assert '--video_player' in args
    assert 'Player1' in args

    # Verify image display logic
    assert preview.lbl_image.image == 'mock_photo_image'
    assert preview.lbl_image.text == ''


def test_preview_slider_movement(manager: UIConfigManager) -> None:
    """Tests that moving the timeline slider updates time text label."""
    parent = MagicMock()
    preview = ImagePreview(parent, manager)

    # Move slider to 25000ms
    preview._on_slider_move('25000.0')

    assert preview.current_time_ms == 25000
    assert '25,000 ms' in preview.lbl_time.text


def test_preview_slider_callback(manager: UIConfigManager) -> None:
    """Tests that moving the timeline slider triggers the callback."""
    parent = MagicMock()
    callback_val = None

    def callback(val: int) -> None:
        nonlocal callback_val
        callback_val = val

    preview = ImagePreview(parent, manager, on_time_changed_callback=callback)

    # Move slider to 35000ms
    preview._on_slider_move('35000.0')

    assert preview.current_time_ms == 35000
    assert callback_val == 35000


def test_preview_in_memory_render(manager: UIConfigManager) -> None:
    from lfdata.model.objects.game import LFGame

    parent = MagicMock()
    manager.game = LFGame(game_id='in_mem_game', duration=600000)
    preview = ImagePreview(parent, manager)
    preview.renderer = MagicMock()
    mock_img = MagicMock()
    mock_img.size = (640, 360)
    preview.renderer.render_frame.return_value = mock_img
    preview._show_image = MagicMock()

    preview.update_preview()

    assert preview.renderer.render_frame.called is True
    assert preview.last_rendered_image == mock_img
    assert preview._show_image.called is True


def test_preview_debounced_schedule(manager: UIConfigManager) -> None:
    parent = MagicMock()
    preview = ImagePreview(parent, manager)
    preview.update_preview = MagicMock()

    preview.schedule_preview(debounce_ms=100)
    assert preview._debounce_timer_id is not None

    preview._on_debounce_fired()
    assert preview._debounce_timer_id is None
    assert preview.update_preview.called is True


def test_preview_stale_generation_discarded(manager: UIConfigManager) -> None:
    parent = MagicMock()
    preview = ImagePreview(parent, manager)
    preview.last_rendered_image = None
    preview._render_generation = 5

    old_img = MagicMock()
    preview._on_render_success(img=old_img, gen_id=4)
    assert preview.last_rendered_image is None

    current_img = MagicMock()
    preview._show_image = MagicMock()
    preview._on_render_success(img=current_img, gen_id=5)
    assert preview.last_rendered_image == current_img
    assert preview._show_image.called is True


def test_preview_render_error_handling(manager: UIConfigManager) -> None:
    parent = MagicMock()
    preview = ImagePreview(parent, manager)
    preview._render_generation = 3

    preview._on_render_error(err_msg='Disk error', gen_id=2)
    assert 'Failed' not in preview.lbl_image.text

    preview._on_render_error(err_msg='Disk error', gen_id=3)
    assert 'Failed to render: Disk error' in preview.lbl_image.text


def test_preview_slider_move_schedules_render(
    manager: UIConfigManager,
) -> None:
    parent = MagicMock()
    preview = ImagePreview(parent, manager)
    preview.schedule_preview = MagicMock()
    callback_calls: list[int] = []
    preview.on_time_changed_callback = lambda t: callback_calls.append(t)

    preview._on_slider_move('12345')

    assert preview.current_time_ms == 12345
    assert manager.current_time_ms == 12345
    assert callback_calls == [12345]
    preview.schedule_preview.assert_called_once_with(debounce_ms=100)


def test_preview_slider_max_from_video_end_ms(
    manager: UIConfigManager,
) -> None:
    from lfdata.model.objects.game import LFGame

    parent = MagicMock()
    manager.game = LFGame(game_id='test_end_game', duration=600000)
    preview = ImagePreview(parent, manager)
    mock_hud = MagicMock()
    mock_hud.get_video_end_ms.return_value = 615000
    preview.renderer.get_or_create_generators = MagicMock(
        return_value=(mock_hud, MagicMock())
    )
    preview.update_preview = MagicMock()

    preview.on_tdf_loaded()

    assert getattr(preview.slider, 'to', None) == 615000.0


