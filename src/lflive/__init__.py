"""lflive real-time Laserforce TDF live streaming parser service.

This package provides real-time ingestion of Laserforce TDF game event streams
over TCP, internal game state recreation, SQLite snapshotting, and broadcast
to consumer visualizers.

Usage example:
    from lflive import LiveDatabase, LiveGameState, TdfIngestor, TdfListener

    state = LiveGameState()
    ingestor = TdfIngestor(game_state=state)
    listener = TdfListener(port=8000, game_state=state, ingestor=ingestor)
"""

from lflive.cli import LFLiveArgs, parse_args, resolve_config
from lflive.config import LFLiveConfig, load_config
from lflive.consumer_listener import ConsumerListener
from lflive.db import LiveDatabase
from lflive.dummy_player_manager import DummyPlayerManager
from lflive.ingestor import TdfIngestor
from lflive.state import (
    LiveGameState,
    LivePlayerState,
    LiveTargetState,
    LiveTeamState,
    SnapshotEntry,
)
from lflive.tdf_listener import TdfListener, detect_encoding

__all__ = [
    'ConsumerListener',
    'DummyPlayerManager',
    'LFLiveArgs',
    'LFLiveConfig',
    'LiveDatabase',
    'LiveGameState',
    'LivePlayerState',
    'LiveTargetState',
    'LiveTeamState',
    'SnapshotEntry',
    'TdfIngestor',
    'TdfListener',
    'detect_encoding',
    'load_config',
    'parse_args',
    'resolve_config',
]
