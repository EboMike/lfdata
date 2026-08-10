"""Class representing a snapshot of game state changes after a specific event.

This module defines data containers that capture incremental score, life, ammo, and status
changes produced by a single processed game event during playback simulation.

Usage example:
    from lfdata.replay import LFReplayEventRecord

    record = LFReplayEventRecord(
        event_id=1, time_ms=1000, description='Player zapped',
        player_changes={}, team_changes={}
    )
"""


class LFReplayEventRecord:
    """Snapshot container for player and team state changes resulting from an event.

    Attributes:
        event_id: Database ID of the triggering event.
        time_ms: Timestamp in milliseconds when the event occurred.
        description: Printable description string of the event.
        player_changes: Mapping of entity IDs to player attribute deltas.
        team_changes: Mapping of team indices to team score deltas.
    """

    def __init__(
        self,
        event_id: int,
        time_ms: int,
        description: str,
        player_changes: dict[str, dict[str, any]],
        team_changes: dict[int, dict[str, any]],
    ) -> None:
        """Initializes the event record.

        Args:
            event_id: The ID of the event record in the database.
            time_ms: The millisecond timestamp of the event.
            description: A string description of the event.
            player_changes: A dictionary of player entity_id to attribute changes.
            team_changes: A dictionary of team_index to attribute changes.
        """
        self.event_id = event_id
        self.time_ms = time_ms
        self.description = description
        self.player_changes = player_changes
        self.team_changes = team_changes

    def __repr__(self) -> str:
        """Returns a string representation of the event record.

        Returns:
            str: The string representation.
        """
        return (
            f'LFReplayEventRecord(time_ms={self.time_ms}, '
            f"description='{self.description}')"
        )
