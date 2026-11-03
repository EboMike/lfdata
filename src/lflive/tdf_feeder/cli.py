"""Command-line argument parser for the tdf_feeder simulation tool.

This module parses command-line parameters for streaming TDF files to an
active live parser server.

Usage example:
    from lflive.tdf_feeder.cli import parse_args

    args = parse_args(['assets/game.tdf', '127.0.0.1:8000'])
    print(args.file_path, args.host, args.port)
"""

import argparse
import dataclasses
from collections.abc import Sequence


@dataclasses.dataclass
class TdfFeederArgs:
    """Parsed command-line options for tdf_feeder.

    Attributes:
        file_path: Path to the TDF file to stream.
        host: Target server host address or IP.
        port: Target server TCP port number.
        speed: Playback speed multiplier (default 1.0 = real time).
    """

    file_path: str
    host: str = '127.0.0.1'
    port: int = 8000
    speed: float = 1.0


def parse_args(args: Sequence[str] | None = None) -> TdfFeederArgs:
    """Parses command-line arguments for tdf_feeder.

    Args:
        args: Optional list of argument strings.

    Returns:
        TdfFeederArgs: Parsed structured options.

    Raises:
        SystemExit: If required arguments are missing or invalid.

    Usage example:
        opts = parse_args(['game.tdf', '--port', '9000'])
        assert opts.port == 9000
    """
    parser = argparse.ArgumentParser(
        description='tdf_feeder - Laserforce TDF real-time stream simulator'
    )
    parser.add_argument(
        'positional_file',
        nargs='?',
        default=None,
        help='Path to the TDF file to stream.',
    )
    parser.add_argument(
        'positional_target',
        nargs='?',
        default=None,
        help='Target host:port (e.g. 127.0.0.1:8000).',
    )
    parser.add_argument(
        '--file',
        '-f',
        dest='flag_file',
        type=str,
        default=None,
        help='Path to the TDF file to stream.',
    )
    parser.add_argument(
        '--host',
        '--ip',
        dest='host',
        type=str,
        default='127.0.0.1',
        help='Target IP address or hostname (default: 127.0.0.1).',
    )
    parser.add_argument(
        '--port',
        '-p',
        dest='port',
        type=int,
        default=8000,
        help='Target TCP port (default: 8000).',
    )
    parser.add_argument(
        '--speed',
        dest='speed',
        type=float,
        default=1.0,
        help='Playback speed multiplier (default: 1.0 = real-time).',
    )

    parsed = parser.parse_args(args=args)

    file_path = parsed.flag_file or parsed.positional_file
    if not file_path:
        parser.error('A TDF file path must be specified.')

    host = parsed.host
    port = parsed.port

    if parsed.positional_target:
        if ':' in parsed.positional_target:
            target_parts = parsed.positional_target.split(':', 1)
            host = target_parts[0]
            try:
                port = int(target_parts[1])
            except ValueError:
                parser.error(
                    f'Invalid port in target: {parsed.positional_target}'
                )
        else:
            host = parsed.positional_target

    return TdfFeederArgs(
        file_path=file_path,
        host=host,
        port=port,
        speed=parsed.speed,
    )
