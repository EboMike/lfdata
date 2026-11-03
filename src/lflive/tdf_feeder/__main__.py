"""Main executable entry point for the tdf_feeder simulator binary.

This module parses command-line flags, reads the specified TDF file, connects
to the target server via TCP, and streams lines in real-time in UTF-16LE.

Usage example:
    python -m lflive.tdf_feeder assets/game.tdf 127.0.0.1:8000
"""

import asyncio
import sys
from collections.abc import Sequence

from lflive.tdf_feeder.cli import parse_args
from lflive.tdf_feeder.feeder import TdfFeeder
from lflive.tdf_feeder.reader import TdfFileReader


def main(args: Sequence[str] | None = None) -> int:
    """Executes the tdf_feeder binary.

    Args:
        args: Optional list of command-line argument strings.

    Returns:
        int: Process exit code (0 for success).

    Raises:
        FileNotFoundError: If the TDF file does not exist.
        ConnectionRefusedError: If the target server is unreachable.

    Usage example:
        exit_code = main(['assets/game.tdf', '--port', '8000'])
        assert exit_code == 0
    """
    opts = parse_args(args=args)

    print(f'Loading TDF file: {opts.file_path}')
    reader = TdfFileReader(file_path=opts.file_path)
    lines = reader.read_lines()
    print(f'Loaded {len(lines)} lines from {opts.file_path}.')

    print(
        f'Connecting to {opts.host}:{opts.port} (playback speed: {opts.speed}x)...'
    )
    feeder = TdfFeeder(
        host=opts.host,
        port=opts.port,
        lines=lines,
        speed=opts.speed,
    )

    try:
        sent_count = asyncio.run(feeder.feed())
        print(f'Successfully streamed {sent_count} lines. Feed complete.')
        return 0
    except KeyboardInterrupt:
        print('\nStreaming interrupted by user.')
        return 1
    except ConnectionRefusedError:
        print(
            f'Error: Could not connect to {opts.host}:{opts.port}. '
            f'Is the server running?'
        )
        return 2


if __name__ == '__main__':
    sys.exit(main())

