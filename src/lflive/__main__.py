"""Main executable entry point for the lflive service.

This module initializes the lflive server skeleton, parses command-line
arguments, loads configuration, and sets up SQLite persistence.

Usage example:
    python -m lflive --log_tdf --tdf_port 8000
"""

import sys
from collections.abc import Sequence

from lflive.cli import parse_args, resolve_config
from lflive.db import LiveDatabase


def main(args: Sequence[str] | None = None) -> int:
    """Executes the lflive service skeleton.

    Parses command-line arguments, resolves the configuration, initializes the
    SQLite database, and prints server startup information.

    Args:
        args: Optional list of command-line argument strings.

    Returns:
        int: Process exit code (0 for success).

    Usage example:
        exit_code = main(['--log_tdf'])
        assert exit_code == 0
    """
    cli_args = parse_args(args=args)
    config = resolve_config(cli_args=cli_args)

    print('Starting lflive server...')
    print(f'Database path: {config.database_path}')
    print(f'TDF listening port: {config.tdf_port}')
    print(f'Consumer broadcast port: {config.consumer_port}')
    print(f'Preroll delay: {config.preroll_ms} ms')
    print(f'Log TDF: {config.log_tdf}')
    print(f'Log Output: {config.log_output}')

    db = LiveDatabase(db_path=config.database_path)
    db.init_db()
    print('SQLite database initialized successfully.')

    return 0


if __name__ == '__main__':
    sys.exit(main())

