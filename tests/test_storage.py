from datetime import datetime
from pathlib import Path

from lfdata.importer import TdfImporter
from lfdata.model import LFGame
from lfdata.storage import DatabaseStorage


def test_database_storage_save_and_retrieve() -> None:
    storage = DatabaseStorage('sqlite:///:memory:')

    game = LFGame(
        game_id='test_game_001',
        timestamp=datetime.now(),
        game_type='Test Game',
        arena_name='Brisbane',
    )

    assert storage.save_game(game) is True

    retrieved = storage.get_game('test_game_001')
    assert retrieved is not None
    assert retrieved.game_id == 'test_game_001'
    assert retrieved.arena_name == 'Brisbane'


def test_database_storage_real_game() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    importer = TdfImporter(real_path)
    game = importer.parse()

    storage = DatabaseStorage('sqlite:///:memory:')
    assert storage.save_game(game) is True

    retrieved = storage.get_game('sm5_sanitized')
    assert retrieved is not None
    assert retrieved.game_id == 'sm5_sanitized'
    assert retrieved.arena_name == 'Invasion'
    assert len(retrieved.teams) == 3
    assert len(retrieved.entities) > 0
    assert len(retrieved.events) > 0
    assert len(retrieved.sm5_stats) > 0
    assert len(retrieved.score_history) > 0
    assert len(retrieved.state_history) > 0

    # Verify player linkage
    player_entity = next(
        (e for e in retrieved.entities if e.type == 'player'), None
    )
    assert player_entity is not None
    assert player_entity.player is not None
    assert player_entity.player.codename == player_entity.desc


def test_database_storage_laserball_game() -> None:
    from lfdata.model import LaserballStats

    storage = DatabaseStorage('sqlite:///:memory:')
    game = LFGame(
        game_id='laserball_game_001',
        timestamp=datetime.now(),
        game_type='Laserball',
        arena_name='Brisbane',
    )
    stat = LaserballStats(
        game_id='laserball_game_001',
        entity_id='P1',
        goals=3,
        assists=2,
        steals=1,
        clears=4,
        blocks=12,
        times_zapped=3,
    )
    game.laserball_stats.append(stat)

    assert storage.save_game(game) is True

    retrieved = storage.get_game('laserball_game_001')
    assert retrieved is not None
    assert retrieved.game_id == 'laserball_game_001'
    assert retrieved.is_laserball is True
    assert len(retrieved.laserball_stats) == 1
    assert retrieved.laserball_stats[0].goals == 3
    assert retrieved.laserball_stats[0].assists == 2
    assert retrieved.laserball_stats[0].score == 50512
