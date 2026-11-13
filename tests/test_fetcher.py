from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from lfdata.lfstats.competition_info import CompetitionInfo
from lfdata.lfstats.fetcher import (
    DEFAULT_BASE_URL,
    DEFAULT_GAME_DURATION_MINUTES,
    DEFAULT_TEST_DATA_DIR,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
    LFStatsFetcher,
    _convert_game_dict_to_scheduled_game,
    _parse_iso_datetime,
)


def test_fetcher_init_defaults() -> None:
    fetcher = LFStatsFetcher()
    assert fetcher.test_mode is False
    assert fetcher.base_url == DEFAULT_BASE_URL
    assert fetcher.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert fetcher.user_agent == DEFAULT_USER_AGENT
    assert fetcher.test_data_dir == DEFAULT_TEST_DATA_DIR


def test_fetcher_init_custom() -> None:
    custom_dir = Path('custom/fixtures')
    fetcher = LFStatsFetcher(
        test_mode=True,
        test_data_dir=custom_dir,
        base_url='https://custom.lfstats.com/api/',
        timeout_seconds=25.0,
        user_agent='custom-agent/2.0',
    )
    assert fetcher.test_mode is True
    assert fetcher.base_url == 'https://custom.lfstats.com/api'
    assert fetcher.timeout_seconds == 25.0
    assert fetcher.user_agent == 'custom-agent/2.0'
    assert fetcher.test_data_dir == custom_dir


def test_parse_iso_datetime() -> None:
    assert _parse_iso_datetime(None) is None
    assert _parse_iso_datetime('') is None
    dt = _parse_iso_datetime('2026-11-02T15:00:00.000Z')
    assert dt == datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)


def test_fetch_competition_schedule_empty_slug_raises() -> None:
    fetcher = LFStatsFetcher(test_mode=True)
    with pytest.raises(ValueError, match='competition_slug cannot be empty'):
        fetcher.fetch_competition_schedule('')
    with pytest.raises(ValueError, match='competition_slug cannot be empty'):
        fetcher.fetch_competition_schedule('   ')


def test_fetch_competition_schedule_missing_fixture_raises(
    tmp_path: Path,
) -> None:
    fetcher = LFStatsFetcher(test_mode=True, test_data_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match='No local fixture found'):
        fetcher.fetch_competition_schedule('non_existent_competition')


def test_fetch_competition_schedule_invalid_json_type_raises(
    tmp_path: Path,
) -> None:
    fixture_file = tmp_path / 'invalid_slug_schedule.json'
    with open(fixture_file, 'w', encoding='utf-8') as f:
        json.dump({'not_a_list': True}, f)

    fetcher = LFStatsFetcher(test_mode=True, test_data_dir=tmp_path)
    with pytest.raises(ValueError, match='Expected schedule data to be a list'):
        fetcher.fetch_competition_schedule('invalid_slug')


def test_fetch_competition_schedule_test_mode_syracuse() -> None:
    fetcher = LFStatsFetcher(test_mode=True)
    games = fetcher.fetch_competition_schedule('syracuse_trios_2026')

    assert len(games) == 5

    first = games[0]
    assert first.game_name == 'R1 M1 G1'
    assert first.round_number == 1
    assert first.match_number == 1
    assert first.game_number == 1
    assert first.stage_indicator == 'G'
    assert first.team_names == [
        "Baden's Overly Optimistic Buddies & Fireball Friends",
        'Death By Budder Knife & Still Expendable',
    ]
    assert first.team_logos[0] == ''
    assert '6478e510' in first.team_logos[1]
    assert first.team_scores == [41172, 11229]
    assert first.score_differential == 29943
    assert first.is_complete is True
    assert first.start_time == datetime(
        2026, 11, 2, 15, 0, tzinfo=timezone.utc
    )
    assert first.end_time == datetime(
        2026, 11, 2, 15, DEFAULT_GAME_DURATION_MINUTES, tzinfo=timezone.utc
    )
    assert first.actual_start_time == datetime(
        2026, 11, 2, 15, 45, 52, tzinfo=timezone.utc
    )
    assert first.actual_time == datetime(
        2026, 11, 2, 15, 45, 52, tzinfo=timezone.utc
    )

    alias_games = fetcher.fetch_schedule('syracuse_trios_2026')
    assert len(alias_games) == 5

    tournament_games = fetcher.fetch_tournament_schedule(
        'syracuse_trios_2026'
    )
    assert len(tournament_games) == 5


