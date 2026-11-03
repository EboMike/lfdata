"""lflive real-time Laserforce TDF live streaming parser service.

This package provides real-time ingestion of Laserforce TDF game event streams
over TCP, internal game state recreation, SQLite snapshotting, and broadcast
to consumer visualizers.

Usage example:
    from lflive import LiveDatabase, LiveGameState, parse_args

    args = parse_args()
    state = LiveGameState()
    db = LiveDatabase(args.database_path or 'lflive.db')
    db.init_db()
"""

from lflive.cli import LFLiveArgs, parse_args, resolve_config
from lflive.config import LFLiveConfig, load_config
from lflive.db import LiveDatabase
from lflive.state import (
    LiveGameState,
    LivePlayerState,
    LiveTargetState,
    LiveTeamState,
    SnapshotEntry,
)

__all__ = [
    'LFLiveArgs',
    'LFLiveConfig',
    'LiveDatabase',
    'LiveGameState',
    'LivePlayerState',
    'LiveTargetState',
    'LiveTeamState',
    'SnapshotEntry',
    'load_config',
    'parse_args',
    'resolve_config',
]
