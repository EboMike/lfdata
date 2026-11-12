from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import patch

from lfdata.model import GameEntity, GameEvent, GameTeam, LFGame
from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_DOWNED_OPPONENT,
    SM5_EVENT_MISSION_START,
)
from lfdata.video.cache import ReplayCachePayload, ReplaySnapshotCache
from lfdata.video.downtime import DowntimeParameters
from lfdata.video.element import (
    LFCameraShake,
    LFEventLogEntry,
    LFHitBorderInstance,
    LFNukeInterval,
    LFPlayerEventLogEntry,
)
from lfdata.video.generator import VisualElementGenerator
from lfdata.video.helpers import LFTeamTransition


def _make_dummy_game() -> LFGame:
    game = LFGame(
        game_id='test_cache_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    game.duration = 60000
    t1 = GameTeam(
        game_id='test_cache_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_cache_game',
        team_index=1,
        desc='Ice Team',
        color_enum=12,
        color_desc='Ice',
        color_rgb='#0050FF',
    )
    game.teams = [t1, t2]

    p1 = GameEntity(
        game_id='test_cache_game',
        entity_id='P1',
        type='player',
        desc='Shooter',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    p2 = GameEntity(
        game_id='test_cache_game',
        entity_id='P2',
        type='player',
        desc='Target',
        team_index=1,
        level=1,
        category=1,
        battlesuit='Scout',
    )
    game.entities = [p1, p2]

    game.events = [
        GameEvent(
            game_id='test_cache_game',
            time=0,
            event_type=SM5_EVENT_MISSION_START,
            action='start',
            raw_message='',
        ),
        GameEvent(
            game_id='test_cache_game',
            time=3000,
            event_type=SM5_EVENT_DOWNED_OPPONENT,
            actor_entity_id='P1',
            target_entity_id='P2',
            action='zaps',
            raw_message='',
        ),
    ]
    return game


def _make_dummy_payload() -> ReplayCachePayload:
    return ReplayCachePayload(
        snapshots=[],
        snapshot_times=[],
        event_log=[
            LFEventLogEntry(
                time=1000,
                desc='Player tagged Target',
                is_important=False,
            )
        ],
        player_event_log=[
            LFPlayerEventLogEntry(
                time=1000,
                desc='You tagged Target',
            )
        ],
        team_transitions=[
            LFTeamTransition(
                event_time_ms=500,
                visual_rank=1.0,
                ranking=1,
            )
        ],
        game_ended_at_ms=900000,
        nuke_intervals=[
            LFNukeInterval(
                start_ms=10000,
                end_ms=15000,
                nuker_name='Shooter',
            )
        ],
        camera_shakes=[
            LFCameraShake(
                start_ms=1000,
                duration_ms=500,
                strength=2.5,
            )
        ],
        nuke_flashes=[20000],
        missile_flashes_ms=[30000],
        hit_borders=[
            LFHitBorderInstance(
                start_ms=5000,
                duration_ms=1000,
                tint_hex='#FF0000',
                max_scale=1.0,
            )
        ],
        downtime_params=DowntimeParameters(),
    )


def test_cache_payload_attributes() -> None:
    payload = _make_dummy_payload()
    assert payload.game_ended_at_ms == 900000
    assert len(payload.event_log) == 1
    assert len(payload.player_event_log) == 1
    assert len(payload.team_transitions) == 1
    assert len(payload.nuke_intervals) == 1
    assert len(payload.camera_shakes) == 1
    assert payload.nuke_flashes == [20000]
    assert payload.missile_flashes_ms == [30000]
    assert len(payload.hit_borders) == 1


def test_compute_key_deterministic() -> None:
    game1 = _make_dummy_game()
    game2 = _make_dummy_game()

    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir))
        key1 = cache.compute_key(game1, 'Shooter', 5000)
        key2 = cache.compute_key(game2, 'Shooter', 5000)
        assert key1 == key2

        key_diff_player = cache.compute_key(game1, 'Target', 5000)
        assert key1 != key_diff_player

        key_diff_delay = cache.compute_key(game1, 'Shooter', 0)
        assert key1 != key_diff_delay


def test_cache_save_and_load_round_trip() -> None:
    game = _make_dummy_game()
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir))
        payload = _make_dummy_payload()

        saved_path = cache.save(game, payload, player_name='Shooter')
        assert saved_path is not None
        assert saved_path.exists()

        loaded = cache.load(game, player_name='Shooter')
        assert loaded is not None
        assert loaded.game_ended_at_ms == 900000
        assert len(loaded.event_log) == 1
        assert loaded.event_log[0].desc == 'Player tagged Target'
        assert loaded.nuke_flashes == [20000]


def test_cache_load_missing() -> None:
    game = _make_dummy_game()
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir))
        assert cache.load(game, player_name='NonExistent') is None


def test_cache_load_corrupted_file() -> None:
    game = _make_dummy_game()
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir))
        cache_path = cache.get_cache_path(game, player_name='Corrupted')
        cache_path.write_bytes(b'garbage data that is not gzip or pickle')

        loaded = cache.load(game, player_name='Corrupted')
        assert loaded is None
        assert not cache_path.exists()


def test_cache_disabled() -> None:
    game = _make_dummy_game()
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir), enabled=False)
        payload = _make_dummy_payload()

        assert cache.save(game, payload, player_name='Shooter') is None
        assert cache.load(game, player_name='Shooter') is None


def test_cache_clear() -> None:
    game = _make_dummy_game()
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir))
        payload = _make_dummy_payload()

        cache.save(game, payload, player_name='Shooter')
        assert cache.load(game, player_name='Shooter') is not None

        cache.clear()
        assert cache.load(game, player_name='Shooter') is None


def test_cache_custom_env_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch.dict('os.environ', {'LFDATA_CACHE_DIR': tmp_dir}):
            cache = ReplaySnapshotCache()
            assert str(cache.cache_dir).startswith(tmp_dir)


def test_generator_uses_cache() -> None:
    game = _make_dummy_game()

    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir))

        # First run: miss and populates cache
        gen1 = VisualElementGenerator(
            game=game,
            player_name='Shooter',
            config={},
            cache=cache,
            use_cache=True,
        )
        assert len(gen1.event_log) > 0

        cache_files = list(Path(tmp_dir).glob('*.cache'))
        assert len(cache_files) == 1

        # Second run: hits cache
        with patch(
            'lfdata.replay.LFReplaySystem.run'
        ) as mock_run:
            gen2 = VisualElementGenerator(
                game=game,
                player_name='Shooter',
                config={},
                cache=cache,
                use_cache=True,
            )
            assert mock_run.call_count == 0
            assert len(gen2.event_log) == len(gen1.event_log)


def test_generator_cache_disabled() -> None:
    game = _make_dummy_game()

    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ReplaySnapshotCache(cache_dir=Path(tmp_dir))

        gen = VisualElementGenerator(
            game=game,
            player_name='Shooter',
            config={},
            cache=cache,
            use_cache=False,
        )
        assert len(gen.event_log) > 0

        cache_files = list(Path(tmp_dir).glob('*.cache'))
        assert len(cache_files) == 0