def test_fetch_competition_schedule_test_mode_internationals_2026() -> None:
    fetcher = LFStatsFetcher(test_mode=True)
    games = fetcher.fetch_competition_schedule('internationals_2026')

    assert len(games) == 5

    # Games 1-3 have scores and actual start time
    assert games[0].game_name == 'R1 M1 G1'
    assert games[0].team_names == ['Hidden Valley Sanch', 'Utah Heatseekers']
    assert games[0].team_scores == [44452, 28130]
    assert games[0].score_differential == 16322
    assert games[0].is_complete is True

    assert games[1].game_name == 'R1 M2 G1'
    assert games[1].team_scores == [33192, 36072]
    assert games[1].is_complete is True

    assert games[2].game_name == 'R1 M3 G1'
    assert games[2].team_scores == [37052, 17970]
    assert games[2].is_complete is True

    # Games 4-5 have no results yet
    assert games[3].game_name == 'R1 M4 G1'
    assert games[3].team_names == ['The Expendables', 'Team Olympus']
    assert games[3].team_scores is None
    assert games[3].actual_start_time is None
    assert games[3].is_complete is False

    assert games[4].game_name == 'R1 M1 G2'
    assert games[4].team_names == ['Hidden Valley Sanch', 'Utah Heatseekers']
    assert games[4].team_scores is None
    assert games[4].actual_start_time is None
    assert games[4].is_complete is False


def test_fetch_from_test_competitions_dataset_dir() -> None:
    dataset_dir = Path('tests/fixtures/test_competitions')
    fetcher = LFStatsFetcher(test_mode=True, test_data_dir=dataset_dir)

    comps = fetcher.fetch_competitions()
    assert len(comps) == 2
    assert [c.slug for c in comps] == [
        'internationals_2026',
        'syracuse_trios_2026',
    ]

    games_intl = fetcher.fetch_competition_schedule('internationals_2026')
    assert len(games_intl) == 5
    assert games_intl[3].is_complete is False
    assert games_intl[4].is_complete is False

    games_syracuse = fetcher.fetch_competition_schedule('syracuse_trios_2026')
    assert len(games_syracuse) == 5
    for g in games_syracuse:
        assert g.is_complete is True
        assert g.team_scores is not None


def test_convert_game_dict_missing_start_time_raises() -> None:
    with pytest.raises(ValueError, match='Cannot determine start_time'):
        _convert_game_dict_to_scheduled_game({'gameName': 'InvalidGame'})


def test_convert_game_dict_with_scheduled_end_and_no_scores() -> None:
    raw = {
        'gameName': 'R2 M4 OT1',
        'team1Name': 'Team Red',
        'team2Name': 'Team Blue',
        'team1LogoUrl': 'https://example.com/red.png',
        'team2LogoUrl': None,
        'scheduledStartTime': '2026-11-03T18:00:00.000Z',
        'scheduledEndTime': '2026-11-03T18:25:00.000Z',
        'team1Score': None,
        'team2Score': None,
        'scoreDifferential': None,
    }
    game = _convert_game_dict_to_scheduled_game(raw)
    assert game.game_name == 'R2 M4 OT1'
    assert game.round_number == 2
    assert game.match_number == 4
    assert game.game_number == 1
    assert game.stage_indicator == 'OT'
    assert game.team_names == ['Team Red', 'Team Blue']
    assert game.team_logos == ['https://example.com/red.png', '']
    assert game.team_scores is None
    assert game.score_differential is None
    assert game.is_complete is False
    assert game.start_time == datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)
    assert game.end_time == datetime(2026, 11, 3, 18, 25, tzinfo=timezone.utc)


