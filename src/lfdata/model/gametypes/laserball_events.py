"""Enums and dataclasses representing Laserball game events and metadata.

This module defines event types, event IDs, descriptions, and metadata for the
Laserball game type in LF.

Usage example:
    from lfdata.model.gametypes.laserball_events import LaserballEvent

    ev = LaserballEvent.from_id('1101')
    if ev:
        print(f'{ev.name}: {ev.description}')
"""

import dataclasses
import enum


@dataclasses.dataclass(frozen=True)
class LaserballEventInfo:
    """Metadata for a Laserball event type.

    Attributes:
        event_id: The 4-digit hexadecimal event code string.
        name: Short identifier name for the event.
        description: Human-readable description of the event.
    """

    event_id: str
    name: str
    description: str


class LaserballEvent(enum.Enum):
    """Enumeration of event types in Laserball games.

    Attributes:
        PASS: Player passes the ball to a teammate.
        GOAL: Player tags enemy base to score a goal.
        ASSIST: Player passes ball to teammate who immediately scores.
        STEAL: Player zaps enemy carrier to steal the ball.
        BLOCK: Player zaps an enemy player.
        ROUND_START: A new round begins.
        ROUND_END: The current round ends.
        GETS_BALL: Player receives ball at beginning of a round.
        CLEAR: Carrier zaps own base to clear ball to another player.
        FAIL_CLEAR: Carrier tries to clear but no teammate is up.
        RESET_ON_BASE: Player zaps neutral base to reset downtime.
    """

    PASS = LaserballEventInfo(
        event_id='1100',
        name='PASS',
        description='Player passes the ball to another player on the team.',
    )
    GOAL = LaserballEventInfo(
        event_id='1101',
        name='GOAL',
        description='The player scores.',
    )
    ASSIST = LaserballEventInfo(
        event_id='1102',
        name='ASSIST',
        description='The player assisted someone else.',
    )
    STEAL = LaserballEventInfo(
        event_id='1103',
        name='STEAL',
        description='Player steals a ball from the enemy ball carrier.',
    )
    BLOCK = LaserballEventInfo(
        event_id='1104',
        name='BLOCK',
        description='Player zaps an enemy player.',
    )
    ROUND_START = LaserballEventInfo(
        event_id='1105',
        name='ROUND_START',
        description='A new round begins.',
    )
    ROUND_END = LaserballEventInfo(
        event_id='1106',
        name='ROUND_END',
        description='The round is over.',
    )
    GETS_BALL = LaserballEventInfo(
        event_id='1107',
        name='GETS_BALL',
        description='A player receives a ball at the beginning of a round.',
    )
    CLEAR = LaserballEventInfo(
        event_id='1109',
        name='CLEAR',
        description='A player clears the ball, a new player receives it.',
    )
    FAIL_CLEAR = LaserballEventInfo(
        event_id='110A',
        name='FAIL_CLEAR',
        description='A player tried to clear, but no teammate was up.',
    )
    RESET_ON_BASE = LaserballEventInfo(
        event_id='110B',
        name='RESET_ON_BASE',
        description='The player zaps a neutral base.',
    )

    def __init__(self, info: LaserballEventInfo) -> None:
        """Initializes the Laserball event enum member.

        Args:
            info: Metadata describing the event.
        """
        self.event_id = info.event_id
        self.display_name = info.name
        self.description = info.description

    @classmethod
    def from_id(cls, event_id: str) -> 'LaserballEvent | None':
        """Retrieves a Laserball event enum by its TDF event ID.

        Args:
            event_id: The 4-digit hexadecimal event code string.

        Returns:
            LaserballEvent | None: The matching enum member, or None.

        Usage:
            event = LaserballEvent.from_id('1101')
        """
        norm_id = event_id.strip().upper()
        for member in cls:
            if member.event_id.upper() == norm_id:
                return member
        return None

    @classmethod
    def is_laserball_event(cls, event_id: str) -> bool:
        """Checks whether an event ID belongs to the Laserball event set.

        Args:
            event_id: The event ID code string.

        Returns:
            bool: True if event_id is a Laserball event, False otherwise.

        Usage:
            if LaserballEvent.is_laserball_event(event.event_type):
                pass
        """
        return cls.from_id(event_id) is not None
