from pathlib import Path
from lflive.config import load_config


def test_default_config() -> None:
    config = load_config(path=None)
    assert config.tdf_port == 8000
    assert config.consumer_port == 8001
    assert config.lfstats_url == 'https://lfstats.com/api/'
    assert config.database_path == 'lflive.db'
    assert config.preroll_ms == 0
    assert config.log_tdf is False
    assert config.log_output is False


def test_load_config_non_existent(tmp_path: Path) -> None:
    non_existent = tmp_path / 'missing.yaml'
    config = load_config(path=str(non_existent))
    assert config.tdf_port == 8000


def test_load_config_custom_values(tmp_path: Path) -> None:
    cfg_file = tmp_path / 'test_cfg.yaml'
    cfg_file.write_text(
        'tdf_port: 9005\n'
        'consumer_port: 9006\n'
        'lfstats_url: https://custom.lfstats.com/api/\n'
        'database_path: custom.db\n'
        'preroll_ms: 750\n'
        'log_tdf: true\n'
        'log_output: true\n',
        encoding='utf-8',
    )
    config = load_config(path=str(cfg_file))
    assert config.tdf_port == 9005
    assert config.consumer_port == 9006
    assert config.lfstats_url == 'https://custom.lfstats.com/api/'
    assert config.database_path == 'custom.db'
    assert config.preroll_ms == 750
    assert config.log_tdf is True
    assert config.log_output is True


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    cfg_file = tmp_path / 'invalid.yaml'
    cfg_file.write_text('just a plain string', encoding='utf-8')
    config = load_config(path=str(cfg_file))
    assert config.tdf_port == 8000
