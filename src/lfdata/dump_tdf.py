"""Dumps game and player states from LF TDF replay simulations.

This module provides state dumping utilities and a command-line interface
to inspect simulated game states across time, triggering on state changes,
events, or fixed intervals, in CSV, JSON, or text formats.

Usage example:
    from lfdata.dump_tdf import TdfStateDumper, TdfDumpTrigger, TdfDumpFormat
    from lfdata.importer import TdfImporter

    game = TdfImporter('game.tdf').parse()
    dumper = TdfStateDumper(
        game=game,
        trigger=TdfDumpTrigger.PLAYER_CHANGE,
        output_format=TdfDumpFormat.CSV,
    )
    csv_text = dumper.dump_to_string()
"""

import argparse
import csv
import dataclasses
import io
import json
import sys
from typing import TextIO

from lfdata.dump_tdf_types import (
    TdfDumpFormat,
    TdfDumpTrigger,
    TdfGameStateEntry,
    TdfPlayerSelection,
    TdfPlayerStateEntry,
    format_time_ms,
)
from lfdata.importer import TdfImporter
from lfdata.model import LFGame
from lfdata.replay import LFReplaySystem
from lfdata.replay.state import LFReplayPlayerState

__all__ = [
    'TdfDumpFormat',
    'TdfDumpTrigger',
    'TdfGameStateEntry',
    'TdfPlayerSelection',
    'TdfPlayerStateEntry',
    'TdfStateDumper',
    'format_time_ms',
    'main',
]


@dataclasses.dataclass(frozen=True)
class _TdfPlayerSnapshot:
    """Internal immutable state used to detect when a player's state changes."""

    score: int
    lives: int
    shots: int
    missiles: int
    special_points: int
    hp: int
    is_down: bool
    is_eliminated: bool


