import pytest

from lfdata.dump_tdf_types import (
    TdfDumpFormat,
    TdfDumpTrigger,
    TdfGameStateEntry,
    TdfPlayerSelection,
    TdfPlayerStateEntry,
    format_time_ms,
)


def test_dump_trigger_from_str_valid() -> None:
    assert (
        TdfDumpTrigger.from_str('player_change') == TdfDumpTrigger.PLAYER_CHANGE
    )
    assert (
        TdfDumpTrigger.from_str('PLAYER_CHANGE') == TdfDumpTrigger.PLAYER_CHANGE
    )
    assert TdfDumpTrigger.from_str(' event ') == TdfDumpTrigger.EVENT
    assert TdfDumpTrigger.from_str('Interval') == TdfDumpTrigger.INTERVAL
    assert TdfDumpTrigger.from_str('FINAL') == TdfDumpTrigger.FINAL


def test_dump_trigger_from_str_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid trigger 'unknown'"):
        TdfDumpTrigger.from_str('unknown')


def test_dump_format_from_str_valid() -> None:
    assert TdfDumpFormat.from_str('csv') == TdfDumpFormat.CSV
    assert TdfDumpFormat.from_str('CSV ') == TdfDumpFormat.CSV
    assert TdfDumpFormat.from_str('json') == TdfDumpFormat.JSON
    assert TdfDumpFormat.from_str('JSONL') == TdfDumpFormat.JSONL
    assert TdfDumpFormat.from_str('text') == TdfDumpFormat.TEXT


def test_dump_format_from_str_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid format 'xml'"):
        TdfDumpFormat.from_str('xml')


def test_format_time_ms() -> None:
    assert format_time_ms(0) == '00:00.000'
    assert format_time_ms(54321) == '00:54.321'
    assert format_time_ms(900004) == '15:00.004'
    assert format_time_ms(612345) == '10:12.345'
    assert format_time_ms(-50) == '00:00.000'


def test_player_selection_from_str_valid() -> None:
    assert TdfPlayerSelection.from_str('all') == TdfPlayerSelection.ALL
    assert TdfPlayerSelection.from_str('ALL ') == TdfPlayerSelection.ALL
    assert TdfPlayerSelection.from_str('changed') == TdfPlayerSelection.CHANGED


def test_player_selection_from_str_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid player selection 'none'"):
        TdfPlayerSelection.from_str('none')


def test_player_state_entry_csv_and_dict() -> None:
    entry = TdfPlayerStateEntry(
        time_ms=54321,
        time_str='00:54.321',
        entity_id='@101',
        name='Shadow',
        team_index=1,
        team_name='Fire Team',
        role='Scout',
        score=2500,
        lives=12,
        shots=450,
        missiles=3,
        special_points=4,
        hp=2,
        state='Down',
        is_down=True,
        is_eliminated=False,
        downtime_ends_at_ms=59321,
    )

    headers = TdfPlayerStateEntry.csv_headers()
    assert headers == [
        'time_ms',
        'time_str',
        'entity_id',
        'name',
        'team_index',
        'team_name',
        'role',
        'score',
        'lives',
        'shots',
        'missiles',
        'special_points',
        'hp',
        'state',
        'is_down',
        'is_eliminated',
        'downtime_ends_at_ms',
    ]

    csv_row = entry.to_csv_row()
    assert csv_row == [
        '54321',
        '00:54.321',
        '@101',
        'Shadow',
        '1',
        'Fire Team',
        'Scout',
        '2500',
        '12',
        '450',
        '3',
        '4',
        '2',
        'Down',
        'True',
        'False',
        '59321',
    ]
    assert len(headers) == len(csv_row)

    data_dict = entry.to_dict()
    assert data_dict['time_ms'] == 54321
    assert data_dict['time_str'] == '00:54.321'
    assert data_dict['entity_id'] == '@101'
    assert data_dict['name'] == 'Shadow'
    assert data_dict['score'] == 2500
    assert data_dict['state'] == 'Down'
    assert data_dict['is_down'] is True
    assert data_dict['downtime_ends_at_ms'] == 59321


def test_game_state_entry_to_dict() -> None:
    player_entry = TdfPlayerStateEntry(
        time_ms=10000,
        time_str='00:10.000',
        entity_id='@102',
        name='Viper',
        team_index=0,
        team_name='Ice Team',
        role='Commander',
        score=3200,
        lives=15,
        shots=300,
        missiles=5,
        special_points=6,
        hp=3,
        state='Active',
        is_down=False,
        is_eliminated=False,
        downtime_ends_at_ms=0,
    )
    game_entry = TdfGameStateEntry(
        time_ms=10000,
        time_str='00:10.000',
        event_description='Viper tagged Shadow',
        players=[player_entry],
    )

    data = game_entry.to_dict()
    assert data['time_ms'] == 10000
    assert data['time_str'] == '00:10.000'
    assert data['event_description'] == 'Viper tagged Shadow'
    assert len(data['players']) == 1
    assert data['players'][0]['entity_id'] == '@102'
    assert data['players'][0]['name'] == 'Viper'
