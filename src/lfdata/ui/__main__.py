"""Main entry point for the LF data UI tool."""

from lfdata.startup import StartupVerifier
from lfdata.ui.app import LFDataUIApp


def main() -> None:
    """Launches the LF data UI application."""
    StartupVerifier.check_assets_and_print_cwd()
    app = LFDataUIApp()
    app.mainloop()


if __name__ == '__main__':
    main()
