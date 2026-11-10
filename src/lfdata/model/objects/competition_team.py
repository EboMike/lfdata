"""SQLAlchemy model for competition teams.

This module defines database ORM models for teams participating in competitions,
storing team slug identifiers, team names, short names, logos, and rosters of
players.

Usage example:
    from lfdata.model import CompetitionTeam, Player

    player = Player(codename='Alpha')
    team = CompetitionTeam(
        slug='tigers',
        name='Tigers',
        short_name='TIG',
        logo_url='https://example.com/logo.png',
        players=[player],
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lfdata.model.base import Base
from lfdata.model.objects.player import Player

if TYPE_CHECKING:
    from lfdata.model.objects.competition import Competition

competition_team_players = Table(
    'competition_team_players',
    Base.metadata,
    Column(
        'team_slug',
        String(50),
        ForeignKey('competition_teams.slug', ondelete='CASCADE'),
        primary_key=True,
    ),
    Column(
        'player_id',
        Integer,
        ForeignKey('players.id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


class CompetitionTeam(Base):
    """Database model for a team participating in a competition.

    Attributes:
        slug: Primary key string identifying the team across a competition.
        name: Full team name string.
        short_name: Short team abbreviation string (typically 3 or 4 chars).
        logo_url: Optional URL string pointing to an image asset for the logo.
        competition_id: Optional foreign key integer referencing Competition.
        competition: Parent Competition ORM relationship.
        players: List of persistent Player ORM objects on the roster.
        logo: Property accessor and setter for logo_url.
        player_codenames: Property returning a list of player codename strings.
    """

    __tablename__ = 'competition_teams'

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str] = mapped_column(String(10))
    logo_url: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    competition_id: Mapped[int | None] = mapped_column(
        ForeignKey('competitions.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
    )

    # Relationships
    competition: Mapped[Competition | None] = relationship(
        'Competition', back_populates='teams'
    )
    players: Mapped[list[Player]] = relationship(
        'Player', secondary=competition_team_players, lazy='selectin'
    )

    def __init__(
        self,
        slug: str,
        name: str,
        short_name: str,
        logo_url: str | None = None,
        logo: str | None = None,
        players: list[Player | str] | None = None,
        competition_id: int | None = None,
    ) -> None:
        """Initializes a competition team.

        Args:
            slug: Unique slug ID for the team.
            name: Full name of the team.
            short_name: Short team abbreviation (typically 3-4 chars).
            logo_url: Optional URL pointing to a logo image asset.
            logo: Optional alias for logo_url.
            players: Optional list of Player objects or player codename strings.
            competition_id: Optional foreign key referencing parent Competition.
        """
        super().__init__()
        self.slug = slug
        self.name = name
        self.short_name = short_name
        self.logo_url = logo if logo is not None else logo_url
        self.competition_id = competition_id

        if players:
            resolved_players: list[Player] = []
            for player in players:
                if isinstance(player, str):
                    resolved_players.append(Player(codename=player))
                else:
                    resolved_players.append(player)
            self.players = resolved_players
        else:
            self.players = []

    @property
    def logo(self) -> str | None:
        """Returns the URL of the team logo image asset.

        Returns:
            str | None: URL to the image asset, or None if not set.
        """
        return self.logo_url

    @logo.setter
    def logo(self, value: str | None) -> None:
        """Sets the team logo image URL.

        Args:
            value: The image asset URL string, or None.
        """
        self.logo_url = value

    @property
    def player_codenames(self) -> list[str]:
        """Returns the list of player codenames on the team roster.

        Returns:
            list[str]: Codenames of all players on the roster.
        """
        return [player.codename for player in self.players]

    def __repr__(self) -> str:
        """Returns a string representation of the competition team.

        Returns:
            str: The string representation.
        """
        return (
            f"CompetitionTeam(slug='{self.slug}', name='{self.name}', "
            f"short_name='{self.short_name}')"
        )

