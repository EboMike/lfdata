"""Helper module for converting LFstats competition player and team records.

This module provides data structures and conversion functions to parse raw JSON
payloads returned by the LFstats API (/api/competitions/{slug}/stats) into
structured CompetitionTeam and Player domain models.

Usage example:
    from lfdata.lfstats.team_converter import parse_competition_teams

    raw_json = {
        'my_comp': [
            {
                'ipl_id': '4-1-101',
                'player_name': 'Alpha',
                'player_picture_url': None,
                'team_name': 'Tigers',
                'team_logo_url': 'https://example.com/tigers.png',
            }
        ]
    }
    teams = parse_competition_teams(raw_json, 'my_comp')
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from lfdata.model.objects.competition_team import CompetitionTeam
from lfdata.model.objects.player import Player


@dataclass
class CompetitionPlayerEntry:
    """Dataclass holding raw competition player and team metadata.

    Attributes:
        ipl_id: Unique entity ID string for the player or None.
        player_name: Display name or codename of the player.
        player_picture_url: Optional URL string to player profile photo.
        team_name: Name of the team the player belongs to.
        team_logo_url: Optional URL string to team logo image asset.
    """

    ipl_id: str | None = None
    player_name: str = ''
    player_picture_url: str | None = None
    team_name: str = ''
    team_logo_url: str | None = None


def slugify_team_name(team_name: str) -> str:
    """Derives a normalized slug identifier from a team name string.

    Args:
        team_name: Human-readable team name string.

    Returns:
        str: Normalized lowercase alphanumeric slug separated by underscores.

    Usage example:
        slug = slugify_team_name("Thunder Tigers")
        # slug == 'thunder_tigers'
    """
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '_', team_name.strip().lower())
    result = cleaned.strip('_')
    return result if result else 'team'


def derive_short_name(team_name: str) -> str:
    """Derives a short 3-4 character abbreviation from a team name.

    Args:
        team_name: Full display name of the team.

    Returns:
        str: Uppercase abbreviation string.

    Usage example:
        short = derive_short_name("Thunder Tigers")
        # short == 'TT'
    """
    words = [w for w in re.split(r'[^a-zA-Z0-9]+', team_name) if w]
    if len(words) >= 2:
        initials = ''.join(w[0].upper() for w in words)
        return initials[:4]
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', team_name)
    return cleaned[:4].upper() if cleaned else 'TEAM'


def _extract_entries_list(
    raw_data: object,
    competition_slug: str,
) -> list[object]:
    """Extracts raw entry list from dictionary or list JSON payload.

    Args:
        raw_data: Raw JSON parsed object (dict or list).
        competition_slug: Unique slug of the competition.

    Returns:
        list[object]: List of raw entry objects.

    Raises:
        ValueError: If raw_data structure is not a supported format.
    """
    if isinstance(raw_data, list):
        return raw_data
    if isinstance(raw_data, dict):
        if competition_slug in raw_data:
            val = raw_data[competition_slug]
            if isinstance(val, list):
                return val
        if len(raw_data) == 1:
            val = next(iter(raw_data.values()))
            if isinstance(val, list):
                return val
        raise ValueError(
            f"Expected dictionary with key '{competition_slug}' containing a "
            f'list of team entries.'
        )
    raise ValueError(
        f'Expected list or dictionary for competition stats data, got '
        f'{type(raw_data)}.'
    )


def _convert_dict_to_player_entry(
    item: dict[str, object],
) -> CompetitionPlayerEntry:
    """Converts a raw JSON dictionary item to a CompetitionPlayerEntry.

    Args:
        item: Dictionary containing player and team metadata keys.

    Returns:
        CompetitionPlayerEntry: Typed player entry dataclass.
    """
    ipl_val = item.get('ipl_id')
    ipl_str = str(ipl_val).strip() if ipl_val is not None else None

    name_val = item.get('player_name', '')
    player_name = str(name_val).strip() if name_val is not None else ''

    pic_val = item.get('player_picture_url')
    player_pic = str(pic_val).strip() if pic_val is not None else None

    team_val = item.get('team_name', '')
    team_name = str(team_val).strip() if team_val is not None else ''

    logo_val = item.get('team_logo_url')
    team_logo = str(logo_val).strip() if logo_val is not None else None

    return CompetitionPlayerEntry(
        ipl_id=ipl_str,
        player_name=player_name,
        player_picture_url=player_pic,
        team_name=team_name,
        team_logo_url=team_logo,
    )


def parse_competition_teams(
    raw_data: object,
    competition_slug: str,
) -> list[CompetitionTeam]:
    """Parses raw competition team stats JSON into a list of CompetitionTeams.

    Uses team name as the primary key to group players and extract team
    metadata (logo URL, slug, short name, and roster).

    Args:
        raw_data: Raw JSON data (dict or list).
        competition_slug: Unique slug identifier for the competition.

    Returns:
        list[CompetitionTeam]: List of aggregated CompetitionTeam domain models.

    Raises:
        ValueError: If the raw data cannot be parsed.

    Usage example:
        teams = parse_competition_teams(data, 'syracuse_trios_2026')
    """
    raw_entries = _extract_entries_list(
        raw_data=raw_data,
        competition_slug=competition_slug,
    )

    grouped_entries: dict[str, list[CompetitionPlayerEntry]] = {}
    for raw_item in raw_entries:
        if not isinstance(raw_item, dict):
            continue
        entry = _convert_dict_to_player_entry(item=raw_item)
        if not entry.team_name:
            continue
        if entry.team_name not in grouped_entries:
            grouped_entries[entry.team_name] = []
        grouped_entries[entry.team_name].append(entry)

    teams: list[CompetitionTeam] = []
    for team_name, player_entries in grouped_entries.items():
        logo_url: str | None = None
        for pe in player_entries:
            if pe.team_logo_url:
                logo_url = pe.team_logo_url
                break

        slug = slugify_team_name(team_name=team_name)
        short_name = derive_short_name(team_name=team_name)

        roster_players: list[Player] = []
        seen_codenames: set[str] = set()
        for pe in player_entries:
            if pe.player_name and pe.player_name not in seen_codenames:
                seen_codenames.add(pe.player_name)
                roster_players.append(Player(codename=pe.player_name))

        team = CompetitionTeam(
            slug=slug,
            name=team_name,
            short_name=short_name,
            logo_url=logo_url,
            players=roster_players,
        )
        teams.append(team)

    return teams

