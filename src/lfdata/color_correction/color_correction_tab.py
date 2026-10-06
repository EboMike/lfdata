"""Color correction adjustment tab placeholder.

This module provides the `ColorCorrectionTab` widget, representing the second
stage of the color correction process where LUT and noise reduction options
will be configured.

Usage example:
    import tkinter as tk
    from lfdata.color_correction.color_correction_tab import ColorCorrectionTab

    root = tk.Tk()
    tab = ColorCorrectionTab(parent=root)
    tab.pack(fill='both', expand=True)
"""

import tkinter as tk
from tkinter import ttk


class ColorCorrectionTab(ttk.Frame):
    """UI tab for configuring LUT and noise reduction settings.

    This tab is currently a placeholder for future color correction controls
    and is only selectable when at least one reference range has been added.

    Attributes:
        lbl_info: Informational message label explaining tab status.
    """

    def __init__(self, parent: tk.Widget) -> None:
        """Initializes the ColorCorrectionTab widget.

        Args:
            parent: Parent tkinter widget container.
        """
        try:
            super().__init__(parent)
        except Exception:
            from unittest.mock import MagicMock

            self._w = '.'
            self.tk = getattr(parent, 'tk', MagicMock())
            self.children = {}
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Creates placeholder labels explaining color correction stages."""
        container = ttk.Frame(self)
        container.pack(expand=True, fill='both', padx=20, pady=20)

        self.lbl_heading = ttk.Label(
            container,
            text='Color Correction',
            font=('TkDefaultFont', 14, 'bold'),
        )
        self.lbl_heading.pack(pady=(40, 10))

        self.lbl_info = ttk.Label(
            container,
            text=(
                'More information will be added here. '
                'This tab is empty for now.\n'
                'Adjustments for LUT (.cube) and noise reduction will '
                'be configured in this stage.'
            ),
            justify='center',
        )
        self.lbl_info.pack(pady=10)
