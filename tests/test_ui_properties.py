"""Tests for the PropertiesPanel class."""

from typing import Any
from unittest.mock import MagicMock
import pytest


# Universal Dummy definitions to prevent conflicts in sys.modules
class DummyStringVar:
    """Mock StringVar for testing."""

    def __init__(self, value: str = '') -> None:
        self._val = str(value)

    def get(self) -> str:
        return self._val

    def set(self, value: str) -> None:
        self._val = str(value)


class DummyBooleanVar:
    """Mock BooleanVar for testing."""

    def __init__(self, value: bool = False) -> None:
        self._val = bool(value)

    def get(self) -> bool:
        return self._val

    def set(self, value: bool) -> None:
        self._val = bool(value)


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

    def __getattr__(self, name: str) -> Any:
        return MagicMock()

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


# Directly monkeypatch the loaded tkinter modules
import tkinter  # noqa: E402
import tkinter.ttk  # noqa: E402

tkinter.StringVar = DummyStringVar
tkinter.BooleanVar = DummyBooleanVar
tkinter.Canvas = DummyWidget
tkinter.ttk.Frame = DummyWidget
tkinter.ttk.Scrollbar = DummyWidget
tkinter.ttk.LabelFrame = DummyWidget
tkinter.ttk.Label = DummyWidget
tkinter.ttk.Entry = DummyWidget
tkinter.ttk.Combobox = DummyWidget
tkinter.ttk.Checkbutton = DummyWidget
tkinter.NORMAL = 'normal'
tkinter.DISABLED = 'disabled'

from lfdata.ui.properties import PropertiesPanel  # noqa: E402
from lfdata.ui.config_manager import UIConfigManager  # noqa: E402


@pytest.fixture
def manager() -> UIConfigManager:
    """Fixture returning a fresh config manager.

    Returns:
        UIConfigManager: Config manager instance.
    """
    cm = UIConfigManager()
    cm.update_element('time', 'enabled', True)
    cm.update_element('time', 'x', 0.8)
    cm.update_element('time', 'y', 0.2)
    cm.update_element('time', 'align', 'right')
    cm.update_element('time', 'font', 'advanced_pixel_lcd-7')
    cm.update_element('time', 'size', 40)
    cm.update_element('time', 'visible_start_ms', 1000)
    return cm


def test_properties_load_element(manager: UIConfigManager) -> None:
    """Tests loading an element into properties panel form variables."""
    update_called = False

    def on_update() -> None:
        nonlocal update_called
        update_called = True

    parent = MagicMock()
    panel = PropertiesPanel(parent, manager, on_update)

    # Initial state should be disabled/clear
    assert panel.selected_element is None

    # Load element
    panel.load_element('time')
    assert panel.selected_element == 'time'
    assert panel.enabled_var.get() is True
    assert panel.x_var.get() == '0.800'
    assert panel.y_var.get() == '0.200'
    assert panel.align_var.get() == 'right'
    assert panel.font_var.get() == 'advanced_pixel_lcd-7'
    assert panel.size_var.get() == '40'
    assert panel.tilt_var.get() == '0.000'
    assert panel.start_ms_var.get() == '1000'
    assert panel.x_anim_var.get() is False
    assert panel.tilt_anim_var.get() is False
    assert panel.anim_overview.winfo_ismapped() is False


def test_properties_clear(manager: UIConfigManager) -> None:
    """Tests clearing the properties panel."""
    parent = MagicMock()
    panel = PropertiesPanel(parent, manager, lambda: None)

    panel.load_element('time')
    panel.load_element(None)

    assert panel.selected_element is None
    assert panel.x_var.get() == ''
    assert panel.y_var.get() == ''
    assert panel.align_var.get() == ''
    assert panel.font_var.get() == ''


def test_properties_apply(manager: UIConfigManager) -> None:
    """Tests applying form changes updates config manager."""
    update_called = False

    def on_update() -> None:
        nonlocal update_called
        update_called = True

    parent = MagicMock()
    panel = PropertiesPanel(parent, manager, on_update)

    panel.load_element('time')

    # Change values in variables
    panel.x_var.set('0.15')
    panel.y_var.set('0.85')
    panel.w_var.set('0.3')
    panel.h_var.set('0.2')
    panel.size_var.set('25')
    panel.start_ms_var.set('5000')

    # Apply changes
    panel._apply_properties()

    assert update_called is True
    el = manager.get_element('time')
    assert el is not None
    assert el.get('x') == 0.15
    assert el.get('y') == 0.85
    assert el.get('extents') == [0.3, 0.2]
    assert el.get('style', {}).get('size') == 25
    assert el.get('visible_start_ms') == 5000

    # Test applying tilt
    panel.tilt_var.set('5.5')
    panel._apply_properties()
    assert el.get('tilt') == 5.5

    # Test toggling animation on property 'x'
    assert panel.anim_overview.winfo_ismapped() is False
    panel._toggle_anim('x')
    assert panel.x_anim_var.get() is True
    assert panel.anim_overview.winfo_ismapped() is True

    # Test toggling animation off
    panel._toggle_anim('x')
    assert panel.x_anim_var.get() is False
    assert panel.anim_overview.winfo_ismapped() is False


