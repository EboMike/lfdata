import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Any
import pytest


@pytest.fixture(autouse=True)
def cleanup_dummy_pref():
    """Fixture to clean up dummy preferences files after each test."""
    yield
    dummy = Path('dummy_nonexistent_pref.json')
    if dummy.exists():
        try:
            os.remove(dummy)
        except Exception:
            pass


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
        self._selection: list[Any] = []
        self._mapped: bool = True
        self._options: dict[str, Any] = {}

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self._mapped = True

    def pack(self, *args: Any, **kwargs: Any) -> None:
        self._mapped = True

    def place(self, *args: Any, **kwargs: Any) -> None:
        self._mapped = True

    def pack_propagate(self, *args: Any, **kwargs: Any) -> None:
        pass

    def grid_propagate(self, *args: Any, **kwargs: Any) -> None:
        pass

    def grid_remove(self, *args: Any, **kwargs: Any) -> None:
        self._mapped = False

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

    def winfo_ismapped(self) -> bool:
        return self._mapped

    def winfo_width(self) -> int:
        return 300

    def winfo_height(self) -> int:
        return 150

    def __setitem__(self, key: str, value: Any) -> None:
        self._options[key] = value
        if key == 'state':
            self._state = value
        elif key == 'text':
            self.text = str(value)
        elif key == 'image':
            self.image = value

    def __getitem__(self, key: str) -> Any:
        return self._options.get(key)

    def config(self, *args: Any, **kwargs: Any) -> None:
        self._options.update(kwargs)
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

    def protocol(self, *args: Any, **kwargs: Any) -> None:
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

    # Listbox / Treeview common methods
    def delete(self, *args: Any, **kwargs: Any) -> None:
        self._items = []

    def insert(self, *args: Any, **kwargs: Any) -> str:
        if len(args) >= 2 and isinstance(args[0], str):
            iid = kwargs.get('iid', args[2] if len(args) > 2 else None)
            text = kwargs.get('text', args[3] if len(args) > 3 else '')
            item_name = iid or text
            if item_name:
                self._items.append(str(item_name))
                return str(item_name)
        elif len(args) >= 2:
            self._items.append(str(args[1]))
            return str(args[1])
        return ''

    def curselection(self) -> list[int]:
        res = []
        for s in self._selection:
            if s in self._items:
                res.append(self._items.index(s))
        return res

    def selection_clear(self, *args: Any) -> None:
        self._selection = []

    def selection_set(self, *args: Any) -> None:
        if not args:
            self._selection = []
            return
        val = args[0]
        if isinstance(val, (list, tuple)):
            self._selection = list(val)
        else:
            self._selection = [val]

    def selection(self) -> list[Any]:
        return self._selection

    def get_children(self) -> list[str]:
        return self._items

    def exists(self, item: str) -> bool:
        return item in self._items

    def item(self, item: str, **kwargs: Any) -> None:
        pass

    def identify_row(self, y: int) -> str | None:
        return self._items[0] if self._items else None

    def identify_element(self, x: int, y: int) -> str:
        return 'image'

    def see(self, index: Any) -> None:
        pass

    def yview(self, *args: Any, **kwargs: Any) -> None:
        pass


class DummyCanvas(DummyWidget):
    """Mock Canvas widget for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.selected_element = None

    def delete(self, *args: Any, **kwargs: Any) -> None:
        pass

    def create_line(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_rectangle(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_oval(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_text(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_window(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def itemconfig(self, *args: Any, **kwargs: Any) -> None:
        pass

    def yview_scroll(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bbox(self, *args: Any, **kwargs: Any) -> tuple[int, int, int, int]:
        return (0, 0, 100, 100)

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
tkinter.ttk.Treeview = DummyWidget
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


def test_app_properties_updated_refresh_preview() -> None:
    """Tests that modifying properties triggers an image preview update."""
    app = LFDataUIApp()
    app.preview = MagicMock()

    app._on_properties_updated()

    assert app.preview.update_preview.called


def test_app_save_preferences(tmp_path) -> None:
    """Tests saving user preferences to a JSON file."""
    pref_file = tmp_path / 'pref.json'
    app = LFDataUIApp(preferences_path=pref_file)

    # Set mock geometry return value
    app.geometry = MagicMock(return_value='1180x820+100+100')

    app._save_preferences(
        tdf_path='dummy.tdf',
        config_path='dummy.yaml',
    )

    assert pref_file.exists()
    import json

    with open(pref_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data.get('most_recent_tdf') == 'dummy.tdf'
    assert data.get('most_recent_config') == 'dummy.yaml'
    assert data.get('window_geometry') == '1180x820+100+100'


@patch.object(LFDataUIApp, '_load_config_path')
@patch.object(LFDataUIApp, '_load_tdf_path')
def test_app_load_preferences_on_startup(
    mock_load_tdf: MagicMock,
    mock_load_config: MagicMock,
    tmp_path,
) -> None:
    """Tests reloading preferences on app startup."""
    pref_file = tmp_path / 'pref.json'
    dummy_tdf = tmp_path / 'dummy.tdf'
    dummy_config = tmp_path / 'dummy.yaml'

    # Write dummy files to disk so os.path.exists passes
    dummy_tdf.write_text('dummy content', encoding='utf-8')
    dummy_config.write_text('dummy content', encoding='utf-8')

    # Save preferences to preferences file
    import json

    pref_data = {
        'most_recent_tdf': str(dummy_tdf),
        'most_recent_config': str(dummy_config),
        'window_geometry': '1180x820+100+100',
    }
    with open(pref_file, 'w', encoding='utf-8') as f:
        json.dump(pref_data, f)

    # Patch geometry to verify it was set on startup
    with patch.object(LFDataUIApp, 'geometry') as mock_geom:
        LFDataUIApp(preferences_path=pref_file)
        mock_geom.assert_any_call('1180x820+100+100')

    mock_load_config.assert_called_once_with(str(dummy_config))
    mock_load_tdf.assert_called_once_with(str(dummy_tdf))
