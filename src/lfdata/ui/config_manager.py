"""Configuration manager for the LF data UI tool."""

import copy
import os
import sys
from typing import Any
import yaml

from lfdata.importer import TdfImporter
from lfdata.model.objects.game import LFGame
from lfdata.video.helpers import (
    DEFAULT_CONFIG,
    _merge_configs,
    resolve_animated_value,
)


class UIConfigManager:
    """Manages the configuration state and TDF data for the UI."""

    def __init__(self) -> None:
        """Initializes the UIConfigManager with default configuration."""
        self.config: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.tdf_path: str | None = None
        self.game: LFGame | None = None
        self.players: list[str] = []
        self.config_path: str | None = None
        self.current_time_ms: int = 0

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

    def resolve_val(self, val: Any) -> Any:
        """Resolves a value at the current preview time.

        Args:
            val: The configuration value (constant or keyframe dict).

        Returns:
            Any: The resolved value or coordinate pair.
        """
        pregame_delay_ms = self.config.get('pregame_delay_ms', 0)
        if (
            isinstance(pregame_delay_ms, dict)
            and 'keyframes' in pregame_delay_ms
        ):
            pregame_delay_ms = resolve_animated_value(
                pregame_delay_ms, self.current_time_ms, 0, 0
            )

        duration_ms = 0
        if self.game:
            duration_ms = self.game.duration or 0

        return resolve_animated_value(
            val,
            self.current_time_ms,
            pregame_delay_ms=pregame_delay_ms,
            game_duration_ms=duration_ms,
        )

    def is_prop_animated(self, element_name: str, prop: str) -> bool:
        """Checks if a specific property of an element is animated.

        Args:
            element_name: The name of the UI element.
            prop: The property key (e.g. 'x', 'y', 'extents', 'size', 'tilt').

        Returns:
            bool: True if the property is animated, False otherwise.
        """
        el = self.get_element(element_name)
        if not el:
            return False

        if prop == 'size':
            val = el.get('style', {}).get('size')
        else:
            val = el.get(prop)

        return isinstance(val, dict) and 'keyframes' in val

    def toggle_prop_animated(self, element_name: str, prop: str) -> bool:
        """Toggles the animation state of a specific property.

        Converts the property to/from keyframe structures.

        Args:
            element_name: The name of the UI element.
            prop: The property key (e.g. 'x', 'y', 'extents', 'size', 'tilt').

        Returns:
            bool: The new animation state of the property.
        """
        el = self.get_element(element_name)
        if not el:
            return False

        prop_parent = el
        prop_key = prop
        if prop == 'size':
            prop_parent = el.setdefault('style', {})

        val = prop_parent.get(prop_key)
        is_anim = isinstance(val, dict) and 'keyframes' in val
        new_state = not is_anim

        if new_state:
            # Convert constant to keyframe dict
            if val is None:
                if prop_key in ('x', 'y'):
                    val = 0.5
                elif prop_key == 'extents':
                    val = [0.1, 0.1]
                elif prop_key == 'size':
                    val = 20
                elif prop_key == 'tilt':
                    val = 0.0

            prop_parent[prop_key] = {
                'keyframes': [
                    {
                        'time': 0,
                        'reference': 'start_of_video',
                        'value': val,
                        'interpolator': 'linear',
                    }
                ]
            }
        else:
            # Convert keyframe dict back to constant
            if isinstance(val, dict) and 'keyframes' in val:
                keyframes = val.get('keyframes', [])
                if keyframes:
                    prop_parent[prop_key] = keyframes[0].get('value')
                else:
                    if prop_key in ('x', 'y'):
                        prop_parent[prop_key] = 0.5
                    elif prop_key == 'extents':
                        prop_parent[prop_key] = [0.1, 0.1]
                    elif prop_key == 'size':
                        prop_parent[prop_key] = 20
                    elif prop_key == 'tilt':
                        prop_parent[prop_key] = 0.0
            else:
                if prop_key in ('x', 'y'):
                    prop_parent[prop_key] = 0.5
                elif prop_key == 'extents':
                    prop_parent[prop_key] = [0.1, 0.1]
                elif prop_key == 'size':
                    prop_parent[prop_key] = 20
                elif prop_key == 'tilt':
                    prop_parent[prop_key] = 0.0
        return new_state

    def update_element(self, element_name: str, key: str, value: Any) -> None:
        """Updates a property of a specific UI element.

        Args:
            element_name: The name of the UI element.
            key: The property key to update.
            value: The new value for the property.
        """
        elements = self.config.setdefault('elements', {})
        el = elements.setdefault(element_name, {})

        # Check if this property is animated
        prop_parent = el
        prop_key = key
        if key == 'size':
            prop_parent = el.setdefault('style', {})

        val_dict = prop_parent.get(prop_key)
        if isinstance(val_dict, dict) and 'keyframes' in val_dict:
            keyframes = val_dict['keyframes']

            pregame_delay_ms = self.config.get('pregame_delay_ms', 0)
            if (
                isinstance(pregame_delay_ms, dict)
                and 'keyframes' in pregame_delay_ms
            ):
                pregame_delay_ms = resolve_animated_value(
                    pregame_delay_ms, self.current_time_ms, 0, 0
                )

            duration_ms = self.game.duration or 0 if self.game else 0

            # Look for an existing keyframe at current_time_ms
            found_kf = None
            for kf in keyframes:
                kf_time_ms = kf.get('time', 0)
                ref = kf.get('reference', 'start_of_video')
                ref_clean = ref.strip().lower().replace(' ', '_')

                if ref_clean in ('start_of_game', 'game_start'):
                    abs_time_ms = pregame_delay_ms + kf_time_ms
                elif ref_clean in ('end_of_game', 'game_end'):
                    abs_time_ms = pregame_delay_ms + duration_ms + kf_time_ms
                else:
                    abs_time_ms = kf_time_ms

                if abs(abs_time_ms - self.current_time_ms) <= 1:
                    found_kf = kf
                    break

            if found_kf:
                found_kf['value'] = value
            else:
                # Create a new keyframe at self.current_time_ms
                # Match reference and interpolator of first keyframe
                ref = 'start_of_video'
                interp = 'linear'
                if keyframes:
                    ref = keyframes[0].get('reference', 'start_of_video')
                    interp = keyframes[0].get('interpolator', 'linear')

                ref_clean = ref.strip().lower().replace(' ', '_')
                if ref_clean in ('start_of_game', 'game_start'):
                    kf_time_ms = self.current_time_ms - pregame_delay_ms
                elif ref_clean in ('end_of_game', 'game_end'):
                    kf_time_ms = self.current_time_ms - (
                        pregame_delay_ms + duration_ms
                    )
                else:
                    kf_time_ms = self.current_time_ms

                keyframes.append(
                    {
                        'time': kf_time_ms,
                        'reference': ref,
                        'value': value,
                        'interpolator': interp,
                    }
                )
            return

        # Fallback to standard constant update if not animated
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
