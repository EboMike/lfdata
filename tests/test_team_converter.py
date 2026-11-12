import pytest

from lfdata.lfstats.team_converter import (
    CompetitionPlayerEntry,
    derive_short_name,
    parse_competition_teams,
    slugify_team_name,
)


def test_slugify_team_name() -> None:
    assert slugify_team_name('Thunder Tigers') == 'thunder_tigers'
    assert (
        slugify_team_name("Baden's Overly Optimistic Buddies")
        == 'baden_s_overly_optimistic_buddies'
    )
    assert slugify_team_name('  Spaces  ') == 'spaces'
    assert slugify_team_name('***Special***') == 'special'
    assert slugify_team_name('') == 'team'


def test_derive_short_name() -> None:
    assert derive_short_name('Thunder Tigers') == 'TT'
    assert derive_short_name('Death By Budder Knife') == 'DBBK'
    assert derive_short_name('Rebels') == 'REBE'
    assert derive_short_name('X') == 'X'
    assert derive_short_name('***') == 'TEAM'


def test_competition_player_entry_dataclass() -> None:
    entry = CompetitionPlayerEntry(
        ipl_id='4-1-101',
        player_name='Striker',
        player_picture_url='https://example.com/p.png',
        team_name='Alpha Team',
        team_logo_url='https://example.com/logo.png',
    )
    assert entry.ipl_id == '4-1-101'
    assert entry.player_name == 'Striker'
    assert entry.player_picture_url == 'https://example.com/p.png'
    assert entry.team_name == 'Alpha Team'
    assert entry.team_logo_url == 'https://example.com/logo.png'


def test_parse_competition_teams_dict_format() -> None:
    data = {
        'comp_2026': [
            {
                'ipl_id': '4-1-1',
                'player_name': 'Alpha',
                'player_picture_url': None,
                'team_name': 'Team Red',
                'team_logo_url': 'https://example.com/red.png',
            },
            {
                'ipl_id': '4-1-2',
                'player_name': 'Bravo',
                'player_picture_url': None,
                'team_name': 'Team Red',
                'team_logo_url': None,
            },
            {
                'ipl_id': '4-2-1',
                'player_name': 'Charlie',
                'player_picture_url': None,
                'team_name': 'Team Blue',
                'team_logo_url': None,
            },
        ]
    }
    teams = parse_competition_teams(data, 'comp_2026')
    assert len(teams) == 2

    red = teams[0]
    assert red.name == 'Team Red'
    assert red.slug == 'team_red'
    assert red.short_name == 'TR'
    assert red.logo_url == 'https://example.com/red.png'
    assert len(red.players) == 2
    assert red.player_codenames == ['Alpha', 'Bravo']

    blue = teams[1]
    assert blue.name == 'Team Blue'
    assert blue.slug == 'team_blue'
    assert blue.short_name == 'TB'
    assert blue.logo_url is None
    assert len(blue.players) == 1
    assert blue.player_codenames == ['Charlie']


def test_parse_competition_teams_list_format() -> None:
    data = [
        {
            'ipl_id': '1',
            'player_name': 'Player One',
            'team_name': 'Solitary Wolves',
            'team_logo_url': 'https://example.com/wolf.png',
        }
    ]
    teams = parse_competition_teams(data, 'any_comp')
    assert len(teams) == 1
    assert teams[0].name == 'Solitary Wolves'
    assert teams[0].slug == 'solitary_wolves'
    assert teams[0].short_name == 'SW'
    assert teams[0].player_codenames == ['Player One']


def test_parse_competition_teams_invalid_payload_raises() -> None:
    with pytest.raises(ValueError, match='Expected list or dictionary'):
        parse_competition_teams('invalid_string', 'comp_slug')

    with pytest.raises(ValueError, match='Expected dictionary with key'):
        parse_competition_teams({'other_slug': 'not_a_list', 'extra': 123}, 'comp_slug')

