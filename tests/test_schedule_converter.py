from datetime import datetime, timezone

from lfdata.lfstats.schedule_converter import (
    convert_game_dict_to_scheduled_game,
    parse_iso_datetime,
)


def test_parse_iso_datetime_formats() -> None:
    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime('') is None
    dt = parse_iso_datetime('2026-11-02T15:00:00.000Z')
    assert dt == datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)


def test_convert_game_dict_full_fields() -> None:
    data = {
        'gameName': 'R2 M3 G1',
        'team1Name': 'Tigers',
        'team2Name': 'Lions',
        'team1LogoUrl': 'https://example.com/tigers.png',
        'team2LogoUrl': None,
        'scheduledStartTime': '2026-11-02T15:00:00.000Z',
        'scheduledEndTime': '2026-11-02T15:15:00.000Z',
        'team1Score': 42000,
        'team2Score': 38000,
        'scoreDifferential': 4000,
    }
    game = convert_game_dict_to_scheduled_game(data)
    assert game.game_name == 'R2 M3 G1'
    assert game.round_number == 2
    assert game.match_number == 3
    assert game.game_number == 1
    assert game.stage_indicator == 'G'
    assert game.team_names == ['Tigers', 'Lions']
    assert game.team_logos == ['https://example.com/tigers.png', '']
    assert game.team_scores == [42000, 38000]
    assert game.score_differential == 4000
