"""Tests for the TimelineWidget canvas component."""

from typing import Any
from unittest.mock import MagicMock, patch

from lfdata.color_correction.time_range import TimeRange


class DummyCanvas:
    """Mock Canvas widget for headless timeline testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._width = 530
        self._height = 40

    def bind(self, *args: Any, **kwargs: Any) -> None:
        pass

    def delete(self, *args: Any, **kwargs: Any) -> None:
        pass

    def create_line(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_rectangle(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def create_polygon(self, *args: Any, **kwargs: Any) -> int:
        return 1

    def winfo_width(self) -> int:
        return self._width

    def winfo_height(self) -> int:
        return self._height


with patch('tkinter.Canvas', DummyCanvas), patch('tkinter.Tk', MagicMock):
    import sys

    sys.modules.pop('lfdata.color_correction.timeline_widget', None)
    from lfdata.color_correction.timeline_widget import TimelineWidget


class DummyEvent:
    """Mock Tkinter event with mouse coordinates."""

    def __init__(self, x: int, y: int = 10) -> None:
        self.x = x
        self.y = y


def test_timeline_widget_init() -> None:
    time_cb_called = []
    range_cb_called = []

    def on_time(t: int) -> None:
        time_cb_called.append(t)

    def on_range(s: int, e: int) -> None:
        range_cb_called.append((s, e))

    widget = TimelineWidget(
        parent=MagicMock(),
        duration_ms=50000,
        on_time_changed=on_time,
        on_range_changed=on_range,
    )
    assert widget.duration_ms == 50000
    assert widget.current_time_ms == 0
    assert widget.range_start_ms is None
    assert widget.range_end_ms is None
    assert widget.get_current_range() is None


def test_timeline_set_duration_and_current_time() -> None:
    widget = TimelineWidget(parent=MagicMock(), duration_ms=20000)
    widget.set_current_time_ms(time_ms=15000)
    assert widget.current_time_ms == 15000

    widget.set_current_time_ms(time_ms=25000)  # Clamps to max duration
    assert widget.current_time_ms == 20000

    widget.set_current_time_ms(time_ms=-500)  # Clamps to 0
    assert widget.current_time_ms == 0

    widget.set_current_time_ms(time_ms=18000)
    widget.set_duration_ms(duration_ms=10000)  # Shrinking duration resets time
    assert widget.duration_ms == 10000
    assert widget.current_time_ms == 0


def test_timeline_range_methods() -> None:
    widget = TimelineWidget(parent=MagicMock(), duration_ms=30000)
    widget.set_range(start_ms=5000, end_ms=12000)
    current_range = widget.get_current_range()
    assert current_range is not None
    assert current_range == TimeRange(start_ms=5000, end_ms=12000)

    widget.clear_range()
    assert widget.get_current_range() is None


def test_timeline_get_current_range_invalid() -> None:
    widget = TimelineWidget(parent=MagicMock(), duration_ms=10000)
    widget.range_start_ms = 4000
    widget.range_end_ms = 4000
    assert widget.get_current_range() is None


def test_timeline_mouse_events() -> None:
    times_recorded: list[int] = []
    ranges_recorded: list[tuple[int, int]] = []

    widget = TimelineWidget(
        parent=MagicMock(),
        duration_ms=10000,
        on_time_changed=lambda t: times_recorded.append(t),
        on_range_changed=lambda s, e: ranges_recorded.append((s, e)),
    )

    # Press button at x = 115 (100 px into usable -> 20% -> 2000 ms)
    widget._on_button_press(DummyEvent(x=115))
    assert widget.current_time_ms == 2000
    assert 2000 in times_recorded

    # Drag motion to x = 265 (250 px into usable -> 50% -> 5000 ms)
    widget._on_button_motion(DummyEvent(x=265))
    assert widget.current_time_ms == 5000
    assert widget.range_start_ms == 2000
    assert widget.range_end_ms == 5000
    assert (2000, 5000) in ranges_recorded

    # Release button
    widget._on_button_release(DummyEvent(x=265))
    assert len(ranges_recorded) >= 2


def test_timeline_redraw() -> None:
    widget = TimelineWidget(parent=MagicMock(), duration_ms=20000)
    widget.set_range(start_ms=1000, end_ms=5000)
    widget.redraw()
