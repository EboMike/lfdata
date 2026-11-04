"""Outbound event emitter and logger for lflive consumer broadcasts.

This module formats and broadcasts tab-delimited UTF-8 protocol messages to
connected visualization clients and logs output lines when --log_output is set.

Usage example:
    from lflive.emitter import OutputEmitter

    emitter = OutputEmitter(log_output=True)
    emitter.emit(3, 1000, 1, 500)
"""

from collections.abc import Callable

from lflive.constants import (
    DATA_TYPE_BALL_CARRIER,
    DATA_TYPE_BASE_DESCRIPTION,
    DATA_TYPE_CENTER_INFO,
    DATA_TYPE_GAME_START_TIME,
    DATA_TYPE_GAME_TYPE,
    DATA_TYPE_IMPORTANT_EVENT,
    DATA_TYPE_NEW_GAME,
    DATA_TYPE_PLAYER_DESCRIPTION,
    DATA_TYPE_PLAYER_HITPOINTS,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_RANKING,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_PLAYER_STATE,
    DATA_TYPE_PRESYNC_END,
    DATA_TYPE_RAPID_FIRE_STATE,
    DATA_TYPE_TEAM_DESCRIPTION,
    DATA_TYPE_TEAM_RANKING,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.state.game_state import LiveGameState


def format_colored_name(name: str, rgb: str | None = None) -> str:
    """Formats an entity name wrapped in HTML-style font color tags.

    Args:
        name: Printable entity or player name.
        rgb: Optional CSS hex RGB color string (e.g. #ff0000).

    Returns:
        str: HTML font tagged string if rgb is given, else raw name.

    Usage example:
        tagged = format_colored_name('Ace', '#ff0000')
        assert tagged == '<font color="#ff0000">Ace</font>'
    """
    if rgb:
        return f'<font color="{rgb}">{name}</font>'
    return name


class OutputEmitter:
    """Formats, logs, and broadcasts outbound consumer protocol lines.

    Attributes:
        log_output: Whether to print every generated line to standard output.
        listeners: List of callback functions receiving emitted lines.
        emitted_lines: In-memory history of emitted protocol lines.
    """

    def __init__(self, log_output: bool = False) -> None:
        """Initializes the output emitter.

        Args:
            log_output: Flag to print generated lines to stdout.
        """
        self.log_output = log_output
        self.listeners: list[Callable[[str], None]] = []
        self.emitted_lines: list[str] = []
        self._next_important_event_id: int = 1

    def add_listener(self, callback: Callable[[str], None]) -> None:
        """Registers a listener callback for emitted broadcast lines.

        Args:
            callback: Callable accepting a single formatted line string.

        Usage example:
            emitter.add_listener(lambda line: print(line))
        """
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]) -> None:
        """Unregisters an existing listener callback.

        Args:
            callback: The callback instance to remove.

        Usage example:
            emitter.remove_listener(my_callback)
        """
        if callback in self.listeners:
            self.listeners.remove(callback)

    def clear(self) -> None:
        """Clears previously recorded emitted lines history.

        Usage example:
            emitter.clear()
        """
        self.emitted_lines.clear()
        self._next_important_event_id = 1

    def next_important_event_id(self) -> int:
        """Returns next sequential important event ID and increments counter.

        Returns:
            int: Sequential unique event identifier.

        Usage example:
            eid = emitter.next_important_event_id()
            assert eid >= 1
        """
        event_id = self._next_important_event_id
        self._next_important_event_id += 1
        return event_id

    def emit_important_event(
        self,
        time_ms: int,
        message: str,
        event_id: int | None = None,
    ) -> tuple[int, str]:
        """Emits an important game event (type 25) with a sequential ID.

        If event_id is None, a new sequential ID is allocated.

        Args:
            time_ms: Elapsed game time in milliseconds.
            message: Formatted event message.
            event_id: Optional existing event ID to reuse for updates.

        Returns:
            tuple[int, str]: Sequential event ID and formatted protocol line.

        Usage example:
            eid, line = emitter.emit_important_event(1000, 'Nuke active')
        """
        if event_id is None:
            event_id = self.next_important_event_id()
        line = self.emit(
            DATA_TYPE_IMPORTANT_EVENT,
            time_ms,
            event_id,
            message,
        )
        return event_id, line

    def emit(
        self,
        event_type: int,
        time_ms: int,
        *values: str | int,
    ) -> str:
        """Formats and broadcasts a protocol data line.

        Prints the line if log_output is enabled, records it in history, and
        notifies all active listeners.

        Args:
            event_type: Protocol numerical data type identifier.
            time_ms: Elapsed game time in milliseconds.
            *values: Sequence of string or integer payload fields.

        Returns:
            str: Tab-delimited protocol line without trailing newline.

        Usage example:
            line = emitter.emit(1, 0, 1, 100)
            assert line == '1\\t0\\t1\\t100'
        """
        parts = [str(event_type), str(time_ms)]
        parts.extend(str(v) for v in values)
        line = '\t'.join(parts)

        if self.log_output:
            print(line)

        self.emitted_lines.append(line)

        for listener in self.listeners:
            listener(line)

        return line

    def generate_presync_events(self, game_state: LiveGameState) -> list[str]:
        """Generates all snapshot events to synchronize a newly connected client.

        Followed by PRESYNC_END (Type 24).

        Args:
            game_state: Current active or reconstructed LiveGameState.

        Returns:
            list[str]: Complete list of protocol lines for initial sync.

        Usage example:
            events = emitter.generate_presync_events(state)
            assert events[-1].startswith('24\\t')
        """
        events: list[str] = []
        cur_ms = game_state.current_time_ms

        events.append(f'{DATA_TYPE_NEW_GAME}\t{cur_ms}')
        events.append(
            f'{DATA_TYPE_GAME_TYPE}\t{cur_ms}\t{game_state.game_type}\t'
            f'{game_state.duration_seconds}'
        )
        if game_state.start_time:
            events.append(
                f'{DATA_TYPE_GAME_START_TIME}\t{cur_ms}\t{game_state.start_time}'
            )
        if game_state.center_id:
            events.append(
                f'{DATA_TYPE_CENTER_INFO}\t{cur_ms}\t{game_state.center_id}\t'
                f'{game_state.center_name}'
            )

        for team in game_state.teams.values():
            events.append(
                f'{DATA_TYPE_TEAM_DESCRIPTION}\t{cur_ms}\t{team.team_id}\t'
                f'{team.name}\t{team.rgb}\t{team.dummy_player_id}'
            )

        for target in game_state.targets.values():
            events.append(
                f'{DATA_TYPE_BASE_DESCRIPTION}\t{cur_ms}\t{target.target_id}\t'
                f'{target.name}\t{target.rgb}'
            )

        for player in game_state.players.values():
            events.append(
                f'{DATA_TYPE_PLAYER_DESCRIPTION}\t{cur_ms}\t{player.player_id}\t'
                f'{player.name}\t{player.entity_id}\t{player.team_id}\t'
                f'{player.role}'
            )
            events.append(
                f'{DATA_TYPE_PLAYER_LIVES}\t{cur_ms}\t{player.player_id}\t'
                f'{player.lives}'
            )
            events.append(
                f'{DATA_TYPE_PLAYER_SHOTS}\t{cur_ms}\t{player.player_id}\t'
                f'{player.shots}'
            )
            events.append(
                f'{DATA_TYPE_PLAYER_MISSILES}\t{cur_ms}\t{player.player_id}\t'
                f'{player.missiles}'
            )
            events.append(
                f'{DATA_TYPE_PLAYER_SPECIAL_POINTS}\t{cur_ms}\t'
                f'{player.player_id}\t{player.special_points}'
            )
            events.append(
                f'{DATA_TYPE_PLAYER_HITPOINTS}\t{cur_ms}\t{player.player_id}\t'
                f'{player.hitpoints}'
            )
            events.append(
                f'{DATA_TYPE_PLAYER_STATE}\t{cur_ms}\t{player.player_id}\t'
                f'{player.state}'
            )
            events.append(
                f'{DATA_TYPE_PLAYER_SCORE}\t{cur_ms}\t{player.player_id}\t'
                f'{player.score}'
            )
            if player.rapid_fire:
                events.append(
                    f'{DATA_TYPE_RAPID_FIRE_STATE}\t{cur_ms}\t'
                    f'{player.player_id}\t1'
                )

        for team in game_state.teams.values():
            dummy = game_state.dummy_players.get(team.team_id)
            if dummy:
                events.append(
                    f'{DATA_TYPE_PLAYER_LIVES}\t{cur_ms}\t{dummy.player_id}\t'
                    f'{dummy.lives}'
                )
                events.append(
                    f'{DATA_TYPE_PLAYER_SHOTS}\t{cur_ms}\t{dummy.player_id}\t'
                    f'{dummy.shots}'
                )
                events.append(
                    f'{DATA_TYPE_PLAYER_MISSILES}\t{cur_ms}\t{dummy.player_id}\t'
                    f'{dummy.missiles}'
                )
                events.append(
                    f'{DATA_TYPE_PLAYER_SPECIAL_POINTS}\t{cur_ms}\t'
                    f'{dummy.player_id}\t{dummy.special_points}'
                )
                events.append(
                    f'{DATA_TYPE_PLAYER_HITPOINTS}\t{cur_ms}\t{dummy.player_id}\t'
                    f'{dummy.hitpoints}'
                )
                events.append(
                    f'{DATA_TYPE_PLAYER_SCORE}\t{cur_ms}\t{dummy.player_id}\t'
                    f'{dummy.score}'
                )

        for team in game_state.teams.values():
            events.append(
                f'{DATA_TYPE_TEAM_SCORE}\t{cur_ms}\t{team.team_id}\t{team.score}'
            )

        player_rankings = game_state.update_player_rankings()
        for team_id, p_ranks in player_rankings.items():
            if p_ranks:
                events.append(
                    f'{DATA_TYPE_PLAYER_RANKING}\t{cur_ms}\t{team_id}\t'
                    f'{",".join(str(p) for p in p_ranks)}'
                )

        team_ranking = game_state.get_team_ranking()
        if team_ranking:
            events.append(
                f'{DATA_TYPE_TEAM_RANKING}\t{cur_ms}\t'
                f'{",".join(str(t) for t in team_ranking)}'
            )

        if game_state.ball_carrier_id is not None:
            events.append(
                f'{DATA_TYPE_BALL_CARRIER}\t{cur_ms}\t'
                f'{game_state.ball_carrier_id}'
            )

        events.append(f'{DATA_TYPE_PRESYNC_END}\t{cur_ms}')
        return events
