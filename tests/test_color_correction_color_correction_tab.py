"""Tests for ColorCorrectionTab component."""

from typing import Any
from unittest.mock import MagicMock, patch

from lfdata.color_correction.color_correction_tab import ColorCorrectionTab


class DummyWidget:
    """Mock widget for headless testing of tab components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._options: dict[str, Any] = dict(kwargs)
        self.text: str = str(kwargs.get('text', ''))
        self._w: str = '.'
        self.tk: Any = MagicMock()
        self.children: dict[str, Any] = {}

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def config(self, *args: Any, **kwargs: Any) -> None:
        self._options.update(kwargs)
        if 'text' in kwargs:
            self.text = str(kwargs['text'])

    def configure(self, *args: Any, **kwargs: Any) -> None:
        self.config(*args, **kwargs)

    def cget(self, key: str) -> Any:
        return self._options.get(key, getattr(self, key, ''))


@patch('tkinter.ttk.Label', DummyWidget)
@patch('tkinter.ttk.Frame', DummyWidget)
def test_color_correction_tab_init() -> None:
    parent = DummyWidget()
    tab = ColorCorrectionTab(parent=parent)
    assert tab.lbl_heading is not None
    assert tab.lbl_info is not None
    assert 'Color Correction' in tab.lbl_heading.cget('text')
    assert 'empty for now' in tab.lbl_info.cget('text')
