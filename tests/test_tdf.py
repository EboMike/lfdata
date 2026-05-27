from pathlib import Path
import pytest

from lfdata.importer import TdfImporter
from lfdata.model import LFGame


def test_tdf_importer_initialization() -> None:
    importer = TdfImporter('dummy_path.tdf')
    assert importer.file_path.name == 'dummy_path.tdf'


def test_tdf_importer_missing_file() -> None:
    importer = TdfImporter('nonexistent_file.tdf')
    with pytest.raises(FileNotFoundError):
        importer.parse()


def test_tdf_importer_parse_placeholder(tmp_path) -> None:
    dummy_file = tmp_path / 'game_123.tdf'
    dummy_file.touch()

    importer = TdfImporter(dummy_file)
    game = importer.parse()

    assert isinstance(game, LFGame)
    assert game.game_id == 'game_123'
    assert game.game_type == 'Standard TDF'


def test_tdf_importer_parse_real_file() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    importer = TdfImporter(real_path)
    game = importer.parse()

    assert game.game_id == 'sm5_sanitized'
    assert game.game_type == 'Space Marines 5 Tournament Edition'
    assert game.file_version == '2.005'
    assert game.program_version == '8.503'
    assert game.centre == '4-43'
    assert game.duration == 900000
    assert game.penalty == -1000
    assert len(game.teams) == 3
    assert len(game.entities) > 0
    assert len(game.events) > 0
    assert len(game.sm5_stats) > 0
    assert len(game.score_history) > 0
    assert len(game.state_history) > 0
