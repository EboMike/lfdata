"""Tests for the UIConfigManager class."""

from pathlib import Path
from typing import Generator
import pytest

from lfdata.ui.config_manager import UIConfigManager


@pytest.fixture
def manager() -> UIConfigManager:
    """Fixture returning a fresh UIConfigManager instance.

    Returns:
        UIConfigManager: A fresh configuration manager.
    """
    return UIConfigManager()


@pytest.fixture
def temp_yaml(tmp_path: Path) -> Generator[Path, None, None]:
    """Fixture returning a temporary path for YAML config.

    Args:
        tmp_path: The pytest temp path.

    Yields:
        Path: A path to a temporary YAML file.
    """
    yield tmp_path / 'test_config.yaml'


def test_initialization(manager: UIConfigManager) -> None:
    """Verifies default values on initialization."""
    assert manager.config is not None
    assert 'elements' in manager.config
    assert manager.tdf_path is None
    assert manager.game is None
    assert not manager.players
    assert manager.config_path is None


def test_load_and_save_config(
    manager: UIConfigManager, temp_yaml: Path
) -> None:
    """Verifies saving and reloading configuration values."""
    manager.update_global_setting('fps', 45)
    manager.update_element('time', 'enabled', False)
    manager.update_element('time', 'size', 99)

    manager.save_config(str(temp_yaml))
    assert temp_yaml.exists()

    new_manager = UIConfigManager()
    new_manager.load_config(str(temp_yaml))

    assert new_manager.config_path == str(temp_yaml)
    assert new_manager.config.get('fps') == 45
    time_el = new_manager.get_element('time')
    assert time_el is not None
    assert time_el.get('enabled') is False
    assert time_el.get('style', {}).get('size') == 99


def test_load_tdf(manager: UIConfigManager) -> None:
    """Verifies loading a real TDF file updates state."""
    real_path = Path('assets') / 'sm5_sanitized.tdf'
    manager.load_tdf(str(real_path))

    assert manager.game is not None
    assert manager.tdf_path == str(real_path)
    assert len(manager.players) > 0
    assert 'None' not in manager.players
    assert manager.get_player_names() == manager.players


def test_update_element_properties(manager: UIConfigManager) -> None:
    """Verifies updating specific properties updates internal config."""
    # Test setting extents
    manager.update_element('scoreboard', 'extents', [0.5, 0.6])
    el = manager.get_element('scoreboard')
    assert el is not None
    assert el.get('extents') == [0.5, 0.6]

    # Test removing extents
    manager.update_element('scoreboard', 'extents', None)
    el = manager.get_element('scoreboard')
    assert el is not None
    assert 'extents' not in el

    # Test setting font
    manager.update_element('time', 'font', 'Arial')
    el = manager.get_element('time')
    assert el is not None
    assert el.get('style', {}).get('font') == 'Arial'

    # Non-existent element retrieval
    assert manager.get_element('non_existent_element') is None


def test_get_lfdata_command(manager: UIConfigManager) -> None:
    """Verifies retrieval of lfdata command in dev and frozen modes."""
    import sys
    import os

    # 1. Dev Mode (sys.frozen is not set)
    if hasattr(sys, 'frozen'):
        delattr(sys, 'frozen')
    cmd = manager.get_lfdata_command()
    assert cmd == [sys.executable, '-m', 'lfdata']

    # 2. Frozen Mode (sys.frozen = True)
    sys.frozen = True
    try:
        cmd_frozen = manager.get_lfdata_command()
        expected_bin = 'lfdata.exe' if os.name == 'nt' else 'lfdata'
        assert expected_bin in cmd_frozen[0]
    finally:
        delattr(sys, 'frozen')
