"""UI user preferences data class and file persistence.

This module provides the UIPreferences dataclass to manage persistent user
preferences such as recently accessed files and window dimensions, converting
parsed JSON data into strongly-typed dataclass structures.

Usage example:
    from pathlib import Path
    from lfdata.ui.preferences import UIPreferences

    prefs = UIPreferences(window_geometry='800x600')
    prefs.save(Path('preferences.json'))
    loaded = UIPreferences.load(Path('preferences.json'))
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class UIPreferences:
    """User preferences and UI window state for the editor application.

    Attributes:
        most_recent_tdf: Optional path string to the last opened TDF file.
        most_recent_config: Optional path string to the last opened config.
        window_geometry: Optional Tkinter geometry string (e.g. '1200x800').
    """

    most_recent_tdf: str | None = None
    most_recent_config: str | None = None
    window_geometry: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> UIPreferences:
        """Constructs UIPreferences from a deserialized JSON dictionary.

        Args:
            data: Raw JSON key-value dictionary.

        Returns:
            UIPreferences: Initialized preferences dataclass.

        Usage example:
            prefs = UIPreferences.from_dict({'window_geometry': '800x600'})
        """
        tdf_val = data.get('most_recent_tdf')
        cfg_val = data.get('most_recent_config')
        geom_val = data.get('window_geometry')

        return cls(
            most_recent_tdf=str(tdf_val) if tdf_val else None,
            most_recent_config=str(cfg_val) if cfg_val else None,
            window_geometry=str(geom_val) if geom_val else None,
        )

    def to_dict(self) -> dict[str, object]:
        """Serializes preferences to a dictionary suitable for JSON encoding.

        Returns:
            dict[str, object]: Dictionary with non-None preference fields.

        Usage example:
            data_dict = prefs.to_dict()
        """
        result: dict[str, object] = {}
        if self.most_recent_tdf is not None:
            result['most_recent_tdf'] = self.most_recent_tdf
        if self.most_recent_config is not None:
            result['most_recent_config'] = self.most_recent_config
        if self.window_geometry is not None:
            result['window_geometry'] = self.window_geometry
        return result

    @classmethod
    def load(cls, path: Path) -> UIPreferences:
        """Loads preferences from a JSON file, returning defaults if not found.

        Args:
            path: Path object pointing to the preferences JSON file.

        Returns:
            UIPreferences: Loaded or default preferences instance.

        Usage example:
            prefs = UIPreferences.load(Path('preferences.json'))
        """
        if not path.is_file():
            return cls()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return cls.from_dict(data)
        except Exception:
            pass
        return cls()

    def save(self, path: Path) -> None:
        """Saves current preferences to a JSON file.

        Args:
            path: Destination file Path.

        Usage example:
            prefs.save(Path('preferences.json'))
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception:
            pass

