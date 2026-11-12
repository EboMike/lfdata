"""LF data UI package for graphical HUD layout editing.

Provides a Tkinter-based desktop interface for previewing, customizing,
and animating HUD video overlay layouts and element configurations.

Usage example:
    $ lfdata_ui
    # Or programmatically:
    from lfdata.ui.app import LFDataUIApp

    app = LFDataUIApp()
    app.mainloop()
"""

from lfdata.ui.preview_renderer import PreviewRenderer

__all__ = ['PreviewRenderer']

