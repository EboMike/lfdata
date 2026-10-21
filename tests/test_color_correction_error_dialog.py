"""Tests for ErrorDialog component."""

from __future__ import annotations

import tkinter as tk
from typing import Any
from unittest.mock import MagicMock, patch

from lfdata.color_correction.error_dialog import ErrorDialog


class DummyWidget:
    """Mock widget for headless testing of dialog components."""

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

    def set(self, *args: Any, **kwargs: Any) -> None:
        pass

    def insert(self, index: str, text: str) -> None:
        self.text += text

    def yview(self, *args: Any, **kwargs: Any) -> None:
        pass


def _create_dialog(
    title: str = 'Error',
    message: str = 'Something went wrong',
    copy_immediately: bool = False,
) -> ErrorDialog:
    """Helper to instantiate ErrorDialog with mocked tkinter widgets."""
    with (
        patch(
            'tkinter.Toplevel.__init__',
            side_effect=tk.TclError('no display'),
        ),
        patch('tkinter.ttk.Frame', DummyWidget),
        patch('tkinter.ttk.Label', DummyWidget),
        patch('tkinter.ttk.Button', DummyWidget),
        patch('tkinter.ttk.Scrollbar', DummyWidget),
        patch('tkinter.Text', DummyWidget),
    ):
        parent = DummyWidget()
        dialog = ErrorDialog(
            parent=parent,
            title=title,
            message=message,
            copy_to_clipboard_immediately=copy_immediately,
        )
    return dialog


def test_error_dialog_init() -> None:
    dialog = _create_dialog(title='Export Failed', message='ffmpeg code 1')
    assert dialog.message == 'ffmpeg code 1'
    assert dialog.btn_copy is not None
    assert dialog.btn_close is not None
    assert dialog.text_widget is not None


def test_error_dialog_on_copy() -> None:
    dialog = _create_dialog(title='Export Failed', message='detailed error')
    with (
        patch.object(dialog, 'clipboard_clear') as mock_clear,
        patch.object(dialog, 'clipboard_append') as mock_append,
    ):
        dialog.on_copy()
        mock_clear.assert_called_once()
        mock_append.assert_called_once_with('detailed error')
        assert 'Copied to clipboard' in dialog.lbl_feedback.text


def test_error_dialog_copy_immediately() -> None:
    with (
        patch(
            'tkinter.Toplevel.__init__',
            side_effect=tk.TclError('no display'),
        ),
        patch('tkinter.ttk.Frame', DummyWidget),
        patch('tkinter.ttk.Label', DummyWidget),
        patch('tkinter.ttk.Button', DummyWidget),
        patch('tkinter.ttk.Scrollbar', DummyWidget),
        patch('tkinter.Text', DummyWidget),
        patch.object(ErrorDialog, 'on_copy') as mock_copy,
    ):
        parent = DummyWidget()
        dialog = ErrorDialog(
            parent=parent,
            title='Error',
            message='test',
            copy_to_clipboard_immediately=True,
        )
        assert dialog is not None
        mock_copy.assert_called_once()


def test_error_dialog_on_close() -> None:
    dialog = _create_dialog()
    with patch.object(dialog, 'destroy') as mock_destroy:
        dialog.on_close()
        mock_destroy.assert_called_once()


def test_error_dialog_show_error_factory() -> None:
    with patch.object(ErrorDialog, '__init__', return_value=None) as mock_init:
        parent = DummyWidget()
        diag = ErrorDialog.show_error(
            parent=parent,
            title='Export Failed',
            message='msg',
            copy_to_clipboard_immediately=True,
        )
        assert isinstance(diag, ErrorDialog)
        mock_init.assert_called_once_with(
            parent=parent,
            title='Export Failed',
            message='msg',
            copy_to_clipboard_immediately=True,
        )