def test_fetch_remote_schedule_mocked() -> None:
    fetcher = LFStatsFetcher(test_mode=False)
    fake_json = json.dumps([
        {
            'gameName': 'R1 M1 G1',
            'team1Name': 'Alpha',
            'team2Name': 'Beta',
            'scheduledStartTime': '2026-11-02T15:00:00.000Z',
        }
    ]).encode('utf-8')

    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_json
    mock_resp.__enter__.return_value = mock_resp

    with (
        patch('urllib.request.urlopen', return_value=mock_resp)
        as mock_urlopen
    ):
        games = fetcher.fetch_competition_schedule('my_event')
        assert len(games) == 1
        assert games[0].game_name == 'R1 M1 G1'
        assert games[0].team_names == ['Alpha', 'Beta']
        req = mock_urlopen.call_args[0][0]
        assert 'my_event/schedule' in req.full_url
        assert req.headers['User-agent'] == DEFAULT_USER_AGENT


def test_fetch_remote_schedule_live() -> None:
    fetcher = LFStatsFetcher(test_mode=False)
    try:
        games = fetcher.fetch_competition_schedule('syracuse_trios_2026')
        assert len(games) == 54
        assert games[0].game_name == 'R1 M1 G1'
    except Exception as e:
        pytest.skip(f'Live LFstats API unreachable: {e}')


def test_fetch_competitions_test_mode() -> None:
    fetcher = LFStatsFetcher(test_mode=True)
    comps = fetcher.fetch_competitions()

    assert len(comps) == 68
    assert comps[0] == CompetitionInfo(
        name='Syracuse Trios 2026',
        slug='syracuse_trios_2026',
    )
    assert comps[3] == CompetitionInfo(
        name='Internationals 2026',
        slug='internationals_2026',
    )
    assert comps[0].name == 'Syracuse Trios 2026'
    assert comps[0].slug == 'syracuse_trios_2026'

    alias_comps = fetcher.fetch_all_competitions()
    assert alias_comps == comps


def test_fetch_competitions_missing_fixture_raises(tmp_path: Path) -> None:
    fetcher = LFStatsFetcher(test_mode=True, test_data_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match='No local fixture found'):
        fetcher.fetch_competitions()


def test_fetch_competitions_invalid_structure_raises(tmp_path: Path) -> None:
    bad_file = tmp_path / 'competitions.json'
    with open(bad_file, 'w', encoding='utf-8') as f:
        json.dump({'data': 'not-a-list'}, f)

    fetcher = LFStatsFetcher(test_mode=True, test_data_dir=tmp_path)
    with pytest.raises(ValueError, match="Expected 'data' field to be a list"):
        fetcher.fetch_competitions()

    with open(bad_file, 'w', encoding='utf-8') as f:
        json.dump(12345, f)

    with pytest.raises(
        ValueError, match='Expected competitions response to be a dict or list'
    ):
        fetcher.fetch_competitions()


def test_fetch_competitions_raw_list(tmp_path: Path) -> None:
    raw_list_file = tmp_path / 'competitions.json'
    with open(raw_list_file, 'w', encoding='utf-8') as f:
        json.dump([
            {'name': 'Direct Cup', 'slug': 'direct_cup'},
            'skip_non_dict',
            {'name': '', 'slug': ''},
        ], f)

    fetcher = LFStatsFetcher(test_mode=True, test_data_dir=tmp_path)
    comps = fetcher.fetch_competitions()
    assert len(comps) == 1
    assert comps[0].name == 'Direct Cup'
    assert comps[0].slug == 'direct_cup'


