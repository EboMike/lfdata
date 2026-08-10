"""Main entry point for the LF data UI desktop tool.

This module provides the executable CLI entry point for launching the graphical HUD
layout customization desktop application (`lfdata_ui`).

Usage example:
    $ lfdata_ui
"""

from lfdata.startup import StartupVerifier
from lfdata.ui.app import LFDataUIApp


def main() -> None:
    """Verifies startup environment assets and launches the Tkinter HUD designer window."""
    StartupVerifier.check_assets_and_print_cwd()
    app = LFDataUIApp()
    app.mainloop()


if __name__ == '__main__':
    main()
