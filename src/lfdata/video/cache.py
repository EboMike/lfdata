"""Disk-based caching of precomputed replay simulation snapshots.

This module provides `ReplaySnapshotCache` and `ReplayCachePayload` to persist
and retrieve computationally intensive replay simulation results and visual
element snapshot timelines to disk using compressed serialization.

Usage example:
    from lfdata.video.cache import ReplaySnapshotCache, ReplayCachePayload

    cache = ReplaySnapshotCache()
    payload = cache.load(game=game, player_name='Player1')
    if payload is None:
        # compute payload
        cache.save(game=game, payload=payload, player_name='Player1')
"""

from dataclasses import dataclass
import gzip
import hashlib
import os
from pathlib import Path
import pickle
import tempfile

from lfdata.video.downtime import DowntimeParameters
from lfdata.model.objects.game import LFGame
from lfdata.replay.state import LFReplayPlayerState, LFReplayTeamState
from lfdata.video.element import (
    LFCameraShake,
    LFEventLogEntry,
    LFHitBorderInstance,
    LFNukeInterval,
    LFPlayerEventLogEntry,
)
from lfdata.video.helpers import LFTeamTransition


@dataclass
class ReplayCachePayload:
    """Serializable container for precomputed replay simulation snapshots.

    Attributes:
        snapshots: List of chronological replay state snapshot tuples.
        snapshot_times: List of snapshot timestamps in milliseconds.
        event_log: List of global LFEventLogEntry records.
        player_event_log: List of focused player LFPlayerEventLogEntry records.
        team_transitions: Dictionary mapping team index to rank transitions.
        game_ended_at_ms: Optional millisecond timestamp when the game ended.
        nuke_intervals: List of active LFNukeInterval intervals.
        camera_shakes: List of LFCameraShake effect instances.
        nuke_flashes: List of nuke flash timestamps in milliseconds.
        missile_flashes_ms: List of missile hit timestamps in milliseconds.
        hit_borders: List of LFHitBorderInstance effect entries.
        downtime_params: DowntimeParameters calculated for the game.
    """

    snapshots: list[
        tuple[
            int,
            dict[str, LFReplayPlayerState],
            dict[int, LFReplayTeamState],
        ]
    ]
    snapshot_times: list[int]
    event_log: list[LFEventLogEntry]
    player_event_log: list[LFPlayerEventLogEntry]
    team_transitions: dict[int, list[LFTeamTransition]]
    game_ended_at_ms: int | None
    nuke_intervals: list[LFNukeInterval]
    camera_shakes: list[LFCameraShake]
    nuke_flashes: list[int]
    missile_flashes_ms: list[int]
    hit_borders: list[LFHitBorderInstance]
    downtime_params: DowntimeParameters