def test_properties_start_time_offset(manager: UIConfigManager) -> None:
    """Tests loading, clearing, and applying start_time_offset."""
    parent = MagicMock()
    panel = PropertiesPanel(parent, manager, lambda: None)

    # 1. Load element (default value check)
    panel.load_element('time')
    assert panel.start_time_offset_var.get() == 'beginning of video'

    # 2. Change start_time_offset combobox selection
    panel.start_time_offset_var.set('beginning of game')
    # Trigger selection handler
    panel._on_start_time_offset_select(MagicMock())

    el = manager.get_element('time')
    assert el is not None
    assert el.get('start_time_offset') == 'beginning of game'

    # 3. Apply properties saving it
    panel.start_time_offset_var.set('end of game')
    panel._apply_properties()
    assert el.get('start_time_offset') == 'end of game'

    # 4. Clear panel resets value
    panel.clear()
    assert panel.start_time_offset_var.get() == ''


def test_properties_end_time_offset(manager: UIConfigManager) -> None:
    """Tests loading, clearing, and applying end_time_offset."""
    parent = MagicMock()
    panel = PropertiesPanel(parent, manager, lambda: None)

    # 1. Load element (default value check)
    panel.load_element('time')
    assert panel.end_time_offset_var.get() == 'beginning of game'

    # 2. Change end_time_offset combobox selection
    panel.end_time_offset_var.set('beginning of video')
    # Trigger selection handler
    panel._on_end_time_offset_select(MagicMock())

    el = manager.get_element('time')
    assert el is not None
    assert el.get('end_time_offset') == 'beginning of video'

    # 3. Apply properties saving it
    panel.end_time_offset_var.set('end of game')
    panel._apply_properties()
    assert el.get('end_time_offset') == 'end of game'

    # 4. Clear panel resets value
    panel.clear()
    assert panel.end_time_offset_var.get() == ''


def test_properties_hit_border(manager: UIConfigManager) -> None:
    """Tests loading, applying, and clearing hit_border properties."""
    # Ensure hit_border exists in the manager config
    manager.update_element('hit_border', 'enabled', True)
    manager.update_element('hit_border', 'duration_hp_s', 0.5)
    manager.update_element('hit_border', 'duration_down_s', 1.0)
    manager.update_element('hit_border', 'max_scale', 1.2)
    manager.update_element('hit_border', 'color_zapped_hp', '#ffff00')
    manager.update_element('hit_border', 'color_resupplied', '#ffffff')
    manager.update_element('hit_border', 'color_other', '#ff0000')

    parent = MagicMock()
    panel = PropertiesPanel(parent, manager, lambda: None)

    # 1. Load hit_border
    panel.load_element('hit_border')
    assert panel.selected_element == 'hit_border'
    assert panel.enabled_var.get() is True
    assert panel.hb_dur_hp_var.get() == '0.5'
    assert panel.hb_dur_down_var.get() == '1.0'
    assert panel.hb_max_scale_var.get() == '1.2'
    assert panel.hb_col_zap_var.get() == '#ffff00'
    assert panel.hb_col_resup_var.get() == '#ffffff'
    assert panel.hb_col_other_var.get() == '#ff0000'

    # 2. Modify and apply
    panel.hb_dur_hp_var.set('0.8')
    panel.hb_max_scale_var.set('1.5')
    panel.hb_col_zap_var.set('#00ff00')
    panel._apply_properties()

    el = manager.get_element('hit_border')
    assert el is not None
    assert el.get('duration_hp_s') == 0.8
    assert el.get('max_scale') == 1.5
    assert el.get('color_zapped_hp') == '#00ff00'

    # 3. Clear panel
    panel.clear()
    assert panel.hb_dur_hp_var.get() == ''
    assert panel.hb_max_scale_var.get() == ''
    assert panel.hb_col_zap_var.get() == ''
