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
    """A universal mocked Tkinter widget to prevent library/display dependencies."""

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

    def after(self, *args: Any, **kwargs: Any) -> None:
        pass

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
