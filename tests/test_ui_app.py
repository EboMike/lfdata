"""Tests for the LFDataUIApp class."""

from unittest.mock import MagicMock, patch
from typing import Any


class DummyStringVar:
    """Mock StringVar for testing."""

    def __init__(self, value: str = '') -> None:
        self._val = str(value)

    def get(self) -> str:
        return self._val

    def set(self, value: str) -> None:
        self._val = str(value)


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
        if args and isinstance(args[0], int):
            idx = args[0]
            if 0 <= idx < len(self._items):
                return self._items[idx]
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


class DummyCanvas(DummyWidget):
    """Mock Canvas widget for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        pass

    def create_line(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_rectangle(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_text(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def select_element(self, *args: Any, **kwargs: Any) -> None:
        pass

    def refresh_elements(self, *args: Any, **kwargs: Any) -> None:
        pass


class DummyMenu:
    """Mock Menu widget for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def add_cascade(self, *args: Any, **kwargs: Any) -> None:
        pass

    def add_command(self, *args: Any, **kwargs: Any) -> None:
        pass

    def add_separator(self, *args: Any, **kwargs: Any) -> None:
        pass


# Patch all Tkinter classes globally
import tkinter  # noqa: E402
import tkinter.ttk  # noqa: E402

tkinter.Tk = DummyWidget
tkinter.Canvas = DummyCanvas
tkinter.Menu = DummyMenu
tkinter.Listbox = DummyWidget
tkinter.StringVar = DummyStringVar
tkinter.DoubleVar = DummyDoubleVar
tkinter.BooleanVar = MagicMock

tkinter.ttk.PanedWindow = DummyWidget
tkinter.ttk.Frame = DummyWidget
tkinter.ttk.LabelFrame = DummyWidget
tkinter.ttk.Label = DummyWidget
tkinter.ttk.Entry = DummyWidget
tkinter.ttk.Combobox = DummyWidget
tkinter.ttk.Scale = DummyWidget
tkinter.ttk.Button = DummyWidget
tkinter.ttk.Scrollbar = DummyWidget
tkinter.ttk.Checkbutton = DummyWidget
tkinter.NORMAL = 'normal'
tkinter.DISABLED = 'disabled'

from lfdata.ui.app import LFDataUIApp  # noqa: E402


def test_app_initialization() -> None:
    """Tests initializing the main application and populating settings."""
    app = LFDataUIApp()

    # Check that managers and sub-panels were instantiated
    assert app.config_manager is not None
    assert app.canvas is not None
    assert app.properties is not None
    assert app.preview is not None

    # Check global settings fields initial values (from DEFAULT_CONFIG)
    assert app.fps_var.get() == '60'
    assert app.width_var.get() == '1920'
    assert app.height_var.get() == '1080'
    assert app.pregame_delay_ms_var.get() == '0'

    # Check that Listbox contains some elements
    assert app.lst_elements._items
    assert 'time' in app.lst_elements._items


def test_app_sync_selection() -> None:
    """Tests synchronizing element selection between components."""
    app = LFDataUIApp()

    # Trigger select element
    app._on_element_selected('time')

    # Selected item in listbox should be 'time'
    selected_indices = app.lst_elements.curselection()
    assert selected_indices
    assert app.lst_elements.get(selected_indices[0]) == 'time'
    assert app.properties.selected_element == 'time'


def test_app_global_settings_change() -> None:
    """Tests modifying FPS and Resolution fields updates the config."""
    app = LFDataUIApp()

    # Set new global fields
    app.fps_var.set('30')
    app.width_var.set('1280')
    app.height_var.set('720')
    app.pregame_delay_ms_var.set('2000')

    # Trigger setting changed callback
    app._on_global_setting_changed()

    cfg = app.config_manager.config
    assert cfg.get('fps') == 30
    assert cfg.get('resolution') == [1280, 720]
    assert cfg.get('pregame_delay_ms') == 2000


@patch('tkinter.filedialog.askopenfilename')
def test_app_open_config(mock_dialog: MagicMock) -> None:
    """Tests opening a config file updates the settings widgets."""
    app = LFDataUIApp()

    # Create dummy config file content
    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(
        suffix='.yaml', mode='w', encoding='utf-8', delete=False
    ) as f:
        temp_name = f.name
        yaml.safe_dump(
            {'fps': 24, 'resolution': [640, 480], 'pregame_delay_ms': 500}, f
        )

    try:
        mock_dialog.return_value = temp_name
        app._open_config()

        # Check values were updated
        assert app.fps_var.get() == '24'
        assert app.width_var.get() == '640'
        assert app.height_var.get() == '480'
        assert app.pregame_delay_ms_var.get() == '500'
    finally:
        import os

        if os.path.exists(temp_name):
            os.remove(temp_name)
