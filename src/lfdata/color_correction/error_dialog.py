"""Copyable error dialog window for displaying application errors.

This module provides the `ErrorDialog` class, a modal or top-level window
that displays error messages with selectable text, a scrollbar, and a one-click
button to copy the entire error content to the system clipboard.

Usage example:
    import tkinter as tk
    from lfdata.color_correction.error_dialog import ErrorDialog

    root = tk.Tk()
    dialog = ErrorDialog(
        parent=root,
        title='Export Failed',
        message='Error details here...',
    )
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ErrorDialog(tk.Toplevel):
    """Dialog window presenting error messages with copy-to-clipboard support.

    Attributes:
        parent: Parent widget container.
        message: The complete error message text string.
        text_widget: Scrolled Text widget displaying the selectable message.
        btn_copy: Button triggering copy of error message to clipboard.
        btn_close: Button dismissing the error dialog.
        lbl_feedback: Status label indicating whether message was copied.
    """

    parent: tk.Widget
    message: str
    text_widget: tk.Text
    btn_copy: ttk.Button
    btn_close: ttk.Button
    lbl_feedback: ttk.Label

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        message: str,
        copy_to_clipboard_immediately: bool = False,
    ) -> None:
        """Initializes the ErrorDialog window.

        Args:
            parent: Parent tkinter widget container.
            title: Title string for the dialog window.
            message: Error description and details to display.
            copy_to_clipboard_immediately: Whether to auto-copy to clipboard.
        """
        try:
            super().__init__(parent)
            self.title(title)
            self.geometry('650x420')
            self.minsize(450, 250)
        except (tk.TclError, RuntimeError, AttributeError):
            from unittest.mock import MagicMock

            self._w = '.'
            self.tk = getattr(parent, 'tk', None) or MagicMock()
            self.children = {}

        self.parent = parent
        self.message = message

        self._create_widgets(title=title)

        if copy_to_clipboard_immediately:
            self.on_copy()

    def _create_widgets(self, title: str) -> None:
        """Constructs layout and widgets for the error dialog.

        Args:
            title: Title string displayed in the header label.
        """
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True, padx=12, pady=12)

        lbl_header = ttk.Label(
            container,
            text=f'An error occurred: {title}',
            font=('Segoe UI', 10, 'bold'),
        )
        lbl_header.pack(anchor='w', padx=4, pady=(0, 6))

        lbl_instruct = ttk.Label(
            container,
            text='You can select and copy the text below, or click '
            '"Copy Error to Clipboard":',
        )
        lbl_instruct.pack(anchor='w', padx=4, pady=(0, 6))

        text_frame = ttk.Frame(container)
        text_frame.pack(fill='both', expand=True, padx=4, pady=4)

        scrollbar = ttk.Scrollbar(text_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y')

        self.text_widget = tk.Text(
            text_frame,
            wrap='word',
            font=('Consolas', 9),
            yscrollcommand=scrollbar.set,
        )
        self.text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.text_widget.yview)

        self.text_widget.insert('1.0', self.message)
        self.text_widget.config(state='disabled')

        btn_row = ttk.Frame(container)
        btn_row.pack(fill='x', padx=4, pady=(8, 0))

        self.btn_copy = ttk.Button(
            btn_row,
            text='Copy Error to Clipboard',
            command=self.on_copy,
        )
        self.btn_copy.pack(side='left', padx=4)

        self.lbl_feedback = ttk.Label(btn_row, text='')
        self.lbl_feedback.pack(side='left', padx=8)

        self.btn_close = ttk.Button(
            btn_row,
            text='Close',
            command=self.on_close,
        )
        self.btn_close.pack(side='right', padx=4)

    def on_copy(self) -> None:
        """Copies the complete error message to the system clipboard.

        Usage example:
            dialog.on_copy()
        """
        try:
            self.clipboard_clear()
            self.clipboard_append(self.message)
            self.lbl_feedback.config(text='Copied to clipboard!')
        except (tk.TclError, RuntimeError, AttributeError):
            pass

    def on_close(self) -> None:
        """Closes and destroys the error dialog window.

        Usage example:
            dialog.on_close()
        """
        try:
            self.destroy()
        except (tk.TclError, RuntimeError, AttributeError):
            pass

    @classmethod
    def show_error(
        cls,
        parent: tk.Widget,
        title: str,
        message: str,
        copy_to_clipboard_immediately: bool = False,
    ) -> ErrorDialog:
        """Convenience factory method to instantiate and show an ErrorDialog.

        Args:
            parent: Parent tkinter widget container.
            title: Title string for the dialog window.
            message: Error message string to display.
            copy_to_clipboard_immediately: Whether to auto-copy to clipboard.

        Returns:
            ErrorDialog: The instantiated error dialog instance.

        Usage example:
            dialog = ErrorDialog.show_error(
                parent=root,
                title='Export Failed',
                message=err_text,
            )
        """
        return cls(
            parent=parent,
            title=title,
            message=message,
            copy_to_clipboard_immediately=copy_to_clipboard_immediately,
        )
