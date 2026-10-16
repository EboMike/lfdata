"""Unit tests for LutPanel visualization and balance control widget."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from lfdata.color_correction.lut import Lut3D
from lfdata.color_correction.lut_panel import LutPanel


class DummyWidget:
    """Mock widget for headless testing of canvas components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._options: dict[str, Any] = dict(kwargs)
        self._w: str = '.'
        self.tk: Any = MagicMock()
        self.children: dict[str, Any] = {}

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, *args: Any, **kwargs: Any) -> None:
        pass

    def config(self, *args: Any, **kwargs: Any) -> None:
        self._options.update(kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:
        self.config(*args, **kwargs)


class DummyCanvas(DummyWidget):
    """Mock Canvas recording drawn shapes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.items: list[str] = []

    def delete(self, *args: Any, **kwargs: Any) -> None:
        self.items.clear()

    def create_image(self, *args: Any, **kwargs: Any) -> int:
        self.items.append('image')
        return len(self.items)

    def create_oval(self, *args: Any, **kwargs: Any) -> int:
        self.items.append('oval')
        return len(self.items)


@patch('tkinter.Canvas', DummyCanvas)
@patch('tkinter.ttk.Frame', DummyWidget)
def test_lut_panel_initialization() -> None:
    parent = DummyWidget()
    lut = Lut3D(size=4)
    panel = LutPanel(parent=parent, lut=lut, canvas_width=200, canvas_height=50)

    assert panel.lut is lut
    assert panel.canvas_width == 200
    assert panel.canvas_height == 50
    assert panel.canvas is not None


@patch('tkinter.Canvas', DummyCanvas)
@patch('tkinter.ttk.Frame', DummyWidget)
def test_lut_panel_update_lut() -> None:
    parent = DummyWidget()
    panel = LutPanel(parent=parent)
    new_lut = Lut3D(size=4)
    new_lut.temperature = 0.5
    panel.update_lut(lut=new_lut)

    assert panel.lut is new_lut


@patch('tkinter.Canvas', DummyCanvas)
@patch('tkinter.ttk.Frame', DummyWidget)
def test_lut_panel_canvas_click_and_drag() -> None:
    parent = DummyWidget()
    lut = Lut3D(size=4)
    changed_balance: list[tuple[float, float]] = []

    def on_changed(temp: float, tint: float) -> None:
        changed_balance.append((temp, tint))

    panel = LutPanel(
        parent=parent,
        lut=lut,
        canvas_width=200,
        canvas_height=100,
        on_balance_changed=on_changed,
    )

    # Click at x=180, y=20 (warm, magenta)
    mock_event = MagicMock()
    mock_event.x = 180
    mock_event.y = 20
    panel._on_canvas_click(event=mock_event)

    assert len(changed_balance) == 1
    temp_val, tint_val = changed_balance[0]
    assert temp_val > 0.5
    assert tint_val > 0.5
    assert lut.temperature == temp_val
    assert lut.tint == tint_val
