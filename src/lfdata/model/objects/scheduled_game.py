"""SQLAlchemy model for scheduled competition games.

This module defines database ORM models for scheduled games within a
competition, holding participating team names, logos, scheduled start and end
timestamps, game identifiers, scores, and score differential.

Usage example:
    from datetime import datetime
    from lfdata.model import ScheduledGame

    game = ScheduledGame(
        game_name='R1 M3 G2',
        start_time=datetime(2026, 7, 10, 14, 0),
        end_time=datetime(2026, 7, 10, 14, 20),
        team_names=['Tigers', 'Lions'],
        team_logos=[
            'https://example.com/tigers.png',
            'https://example.com/lions.png',
        ],
        round_number=1,
        match_number=3,
        game_number=2,
    )
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base
from lfdata.model.constants.competition import (
    DEFAULT_STAGE_INDICATOR,
    StageType,
)

if TYPE_CHECKING:
    from lfdata.model.objects.competition import Competition
    from lfdata.model.objects.game import LFGame


def format_game_name(
    round_number: int | None = None,
    match_number: int | None = None,
    game_number: int | None = None,
    stage_indicator: str = DEFAULT_STAGE_INDICATOR,
) -> str:
    """Formats a standard game name from round, match, and game components.

    Produces strings such as 'R1 M3 G2', 'R2 M3 H1', or 'R2 M3 OT1'.

    Args:
        round_number: Optional integer round number.
        match_number: Optional integer match number.
        game_number: Optional integer game number.
        stage_indicator: Stage prefix code ('G' for game, 'H' for half,
            'OT' for overtime). Defaults to 'G'.

    Returns:
        str: Formatted game name string.

    Usage example:
        name = format_game_name(round_number=1, match_number=3, game_number=2)
    """
    parts: list[str] = []
    if round_number is not None:
        parts.append(f'R{round_number}')
    if match_number is not None:
        parts.append(f'M{match_number}')
    if game_number is not None:
        parts.append(f'{stage_indicator}{game_number}')
    return ' '.join(parts)


def parse_game_name(
    game_name: str,
) -> tuple[int | None, int | None, int | None, str]:
    """Parses a game name into round, match, game numbers, and stage indicator.

    Extracts optional round number from 'R{n}', match number from 'M{n}',
    game number, and stage indicator (e.g. 'G', 'H', 'OT') from game name
    strings such as 'R1 M3 G2', 'R2 M3 H1', or 'R2 M3 OT1'.

    Args:
        game_name: Formatted game name string to parse.

    Returns:
        tuple[int | None, int | None, int | None, str]: A tuple of
            (round_number, match_number, game_number, stage_indicator).

    Usage example:
        round_num, match_num, game_num, stage = parse_game_name('R1 M3 G2')
    """
    round_match = re.search(r'\bR(\d+)\b', game_name)
    round_number = int(round_match.group(1)) if round_match else None

    match_match = re.search(r'\bM(\d+)\b', game_name)
    match_number = int(match_match.group(1)) if match_match else None

    game_number: int | None = None
    stage_indicator = DEFAULT_STAGE_INDICATOR
    for candidate in re.finditer(r'\b([A-Za-z]+)(\d+)\b', game_name):
        prefix = candidate.group(1)
        if prefix not in ('R', 'M'):
            stage_indicator = prefix
            game_number = int(candidate.group(2))
            break

    return (round_number, match_number, game_number, stage_indicator)


class ScheduledGame(Base):
    """Database model for a scheduled game within a competition.

    Attributes:
        id: Primary key integer ID.
        competition_id: Optional foreign key integer referencing Competition.
        competition: Parent Competition ORM relationship.
        game_name: Human-readable game name string (e.g. 'R1 M3 G2').
        round_number: Optional integer round number.
        match_number: Optional integer match number.
        game_number: Optional integer game number.
        stage_indicator: Stage code string ('G', 'H', 'OT').
        start_time: Scheduled start DateTime timestamp.
        end_time: Scheduled end DateTime timestamp.
        actual_start_time: Optional actual start DateTime when game occurred.
        team_names: List of names of teams playing in this match.
        team_logos: List of logo image URLs for teams playing.
        team_scores: Optional list of integer scores for each team.
        game_id: Optional foreign key string referencing an LFGame session.
        game: Optional linked LFGame ORM relationship.
        scheduled_start: Property accessor/setter for start_time.
        scheduled_end: Property accessor/setter for end_time.
        actual_time: Property accessor/setter for actual_start_time.
        logos: Property accessor/setter for team_logos.
        scores: Property accessor/setter for team_scores.
        names: Property accessor/setter for team_names.
        score_differential: Property returning absolute score difference.
        is_complete: Property indicating whether game scores are recorded.
    """

    __tablename__ = 'scheduled_games'

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int | None] = mapped_column(
        ForeignKey('competitions.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
    )
    game_name: Mapped[str] = mapped_column(String(100))
    round_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage_indicator: Mapped[str] = mapped_column(
        String(10), default=DEFAULT_STAGE_INDICATOR
    )
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    actual_start_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )
    team_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    team_logos: Mapped[list[str]] = mapped_column(JSON, default=list)
    team_scores: Mapped[list[int] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    _score_differential: Mapped[int | None] = mapped_column(
        'score_differential', Integer, nullable=True, default=None
    )
    game_id: Mapped[str | None] = mapped_column(
        ForeignKey('lf_games.game_id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

    # Relationships
    competition: Mapped[Competition | None] = relationship(
        'Competition', back_populates='schedule'
    )
    game: Mapped[LFGame | None] = relationship('LFGame')

    def __init__(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        game_name: str | None = None,
        round_number: int | None = None,
        match_number: int | None = None,
        game_number: int | None = None,
        stage_indicator: str | StageType = DEFAULT_STAGE_INDICATOR,
        team_names: list[str] | None = None,
        team_logos: list[str] | None = None,
        team_scores: list[int] | None = None,
        score_differential: int | None = None,
        competition_id: int | None = None,
        game_id: str | None = None,
        scheduled_start: datetime | None = None,
        scheduled_end: datetime | None = None,
        actual_start_time: datetime | None = None,
        actual_time: datetime | None = None,
        logos: list[str] | None = None,
        scores: list[int] | None = None,
        names: list[str] | None = None,
    ) -> None:
        """Initializes a scheduled competition game.

        Args:
            start_time: Scheduled start timestamp.
            end_time: Scheduled end timestamp.
            game_name: Name of the game (e.g. 'R1 M3 G2').
            round_number: Optional integer round number.
            match_number: Optional integer match number.
            game_number: Optional integer game number.
            stage_indicator: Stage code or StageType (defaults to 'G').
            team_names: List of playing team names.
            team_logos: List of logo image URLs for playing teams.
            team_scores: Optional list of team scores after completion.
            score_differential: Optional explicit score differential.
            competition_id: Optional foreign key to parent Competition.
            game_id: Optional foreign key string to played LFGame.
            scheduled_start: Alias for start_time.
            scheduled_end: Alias for end_time.
            actual_start_time: Optional actual start timestamp.
            actual_time: Alias for actual_start_time.
            logos: Alias for team_logos.
            scores: Alias for team_scores.
            names: Alias for team_names.
        """
        super().__init__()
        resolved_start = (
            start_time if start_time is not None else scheduled_start
        )
        resolved_end = (
            end_time if end_time is not None else scheduled_end
        )
        if resolved_start is None or resolved_end is None:
            raise ValueError('start_time and end_time must be provided.')

        self.start_time = resolved_start
        self.end_time = resolved_end
        resolved_actual = (
            actual_start_time if actual_start_time is not None else actual_time
        )
        self.actual_start_time = resolved_actual
        self.round_number = round_number
        self.match_number = match_number
        self.game_number = game_number

        if isinstance(stage_indicator, StageType):
            self.stage_indicator = stage_indicator.code
        else:
            self.stage_indicator = stage_indicator

        if game_name:
            self.game_name = game_name
        else:
            generated_name = format_game_name(
                round_number=round_number,
                match_number=match_number,
                game_number=game_number,
                stage_indicator=self.stage_indicator,
            )
            self.game_name = (
                generated_name if generated_name else 'Scheduled Game'
            )

        resolved_names = names if names is not None else team_names
        self.team_names = list(resolved_names) if resolved_names else []

        resolved_logos = logos if logos is not None else team_logos
        self.team_logos = list(resolved_logos) if resolved_logos else []

        resolved_scores = scores if scores is not None else team_scores
        self.team_scores = (
            list(resolved_scores) if resolved_scores is not None else None
        )

        self._score_differential = score_differential
        self.competition_id = competition_id
        self.game_id = game_id

    @property
    def scheduled_start(self) -> datetime:
        """Returns the scheduled start timestamp.

        Returns:
            datetime: The start timestamp.
        """
        return self.start_time

    @scheduled_start.setter
    def scheduled_start(self, value: datetime) -> None:
        """Sets the scheduled start timestamp.

        Args:
            value: The new start timestamp.
        """
        self.start_time = value

    @property
    def scheduled_end(self) -> datetime:
        """Returns the scheduled end timestamp.

        Returns:
            datetime: The end timestamp.
        """
        return self.end_time

    @scheduled_end.setter
    def scheduled_end(self, value: datetime) -> None:
        """Sets the scheduled end timestamp.

        Args:
            value: The new end timestamp.
        """
        self.end_time = value

    @property
    def actual_time(self) -> datetime | None:
        """Returns the actual start timestamp when the game occurred.

        Returns:
            datetime | None: The actual game start timestamp or None.
        """
        return self.actual_start_time

    @actual_time.setter
    def actual_time(self, value: datetime | None) -> None:
        """Sets the actual start timestamp when the game occurred.

        Args:
            value: The actual start timestamp or None.
        """
        self.actual_start_time = value

    @property
    def logos(self) -> list[str]:
        """Returns the list of logos for teams playing.

        Returns:
            list[str]: Logo image URLs.
        """
        return self.team_logos

    @logos.setter
    def logos(self, value: list[str]) -> None:
        """Sets the list of logos for teams playing.

        Args:
            value: List of logo image URLs.
        """
        self.team_logos = value

    @property
    def scores(self) -> list[int] | None:
        """Returns the scores for each team playing.

        Returns:
            list[int] | None: Team scores, or None if not completed.
        """
        return self.team_scores

    @scores.setter
    def scores(self, value: list[int] | None) -> None:
        """Sets the team scores.

        Args:
            value: List of integer scores or None.
        """
        self.team_scores = value

    @property
    def names(self) -> list[str]:
        """Returns the names of each team playing.

        Returns:
            list[str]: Team names.
        """
        return self.team_names

    @names.setter
    def names(self, value: list[str]) -> None:
        """Sets the names of each team playing.

        Args:
            value: List of team name strings.
        """
        self.team_names = value

    @property
    def score_differential(self) -> int | None:
        """Returns the score differential between the two teams.

        Returns:
            int | None: Absolute difference between the two team scores,
            or None if fewer than two scores are available.
        """
        if self._score_differential is not None:
            return self._score_differential
        if self.team_scores is not None and len(self.team_scores) >= 2:
            return abs(self.team_scores[0] - self.team_scores[1])
        return None

    @score_differential.setter
    def score_differential(self, value: int | None) -> None:
        """Explicitly sets the score differential.

        Args:
            value: The score differential integer or None.
        """
        self._score_differential = value

    @property
    def is_complete(self) -> bool:
        """Returns whether the scheduled game has completed and scores recorded.

        Returns:
            bool: True if team_scores is recorded and non-empty.
        """
        return self.team_scores is not None and len(self.team_scores) > 0

    def __repr__(self) -> str:
        """Returns a string representation of the scheduled game.

        Returns:
            str: The string representation.
        """
        return (
            f"ScheduledGame(id={self.id}, game_name='{self.game_name}', "
            f"teams={self.team_names})"
        )
