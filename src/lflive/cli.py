"""Command-line interface argument parser for lflive.

This module parses command-line arguments for running the lflive service,
supporting configuration file loading and flag overrides.

Usage example:
    from lflive.cli import parse_args

    args = parse_args(['--log_tdf', '--tdf_port', '9000'])
    print(args.log_tdf, args.tdf_port)
"""

import argparse
import dataclasses
from collections.abc import Sequence

from lflive.config import LFLiveConfig, load_config


@dataclasses.dataclass
class LFLiveArgs:
    """Parsed command-line arguments for lflive.

    Attributes:
        config: Path to optional YAML configuration file.
        log_tdf: Flag to print received TDF lines to stdout.
        log_output: Flag to print outbound broadcast lines to stdout.
        tdf_port: Optional TCP port override for incoming TDF stream.
        consumer_port: Optional TCP port override for consumer connections.
        database_path: Optional SQLite database file path override.
        preroll_ms: Optional preroll delay override in milliseconds.
        lfstats_url: Optional URL override for lfstats API.
    """

    config: str | None = None
    log_tdf: bool = False
    log_output: bool = False
    tdf_port: int | None = None
    consumer_port: int | None = None
    database_path: str | None = None
    preroll_ms: int | None = None
    lfstats_url: str | None = None


def parse_args(args: Sequence[str] | None = None) -> LFLiveArgs:
    """Parses command-line arguments for lflive.

    Args:
        args: Optional list of raw string arguments. If None, sys.argv is used.

    Returns:
        LFLiveArgs: Structured parsed command-line arguments.

    Raises:
        SystemExit: If argument parsing fails or --help is requested.

    Usage example:
        cli_args = parse_args(['--log_tdf'])
        assert cli_args.log_tdf is True
    """
    parser = argparse.ArgumentParser(
        description='lflive - Laserforce real-time live game parser service'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to YAML configuration file.',
    )
    parser.add_argument(
        '--log_tdf',
        action='store_true',
        default=False,
        help='Print every received TDF line to standard output.',
    )
    parser.add_argument(
        '--log_output',
        action='store_true',
        default=False,
        help='Print every consumer broadcast line to standard output.',
    )
    parser.add_argument(
        '--tdf_port',
        type=int,
        default=None,
        help='TCP port to listen on for incoming TDF stream.',
    )
    parser.add_argument(
        '--consumer_port',
        type=int,
        default=None,
        help='TCP port to listen on for consumer connections.',
    )
    parser.add_argument(
        '--database',
        '--db_path',
        dest='database_path',
        type=str,
        default=None,
        help='Relative path to SQLite database file.',
    )
    parser.add_argument(
        '--preroll_ms',
        '--delay_ms',
        dest='preroll_ms',
        type=int,
        default=None,
        help='Preroll delay in milliseconds.',
    )
    parser.add_argument(
        '--lfstats_url',
        type=str,
        default=None,
        help='Base URL endpoint for the lfstats API.',
    )

    parsed = parser.parse_args(args=args)

    return LFLiveArgs(
        config=parsed.config,
        log_tdf=bool(parsed.log_tdf),
        log_output=bool(parsed.log_output),
        tdf_port=parsed.tdf_port,
        consumer_port=parsed.consumer_port,
        database_path=parsed.database_path,
        preroll_ms=parsed.preroll_ms,
        lfstats_url=parsed.lfstats_url,
    )


def resolve_config(cli_args: LFLiveArgs) -> LFLiveConfig:
    """Merges CLI argument overrides into loaded YAML configuration.

    Args:
        cli_args: Parsed command-line arguments.

    Returns:
        LFLiveConfig: Resolved runtime configuration.

    Usage example:
        args = parse_args(['--tdf_port', '9999'])
        cfg = resolve_config(args)
        assert cfg.tdf_port == 9999
    """
    config = load_config(path=cli_args.config)

    tdf_port = (
        cli_args.tdf_port if cli_args.tdf_port is not None else config.tdf_port
    )
    consumer_port = (
        cli_args.consumer_port
        if cli_args.consumer_port is not None
        else config.consumer_port
    )
    database_path = (
        cli_args.database_path
        if cli_args.database_path is not None
        else config.database_path
    )
    preroll_ms = (
        cli_args.preroll_ms
        if cli_args.preroll_ms is not None
        else config.preroll_ms
    )
    lfstats_url = (
        cli_args.lfstats_url
        if cli_args.lfstats_url is not None
        else config.lfstats_url
    )
    log_tdf = config.log_tdf or cli_args.log_tdf
    log_output = config.log_output or cli_args.log_output

    return LFLiveConfig(
        tdf_port=tdf_port,
        consumer_port=consumer_port,
        lfstats_url=lfstats_url,
        database_path=database_path,
        preroll_ms=preroll_ms,
        log_tdf=log_tdf,
        log_output=log_output,
    )
