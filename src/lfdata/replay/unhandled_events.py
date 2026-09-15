"""Detection and diagnostic analysis of unhandled or ignored game event types.

This module provides utilities to inspect event streams in LF games, identifying
event types that lfdata ignores or cannot process during replay simulation. It
correlates unhandled events with players who experience end-state discrepancies
(lives, ammo, score) to highlight potential sources of simulation divergence.

Usage example:
    from lfdata.replay.unhandled_events import LFUnhandledEventsAnalyzer

    analyzer = LFUnhandledEventsAnalyzer(game=game, discrepancies=discrepancies)
    unhandled = analyzer.find_unhandled_events()
    analyzer.dump_unhandled_events(unhandled_events=unhandled)
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from lfdata.model import LFGame

if TYPE_CHECKING:
    from lfdata.replay.diagnostics import PlayerDiscrepancy


def format_timestamp_ms(time_ms: int) -> str:
    """Formats millisecond game time into MM:SS.sss display format.

    Args:
        time_ms: Millisecond timestamp.

    Returns:
        str: Formatted string in MM:SS.sss format.

    Usage:
        formatted = format_timestamp_ms(170566)
    """
    total_ms = max(0, time_ms)
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) / 1000.0
    return f'{minutes:02d}:{seconds:06.3f}'


HANDLED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        '0100',  # Mission start
        '0101',  # Mission end
        '0201',  # Shot miss
        '0202',  # Shot miss base
        '0203',  # Shot zap (shielded)
        '0204',  # Base destroy (zap)
        '0205',  # Damaged opponent zap
        '0206',  # Downed opponent zap
        '0207',  # Damaged teammate zap
        '0208',  # Downed teammate zap
        '0300',  # Missile locking
        '0301',  # Missile miss base
        '0302',  # Missile zap (shielded)
        '0303',  # Base destroy (missile)
        '0304',  # Missile miss
        '0306',  # Missile downed opponent
        '0308',  # Missile downed teammate
        '0400',  # Rapid fire activate
        '0404',  # Nuke activate
        '0405',  # Nuke detonate
        '0500',  # Resupply ammo (team member)
        '0502',  # Resupply lives (team member)
        '0510',  # Resupply ammo (team boost)
        '0512',  # Resupply lives (team boost)
        '0600',  # Penalty
        '0900',  # Achievement
        '0902',  # Reward
        '0B03',  # Base awarded
        'nuke_cancel',  # Inferred nuke cancel
    }
)


@dataclasses.dataclass(frozen=True)
class UnhandledEventInfo:
    """Represents an event whose type is unhandled and ignored by lfdata.

    Attributes:
        time_ms: Timestamp in milliseconds when the event occurred.
        event_type: The TDF event type code string (e.g. '0200', '0305').
        action: The action description string recorded for the event.
        actor_entity_id: The entity ID of the actor, or None.
        target_entity_id: The entity ID of the target, or None.
        actor_name: Resolved display name of the actor, or None.
        target_name: Resolved display name of the target, or None.
        pertains_to_mismatched_player: True if actor or target has a
            discrepancy.
        mismatched_player_ids: List of entity IDs of mismatched players
            involved in this event.
        discrepancy_summaries: List of descriptions of discrepancies for the
            involved players.
    """

    time_ms: int
    event_type: str
    action: str
    actor_entity_id: str | None = None
    target_entity_id: str | None = None
    actor_name: str | None = None
    target_name: str | None = None
    pertains_to_mismatched_player: bool = False
    mismatched_player_ids: list[str] = dataclasses.field(default_factory=list)
    discrepancy_summaries: list[str] = dataclasses.field(default_factory=list)


class LFUnhandledEventsAnalyzer:
    """Analyzes and reports event types ignored or unhandled by lfdata.

    Scans game events for types outside the handled set and identifies
    events involving players with state discrepancies.

    Attributes:
        game: The LFGame model containing entities and events.
        discrepancies: Mapping of player entity IDs to their discrepancies.
    """

    def __init__(
        self,
        game: LFGame,
        discrepancies: dict[str, list[PlayerDiscrepancy]] | None = None,
    ) -> None:
        """Initializes the unhandled events analyzer.

        Args:
            game: The game database model to analyze.
            discrepancies: Optional mapping of entity IDs to discrepancy lists.

        Usage:
            analyzer = LFUnhandledEventsAnalyzer(game=game)
        """
        self.game = game
        self.discrepancies: dict[str, list[PlayerDiscrepancy]] = (
            discrepancies if discrepancies is not None else {}
        )

    def _resolve_name(self, entity_id: str | None) -> str | None:
        """Resolves an entity ID to its display name from game entities.

        Args:
            entity_id: The entity ID string or None.

        Returns:
            The entity display name or None if entity_id is None.
        """
        if entity_id is None:
            return None
        if self.game.entities:
            for e in self.game.entities:
                if e.entity_id == entity_id:
                    return e.desc or entity_id
        return entity_id

    def _build_discrepancy_summary(self, entity_id: str) -> str:
        """Builds a human-readable summary of discrepancies for a player.

        Args:
            entity_id: The entity ID of the player.

        Returns:
            A formatted string describing the player's discrepancies.
        """
        name = self._resolve_name(entity_id=entity_id) or entity_id
        discs = self.discrepancies.get(entity_id, [])
        details: list[str] = []
        for d in discs:
            diff = d.computed - d.expected
            details.append(
                f'{d.field}: computed={d.computed}, expected={d.expected} '
                f'({diff:+d})'
            )
        joined_details = '; '.join(details)
        return f'Player {name} ({entity_id}): {joined_details}'

    def find_unhandled_events(self) -> list[UnhandledEventInfo]:
        """Finds all events with types not handled by lfdata in the game.

        Returns:
            A list of UnhandledEventInfo records for all unhandled events.

        Usage:
            unhandled = analyzer.find_unhandled_events()
        """
        unhandled: list[UnhandledEventInfo] = []
        if not self.game.events:
            return unhandled

        for event in self.game.events:
            if event.event_type in HANDLED_EVENT_TYPES:
                continue

            mismatched_ids: list[str] = []
            summaries: list[str] = []

            for pid in (event.actor_entity_id, event.target_entity_id):
                if (
                    pid
                    and pid in self.discrepancies
                    and pid not in mismatched_ids
                ):
                    mismatched_ids.append(pid)
                    summaries.append(self._build_discrepancy_summary(pid))

            pertains = len(mismatched_ids) > 0
            actor_name = self._resolve_name(entity_id=event.actor_entity_id)
            target_name = self._resolve_name(entity_id=event.target_entity_id)

            unhandled.append(
                UnhandledEventInfo(
                    time_ms=event.time,
                    event_type=event.event_type,
                    action=event.action,
                    actor_entity_id=event.actor_entity_id,
                    target_entity_id=event.target_entity_id,
                    actor_name=actor_name,
                    target_name=target_name,
                    pertains_to_mismatched_player=pertains,
                    mismatched_player_ids=mismatched_ids,
                    discrepancy_summaries=summaries,
                )
            )

        return unhandled

    def get_events_for_player(self, entity_id: str) -> list[UnhandledEventInfo]:
        """Gets all unhandled events involving a specific player.

        Args:
            entity_id: The entity ID of the player to filter by.

        Returns:
            List of UnhandledEventInfo records where the player is actor or
            target.

        Usage:
            events = analyzer.get_events_for_player('player_1')
        """
        all_unhandled = self.find_unhandled_events()
        return [
            ev
            for ev in all_unhandled
            if ev.actor_entity_id == entity_id
            or ev.target_entity_id == entity_id
        ]

    def _dump_single_event(self, ev: UnhandledEventInfo) -> None:
        """Prints diagnostic information for a single unhandled event.

        Args:
            ev: The UnhandledEventInfo record to print.
        """
        time_str = format_timestamp_ms(time_ms=ev.time_ms)
        actor_label = (
            f'actor={ev.actor_name or ev.actor_entity_id}'
            if ev.actor_entity_id
            else None
        )
        target_label = (
            f'target={ev.target_name or ev.target_entity_id}'
            if ev.target_entity_id
            else None
        )
        parts = [p for p in (actor_label, target_label) if p]
        entities_str = f' ({", ".join(parts)})' if parts else ''

        print(
            f'  - {ev.time_ms} ms ({time_str}): Type {ev.event_type} '
            f'action="{ev.action}"{entities_str}'
        )

        if ev.pertains_to_mismatched_player:
            print('    *** HIGHLIGHT: PERTAINS TO PLAYER WITH DISCREPANCY ***')
            for summary in ev.discrepancy_summaries:
                print(f'    * {summary}')

    def dump_unhandled_events(
        self, unhandled_events: list[UnhandledEventInfo] | None = None
    ) -> None:
        """Prints a diagnostic report of unhandled or ignored game events.

        Highlights events that involve any player experiencing a discrepancy.

        Args:
            unhandled_events: Optional pre-filtered list of unhandled events.
                If None, finds all unhandled events in the game.

        Returns:
            None.

        Usage:
            analyzer.dump_unhandled_events()
        """
        events = (
            unhandled_events
            if unhandled_events is not None
            else self.find_unhandled_events()
        )
        if not events:
            return

        separator = '-' * 72
        print('\n' + separator)
        print('UNHANDLED & IGNORED EVENT ANALYSIS')
        print(separator)
        print(
            f'Found {len(events)} event(s) with types ignored/unhandled '
            'by lfdata:'
        )
        for ev in events:
            self._dump_single_event(ev=ev)