class TdfStateDumper:
    """Orchestrates LF replay simulation and formats game state dumps."""

    def __init__(
        self,
        game: LFGame,
        trigger: TdfDumpTrigger = TdfDumpTrigger.PLAYER_CHANGE,
        output_format: TdfDumpFormat = TdfDumpFormat.CSV,
        player_selection: TdfPlayerSelection = TdfPlayerSelection.ALL,
        interval_ms: int = 1000,
    ) -> None:
        """Initializes the TDF state dumper with replay parameters.

        Args:
            game: The LFGame model instance containing events and entities.
            trigger: Condition deciding when an entry is recorded.
            output_format: Output format for the serialized data.
            player_selection: Whether to include all players or changed only.
            interval_ms: Millisecond interval when trigger is INTERVAL.
        """
        self.game = game
        self.trigger = trigger
        self.output_format = output_format
        self.player_selection = player_selection
        self.interval_ms = max(1, interval_ms)
        self.replay = LFReplaySystem(game=game, align_stats=True)

    def collect_entries(self) -> list[TdfGameStateEntry]:
        """Simulates replay events and collects recorded game state entries.

        Returns:
            list[TdfGameStateEntry]: Ordered list of game state entries.
        """
        entries: list[TdfGameStateEntry] = []
        sorted_events = sorted(self.game.events, key=lambda e: e.time)

        if self.trigger in (
            TdfDumpTrigger.PLAYER_CHANGE,
            TdfDumpTrigger.INTERVAL,
        ):
            initial_entry = self._build_game_state_entry(
                time_ms=0,
                event_desc='Initial State',
                changed_ids=None,
            )
            entries.append(initial_entry)

        last_interval_time_ms = 0
        prev_snapshots = {
            p.entity_id: self._snapshot_player(p, time_ms=0)
            for p in self.replay.game_state.players.values()
        }

        for event in sorted_events:
            event_time_ms = event.time

            if self.trigger == TdfDumpTrigger.INTERVAL:
                while last_interval_time_ms + self.interval_ms <= event_time_ms:
                    last_interval_time_ms += self.interval_ms
                    for p in self.replay.game_state.players.values():
                        p.update_downtime(last_interval_time_ms)
                    entries.append(
                        self._build_game_state_entry(
                            time_ms=last_interval_time_ms,
                            event_desc=None,
                            changed_ids=None,
                        )
                    )

            for player in self.replay.game_state.players.values():
                player.update_downtime(event_time_ms)

            description = self.replay._dispatch_event(event)
            self.replay.game_state.update_team_scores_and_rankings()

            for player in self.replay.game_state.players.values():
                player.update_downtime(event_time_ms)

            curr_snapshots = {
                p.entity_id: self._snapshot_player(p, time_ms=event_time_ms)
                for p in self.replay.game_state.players.values()
            }

            changed_ids = [
                eid
                for eid, curr in curr_snapshots.items()
                if curr != prev_snapshots[eid]
            ]
            prev_snapshots = curr_snapshots

            if self.trigger == TdfDumpTrigger.PLAYER_CHANGE and changed_ids:
                entries.append(
                    self._build_game_state_entry(
                        time_ms=event_time_ms,
                        event_desc=description,
                        changed_ids=set(changed_ids),
                    )
                )
            elif self.trigger == TdfDumpTrigger.EVENT:
                entries.append(
                    self._build_game_state_entry(
                        time_ms=event_time_ms,
                        event_desc=description,
                        changed_ids=set(changed_ids),
                    )
                )

            if event.event_type == '0101':
                break

        final_time_ms = (
            sorted_events[-1].time if sorted_events else self.game.duration or 0
        )
        if self.trigger == TdfDumpTrigger.FINAL:
            entries.append(
                self._build_game_state_entry(
                    time_ms=final_time_ms,
                    event_desc='Game Final State',
                    changed_ids=None,
                )
            )

        return entries

    def _snapshot_player(
        self, player: LFReplayPlayerState, time_ms: int
    ) -> _TdfPlayerSnapshot:
        """Takes an internal immutable snapshot of a player's core stats.

        Args:
            player: Replay player state instance.
            time_ms: Current timestamp in milliseconds.

        Returns:
            _TdfPlayerSnapshot: Snapshot instance.
        """
        return _TdfPlayerSnapshot(
            score=player.score,
            lives=player.lives,
            shots=player.shots,
            missiles=player.missiles,
            special_points=player.special_points,
            hp=player.hp,
            is_down=player.is_down(time_ms),
            is_eliminated=player.is_eliminated(),
        )

    def _build_game_state_entry(
        self,
        time_ms: int,
        event_desc: str | None,
        changed_ids: set[str] | None,
    ) -> TdfGameStateEntry:
        """Constructs a TdfGameStateEntry container from current replay state.

        Args:
            time_ms: Millisecond timestamp of the entry.
            event_desc: Description string of triggering event, if any.
            changed_ids: Optional set of entity IDs that changed.

        Returns:
            TdfGameStateEntry: Constructed entry snapshot.
        """
        player_entries: list[TdfPlayerStateEntry] = []
        team_names = {
            t.team_index: t.name for t in self.replay.game_state.teams.values()
        }

        time_str = format_time_ms(time_ms)
        for p in self.replay.game_state.players.values():
            if (
                self.player_selection == TdfPlayerSelection.CHANGED
                and changed_ids is not None
                and p.entity_id not in changed_ids
            ):
                continue

            if p.is_eliminated():
                state_str = 'Eliminated'
            elif p.is_down(time_ms):
                state_str = 'Resettable' if p.is_resettable(time_ms) else 'Down'
            else:
                state_str = 'Active'

            codename = self.replay.entity_names.get(p.entity_id, p.entity_id)
            team_name = team_names.get(p.team_index, f'Team {p.team_index}')

            entry = TdfPlayerStateEntry(
                time_ms=time_ms,
                time_str=time_str,
                entity_id=p.entity_id,
                name=codename,
                team_index=p.team_index,
                team_name=team_name,
                role=p.role.display_name,
                score=p.score,
                lives=p.lives,
                shots=p.shots,
                missiles=p.missiles,
                special_points=p.special_points,
                hp=p.hp,
                state=state_str,
                is_down=p.is_down(time_ms),
                is_eliminated=p.is_eliminated(),
                downtime_ends_at_ms=p.downtime_ends_at_ms,
            )
            player_entries.append(entry)

        return TdfGameStateEntry(
            time_ms=time_ms,
            time_str=time_str,
            event_description=event_desc,
            players=player_entries,
        )

    def format_entries(self, entries: list[TdfGameStateEntry]) -> str:
        """Formats collected game state entries according to selected format.

        Args:
            entries: List of collected game state entries.

        Returns:
            str: Serialized output string.
        """
        if self.output_format == TdfDumpFormat.CSV:
            return self._format_csv(entries)
        if self.output_format == TdfDumpFormat.JSON:
            return self._format_json(entries)
        if self.output_format == TdfDumpFormat.JSONL:
            return self._format_jsonl(entries)
        return self._format_text(entries)

    def _format_csv(self, entries: list[TdfGameStateEntry]) -> str:
        """Formats entries as a CSV string where each row is one player state.

        Args:
            entries: List of state entries.

        Returns:
            str: CSV text content.
        """
        output = io.StringIO()
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(TdfPlayerStateEntry.csv_headers())
        for entry in entries:
            for p in entry.players:
                writer.writerow(p.to_csv_row())
        return output.getvalue()

    def _format_json(self, entries: list[TdfGameStateEntry]) -> str:
        """Formats entries as a standard JSON string.

        Args:
            entries: List of state entries.

        Returns:
            str: JSON text content.
        """
        data = [e.to_dict() for e in entries]
        return json.dumps(data, indent=2)

    def _format_jsonl(self, entries: list[TdfGameStateEntry]) -> str:
        """Formats entries as JSON Lines (one JSON object per player state).

        Args:
            entries: List of state entries.

        Returns:
            str: JSONL text content.
        """
        lines = []
        for entry in entries:
            for p in entry.players:
                lines.append(json.dumps(p.to_dict()))
        return '\n'.join(lines) + ('\n' if lines else '')

    def _format_text(self, entries: list[TdfGameStateEntry]) -> str:
        """Formats entries as a human-readable text report.

        Args:
            entries: List of state entries.

        Returns:
            str: Plain-text report.
        """
        lines: list[str] = []
        for entry in entries:
            event_info = (
                f' ({entry.event_description})'
                if entry.event_description
                else ''
            )
            lines.append(
                f'=== Game State at {entry.time_str} '
                f'({entry.time_ms} ms){event_info} ==='
            )
            for p in entry.players:
                lines.append(
                    f'  [{p.team_name}] {p.name} ({p.role}): '
                    f'Score={p.score}, Lives={p.lives}, Shots={p.shots}, '
                    f'Missiles={p.missiles}, SP={p.special_points}, '
                    f'HP={p.hp}, State={p.state}'
                )
            lines.append('')
        return '\n'.join(lines)

    def dump_to_string(self) -> str:
        """Dumps simulated game state directly to a formatted string.

        Returns:
            str: Formatted state dump string.
        """
        entries = self.collect_entries()
        return self.format_entries(entries)

    def dump(self, output: TextIO) -> None:
        """Writes the formatted state dump to the provided text stream.

        Args:
            output: Destination TextIO stream.
        """
        output.write(self.dump_to_string())


