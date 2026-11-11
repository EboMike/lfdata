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

from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from lfdata.lfstats.competition_info import CompetitionInfo
from lfdata.model.objects.scheduled_game import (
    ScheduledGame,
    parse_game_name,
)

DEFAULT_BASE_URL = 'https://lfstats.com/api'
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = 'lfdata/1.0'
DEFAULT_GAME_DURATION_MINUTES = 15
DEFAULT_TEST_DATA_DIR = Path('tests/fixtures/lfstats')


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parses an ISO 8601 datetime string.

    Args:
        value: ISO formatted string or None.

    Returns:
        datetime | None: Parsed datetime object or None if value is empty.
    """
    if not value:
        return None
    cleaned = value.replace('Z', '+00:00')
    return datetime.fromisoformat(cleaned)


def _convert_game_dict_to_scheduled_game(
    item: dict[str, Any],
) -> ScheduledGame:
    """Converts a raw LFstats schedule JSON dictionary into a ScheduledGame.

    Args:
        item: Dictionary representing a scheduled game from the LFstats API.

    Returns:
        ScheduledGame: Initialized ScheduledGame model instance.

    Raises:
        ValueError: If start_time cannot be parsed or determined.
    """
    game_name = str(item.get('gameName', ''))
    round_num, match_num, game_num, stage = parse_game_name(game_name)

    start_time = _parse_iso_datetime(item.get('scheduledStartTime'))
    if start_time is None:
        start_time = _parse_iso_datetime(item.get('actualStartTime'))
    if start_time is None:
        raise ValueError(
            f"Cannot determine start_time for game '{game_name}'."
        )

    end_time = _parse_iso_datetime(item.get('scheduledEndTime'))
    if end_time is None:
        end_time = start_time + timedelta(minutes=DEFAULT_GAME_DURATION_MINUTES)

    team1_name = item.get('team1Name') or ''
    team2_name = item.get('team2Name') or ''
    team_names = [team1_name, team2_name]

    team1_logo = item.get('team1LogoUrl') or ''
    team2_logo = item.get('team2LogoUrl') or ''
    team_logos = [team1_logo, team2_logo]

    team1_score = item.get('team1Score')
    team2_score = item.get('team2Score')
    team_scores = (
        [int(team1_score), int(team2_score)]
        if team1_score is not None and team2_score is not None
        else None
    )

    diff = item.get('scoreDifferential')
    differential = abs(int(diff)) if diff is not None else None

    return ScheduledGame(
        game_name=game_name,
        round_number=round_num,
        match_number=match_num,
        game_number=game_num,
        stage_indicator=stage,
        start_time=start_time,
        end_time=end_time,
        team_names=team_names,
        team_logos=team_logos,
        team_scores=team_scores,
        score_differential=differential,
    )


class LFStatsFetcher:
    """Client for fetching data from the LFstats API with local test mode.

    Attributes:
        base_url: The root URL of the LFstats API endpoint.
        test_mode: Whether to read test fixtures from local storage.
        test_data_dir: Path to directory holding local test fixtures.
        timeout_seconds: Network request timeout duration in seconds.
        user_agent: HTTP User-Agent header string.
    """

    base_url: str
    test_mode: bool
    test_data_dir: Path
    timeout_seconds: float
    user_agent: str

    def __init__(
        self,
        test_mode: bool = False,
        test_data_dir: str | Path | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
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
        """
        self.test_mode = test_mode
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        if test_data_dir is not None:
            self.test_data_dir = Path(test_data_dir)
        else:
            self.test_data_dir = DEFAULT_TEST_DATA_DIR

    def _fetch_remote_json(self, endpoint_path: str) -> Any:
        """Performs HTTP GET to retrieve remote JSON from an API endpoint.

        Args:
            endpoint_path: Relative URL path (e.g. '/competitions').

        Returns:
            Any: Parsed JSON response (dict or list).

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
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': self.user_agent,
                'Accept': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            content = resp.read().decode('utf-8')
            return json.loads(content)

    def _load_local_fixture(
        self,
        candidate_paths: list[Path],
        item_description: str,
    ) -> Any:
        """Loads data from the first matching local JSON fixture file.

        Args:
            candidate_paths: List of relative candidate file paths to check.
            item_description: Human-readable description for error messages.

        Returns:
            Any: Parsed JSON data from the first existing fixture file.

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
    ) -> Any:
        """Fetches data from local fixture in test mode or HTTP in live mode.

        Args:
            endpoint_path: Relative API endpoint path.
            candidate_fixture_paths: Candidate paths for local fixture loading.
            item_description: Human-readable description for error reporting.

        Returns:
            Any: Parsed JSON data.
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

        if isinstance(raw_data, dict):
            items = raw_data.get('data')
            if not isinstance(items, list):
                raise ValueError(
                    f"Expected 'data' field to be a list, got {type(items)}."
                )
        elif isinstance(raw_data, list):
            items = raw_data
        else:
            raise ValueError(
                'Expected competitions response to be a dict or list, got '
                f'{type(raw_data)}.'
            )

        results: list[CompetitionInfo] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name', ''))
            slug = str(item.get('slug', ''))
            if name or slug:
                results.append(CompetitionInfo(name=name, slug=slug))
        return results

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
            (
                self.test_data_dir
                / 'competitions'
                / slug
                / 'schedule.json'
            ),
            self.test_data_dir / slug / 'schedule.json',
            self.test_data_dir / f'{slug}_schedule.json',
            self.test_data_dir / f'{slug}.json',
        ]
        raw_data = self._fetch_data(
            endpoint_path=f'/competitions/{encoded_slug}/schedule',
            candidate_fixture_paths=candidate_paths,
            item_description=f"schedule of '{slug}'",
        )

        if not isinstance(raw_data, list):
            raise ValueError(
                f'Expected schedule data to be a list, got {type(raw_data)}.'
            )

        return [_convert_game_dict_to_scheduled_game(item) for item in raw_data]

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

    def _load_local_schedule_fixture(
        self,
        competition_slug: str,
    ) -> list[dict[str, Any]]:
        """Loads schedule data from a local JSON fixture file.

        Args:
            competition_slug: Unique competition slug to find.

        Returns:
            list[dict[str, Any]]: Parsed JSON list.

        Raises:
            FileNotFoundError: If no candidate fixture file exists.
        """
        candidate_paths = [
            (
                self.test_data_dir
                / 'competitions'
                / competition_slug
                / 'schedule.json'
            ),
            self.test_data_dir / competition_slug / 'schedule.json',
            self.test_data_dir / f'{competition_slug}_schedule.json',
            self.test_data_dir / f'{competition_slug}.json',
        ]
        return self._load_local_fixture(
            candidate_paths=candidate_paths,
            item_description=f"schedule for '{competition_slug}'",
        )

    def _fetch_remote_schedule(
        self,
        competition_slug: str,
    ) -> list[dict[str, Any]]:
        """Performs HTTP GET to retrieve remote competition schedule.

        Args:
            competition_slug: Unique competition slug.

        Returns:
            list[dict[str, Any]]: Parsed JSON response.

        Raises:
            urllib.error.HTTPError: If HTTP status is not 200.
            urllib.error.URLError: If connection fails.
        """
        encoded_slug = urllib.parse.quote(competition_slug)
        return self._fetch_remote_json(
            endpoint_path=f'/competitions/{encoded_slug}/schedule'
        )
