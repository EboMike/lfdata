"""SQLAlchemy model for competitions.

This module defines database ORM models for competitions occurring at a
specific site within a timeframe, tracking participating teams, rosters, and
scheduled games.

Usage example:
    from datetime import datetime
    from lfdata.model import Competition, CompetitionTeam, ScheduledGame

    competition = Competition(
        name='LF World Championships 2026',
        site='Brisbane',
        start_time=datetime(2026, 7, 10),
        end_time=datetime(2026, 7, 17),
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base

if TYPE_CHECKING:
    from lfdata.model.objects.competition_team import CompetitionTeam
    from lfdata.model.objects.scheduled_game import ScheduledGame


class Competition(Base):
    """Database model for an LF competition event.

    Attributes:
        id: Primary key integer ID.
        name: Full display name string of the competition.
        slug: Optional unique slug string identifier for URL/lookup.
        site: Optional location or arena name string where the event occurs.
        start_time: Optional DateTime timestamp when the competition begins.
        end_time: Optional DateTime timestamp when the competition ends.
        teams: List of CompetitionTeam ORM objects participating.
        schedule: List of ScheduledGame ORM objects in the tournament schedule.
    """

    __tablename__ = 'competitions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    site: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    teams: Mapped[list[CompetitionTeam]] = relationship(
        'CompetitionTeam',
        back_populates='competition',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    schedule: Mapped[list[ScheduledGame]] = relationship(
        'ScheduledGame',
        back_populates='competition',
        cascade='all, delete-orphan',
        lazy='selectin',
    )

    def __init__(
        self,
        name: str,
        slug: str | None = None,
        site: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        teams: list[CompetitionTeam] | None = None,
        schedule: list[ScheduledGame] | None = None,
    ) -> None:
        """Initializes a competition.

        Args:
            name: Full name of the competition.
            slug: Optional URL/reference slug identifier.
            site: Optional location or venue name.
            start_time: Optional starting timestamp.
            end_time: Optional ending timestamp.
            teams: Optional list of participating CompetitionTeam instances.
            schedule: Optional list of ScheduledGame instances.
        """
        super().__init__()
        self.name = name
        self.slug = slug
        self.site = site
        self.start_time = start_time
        self.end_time = end_time
        self.teams = list(teams) if teams is not None else []
        self.schedule = list(schedule) if schedule is not None else []

    def get_team(self, slug: str) -> CompetitionTeam | None:
        """Finds a team by its slug ID in this competition.

        Args:
            slug: The slug ID string of the team.

        Returns:
            CompetitionTeam | None: The matching team, or None if not found.

        Usage example:
            team = competition.get_team('tigers')
        """
        for team in self.teams:
            if team.slug == slug:
                return team
        return None

    def add_team(self, team: CompetitionTeam) -> None:
        """Adds a team to this competition.

        Args:
            team: The CompetitionTeam instance to add.

        Usage example:
            competition.add_team(team)
        """
        if team not in self.teams:
            self.teams.append(team)
            team.competition = self

    def get_scheduled_game(self, game_name: str) -> ScheduledGame | None:
        """Finds a scheduled game by its game name in this competition.

        Args:
            game_name: The name string of the game (e.g. 'R1 M3 G2').

        Returns:
            ScheduledGame | None: The matching scheduled game, or None if
            not found.

        Usage example:
            game = competition.get_scheduled_game('R1 M3 G2')
        """
        for game in self.schedule:
            if game.game_name == game_name:
                return game
        return None

    def add_scheduled_game(self, game: ScheduledGame) -> None:
        """Adds a scheduled game to this competition schedule.

        Args:
            game: The ScheduledGame instance to add.

        Usage example:
            competition.add_scheduled_game(game)
        """
        if game not in self.schedule:
            self.schedule.append(game)
            game.competition = self

    def __repr__(self) -> str:
        """Returns a string representation of the competition.

        Returns:
            str: The string representation.
        """
        return (
            f"Competition(id={self.id}, name='{self.name}', site='{self.site}')"
        )


Tournament = Competition
