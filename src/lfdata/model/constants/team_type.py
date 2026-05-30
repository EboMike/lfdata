"""Enums representing LF game teams and metadata."""

import dataclasses
import enum

from lfdata.model.constants.color import LFTeamColor


@dataclasses.dataclass(frozen=True)
class LFTeamTypeStats:
    """Statistics and metadata for a team type.

    Attributes:
        team_index: The index of the team.
        display_name: The display name of the team.
        color: The color enum of the team.
    """

    team_index: int
    display_name: str
    color: LFTeamColor


class LFTeamType(enum.Enum):
    """Defines team types in LF SM5 games, linking indexes to team colors.

    Includes display names and the color enum.
    """

    FIRE = LFTeamTypeStats(
        team_index=0, display_name='Fire Team', color=LFTeamColor.FIRE
    )
    EARTH = LFTeamTypeStats(
        team_index=1, display_name='Earth Team', color=LFTeamColor.EARTH
    )
    NEUTRAL = LFTeamTypeStats(
        team_index=2, display_name='Neutral', color=LFTeamColor.NONE
    )

    def __init__(self, stats: LFTeamTypeStats) -> None:
        """Initializes the team type.

        Args:
            stats: The team type metadata statistics object.
        """
        self.team_index = stats.team_index
        self.display_name = stats.display_name
        self.color = stats.color

    @classmethod
    def from_index(cls, team_index: int) -> 'LFTeamType':
        """Retrieves a team type by its team index.

        Args:
            team_index: The index of the team.

        Returns:
            LFTeamType: The matching team type.

        Raises:
            ValueError: If the team_index is not valid.
        """
        for ttype in cls:
            if ttype.team_index == team_index:
                return ttype
        raise ValueError(f'Invalid team index: {team_index}')
