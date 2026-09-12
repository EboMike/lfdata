import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lfdata.dump_tdf import TdfStateDumper, main
from lfdata.dump_tdf_types import (
    TdfDumpFormat,
    TdfDumpTrigger,
    TdfPlayerSelection,
)
from lfdata.importer import TdfImporter


@pytest.fixture
def sample_tdf_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent / 'assets' / 'sm5_sanitized.tdf'
    )


def test_dumper_default_csv_player_change(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    player_count = len([e for e in game.entities if e.type == 'player'])
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.PLAYER_CHANGE,
        output_format=TdfDumpFormat.CSV,
        player_selection=TdfPlayerSelection.ALL,
    )

    entries = dumper.collect_entries()
    assert len(entries) > 0
    # First entry should be initial state at 0 ms
    assert entries[0].time_ms == 0
    assert entries[0].event_description == 'Initial State'
    assert len(entries[0].players) == player_count

    csv_output = dumper.dump_to_string()
    reader = list(csv.reader(io.StringIO(csv_output)))
    assert len(reader) > 1
    assert reader[0][0] == 'time_ms'
    assert reader[0][1] == 'time_str'
    assert reader[0][2] == 'entity_id'
    assert reader[0][7] == 'score'
    # Initial state row has formatted time 00:00.000
    assert reader[1][0] == '0'
    assert reader[1][1] == '00:00.000'


def test_dumper_player_change_changed_only(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    player_count = len([e for e in game.entities if e.type == 'player'])
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.PLAYER_CHANGE,
        output_format=TdfDumpFormat.CSV,
        player_selection=TdfPlayerSelection.CHANGED,
    )

    entries = dumper.collect_entries()
    assert len(entries) > 0
    # Subsequent entries should only include players who changed
    for entry in entries[1:]:
        assert len(entry.players) >= 1
        assert len(entry.players) <= player_count


def test_dumper_format_json(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    player_count = len([e for e in game.entities if e.type == 'player'])
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.FINAL,
        output_format=TdfDumpFormat.JSON,
    )

    json_str = dumper.dump_to_string()
    data = json.loads(json_str)
    assert isinstance(data, list)
    assert len(data) == 1
    assert 'time_ms' in data[0]
    assert 'time_str' in data[0]
    assert data[0]['time_str'] == '15:00.004'
    assert 'players' in data[0]
    assert len(data[0]['players']) == player_count


def test_dumper_format_jsonl(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    player_count = len([e for e in game.entities if e.type == 'player'])
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.FINAL,
        output_format=TdfDumpFormat.JSONL,
    )

    jsonl_str = dumper.dump_to_string().strip()
    lines = jsonl_str.split('\n')
    assert len(lines) == player_count
    first_record = json.loads(lines[0])
    assert 'entity_id' in first_record
    assert 'time_str' in first_record
    assert first_record['time_str'] == '15:00.004'
    assert 'score' in first_record
    assert 'hp' in first_record


def test_dumper_format_text(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.FINAL,
        output_format=TdfDumpFormat.TEXT,
    )

    text_output = dumper.dump_to_string()
    assert '=== Game State at ' in text_output
    assert 'Score=' in text_output
    assert 'Lives=' in text_output


def test_dumper_trigger_event(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.EVENT,
        output_format=TdfDumpFormat.CSV,
    )

    entries = dumper.collect_entries()
    assert len(entries) == len(game.events)


def test_dumper_trigger_interval(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    interval_ms = 60000
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.INTERVAL,
        output_format=TdfDumpFormat.CSV,
        interval_ms=interval_ms,
    )

    entries = dumper.collect_entries()
    assert len(entries) >= 2
    # Timestamps should be multiples of interval_ms (0, 60000, 120000, ...)
    for idx, entry in enumerate(entries):
        assert entry.time_ms == idx * interval_ms


def test_dumper_dump_to_stream(sample_tdf_path: Path) -> None:
    game = TdfImporter(str(sample_tdf_path)).parse()
    player_count = len([e for e in game.entities if e.type == 'player'])
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.FINAL,
        output_format=TdfDumpFormat.CSV,
    )

    buffer = io.StringIO()
    dumper.dump(buffer)
    content = buffer.getvalue()
    assert 'time_ms' in content
    assert len(content.splitlines()) == player_count + 1


def test_main_no_args_exits() -> None:
    with patch('sys.argv', ['dump-tdf.py']):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


def test_main_stdout_csv(sample_tdf_path: Path) -> None:
    with (
        patch(
            'sys.argv',
            ['dump-tdf.py', str(sample_tdf_path), '--trigger', 'final'],
        ),
        patch('sys.stdout', new_callable=io.StringIO) as mock_stdout,
    ):
        main()
        output = mock_stdout.getvalue()
        assert 'time_ms' in output
        assert 'time_str' in output
        assert '15:00.004' in output
        assert 'entity_id' in output


def test_main_output_file_json(sample_tdf_path: Path, tmp_path: Path) -> None:
    out_file = tmp_path / 'dump.json'
    test_args = [
        'dump-tdf.py',
        '--input_tdf',
        str(sample_tdf_path),
        '--trigger',
        'final',
        '--format',
        'json',
        '--output',
        str(out_file),
    ]
    with patch('sys.argv', test_args):
        main()

    assert out_file.exists()
    content = json.loads(out_file.read_text(encoding='utf-8'))
    assert isinstance(content, list)
    assert len(content) == 1


def test_main_root_script_invocation(
    sample_tdf_path: Path, tmp_path: Path
) -> None:
    import importlib.util

    root_script = Path(__file__).resolve().parent.parent / 'dump-tdf.py'
    spec = importlib.util.spec_from_file_location(
        'root_dump_tdf', str(root_script)
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out_file = tmp_path / 'root_test.csv'
    test_args = [
        'dump-tdf.py',
        str(sample_tdf_path),
        '--trigger',
        'final',
        '--output',
        str(out_file),
    ]
    with patch('sys.argv', test_args):
        module.run()

    assert out_file.exists()
    assert 'time_ms' in out_file.read_text(encoding='utf-8')
