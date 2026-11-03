"""TDF feeder simulator tool for lflive.

This package provides a simulator binary that reads Laserforce TDF files and
streams them over TCP to a live parser server in real-time in UTF-16LE.

Usage example:
    from lflive.tdf_feeder import TdfFeeder, TdfFileReader

    reader = TdfFileReader('assets/game.tdf')
    lines = reader.read_lines()
    feeder = TdfFeeder('127.0.0.1', 8000, lines)
    await feeder.feed()
"""

from lflive.tdf_feeder.cli import TdfFeederArgs, parse_args
from lflive.tdf_feeder.feeder import TdfFeeder
from lflive.tdf_feeder.reader import TdfFileReader, TdfLine

__all__ = [
    'TdfFeeder',
    'TdfFeederArgs',
    'TdfFileReader',
    'TdfLine',
    'parse_args',
]

