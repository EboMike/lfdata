"""lflive real-time Laserforce TDF live streaming parser service.

This package provides real-time ingestion of Laserforce TDF game event streams
over TCP, internal game state recreation, SQLite snapshotting, and broadcast
to consumer visualizers.

Usage example:
    from lflive import LiveDatabase, LiveGameState, TdfListener, parse_args

    args = parse_args()
    state = LiveGameState()
    listener = TdfListener(port=args.tdf_port or 8000, game_state=state)
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
from lflive.tdf_listener import TdfListener, detect_encoding

__all__ = [
    'LFLiveArgs',
    'LFLiveConfig',
    'LiveDatabase',
    'LiveGameState',
    'LivePlayerState',
    'LiveTargetState',
    'LiveTeamState',
    'SnapshotEntry',
    'TdfListener',
    'detect_encoding',
    'load_config',
    'parse_args',
    'resolve_config',
]
