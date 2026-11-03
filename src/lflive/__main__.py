"""Main executable entry point for the lflive service.

This module initializes the lflive server, parses command-line arguments,
loads configuration, sets up SQLite persistence, and starts the TDF listener.

Usage example:
    python -m lflive --log_tdf --tdf_port 8000
"""

import asyncio
import sys
from collections.abc import Sequence

from lflive.cli import parse_args, resolve_config
from lflive.config import LFLiveConfig
from lflive.db import LiveDatabase
from lflive.emitter import OutputEmitter
from lflive.state.game_state import LiveGameState
from lflive.tdf_listener import TdfListener


async def run_server(config: LFLiveConfig) -> int:
    """Runs the asynchronous server listeners until cancelled.

    Args:
        config: Runtime configuration options.

    Returns:
        int: Process exit code.
    """
    db = LiveDatabase(db_path=config.database_path)
    db.init_db()
    state = LiveGameState()
    emitter = OutputEmitter(log_output=config.log_output)

    listener = TdfListener(
        port=config.tdf_port,
        log_tdf=config.log_tdf,
        game_state=state,
        db=db,
        emitter=emitter,
    )
    await listener.start()
    print(f'Listening for TDF stream on port {config.tdf_port}...')

    try:
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await listener.stop()

    return 0


def main(
    args: Sequence[str] | None = None,
    run_forever: bool = False,
) -> int:
    """Executes the lflive service.

    Parses command-line arguments, resolves the configuration, initializes the
    SQLite database, and optionally starts the server event loop.

    Args:
        args: Optional list of command-line argument strings.
        run_forever: Whether to start and block on the async server loop.

    Returns:
        int: Process exit code (0 for success).

    Usage example:
        exit_code = main(['--log_tdf'], run_forever=False)
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

    if run_forever:
        try:
            return asyncio.run(run_server(config=config))
        except KeyboardInterrupt:
            return 0

    return 0


if __name__ == '__main__':
    sys.exit(main(run_forever=True))
