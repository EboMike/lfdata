"""Executable script for dumping LF game state from a TDF file.

This script provides a direct command-line entrypoint to parse a TDF file,
simulate game replay, and dump player/game state entries at specified triggers
in CSV, JSON, JSONL, or text format.

Usage example:
    python dump-tdf.py game.tdf --format csv --trigger player_change
"""

from pathlib import Path
import sys


def run() -> None:
    """Invokes the main CLI entrypoint for dumping TDF states.

    Usage example:
        run()
    """
    src_dir = Path(__file__).resolve().parent / 'src'
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from lfdata.dump_tdf import main

    main()


if __name__ == '__main__':
    run()
