"""LF replay system package for simulating game playback and verifying state.

Provides state simulation (`LFReplaySystem`), event records (`LFReplayEventRecord`),
game state snapshot containers, and integrity verifiers (`LFReplayVerifier`).

Usage example:
    from lfdata.replay import LFReplaySystem

    replay = LFReplaySystem(game=game)
    replay.process_all_events()
"""

from lfdata.replay.record import LFReplayEventRecord
from lfdata.replay.replay import LFReplaySystem
from lfdata.replay.state import (
    LFReplayGameState,
    LFReplayPlayerState,
    LFReplayTeamState,
)
from lfdata.replay.verification import LFReplayVerifier

__all__ = [
    'LFReplaySystem',
    'LFReplayEventRecord',
    'LFReplayPlayerState',
    'LFReplayTeamState',
    'LFReplayGameState',
    'LFReplayVerifier',
]
