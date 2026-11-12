"""LFstats integration package.

This package provides interfaces and clients for interacting with the LFstats
global stats API (https://lfstats.com/api), fetching competition schedules,
rosters, and tournament statistics with offline fixture support.

Usage example:
    from lfdata.lfstats import CompetitionInfo, LFStatsFetcher

    fetcher = LFStatsFetcher(test_mode=True)
    competitions = fetcher.fetch_competitions()
    for comp in competitions:
        print(comp.name, comp.slug)
"""

from lfdata.lfstats.competition_info import CompetitionInfo
from lfdata.lfstats.fetcher import LFStatsFetcher
from lfdata.lfstats.team_converter import (
    CompetitionPlayerEntry,
    parse_competition_teams,
)

__all__ = [
    'CompetitionInfo',
    'CompetitionPlayerEntry',
    'LFStatsFetcher',
    'parse_competition_teams',
]
