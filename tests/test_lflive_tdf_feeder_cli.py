import pytest
from lflive.tdf_feeder.cli import parse_args


def test_parse_args_positional() -> None:
    args = parse_args(['sample.tdf', '10.0.0.5:9050'])
    assert args.file_path == 'sample.tdf'
    assert args.host == '10.0.0.5'
    assert args.port == 9050
    assert args.speed == 1.0


def test_parse_args_flags() -> None:
    args = parse_args(
        [
            '--file',
            'game.tdf',
            '--host',
            '192.168.1.1',
            '--port',
            '7000',
            '--speed',
            '2.5',
        ]
    )
    assert args.file_path == 'game.tdf'
    assert args.host == '192.168.1.1'
    assert args.port == 7000
    assert args.speed == 2.5


def test_parse_args_target_host_only() -> None:
    args = parse_args(['game.tdf', '10.0.0.2'])
    assert args.host == '10.0.0.2'
    assert args.port == 8000


def test_parse_args_missing_file() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_invalid_port() -> None:
    with pytest.raises(SystemExit):
        parse_args(['game.tdf', '127.0.0.1:invalid'])
