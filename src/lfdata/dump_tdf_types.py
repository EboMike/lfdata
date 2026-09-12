"""Data structures and enums for dumping LF game and player states.

This module defines enums for triggers, formats, and player selections,
as well as dataclasses representing individual player state entries
and complete game state snapshots.

Usage example:
    from lfdata.dump_tdf_types import (
        TdfDumpTrigger,
        TdfDumpFormat,
        TdfPlayerStateEntry,
    )

    trigger = TdfDumpTrigger.PLAYER_CHANGE
    fmt = TdfDumpFormat.CSV
"""

import dataclasses
import enum


class TdfDumpTrigger(enum.Enum):
    """Enumeration of trigger conditions for recording game state entries.

    Attributes:
        PLAYER_CHANGE: Record an entry whenever any player's state changes.
        EVENT: Record an entry after each processed game event.
        INTERVAL: Record an entry at fixed periodic time intervals.
        FINAL: Record an entry only once at the end of the game.
    """

    PLAYER_CHANGE = 'player_change'
    EVENT = 'event'
    INTERVAL = 'interval'
    FINAL = 'final'

    @classmethod
    def from_str(cls, value: str) -> 'TdfDumpTrigger':
        """Parses a string into a TdfDumpTrigger enum.

        Args:
            value: Case-insensitive trigger name string.

        Returns:
            TdfDumpTrigger: The matched enum value.

        Raises:
            ValueError: If value does not match any valid trigger.
        """
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        valid = ', '.join([m.value for m in cls])
        raise ValueError(
            f"Invalid trigger '{value}'. Valid options are: {valid}"
        )


class TdfDumpFormat(enum.Enum):
    """Enumeration of output formats for dumped game state data.

    Attributes:
        CSV: Comma-separated values with one row per player state.
        JSON: Standard JSON document containing a list of state snapshots.
        JSONL: JSON Lines document with one object per line.
        TEXT: Formatted plain-text tables for human inspection.
    """

    CSV = 'csv'
    JSON = 'json'
    JSONL = 'jsonl'
    TEXT = 'text'

    @classmethod
    def from_str(cls, value: str) -> 'TdfDumpFormat':
        """Parses a string into a TdfDumpFormat enum.

        Args:
            value: Case-insensitive format name string.

        Returns:
            TdfDumpFormat: The matched enum value.

        Raises:
            ValueError: If value does not match any valid format.
        """
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        valid = ', '.join([m.value for m in cls])
        raise ValueError(
            f"Invalid format '{value}'. Valid options are: {valid}"
        )


class TdfPlayerSelection(enum.Enum):
    """Enumeration of player filtering options per recorded state entry.

    Attributes:
        ALL: Include all participating players in every state entry.
        CHANGED: Include only players whose state changed at this trigger.
    """

    ALL = 'all'
    CHANGED = 'changed'

    @classmethod
    def from_str(cls, value: str) -> 'TdfPlayerSelection':
        """Parses a string into a TdfPlayerSelection enum.

        Args:
            value: Case-insensitive selection name string.

        Returns:
            TdfPlayerSelection: The matched enum value.

        Raises:
            ValueError: If value does not match any valid selection.
        """
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        valid = ', '.join([m.value for m in cls])
        raise ValueError(
            f"Invalid player selection '{value}'. Valid options: {valid}"
        )


def format_time_ms(time_ms: int) -> str:
    """Formats millisecond game time into MM:SS.sss display format.

    Args:
        time_ms: Millisecond timestamp.

    Returns:
        str: Formatted string in MM:SS.sss format.
    """
    total_ms = max(0, time_ms)
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) / 1000.0
    return f'{minutes:02d}:{seconds:06.3f}'


@dataclasses.dataclass(frozen=True)
class TdfPlayerStateEntry:
    """Data record capturing the state of a single player at a timestamp.

    Attributes:
        time_ms: Milliseconds elapsed since the beginning of the game.
        time_str: Formatted timestamp as MM:SS.sss.
        entity_id: Unique entity ID string for the player.
        name: Printable codename or description of the player.
        team_index: Team index integer (0 or 1).
        team_name: Printable team name string.
        role: Display name string of the player's role.
        score: Current score integer.
        lives: Remaining lives count.
        shots: Remaining shots count.
        missiles: Remaining missiles count.
        special_points: Current special points value.
        hp: Current hit points (shields) integer.
        state: State descriptor ('Active', 'Down', 'Resettable', 'Eliminated').
        is_down: Boolean indicating whether player is in downtime.
        is_eliminated: Boolean indicating whether player is out of lives.
        downtime_ends_at_ms: Millisecond timestamp when downtime expires.
    """

    time_ms: int
    time_str: str
    entity_id: str
    name: str
    team_index: int
    team_name: str
    role: str
    score: int
    lives: int
    shots: int
    missiles: int
    special_points: int
    hp: int
    state: str
    is_down: bool
    is_eliminated: bool
    downtime_ends_at_ms: int

    @classmethod
    def csv_headers(cls) -> list[str]:
        """Returns the list of column header strings for CSV output.

        Returns:
            list[str]: Column header names.
        """
        return [
            'time_ms',
            'time_str',
            'entity_id',
            'name',
            'team_index',
            'team_name',
            'role',
            'score',
            'lives',
            'shots',
            'missiles',
            'special_points',
            'hp',
            'state',
            'is_down',
            'is_eliminated',
            'downtime_ends_at_ms',
        ]

    def to_csv_row(self) -> list[str]:
        """Converts the player state entry to a list of CSV cell values.

        Returns:
            list[str]: Formatted string values in column order.
        """
        return [
            str(self.time_ms),
            self.time_str,
            self.entity_id,
            self.name,
            str(self.team_index),
            self.team_name,
            self.role,
            str(self.score),
            str(self.lives),
            str(self.shots),
            str(self.missiles),
            str(self.special_points),
            str(self.hp),
            self.state,
            str(self.is_down),
            str(self.is_eliminated),
            str(self.downtime_ends_at_ms),
        ]

    def to_dict(self) -> dict[str, object]:
        """Converts the entry to a dictionary for JSON serialization.

        Returns:
            dict[str, object]: Dictionary representation of the state entry.
        """
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class TdfGameStateEntry:
    """Snapshot containing all player state records captured at a timestamp.

    Attributes:
        time_ms: Millisecond timestamp when the state entry was recorded.
        time_str: Formatted timestamp as MM:SS.sss.
        event_description: Optional description of event triggering this entry.
        players: List of TdfPlayerStateEntry records.
    """

    time_ms: int
    time_str: str
    event_description: str | None
    players: list[TdfPlayerStateEntry]

    def to_dict(self) -> dict[str, object]:
        """Converts the game state entry to a dictionary for serialization.

        Returns:
            dict[str, object]: Dictionary representation.
        """
        return {
            'time_ms': self.time_ms,
            'time_str': self.time_str,
            'event_description': self.event_description,
            'players': [p.to_dict() for p in self.players],
        }
