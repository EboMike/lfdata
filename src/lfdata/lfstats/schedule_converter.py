"""Helper module for converting LFstats competition schedule records.

This module provides parsing functions to convert raw JSON game schedule items
returned by the LFstats API (/api/competitions/{slug}/schedule) into
domain-level ScheduledGame models.

Usage example:
    from lfdata.lfstats.schedule_converter import (
        convert_game_dict_to_scheduled_game,
    )

    game_dict = {
        'gameName': 'R1 M1 G1',
        'team1Name': 'Tigers',
        'team2Name': 'Lions',
        'scheduledStartTime': '2026-11-02T15:00:00.000Z',
    }
    game = convert_game_dict_to_scheduled_game(game_dict)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from lfdata.model.objects.scheduled_game import (
    ScheduledGame,
    parse_game_name,
)

DEFAULT_GAME_DURATION_MINUTES = 15


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parses an ISO 8601 datetime string.

    Args:
        value: ISO formatted string or None.

    Returns:
        datetime | None: Parsed datetime object or None if value is empty.

    Usage example:
        dt = parse_iso_datetime("2026-11-02T15:00:00.000Z")
    """
    if not value:
        return None
    cleaned = value.replace('Z', '+00:00')
    return datetime.fromisoformat(cleaned)


def convert_game_dict_to_scheduled_game(
    item: dict[str, object],
) -> ScheduledGame:
    """Converts a raw JSON dictionary item into a ScheduledGame object.

    Args:
        item: Raw dictionary representing a scheduled game.

    Returns:
        ScheduledGame: Parsed game object.

    Usage example:
        game = convert_game_dict_to_scheduled_game(item)
    """
    game_name_val = item.get('gameName', '')
    game_name = str(game_name_val) if game_name_val is not None else ''
    round_num, match_num, game_num, stage = parse_game_name(game_name)

    start_val = item.get('scheduledStartTime')
    start_time = parse_iso_datetime(str(start_val) if start_val else None)
    actual_val = item.get('actualStartTime')
    actual_start_time = parse_iso_datetime(
        str(actual_val) if actual_val else None
    )
    if start_time is None:
        start_time = actual_start_time
    if start_time is None:
        raise ValueError(
            f"Cannot determine start_time for game '{game_name}'."
        )

    end_val = item.get('scheduledEndTime')
    end_time = parse_iso_datetime(str(end_val) if end_val else None)
    if end_time is None:
        end_time = start_time + timedelta(minutes=DEFAULT_GAME_DURATION_MINUTES)

    team1_name = str(item.get('team1Name') or '')
    team2_name = str(item.get('team2Name') or '')
    team_names = [team1_name, team2_name]

    logo1_val = item.get('team1LogoUrl') or ''
    logo2_val = item.get('team2LogoUrl') or ''
    team_logos = [str(logo1_val), str(logo2_val)]

    team1_score_val = item.get('team1Score')
    team2_score_val = item.get('team2Score')
    team_scores: list[int] | None = None
    if team1_score_val is not None and team2_score_val is not None:
        team_scores = [int(team1_score_val), int(team2_score_val)]

    score_diff_val = item.get('scoreDifferential')
    score_diff = (
        abs(int(score_diff_val)) if score_diff_val is not None else None
    )

    return ScheduledGame(
        game_name=game_name,
        round_number=round_num,
        match_number=match_num,
        game_number=game_num,
        stage_indicator=stage,
        start_time=start_time,
        end_time=end_time,
        actual_start_time=actual_start_time,
        team_names=team_names,
        team_logos=team_logos,
        team_scores=team_scores,
        score_differential=score_diff,
    )


def parse_competition_schedule(raw_data: object) -> list[ScheduledGame]:
    """Parses raw JSON data into a list of ScheduledGame instances.

    Args:
        raw_data: Raw JSON data (expected to be a list of game dicts).

    Returns:
        list[ScheduledGame]: Parsed ScheduledGame list.

    Raises:
        ValueError: If raw_data is not a list.

    Usage example:
        games = parse_competition_schedule(raw_json)
    """
    if not isinstance(raw_data, list):
        raise ValueError(
            f'Expected schedule data to be a list, got {type(raw_data)}.'
        )
    return [
        convert_game_dict_to_scheduled_game(item)
        for item in raw_data
        if isinstance(item, dict)
    ]
