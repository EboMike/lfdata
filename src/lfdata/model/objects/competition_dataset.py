"""Test dataset generator for LF competitions and scheduled tournament games.

This module provides a preconfigured test dataset loader and builder
containing two LF competitions: 'Internationals 2026' and
'Syracuse Trios 2026'. Each competition contains 5 scheduled tournament
games loaded from standardized test fixture files. For 'Internationals 2026',
the first 3 games have completed scores while the last 2 games have no
results yet. For 'Syracuse Trios 2026', all 5 games have completed scores.

Usage example:
    from lfdata.model.objects.competition_dataset import CompetitionDataset

    dataset = CompetitionDataset()
    competitions = dataset.get_competitions()
    for comp in competitions:
        print(comp.name, len(comp.schedule))
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from lfdata.lfstats.competition_info import parse_competitions_list
from lfdata.lfstats.schedule_converter import parse_competition_schedule
from lfdata.model.objects.competition import Competition, Tournament

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

DEFAULT_TEST_COMPETITIONS_DIR = Path('tests/fixtures/test_competitions')
SLUG_INTERNATIONALS_2026 = 'internationals_2026'
SLUG_SYRACUSE_TRIOS_2026 = 'syracuse_trios_2026'
EXPECTED_GAMES_PER_COMPETITION = 5


class CompetitionDataset:
    """Provides a structured test dataset of LF competitions and schedules.

    Loads and holds two tournament competitions with 5 scheduled games each:
    - 'internationals_2026': 5 games (games 1-3 finished, games 4-5 pending).
    - 'syracuse_trios_2026': 5 games (all 5 games finished with results).

    Attributes:
        fixtures_dir: Path to the directory holding JSON fixture files.
        competitions: List of loaded Competition model objects.
    """

    fixtures_dir: Path
    competitions: list[Competition]

    def __init__(
        self,
        fixtures_dir: Path | str | None = None,
    ) -> None:
        """Initializes the test competition dataset.

        Args:
            fixtures_dir: Optional custom path to fixtures directory. Defaults
                to 'tests/fixtures/test_competitions'.

        Raises:
            FileNotFoundError: If the fixture files cannot be found.
            ValueError: If the fixture JSON structure is invalid.
        """
        if fixtures_dir is None:
            self.fixtures_dir = DEFAULT_TEST_COMPETITIONS_DIR
        elif isinstance(fixtures_dir, str):
            self.fixtures_dir = Path(fixtures_dir)
        else:
            self.fixtures_dir = fixtures_dir

        self.competitions = self._load_competitions()

    def _load_competitions(self) -> list[Competition]:
        """Loads and constructs the competitions with their scheduled games.

        Returns:
            list[Competition]: Loaded list of competition models.

        Raises:
            FileNotFoundError: If fixture files are missing.
            ValueError: If fixture JSON format is invalid.
        """
        competitions_file = self.fixtures_dir / 'competitions.json'
        if not competitions_file.is_file():
            raise FileNotFoundError(
                f'Competitions fixture file not found: {competitions_file}'
            )

        with open(competitions_file, 'r', encoding='utf-8') as f:
            raw_comps = json.load(f)

        comp_infos = parse_competitions_list(raw_data=raw_comps)
        competitions: list[Competition] = []

        for info in comp_infos:
            schedule = self._load_schedule_for_slug(slug=info.slug)
            comp = Competition(
                name=info.name,
                slug=info.slug,
                schedule=schedule,
            )
            competitions.append(comp)

        return competitions

    def _load_schedule_for_slug(self, slug: str) -> list:
        """Loads the scheduled games for a specific competition slug.

        Args:
            slug: Competition slug identifier.

        Returns:
            list[ScheduledGame]: Parsed scheduled games for the competition.

        Raises:
            FileNotFoundError: If schedule fixture is missing.
            ValueError: If schedule JSON format is invalid.
        """
        candidates = [
            self.fixtures_dir / 'competitions' / slug / 'schedule.json',
            self.fixtures_dir / slug / 'schedule.json',
            self.fixtures_dir / f'{slug}_schedule.json',
        ]
        schedule_file: Path | None = None
        for candidate in candidates:
            if candidate.is_file():
                schedule_file = candidate
                break

        if schedule_file is None:
            raise FileNotFoundError(
                f'Schedule fixture not found for competition slug: {slug}'
            )

        with open(schedule_file, 'r', encoding='utf-8') as f:
            raw_schedule = json.load(f)

        return parse_competition_schedule(raw_data=raw_schedule)

    def get_competitions(self) -> list[Competition]:
        """Returns all competitions in this test dataset.

        Returns:
            list[Competition]: List of loaded competition objects.

        Usage example:
            dataset = CompetitionDataset()
            comps = dataset.get_competitions()
        """
        return list(self.competitions)

    def get_tournaments(self) -> list[Tournament]:
        """Returns all tournaments in this test dataset (alias).

        Returns:
            list[Tournament]: List of loaded tournament objects.

        Usage example:
            dataset = CompetitionDataset()
            tournaments = dataset.get_tournaments()
        """
        return self.get_competitions()

    def get_competition(self, slug: str) -> Competition | None:
        """Finds a competition by its unique slug identifier.

        Args:
            slug: Unique slug string to look up.

        Returns:
            Competition | None: Matching Competition or None if not found.

        Usage example:
            dataset = CompetitionDataset()
            comp = dataset.get_competition('internationals_2026')
        """
        for comp in self.competitions:
            if comp.slug == slug:
                return comp
        return None

    def get_tournament(self, slug: str) -> Tournament | None:
        """Finds a tournament by its slug identifier (alias).

        Args:
            slug: Unique slug string to look up.

        Returns:
            Tournament | None: Matching Tournament or None if not found.

        Usage example:
            dataset = CompetitionDataset()
            tourney = dataset.get_tournament('syracuse_trios_2026')
        """
        return self.get_competition(slug=slug)

    def get_internationals_2026(self) -> Competition:
        """Convenience accessor for the Internationals 2026 competition.

        Returns:
            Competition: The Internationals 2026 competition instance.

        Raises:
            KeyError: If Internationals 2026 is missing from dataset.

        Usage example:
            dataset = CompetitionDataset()
            internationals = dataset.get_internationals_2026()
        """
        comp = self.get_competition(slug=SLUG_INTERNATIONALS_2026)
        if comp is None:
            raise KeyError(
                f'Competition {SLUG_INTERNATIONALS_2026} not in dataset.'
            )
        return comp

    def get_syracuse_trios_2026(self) -> Competition:
        """Convenience accessor for the Syracuse Trios 2026 competition.

        Returns:
            Competition: The Syracuse Trios 2026 competition instance.

        Raises:
            KeyError: If Syracuse Trios 2026 is missing from dataset.

        Usage example:
            dataset = CompetitionDataset()
            syracuse = dataset.get_syracuse_trios_2026()
        """
        comp = self.get_competition(slug=SLUG_SYRACUSE_TRIOS_2026)
        if comp is None:
            raise KeyError(
                f'Competition {SLUG_SYRACUSE_TRIOS_2026} not in dataset.'
            )
        return comp

    def populate_database(self, session: Session) -> list[Competition]:
        """Persists the competitions and their scheduled games to a database.

        Args:
            session: Active SQLAlchemy database session.

        Returns:
            list[Competition]: Persisted competition instances.

        Usage example:
            dataset = CompetitionDataset()
            persisted = dataset.populate_database(session)
        """
        for comp in self.competitions:
            session.add(comp)
        session.commit()
        return self.competitions