def test_fetch_competitions_mocked_remote() -> None:
    fetcher = LFStatsFetcher(test_mode=False)
    fake_json = json.dumps({
        'data': [
            {'name': 'National League', 'slug': 'nat_league'},
        ],
        'truncated': False,
    }).encode('utf-8')

    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_json
    mock_resp.__enter__.return_value = mock_resp

    with (
        patch('urllib.request.urlopen', return_value=mock_resp)
        as mock_urlopen
    ):
        comps = fetcher.fetch_competitions()
        assert len(comps) == 1
        assert comps[0].name == 'National League'
        assert comps[0].slug == 'nat_league'
        req = mock_urlopen.call_args[0][0]
        assert req.full_url.endswith('/competitions')
        assert req.headers['Accept'] == 'application/json'


def test_fetch_competitions_live() -> None:
    fetcher = LFStatsFetcher(test_mode=False)
    try:
        comps = fetcher.fetch_competitions()
        assert len(comps) > 0
        assert all(isinstance(c, CompetitionInfo) for c in comps)
        assert any('syracuse' in c.slug.lower() for c in comps)
    except Exception as e:
        pytest.skip(f'Live LFstats API unreachable: {e}')


def test_fetch_competition_teams_empty_slug_raises() -> None:
    fetcher = LFStatsFetcher(test_mode=True)
    with pytest.raises(ValueError, match='competition_slug cannot be empty'):
        fetcher.fetch_competition_teams('')
    with pytest.raises(ValueError, match='competition_slug cannot be empty'):
        fetcher.fetch_competition_teams('   ')


def test_fetch_competition_teams_missing_fixture_raises(
    tmp_path: Path,
) -> None:
    fetcher = LFStatsFetcher(test_mode=True, test_data_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match='No local fixture found'):
        fetcher.fetch_competition_teams('non_existent_competition')


def test_fetch_competition_teams_test_mode_syracuse() -> None:
    fetcher = LFStatsFetcher(test_mode=True)
    teams = fetcher.fetch_competition_teams('syracuse_trios_2026')

    assert len(teams) == 4
    team_names = [t.name for t in teams]
    assert "Baden's Overly Optimistic Buddies" in team_names
    assert 'Fireball Friends' in team_names
    assert 'Death By Budder Knife' in team_names
    assert 'Still Expendable' in team_names

    boob = next(
        t for t in teams if t.name == "Baden's Overly Optimistic Buddies"
    )
    assert boob.slug == 'baden_s_overly_optimistic_buddies'
    assert boob.logo_url == 'https://example.com/logos/boob.png'
    assert boob.player_codenames == ['Baden', 'Sunny', 'Cheer']

    knife = next(t for t in teams if t.name == 'Death By Budder Knife')
    assert knife.logo_url is not None
    assert '6478e510' in knife.logo_url
    assert knife.player_codenames == ['Budder', 'Slick', 'Dagger']

    alias1 = fetcher.fetch_teams('syracuse_trios_2026')
    assert [t.name for t in alias1] == team_names

    alias2 = fetcher.fetch_competition_team_details('syracuse_trios_2026')
    assert [t.name for t in alias2] == team_names


def test_fetch_competition_teams_mocked_remote_with_api_key() -> None:
    fetcher = LFStatsFetcher(test_mode=False, api_key='secret_key_123')
    fake_json = json.dumps({
        'tournament_slug': [
            {
                'ipl_id': '10',
                'player_name': 'Striker',
                'team_name': 'Vipers',
                'team_logo_url': 'https://example.com/viper.png',
            }
        ]
    }).encode('utf-8')

    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_json
    mock_resp.__enter__.return_value = mock_resp

    with (
        patch('urllib.request.urlopen', return_value=mock_resp)
        as mock_urlopen
    ):
        teams = fetcher.fetch_competition_teams('tournament_slug')
        assert len(teams) == 1
        assert teams[0].name == 'Vipers'
        assert teams[0].player_codenames == ['Striker']
        req = mock_urlopen.call_args[0][0]
        assert 'tournament_slug/stats' in req.full_url
        assert req.headers['Authorization'] == 'Bearer secret_key_123'
        assert req.headers['X-api-key'] == 'secret_key_123'

