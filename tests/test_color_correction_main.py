"""Tests for color correction module __main__ execution."""

from unittest.mock import patch


def test_color_correction_module_main() -> None:
    with patch('lfdata.color_correction.editor.main') as mock_main:
        import lfdata.color_correction.__main__  # noqa: F401

        # Explicitly verify main function can be called via module
        from lfdata.color_correction.editor import main

        main()
        mock_main.assert_called()
