"""LFstats API data fetcher module.

This module provides the LFStatsFetcher class to interact with the LFstats API
(https://lfstats.com/api), fetching competition lists, schedules, teams,
rosters, and player statistics. It supports a test mode where data is loaded
from local storage fixtures instead of making live network requests.

Usage example:
    from lfdata.lfstats import LFStatsFetcher

    fetcher = LFStatsFetcher(test_mode=True)
    competitions = fetcher.fetch_competitions()
    for comp in competitions:
        print(comp.name, comp.slug)

    schedule = fetcher.fetch_competition_schedule('syracuse_trios_2026')
    for game in schedule:
        print(game.game_name, game.team_names, game.start_time)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from lfdata.lfstats.competition_info import (
    CompetitionInfo,
    parse_competitions_list,
)
from lfdata.lfstats.schedule_converter import (
    DEFAULT_GAME_DURATION_MINUTES,
    convert_game_dict_to_scheduled_game,
    parse_competition_schedule,
    parse_iso_datetime,
)
from lfdata.lfstats.team_converter import parse_competition_teams
from lfdata.model.objects.competition_team import CompetitionTeam
from lfdata.model.objects.scheduled_game import (
    ScheduledGame,
    parse_game_name,
)

DEFAULT_BASE_URL = 'https://lfstats.com/api'
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = 'lfdata/1.0'
DEFAULT_TEST_DATA_DIR = Path('tests/fixtures/lfstats')

_parse_iso_datetime = parse_iso_datetime
_convert_game_dict_to_scheduled_game = convert_game_dict_to_scheduled_game


class LFStatsFetcher:
    """Client for fetching data from the LFstats API with local test mode.

    Attributes:
        base_url: The root URL of the LFstats API endpoint.
        test_mode: Whether to read test fixtures from local storage.
        test_data_dir: Path to directory holding local test fixtures.
        timeout_seconds: Network request timeout duration in seconds.
        user_agent: HTTP User-Agent header string.
        api_key: Optional API key for authenticated API endpoints.
    """

    base_url: str
    test_mode: bool
    test_data_dir: Path
    timeout_seconds: float
    user_agent: str
    api_key: str | None

    def __init__(
        self,
        test_mode: bool = False,
        test_data_dir: str | Path | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        api_key: str | None = None,
    ) -> None:
        """Initializes the LFstats data fetcher.

        Args:
            test_mode: When True, reads local test fixtures instead of
                calling the remote API. Defaults to False.
            test_data_dir: Optional custom directory path for local test
                fixtures. Defaults to 'tests/fixtures/lfstats'.
            base_url: Root API endpoint URL. Defaults to
                'https://lfstats.com/api'.
            timeout_seconds: Request timeout in seconds. Defaults to 10.0.
            user_agent: HTTP User-Agent header. Defaults to 'lfdata/1.0'.
            api_key: Optional API authentication key. If omitted, checks
                the LFSTATS_API_KEY environment variable.
        """
        self.test_mode = test_mode
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.api_key = (
            api_key
            if api_key is not None
            else os.environ.get('LFSTATS_API_KEY')
        )
        if test_data_dir is not None:
            self.test_data_dir = Path(test_data_dir)
        else:
            self.test_data_dir = DEFAULT_TEST_DATA_DIR

    def _fetch_remote_json(self, endpoint_path: str) -> object:
        """Performs HTTP GET to retrieve remote JSON from an API endpoint.

        Args:
            endpoint_path: Relative URL path (e.g. '/competitions').

        Returns:
            object: Parsed JSON response (dict or list).

        Raises:
            urllib.error.HTTPError: If the server returns an HTTP error status.
            urllib.error.URLError: If the network connection fails.
        """
        normalized_path = (
            endpoint_path
            if endpoint_path.startswith('/')
            else f'/{endpoint_path}'
        )
        url = f'{self.base_url}{normalized_path}'
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            headers['X-API-Key'] = self.api_key
        req = urllib.request.Request(
            url,
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            content = resp.read().decode('utf-8')
            return json.loads(content)

    def _load_local_fixture(
        self,
        candidate_paths: list[Path],
        item_description: str,
    ) -> object:
        """Loads data from the first matching local JSON fixture file.

        Args:
            candidate_paths: List of relative candidate file paths to check.
            item_description: Human-readable description for error messages.

        Returns:
            object: Parsed JSON data from the first existing fixture file.

        Raises:
            FileNotFoundError: If none of the candidate files exist.
        """
        for path in candidate_paths:
            if path.is_file():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)

        searched = ', '.join(str(p) for p in candidate_paths)
        raise FileNotFoundError(
            f'No local fixture found for {item_description}. '
            f'Checked: {searched}'
        )

    def _fetch_data(
        self,
        endpoint_path: str,
        candidate_fixture_paths: list[Path],
        item_description: str,
    ) -> object:
        """Fetches data from local fixture in test mode or HTTP in live mode.

        Args:
            endpoint_path: Relative API endpoint path.
            candidate_fixture_paths: Candidate paths for local fixture loading.
            item_description: Human-readable description for error reporting.

        Returns:
            object: Parsed JSON data.
        """
        if self.test_mode:
            return self._load_local_fixture(
                candidate_paths=candidate_fixture_paths,
                item_description=item_description,
            )
        return self._fetch_remote_json(endpoint_path=endpoint_path)

    def fetch_competitions(self) -> list[CompetitionInfo]:
        """Fetches all competitions, returning their names and slugs.

        Queries the LFstats API at /api/competitions or loads the competitions
        fixture from local storage if in test mode.

        Returns:
            list[CompetitionInfo]: List of CompetitionInfo objects.

        Raises:
            ValueError: If the API response format is invalid.
            FileNotFoundError: If test_mode is enabled but no local competitions
                fixture exists.
            urllib.error.HTTPError: If the remote API returns an HTTP error.
            urllib.error.URLError: If connection to the remote API fails.

        Usage example:
            fetcher = LFStatsFetcher()
            competitions = fetcher.fetch_competitions()
            for comp in competitions:
                print(comp.name, comp.slug)
        """
        candidate_paths = [
            self.test_data_dir / 'competitions.json',
            self.test_data_dir / 'competitions' / 'competitions.json',
            self.test_data_dir / 'competitions' / 'index.json',
        ]
        raw_data = self._fetch_data(
            endpoint_path='/competitions',
            candidate_fixture_paths=candidate_paths,
            item_description='competitions list',
        )
        return parse_competitions_list(raw_data=raw_data)

    def fetch_all_competitions(self) -> list[CompetitionInfo]:
        """Convenience alias for fetch_competitions.

        Returns:
            list[CompetitionInfo]: List of CompetitionInfo objects.

        Usage example:
            fetcher = LFStatsFetcher()
            competitions = fetcher.fetch_all_competitions()
        """
        return self.fetch_competitions()

    def fetch_competition_schedule(
        self,
        competition_slug: str,
    ) -> list[ScheduledGame]:
        """Fetches the game schedule for a competition by its slug.

        Queries the LFstats API at /api/competitions/{competition_slug}/schedule
        or loads the fixture from local storage if in test mode.

        Args:
            competition_slug: Unique competition slug
                (e.g. 'syracuse_trios_2026').

        Returns:
            list[ScheduledGame]: List of scheduled games in chronological order.

        Raises:
            ValueError: If competition_slug is empty or the response data
                is not a valid list.
            FileNotFoundError: If test_mode is enabled but no local fixture
                exists for the requested competition slug.
            urllib.error.HTTPError: If the remote API returns an HTTP error.
            urllib.error.URLError: If connection to the remote API fails.

        Usage example:
            fetcher = LFStatsFetcher()
            games = fetcher.fetch_competition_schedule('syracuse_trios_2026')
        """
        slug = competition_slug.strip()
        if not slug:
            raise ValueError('competition_slug cannot be empty.')

        encoded_slug = urllib.parse.quote(slug)
        candidate_paths = [
            self.test_data_dir / 'competitions' / slug / 'schedule.json',
            self.test_data_dir / slug / 'schedule.json',
            self.test_data_dir / f'{slug}_schedule.json',
            self.test_data_dir / f'{slug}.json',
        ]
        raw_data = self._fetch_data(
            endpoint_path=f'/competitions/{encoded_slug}/schedule',
            candidate_fixture_paths=candidate_paths,
            item_description=f"schedule for '{slug}'",
        )
        return parse_competition_schedule(raw_data=raw_data)

    def fetch_schedule(
        self,
        competition_slug: str,
    ) -> list[ScheduledGame]:
        """Convenience alias for fetch_competition_schedule.

        Args:
            competition_slug: Unique competition slug.

        Returns:
            list[ScheduledGame]: List of scheduled games.

        Raises:
            ValueError: If competition_slug is empty.

        Usage example:
            fetcher = LFStatsFetcher()
            games = fetcher.fetch_schedule('syracuse_trios_2026')
        """
        return self.fetch_competition_schedule(
            competition_slug=competition_slug
        )

    def fetch_tournament_schedule(
        self,
        tournament_slug: str,
    ) -> list[ScheduledGame]:
        """Fetches the game schedule for a tournament by its slug.

        Convenience alias for fetch_competition_schedule.

        Args:
            tournament_slug: Unique tournament or competition slug.

        Returns:
            list[ScheduledGame]: List of scheduled games.

        Raises:
            ValueError: If tournament_slug is empty.

        Usage example:
            fetcher = LFStatsFetcher()
            games = fetcher.fetch_tournament_schedule('syracuse_trios_2026')
        """
        return self.fetch_competition_schedule(
            competition_slug=tournament_slug
        )

    def fetch_competition_teams(
        self,
        competition_slug: str,
    ) -> list[CompetitionTeam]:
        """Fetches the team details and rosters for a competition slug.

        Queries the LFstats API at /api/competitions/{competition_slug}/stats
        or loads local test fixture if in test mode.

        Args:
            competition_slug: Unique competition slug (e.g.
                'syracuse_trios_2026').

        Returns:
            list[CompetitionTeam]: List of participating competition teams.

        Raises:
            ValueError: If competition_slug is empty or the response data
                cannot be parsed.
            FileNotFoundError: If test_mode is enabled but no local fixture
                exists for the requested competition slug.
            urllib.error.HTTPError: If the remote API returns an HTTP error.
            urllib.error.URLError: If connection to the remote API fails.

        Usage example:
            fetcher = LFStatsFetcher()
            teams = fetcher.fetch_competition_teams('syracuse_trios_2026')
        """
        slug = competition_slug.strip()
        if not slug:
            raise ValueError('competition_slug cannot be empty.')

        encoded_slug = urllib.parse.quote(slug)
        candidate_paths = [
            self.test_data_dir / 'competitions' / slug / 'stats.json',
            self.test_data_dir / 'competitions' / slug / 'teams.json',
            self.test_data_dir / slug / 'stats.json',
            self.test_data_dir / slug / 'teams.json',
            self.test_data_dir / f'{slug}_stats.json',
            self.test_data_dir / f'{slug}_teams.json',
        ]
        raw_data = self._fetch_data(
            endpoint_path=f'/competitions/{encoded_slug}/stats',
            candidate_fixture_paths=candidate_paths,
            item_description=f"team details for '{slug}'",
        )
        return parse_competition_teams(
            raw_data=raw_data,
            competition_slug=slug,
        )

    def fetch_teams(
        self,
        competition_slug: str,
    ) -> list[CompetitionTeam]:
        """Convenience alias for fetch_competition_teams.

        Args:
            competition_slug: Unique competition slug.

        Returns:
            list[CompetitionTeam]: List of participating competition teams.

        Raises:
            ValueError: If competition_slug is empty.

        Usage example:
            fetcher = LFStatsFetcher()
            teams = fetcher.fetch_teams('syracuse_trios_2026')
        """
        return self.fetch_competition_teams(competition_slug=competition_slug)

    def fetch_competition_team_details(
        self,
        competition_slug: str,
    ) -> list[CompetitionTeam]:
        """Convenience alias for fetch_competition_teams.

        Args:
            competition_slug: Unique competition slug.

        Returns:
            list[CompetitionTeam]: List of participating competition teams.

        Raises:
            ValueError: If competition_slug is empty.

        Usage example:
            fetcher = LFStatsFetcher()
            teams = fetcher.fetch_competition_team_details(
                'syracuse_trios_2026'
            )
        """
        return self.fetch_competition_teams(competition_slug=competition_slug)
