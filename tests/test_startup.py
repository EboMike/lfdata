from pathlib import Path
from unittest.mock import patch

import pytest

from lfdata.startup import StartupVerifier


def test_check_assets_and_print_cwd_success(capsys) -> None:
    # Under standard test runner conditions, all assets exist in the workspace root.
    StartupVerifier.check_assets_and_print_cwd()
    captured = capsys.readouterr()
    assert 'Current directory:' in captured.out


def test_check_assets_and_print_cwd_missing_asset(capsys) -> None:
    # Mock Path.exists to return False to simulate a missing asset
    with patch.object(Path, 'exists', return_value=False):
        with pytest.raises(FileNotFoundError) as exc_info:
            StartupVerifier.check_assets_and_print_cwd()
        assert 'Required asset not found:' in str(exc_info.value)