class ReplaySnapshotCache:
    """Disk cache manager for replay snapshots and simulation timelines.

    Attributes:
        cache_dir: Filesystem directory storing compressed cache files.
        enabled: Boolean flag indicating if caching is active.
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        enabled: bool = True,
    ) -> None:
        """Initializes the replay snapshot cache.

        Args:
            cache_dir: Optional custom directory path to store cache files.
            enabled: Boolean flag to enable or disable disk caching.
        """
        self.enabled = enabled
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir)
        else:
            env_dir = os.environ.get('LFDATA_CACHE_DIR')
            if env_dir:
                self.cache_dir = Path(env_dir)
            else:
                self.cache_dir = (
                    Path.home() / '.cache' / 'lfdata' / 'replays'
                )

        if self.enabled:
            self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Creates the cache directory on disk if it does not exist."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def compute_key(
        self,
        game: LFGame,
        player_name: str | None = None,
        pregame_delay_ms: int = 0,
    ) -> str:
        """Computes a deterministic SHA-256 cache key for a game session.

        Args:
            game: The LFGame instance to hash.
            player_name: Optional focused player codename string.
            pregame_delay_ms: Pregame delay timing offset in milliseconds.

        Returns:
            str: Hexadecimal SHA-256 hash string.
        """
        hasher = hashlib.sha256()
        hasher.update(str(game.game_id or '').encode('utf-8'))
        hasher.update(str(game.duration or 0).encode('utf-8'))
        hasher.update(str(game.game_type or '').encode('utf-8'))
        hasher.update(str(player_name or '').encode('utf-8'))
        hasher.update(str(pregame_delay_ms).encode('utf-8'))

        events = game.events or []
        hasher.update(str(len(events)).encode('utf-8'))

        if events:
            # Sample events across the timeline to capture any event mutations
            step = max(1, len(events) // 100)
            for ev in events[::step]:
                part = (
                    f'{ev.time}:{ev.event_type}:{ev.actor_entity_id}:'
                    f'{ev.target_entity_id}'
                )
                hasher.update(part.encode('utf-8'))

        return hasher.hexdigest()

    def get_cache_path(
        self,
        game: LFGame,
        player_name: str | None = None,
        pregame_delay_ms: int = 0,
    ) -> Path:
        """Returns the file path for the cached replay data.

        Args:
            game: The LFGame instance.
            player_name: Optional focused player codename string.
            pregame_delay_ms: Pregame delay timing offset in milliseconds.

        Returns:
            Path: Path object pointing to the expected cache file.
        """
        key = self.compute_key(
            game=game,
            player_name=player_name,
            pregame_delay_ms=pregame_delay_ms,
        )
        return self.cache_dir / f'{key}.cache'

    def load(
        self,
        game: LFGame,
        player_name: str | None = None,
        pregame_delay_ms: int = 0,
    ) -> ReplayCachePayload | None:
        """Loads and deserializes cached replay data from disk.

        Args:
            game: The LFGame instance.
            player_name: Optional focused player codename string.
            pregame_delay_ms: Pregame delay timing offset in milliseconds.

        Returns:
            ReplayCachePayload | None: Deserialized payload, or None on miss.
        """
        if not self.enabled:
            return None

        cache_path = self.get_cache_path(
            game=game,
            player_name=player_name,
            pregame_delay_ms=pregame_delay_ms,
        )
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'rb') as f:
                compressed = f.read()
            decompressed = gzip.decompress(compressed)
            data = pickle.loads(decompressed)
            if isinstance(data, ReplayCachePayload):
                return data
        except Exception:
            # Remove corrupted or incompatible cache file
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass

        return None

    def save(
        self,
        game: LFGame,
        payload: ReplayCachePayload,
        player_name: str | None = None,
        pregame_delay_ms: int = 0,
    ) -> Path | None:
        """Serializes and saves replay payload to disk compressed with gzip.

        Args:
            game: The LFGame instance.
            payload: The precomputed ReplayCachePayload to save.
            player_name: Optional focused player codename string.
            pregame_delay_ms: Pregame delay timing offset in milliseconds.

        Returns:
            Path | None: Saved cache file path, or None if disabled or failed.
        """
        if not self.enabled:
            return None

        self._ensure_cache_dir()
        cache_path = self.get_cache_path(
            game=game,
            player_name=player_name,
            pregame_delay_ms=pregame_delay_ms,
        )

        try:
            raw_bytes = pickle.dumps(
                payload, protocol=pickle.HIGHEST_PROTOCOL
            )
            compressed = gzip.compress(raw_bytes, compresslevel=1)

            # Atomic write via temporary file
            temp_file = tempfile.NamedTemporaryFile(
                dir=str(self.cache_dir), delete=False
            )
            temp_path = Path(temp_file.name)
            try:
                temp_file.write(compressed)
                temp_file.flush()
                temp_file.close()
                temp_path.replace(cache_path)
                return cache_path
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
        except Exception:
            return None

    def clear(self) -> int:
        """Removes all cached replay files from the cache directory.

        Returns:
            int: Number of deleted cache files.
        """
        count = 0
        if not self.cache_dir.exists():
            return count

        for p in self.cache_dir.glob('*.cache'):
            try:
                p.unlink()
                count += 1
            except OSError:
                pass

        return count
