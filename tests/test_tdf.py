from pathlib import Path

import pytest

from lfdata import parse_tdf as top_level_parse_tdf
from lfdata.importer import TdfImporter, parse_tdf
from lfdata.model import LFGame


def test_parse_tdf_helper() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    game = parse_tdf(real_path)

    assert isinstance(game, LFGame)
    assert game.game_id == 'sm5_sanitized'
    assert game.centre == '4-43'


def test_top_level_package_exports() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    game = top_level_parse_tdf(real_path)

    assert isinstance(game, LFGame)
    assert game.game_id == 'sm5_sanitized'


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
    assert game.normalized_game_type == 'SM5'
    assert game.mission_type == 5
    assert game.is_sm5 is True
    assert game.start == '20240114205710'
    assert game.file_version == '2.005'
    assert game.program_version == '8.503'
    assert game.centre == '4-43'
    assert game.arena_name == 'Invasion'
    assert game.duration == 900000
    assert game.penalty == -1000
    assert len(game.teams) == 3
    assert len(game.entities) > 0
    assert len(game.events) > 0
    assert len(game.sm5_stats) > 0
    assert len(game.score_history) > 0
    assert len(game.state_history) > 0


def test_tdf_importer_encodings(tmp_path) -> None:
    tdf_line = '0\t2.005\t8.503\t4-43\tInvasion\t900000\t-1000\n'

    # 1. UTF-16 with BOM
    f1 = tmp_path / 'f1.tdf'
    with open(f1, 'w', encoding='utf-16') as f:
        f.write(tdf_line)
    importer1 = TdfImporter(f1)
    game1 = importer1.parse()
    assert game1.centre == '4-43'

    # 2. UTF-16-LE without BOM
    f2 = tmp_path / 'f2.tdf'
    with open(f2, 'w', encoding='utf-16-le') as f:
        f.write(tdf_line)
    importer2 = TdfImporter(f2)
    game2 = importer2.parse()
    assert game2.centre == '4-43'

    # 3. UTF-16-BE without BOM
    f3 = tmp_path / 'f3.tdf'
    with open(f3, 'w', encoding='utf-16-be') as f:
        f.write(tdf_line)
    importer3 = TdfImporter(f3)
    game3 = importer3.parse()
    assert game3.centre == '4-43'

    # 4. UTF-8
    f4 = tmp_path / 'f4.tdf'
    with open(f4, 'w', encoding='utf-8') as f:
        f.write(tdf_line)
    importer4 = TdfImporter(f4)
    game4 = importer4.parse()
    assert game4.centre == '4-43'


def test_tdf_importer_non_sm5(tmp_path: Path) -> None:
    non_sm5_file = tmp_path / 'non_sm5.tdf'
    content = (
        ';1/mission\ttype\tdesc\tstart\tduration\tpenalty\n'
        '1\t2\tTeam Elimination\t20240114205710\t900000\t-1000\n'
    )
    non_sm5_file.write_text(content, encoding='utf-8')
    importer = TdfImporter(non_sm5_file)
    game = importer.parse()
    assert game.mission_type == 2
    assert game.is_sm5 is False


def test_tdf_importer_parse_event_0b00(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'beacon_event.tdf'
    content = (
        ';1/mission\ttype\tdesc\tstart\tduration\tpenalty\n'
        '1\t5\tSpace Marines 5\t20240114205710\t900000\t-1000\n'
        '4\t15000\t0B00\t#P1\t claims a beacon\n'
        '4\t20000\t0B00\t#P2\t claims a beacon \t@B1\n'
        '4\t25000\t0B00\t#P3\n'
    )
    tdf_file.write_text(content, encoding='utf-8')
    importer = TdfImporter(tdf_file)
    game = importer.parse()

    assert len(game.events) == 3

    assert game.events[0].time == 15000
    assert game.events[0].event_type == '0B00'
    assert game.events[0].actor_entity_id == '#P1'
    assert game.events[0].action == 'claims a beacon'
    assert game.events[0].target_entity_id is None

    assert game.events[1].time == 20000
    assert game.events[1].event_type == '0B00'
    assert game.events[1].actor_entity_id == '#P2'
    assert game.events[1].action == 'claims a beacon'
    assert game.events[1].target_entity_id == '@B1'

    assert game.events[2].time == 25000
    assert game.events[2].event_type == '0B00'
    assert game.events[2].actor_entity_id == '#P3'
    assert game.events[2].action == 'claims a beacon'
    assert game.events[2].target_entity_id is None


def test_tdf_importer_parse_event_0209(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'warbot_zap_event.tdf'
    content = (
        ';1/mission\ttype\tdesc\tstart\tduration\tpenalty\n'
        '1\t5\tSpace Marines 5\t20240114205710\t900000\t-1000\n'
        '4\t12000\t0209\t#W1\tzaps\t#P1\n'
    )
    tdf_file.write_text(content, encoding='utf-8')
    importer = TdfImporter(tdf_file)
    game = importer.parse()

    assert len(game.events) == 1
    assert game.events[0].time == 12000
    assert game.events[0].event_type == '0209'
    assert game.events[0].actor_entity_id == '#W1'
    assert game.events[0].action == 'zaps'
    assert game.events[0].target_entity_id == '#P1'
