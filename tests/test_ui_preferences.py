from pathlib import Path

from lfdata.ui.preferences import UIPreferences


def test_ui_preferences_defaults() -> None:
    prefs = UIPreferences()
    assert prefs.most_recent_tdf is None
    assert prefs.most_recent_config is None
    assert prefs.window_geometry is None
    assert prefs.to_dict() == {}


def test_ui_preferences_custom() -> None:
    prefs = UIPreferences(
        most_recent_tdf='game.tdf',
        most_recent_config='config.yaml',
        window_geometry='1024x768',
    )
    assert prefs.most_recent_tdf == 'game.tdf'
    assert prefs.most_recent_config == 'config.yaml'
    assert prefs.window_geometry == '1024x768'

    expected = {
        'most_recent_tdf': 'game.tdf',
        'most_recent_config': 'config.yaml',
        'window_geometry': '1024x768',
    }
    assert prefs.to_dict() == expected


def test_ui_preferences_from_dict() -> None:
    raw: dict[str, object] = {
        'most_recent_tdf': 'alpha.tdf',
        'most_recent_config': 'beta.yaml',
        'window_geometry': '1440x900',
    }
    prefs = UIPreferences.from_dict(raw)
    assert prefs.most_recent_tdf == 'alpha.tdf'
    assert prefs.most_recent_config == 'beta.yaml'
    assert prefs.window_geometry == '1440x900'


def test_ui_preferences_save_and_load(tmp_path: Path) -> None:
    pref_file = tmp_path / 'prefs.json'
    prefs = UIPreferences(
        most_recent_tdf='match.tdf',
        most_recent_config='hud.yaml',
        window_geometry='1280x720',
    )
    prefs.save(pref_file)
    assert pref_file.is_file()

    loaded = UIPreferences.load(pref_file)
    assert loaded.most_recent_tdf == 'match.tdf'
    assert loaded.most_recent_config == 'hud.yaml'
    assert loaded.window_geometry == '1280x720'


def test_ui_preferences_load_missing_or_invalid(tmp_path: Path) -> None:
    missing_file = tmp_path / 'missing.json'
    default_prefs = UIPreferences.load(missing_file)
    assert default_prefs == UIPreferences()

    corrupt_file = tmp_path / 'corrupt.json'
    with open(corrupt_file, 'w', encoding='utf-8') as f:
        f.write('not-valid-json{{{')

    fallback_prefs = UIPreferences.load(corrupt_file)
    assert fallback_prefs == UIPreferences()

