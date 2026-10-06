"""Tests for ReferenceVideoTab component."""

from typing import Any
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest

from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.video_reader import VideoReader


class DummyWidget:
    """Mock widget for headless testing of tab components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._options: dict[str, Any] = dict(kwargs)
        self.text: str = str(kwargs.get('text', ''))
        self.image: Any = kwargs.get('image', None)
        self._items: list[str] = []
        self._selection: list[Any] = []
        self._mapped: bool = True

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def pack_propagate(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, *args: Any, **kwargs: Any) -> None:
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
        if 'values' in kwargs:
            self._options[f'item_{iid}_values'] = kwargs['values']
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
        if args and args[0] == 'values':
            return self._options.get(
                f'item_{item}_values', (1, '00:00.000', '00:05.000', '5.000s')
            )
        return self._options.get(f'item_{item}_values', {})


class DummyCanvas(DummyWidget):
    """Mock Canvas for timeline integration in tab."""

    def delete(self, *args: Any, **kwargs: Any) -> None:
        pass

    def create_line(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_rectangle(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_polygon(self, *args: Any, **kwargs: Any) -> int:
        return 1


with (
    patch('tkinter.ttk.Frame', DummyWidget),
    patch('tkinter.ttk.Label', DummyWidget),
    patch('tkinter.ttk.Button', DummyWidget),
    patch('tkinter.ttk.LabelFrame', DummyWidget),
    patch('tkinter.ttk.Treeview', DummyWidget),
    patch('tkinter.ttk.Scrollbar', DummyWidget),
    patch('tkinter.Canvas', DummyCanvas),
):
    import sys

    sys.modules.pop('lfdata.color_correction.reference_video_tab', None)
    sys.modules.pop('lfdata.color_correction.timeline_widget', None)
    from lfdata.color_correction.reference_video_tab import ReferenceVideoTab


@pytest.fixture(autouse=True)
def patch_tkinter_for_reference_tab() -> Any:
    with (
        patch('tkinter.ttk.Frame', DummyWidget),
        patch('tkinter.ttk.Label', DummyWidget),
        patch('tkinter.ttk.Button', DummyWidget),
        patch('tkinter.ttk.LabelFrame', DummyWidget),
        patch('tkinter.ttk.Treeview', DummyWidget),
        patch('tkinter.ttk.Scrollbar', DummyWidget),
        patch('tkinter.Canvas', DummyCanvas),
    ):
        yield


@pytest.fixture
def mock_video_reader() -> VideoReader:
    reader = MagicMock(spec=VideoReader)
    reader.duration_ms = 45000
    reader.fps = 30.0
    reader.width = 1920
    reader.height = 1080
    reader.load.return_value = 45000
    reader.get_frame_at.return_value = Image.new('RGB', (160, 120), 'blue')
    return reader


def test_reference_video_tab_init() -> None:
    tab = ReferenceVideoTab(parent=DummyWidget())
    assert tab.ranges == []
    assert tab.btn_load_video is not None
    assert not tab.is_video_loaded


def test_reference_video_tab_load_video(
    mock_video_reader: VideoReader,
) -> None:
    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        video_reader=mock_video_reader,
    )
    tab.load_video('test_reference.mp4')

    mock_video_reader.load.assert_called_once_with(
        video_path='test_reference.mp4'
    )
    mock_video_reader.get_frame_at.assert_called_with(timestamp_ms=0)
    assert tab.timeline.duration_ms == 45000
    assert 'test_reference.mp4' in tab.lbl_video_info.cget('text')
    assert tab.is_video_loaded is True


def test_reference_video_tab_add_and_delete_range(
    mock_video_reader: VideoReader,
) -> None:
    ranges_recorded: list[list[TimeRange]] = []

    def on_ranges(r: list[TimeRange]) -> None:
        ranges_recorded.append(list(r))

    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        on_ranges_changed=on_ranges,
        video_reader=mock_video_reader,
    )
    tab.load_video('clip.mp4')

    # Add range manually
    time_range = TimeRange(start_ms=2000, end_ms=8000)
    tab.add_range(time_range=time_range)

    assert len(tab.ranges) == 1
    assert tab.ranges[0] == time_range
    assert len(ranges_recorded) == 1
    assert len(tab.tree_ranges.get_children()) == 1

    # Add second range
    time_range2 = TimeRange(start_ms=10000, end_ms=15000)
    tab.add_range(time_range=time_range2)
    assert len(tab.ranges) == 2
    assert len(ranges_recorded) == 2

    # Delete first range
    tab.delete_range_at(index=0)
    assert len(tab.ranges) == 1
    assert tab.ranges[0] == time_range2
    assert len(ranges_recorded) == 3


def test_reference_video_tab_on_add_range_click(
    mock_video_reader: VideoReader,
) -> None:
    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        video_reader=mock_video_reader,
    )
    tab.load_video('clip.mp4')

    # No range selected yet
    with patch('tkinter.messagebox.showinfo') as mock_info:
        tab._on_add_range_click()
        mock_info.assert_called_once()
        assert len(tab.ranges) == 0

    # Select range on timeline
    tab.timeline.set_range(start_ms=3000, end_ms=7000)
    tab._on_add_range_click()

    assert len(tab.ranges) == 1
    assert tab.ranges[0] == TimeRange(start_ms=3000, end_ms=7000)


def test_reference_video_tab_on_delete_range_click_empty(
    mock_video_reader: VideoReader,
) -> None:
    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        video_reader=mock_video_reader,
    )
    tab.load_video('clip.mp4')

    with patch('tkinter.messagebox.showinfo') as mock_info:
        tab._on_delete_range_click()
        mock_info.assert_called_once()


def test_reference_video_tab_on_delete_range_click_with_selection(
    mock_video_reader: VideoReader,
) -> None:
    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        video_reader=mock_video_reader,
    )
    tab.load_video('clip.mp4')
    tab.add_range(TimeRange(start_ms=1000, end_ms=4000))

    children = tab.tree_ranges.get_children()
    tab.tree_ranges.selection_set(children[0])

    tab._on_delete_range_click()
    assert len(tab.ranges) == 0


def test_reference_video_tab_on_load_video_click(
    mock_video_reader: VideoReader,
) -> None:
    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        video_reader=mock_video_reader,
    )
    with patch('tkinter.filedialog.askopenfilename', return_value='video.mp4'):
        tab._on_load_video_click()
        mock_video_reader.load.assert_called_once_with(video_path='video.mp4')


def test_reference_video_tab_on_load_video_click_cancelled(
    mock_video_reader: VideoReader,
) -> None:
    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        video_reader=mock_video_reader,
    )
    with patch('tkinter.filedialog.askopenfilename', return_value=''):
        tab._on_load_video_click()
        mock_video_reader.load.assert_not_called()


def test_reference_video_tab_load_failure(
    mock_video_reader: VideoReader,
) -> None:
    tab = ReferenceVideoTab(
        parent=DummyWidget(),
        video_reader=mock_video_reader,
    )
    mock_video_reader.load.side_effect = ValueError('Corrupted video')
    with (
        patch('tkinter.filedialog.askopenfilename', return_value='bad.mp4'),
        patch('tkinter.messagebox.showerror') as mock_error,
    ):
        tab._on_load_video_click()
        mock_error.assert_called_once()
        assert not tab.is_video_loaded
