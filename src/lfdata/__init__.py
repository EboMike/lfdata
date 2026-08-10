"""lfdata package for importing, storing, and rendering LF data.

This package serves as the main entry point for managing Laserforce (LF) game data.
It handles parsing TDF data files into structured database models, simulating
game state playback, and generating high-quality video visualizers.

Usage example:
    from lfdata import parse_tdf

    game = parse_tdf('path/to/game.tdf')
    print(f'Imported game {game.game_id} with {len(game.entities)} entities.')
"""

from lfdata.importer import TdfImporter, parse_tdf

__version__ = '0.9.3'

__all__ = ['TdfImporter', 'parse_tdf', '__version__']
