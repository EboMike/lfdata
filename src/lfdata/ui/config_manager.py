"""Configuration manager for the LF data UI tool."""

import copy
import os
import sys
from typing import Any
import yaml

from lfdata.importer import TdfImporter
from lfdata.model.objects.game import LFGame
from lfdata.video.helpers import DEFAULT_CONFIG, _merge_configs


class UIConfigManager:
    """Manages the configuration state and TDF data for the UI."""

    def __init__(self) -> None:
        """Initializes the UIConfigManager with default configuration."""
        self.config: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.tdf_path: str | None = None
        self.game: LFGame | None = None
        self.players: list[str] = []
        self.config_path: str | None = None

    def load_config(self, path: str) -> None:
        """Loads and parses a YAML configuration file.

        Args:
            path: The file path to the YAML configuration.

        Raises:
            RuntimeError: If the config file fails to load or parse.
        """
        self.config_path = path
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    self.config = _merge_configs(DEFAULT_CONFIG, loaded)
        except Exception as e:
            raise RuntimeError(f'Failed to load config: {e}') from e

    def save_config(self, path: str) -> None:
        """Saves the current configuration to a YAML file.

        Args:
            path: The file path to save the YAML configuration.

        Raises:
            RuntimeError: If the config file fails to write.
        """
        self.config_path = path
        try:
            with open(path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
        except Exception as e:
            raise RuntimeError(f'Failed to save config: {e}') from e

    def load_tdf(self, path: str) -> None:
        """Loads and parses a TDF file to populate game and player lists.

        Args:
            path: The file path to the TDF file.

        Raises:
            RuntimeError: If the TDF parser fails.
        """
        self.tdf_path = path
        try:
            importer = TdfImporter(path)
            self.game = importer.parse()
            self.players = sorted(
                [e.desc for e in self.game.entities if e.type == 'player']
            )
        except Exception as e:
            raise RuntimeError(f'Failed to load TDF: {e}') from e

    def get_element(self, element_name: str) -> dict[str, Any] | None:
        """Retrieves configuration dictionary for a specific UI element.

        Args:
            element_name: The name of the UI element.

        Returns:
            The element's config dict, or None if not found.
        """
        elements = self.config.get('elements', {})
        if not elements:
            return None
        return elements.get(element_name)

    def update_element(self, element_name: str, key: str, value: Any) -> None:
        """Updates a property of a specific UI element.

        Args:
            element_name: The name of the UI element.
            key: The property key to update.
            value: The new value for the property.
        """
        elements = self.config.setdefault('elements', {})
        el = elements.setdefault(element_name, {})

        if key in ('font', 'size'):
            style = el.setdefault('style', {})
            style[key] = value
        elif key == 'extents':
            if value is None:
                if 'extents' in el:
                    del el['extents']
            else:
                el['extents'] = value
        else:
            el[key] = value

    def get_player_names(self) -> list[str]:
        """Gets the list of player names loaded from the TDF file.

        Returns:
            A list of player names.
        """
        return self.players

    def update_global_setting(self, key: str, value: Any) -> None:
        """Updates a global configuration setting.

        Args:
            key: The configuration key.
            value: The new value.
        """
        self.config[key] = value

    def get_lfdata_command(self) -> list[str]:
        """Returns the base command list to run the lfdata CLI.

        Returns:
            A list of strings representing the base command prefix.
        """
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            bin_name = 'lfdata.exe' if os.name == 'nt' else 'lfdata'
            sibling_bin = os.path.join(exe_dir, bin_name)
            if os.path.exists(sibling_bin):
                return [sibling_bin]
            return [bin_name]

        return [sys.executable, '-m', 'lfdata']
