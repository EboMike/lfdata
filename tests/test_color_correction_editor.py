"""Tests for ColorCorrectionEditorApp main window."""

from typing import Any
from unittest.mock import MagicMock, patch

from lfdata.color_correction.editor import ColorCorrectionEditorApp, main
from lfdata.color_correction.time_range import TimeRange


class DummyWidget:
    """Mock widget for headless testing of UI editor components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._options: dict[str, Any] = dict(kwargs)
        self.text: str = str(kwargs.get('text', ''))
        self.image: Any = kwargs.get('image', None)
        self._items: list[str] = []
        self._selection: list[Any] = []
        self._mapped: bool = True
        self._w: str = '.'
        self.tk: Any = MagicMock()
        self.children: dict[str, Any] = {}

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def pack_propagate(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, *args: Any, **kwargs: Any) -> None:
        pass

    def title(self, *args: Any, **kwargs: Any) -> None:
        pass

    def geometry(self, *args: Any, **kwargs: Any) -> None:
        pass

    def minsize(self, *args: Any, **kwargs: Any) -> None:
        pass

    def config(self, *args: Any, **kwargs: Any) -> None:
        self._options.update(kwargs)
        if 'text' in kwargs:
            self.text = str(kwargs['text'])
        if 'image' in kwargs:
            self.image = kwargs['image']

    def configure(self, *args: Any, **kwargs: Any) -> None:
        self.config(*args, **kwargs)

    def cget(self, key: str) -> Any:
        return self._options.get(key, getattr(self, key, ''))

    def winfo_width(self) -> int:
        return 640

    def winfo_height(self) -> int:
        return 360

    def heading(self, *args: Any, **kwargs: Any) -> None:
        pass

    def column(self, *args: Any, **kwargs: Any) -> None:
        pass

    def yview(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set(self, *args: Any, **kwargs: Any) -> None:
        pass

    def insert(self, *args: Any, **kwargs: Any) -> str:
        iid = str(len(self._items) + 1)
        self._items.append(iid)
        return iid

    def delete(self, *args: Any, **kwargs: Any) -> None:
        self._items = []

    def get_children(self) -> list[str]:
        return list(self._items)

    def selection(self) -> list[Any]:
        return list(self._selection)

    def selection_set(self, item: Any) -> None:
        self._selection = [item] if not isinstance(item, list) else item

    def item(self, item: str, *args: Any, **kwargs: Any) -> Any:
        return self._options.get(f'item_{item}_values', {})


class DummyCanvas(DummyWidget):
    """Mock Canvas for timeline drawing."""

    def delete(self, *args: Any, **kwargs: Any) -> None:
        pass

    def create_line(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_rectangle(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_polygon(self, *args: Any, **kwargs: Any) -> int:
        return 1


class DummyNotebook(DummyWidget):
    """Mock ttk.Notebook supporting tab states and selection."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tabs: list[dict[str, Any]] = []
        self._current_index: int = 0

    def add(self, child: Any, **kwargs: Any) -> None:
        tab_info = {'child': child, 'state': 'normal'}
        tab_info.update(kwargs)
        self._tabs.append(tab_info)

    def tab(self, tab_id: int, option: str | None = None, **kwargs: Any) -> Any:
        if 0 <= tab_id < len(self._tabs):
            if kwargs:
                self._tabs[tab_id].update(kwargs)
            if option is not None:
                return self._tabs[tab_id].get(option)
            return self._tabs[tab_id]
        return None

    def index(self, tab_id: Any) -> int:
        if tab_id == 'current':
            return self._current_index
        if isinstance(tab_id, int):
            return tab_id
        return 0

    def select(self, tab_id: Any = None) -> Any:
        if tab_id is not None:
            if isinstance(tab_id, int):
                self._current_index = tab_id
        return self._current_index


def create_mocked_app() -> ColorCorrectionEditorApp:
    with (
        patch('tkinter.Tk.__init__', return_value=None),
        patch('tkinter.Tk.title', return_value=None),
        patch('tkinter.Tk.geometry', return_value=None),
        patch('tkinter.Tk.minsize', return_value=None),
        patch('tkinter.ttk.Notebook', DummyNotebook),
        patch('tkinter.ttk.Frame', DummyWidget),
        patch('tkinter.ttk.Label', DummyWidget),
        patch('tkinter.ttk.Button', DummyWidget),
        patch('tkinter.ttk.LabelFrame', DummyWidget),
        patch('tkinter.ttk.Treeview', DummyWidget),
        patch('tkinter.ttk.Scrollbar', DummyWidget),
        patch('tkinter.Canvas', DummyCanvas),
    ):
        return ColorCorrectionEditorApp()


def test_editor_app_init() -> None:
    app = create_mocked_app()
    assert app.app_title == 'Color Correction Editor'
    assert app.notebook is not None
    assert app.tab_reference is not None
    assert app.tab_color_correction is not None
    assert app.notebook.tab(1, option='state') == 'disabled'


def test_editor_app_tab_state_transitions() -> None:
    app = create_mocked_app()
    assert app.notebook.tab(1, option='state') == 'disabled'

    # Adding a range enables Tab 1
    sample_range = TimeRange(start_ms=1000, end_ms=4000)
    app.tab_reference.add_range(time_range=sample_range)
    assert app.notebook.tab(1, option='state') == 'normal'

    # Select tab 1 and delete range -> disables Tab 1 and resets to Tab 0
    app.notebook.select(1)
    app.tab_reference.delete_range_at(index=0)
    assert app.notebook.tab(1, option='state') == 'disabled'
    assert app.notebook.index('current') == 0


def test_editor_app_enforce_no_switch_when_empty() -> None:
    app = create_mocked_app()
    app.notebook.select(1)
    mock_event = MagicMock()
    app._on_tab_changed(event=mock_event)
    assert app.notebook.index('current') == 0


def test_editor_main() -> None:
    with (
        patch.object(ColorCorrectionEditorApp, 'mainloop') as mock_mainloop,
        patch.object(ColorCorrectionEditorApp, '__init__', return_value=None),
    ):
        main()
        mock_mainloop.assert_called_once()