def _build_arg_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for the dump-tdf CLI tool.

    Returns:
        argparse.ArgumentParser: Configured parser instance.
    """
    parser = argparse.ArgumentParser(
        description='Dump LF game states from a TDF file during replay playback.'
    )
    parser.add_argument(
        'input_tdf',
        nargs='?',
        type=str,
        help='Path to the TDF file to inspect.',
    )
    parser.add_argument(
        '--input_tdf',
        dest='input_tdf_opt',
        type=str,
        help='Alternative flag to specify input TDF file path.',
    )
    parser.add_argument(
        '--trigger',
        type=str,
        default=TdfDumpTrigger.PLAYER_CHANGE.value,
        choices=[t.value for t in TdfDumpTrigger],
        help=(
            'Condition deciding when to dump a game state entry. '
            'Defaults to player_change.'
        ),
    )
    parser.add_argument(
        '--format',
        '-f',
        type=str,
        default=TdfDumpFormat.CSV.value,
        choices=[f.value for f in TdfDumpFormat],
        help='Output format for dumped state entries. Defaults to csv.',
    )
    parser.add_argument(
        '--players',
        type=str,
        default=TdfPlayerSelection.ALL.value,
        choices=[s.value for s in TdfPlayerSelection],
        help=(
            'Filter players in each entry: all (all players) or '
            'changed (only players whose state changed).'
        ),
    )
    parser.add_argument(
        '--interval_ms',
        type=int,
        default=1000,
        help='Time interval in milliseconds when using --trigger interval.',
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='File path to write output to. Defaults to standard output.',
    )
    return parser


def main() -> None:
    """Main CLI entrypoint for the dump-tdf command-line utility.

    Parses command-line arguments, ingests the target TDF file, runs the
    simulation, and writes the state dump to stdout or a file.
    """
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = _build_arg_parser()
    args = parser.parse_args()

    tdf_path = args.input_tdf or args.input_tdf_opt
    if not tdf_path:
        parser.print_help()
        sys.exit(1)

    trigger = TdfDumpTrigger.from_str(args.trigger)
    output_format = TdfDumpFormat.from_str(args.format)
    player_selection = TdfPlayerSelection.from_str(args.players)

    importer = TdfImporter(tdf_path)
    game = importer.parse()

    dumper = TdfStateDumper(
        game=game,
        trigger=trigger,
        output_format=output_format,
        player_selection=player_selection,
        interval_ms=args.interval_ms,
    )

    if args.output:
        with open(args.output, 'w', encoding='utf-8', newline='') as f:
            dumper.dump(f)
    else:
        dumper.dump(sys.stdout)


if __name__ == '__main__':
    main()
