"""LFstats integration package.

This package provides interfaces and clients for interacting with the LFstats
global stats API (https://lfstats.com/api), fetching competition schedules,
rosters, and tournament statistics with offline fixture support.

Usage example:
    from lfdata.lfstats import LFStatsFetcher

    fetcher = LFStatsFetcher(test_mode=True)
    schedule = fetcher.fetch_competition_schedule('syracuse_trios_2026')
"""

from lfdata.lfstats.fetcher import LFStatsFetcher

__all__ = ['LFStatsFetcher']

