"""In-memory state container for a team in lflive.

This module defines `LiveTeamState`, representing the mutable real-time score,
metadata, and ranking for a team.

Usage example:
    from lflive.state.team_state import LiveTeamState

    team = LiveTeamState(
        team_id=1,
        name='Fire',
        color='Red',
        rgb='#ff0000',
    )
    team.score += 100
"""

import dataclasses


@dataclasses.dataclass
class LiveTeamState:
    """In-memory real-time state of a single team.

    Attributes:
        team_id: Numerical primary key sent to consumers.
        name: Printable display name of the team.
        color: Internal color name.
        rgb: CSS RGB hex string (e.g. #ff0000).
        score: Cumulative team score.
        ranking: 1-based team position rank.
    """

    team_id: int
    name: str
    color: str
    rgb: str
    score: int = 0
    ranking: int = 1
