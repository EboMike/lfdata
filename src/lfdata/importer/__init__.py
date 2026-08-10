"""Modules for importing LF data from various file formats.

Provides importers for reading game session files (such as tab-delimited TDF files)
and converting them into populated model instances.

Usage example:
    from lfdata.importer import parse_tdf

    game = parse_tdf('path/to/game.tdf')
"""

from .tdf import TdfImporter, parse_tdf

__all__ = ['TdfImporter', 'parse_tdf']
