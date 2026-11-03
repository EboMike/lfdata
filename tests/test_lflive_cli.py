from pathlib import Path
from lflive.cli import parse_args, resolve_config


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.config is None
    assert args.log_tdf is False
    assert args.log_output is False
    assert args.tdf_port is None
    assert args.consumer_port is None
    assert args.database_path is None
    assert args.preroll_ms is None
    assert args.lfstats_url is None


def test_parse_args_explicit() -> None:
    args = parse_args(
        [
            '--config',
            'my_config.yaml',
            '--log_tdf',
            '--log_output',
            '--tdf_port',
            '7777',
            '--consumer_port',
            '8888',
            '--database',
            'live_test.db',
            '--preroll_ms',
            '500',
            '--lfstats_url',
            'https://api.example.com',
        ]
    )
    assert args.config == 'my_config.yaml'
    assert args.log_tdf is True
    assert args.log_output is True
    assert args.tdf_port == 7777
    assert args.consumer_port == 8888
    assert args.database_path == 'live_test.db'
    assert args.preroll_ms == 500
    assert args.lfstats_url == 'https://api.example.com'


def test_resolve_config_overrides(tmp_path: Path) -> None:
    cfg_file = tmp_path / 'base.yaml'
    cfg_file.write_text(
        'tdf_port: 8000\nconsumer_port: 8001\n', encoding='utf-8'
    )
    args = parse_args(
        [
            '--config',
            str(cfg_file),
            '--tdf_port',
            '9100',
            '--log_tdf',
        ]
    )
    config = resolve_config(cli_args=args)
    assert config.tdf_port == 9100
    assert config.consumer_port == 8001
    assert config.log_tdf is True
