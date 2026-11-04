"""Dummy player manager for lflive team aggregates.

This module provides `DummyPlayerManager`, which tracks and recalculates
team dummy players whose stats represent the sum of all actual players
on each team, broadcasting real-time protocol updates as values change.

Usage example:
    from lflive.dummy_player_manager import DummyPlayerManager
    from lflive.emitter import OutputEmitter
    from lflive.state.game_state import LiveGameState

    state = LiveGameState()
    emitter = OutputEmitter()
    manager = DummyPlayerManager(game_state=state, emitter=emitter)
"""

from typing import TYPE_CHECKING
from lflive.constants import (
    DATA_TYPE_PLAYER_ASSISTS,
    DATA_TYPE_PLAYER_BLOCKS,
    DATA_TYPE_PLAYER_GOALS,
    DATA_TYPE_PLAYER_HITPOINTS,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_PLAYER_STEALS,
    DATA_TYPE_NUKES_ACTIVATED,
    DATA_TYPE_NUKES_DETONATED,
)

if TYPE_CHECKING:
    from lflive.emitter import OutputEmitter
    from lflive.state.game_state import LiveGameState


STAT_TYPE_TO_ATTR: dict[int, str] = {
    DATA_TYPE_PLAYER_SCORE: 'score',
    DATA_TYPE_PLAYER_LIVES: 'lives',
    DATA_TYPE_PLAYER_SHOTS: 'shots',
    DATA_TYPE_PLAYER_SPECIAL_POINTS: 'special_points',
    DATA_TYPE_PLAYER_HITPOINTS: 'hitpoints',
    DATA_TYPE_PLAYER_MISSILES: 'missiles',
    DATA_TYPE_PLAYER_GOALS: 'goals',
    DATA_TYPE_PLAYER_ASSISTS: 'assists',
    DATA_TYPE_PLAYER_BLOCKS: 'blocks',
    DATA_TYPE_PLAYER_STEALS: 'steals',
    DATA_TYPE_NUKES_ACTIVATED: 'nukes_activated',
    DATA_TYPE_NUKES_DETONATED: 'nukes_detonated',
}


class DummyPlayerManager:
    """Coordinates calculation and broadcasting of team dummy player stats.

    Attributes:
        game_state: Active LiveGameState instance.
        emitter: Optional OutputEmitter instance for broadcasting.
    """

    def __init__(
        self,
        game_state: 'LiveGameState',
        emitter: 'OutputEmitter | None' = None,
    ) -> None:
        """Initializes the dummy player manager.

        Args:
            game_state: Active LiveGameState instance.
            emitter: Optional OutputEmitter for event dispatching.
        """
        self.game_state = game_state
        self.emitter = emitter

    def is_dummy_player(self, player_id: int) -> bool:
        """Checks if a given player ID belongs to a team dummy player.

        Inspects registered teams and dummy player mappings.

        Args:
            player_id: Numerical player primary key to test.

        Returns:
            bool: True if player_id is a dummy player, False otherwise.

        Usage example:
            if manager.is_dummy_player(101):
                ...
        """
        for team in self.game_state.teams.values():
            if team.dummy_player_id == player_id:
                return True
        for dummy in self.game_state.dummy_players.values():
            if dummy.player_id == player_id:
                return True
        return False

    def on_line_emitted(self, line: str) -> None:
        """Processes emitted protocol line to sync dummy player stats.

        When a player stat event is emitted, identifies the player's team,
        recalculates that specific stat sum, and emits a dummy player update
        if the aggregated value changed.

        Args:
            line: Tab-delimited protocol line without trailing newline.

        Usage example:
            manager.on_line_emitted('4\t1000\t1\t14')
        """
        parts = line.split('\t')
        if len(parts) < 4:
            return

        try:
            event_type = int(parts[0])
            time_ms = int(parts[1])
            player_id = int(parts[2])
        except ValueError:
            return

        if event_type not in STAT_TYPE_TO_ATTR:
            return

        if self.is_dummy_player(player_id=player_id):
            return

        player = self.game_state.players.get(player_id)
        if not player:
            return

        self.recalculate_stat(
            team_id=player.team_id,
            time_ms=time_ms,
            event_type=event_type,
        )

    def recalculate_stat(
        self,
        team_id: int,
        time_ms: int,
        event_type: int,
    ) -> None:
        """Recalculates a single stat for a team dummy player.

        Sums the stat across all active players on the team and emits an
        update event if the aggregated sum differs from the dummy's stat.

        Args:
            team_id: Numerical primary key of the team.
            time_ms: Elapsed game time in milliseconds.
            event_type: Protocol data type identifier for the stat.

        Usage example:
            manager.recalculate_stat(1, 1000, 4)
        """
        attr = STAT_TYPE_TO_ATTR.get(event_type)
        if not attr:
            return

        dummy = self.game_state.dummy_players.get(team_id)
        if not dummy:
            return

        team_players = [
            p for p in self.game_state.players.values() if p.team_id == team_id
        ]

        if event_type == DATA_TYPE_PLAYER_SHOTS:
            new_shots = sum(p.shots for p in team_players)
            new_fired = sum(p.shots_fired for p in team_players)
            new_hit = sum(p.shots_hit for p in team_players)
            changed = (
                dummy.shots != new_shots
                or dummy.shots_fired != new_fired
                or dummy.shots_hit != new_hit
            )
            if changed:
                dummy.shots = new_shots
                dummy.shots_fired = new_fired
                dummy.shots_hit = new_hit
                if self.emitter:
                    self.emitter.emit(
                        DATA_TYPE_PLAYER_SHOTS,
                        time_ms,
                        dummy.player_id,
                        dummy.shots,
                        dummy.shots_fired,
                        dummy.shots_hit,
                        dummy.get_accuracy_string(),
                    )
            return

        if event_type == DATA_TYPE_PLAYER_MISSILES:
            new_missiles = sum(p.missiles for p in team_players)
            new_fired = sum(p.missiles_fired for p in team_players)
            new_landed = sum(p.missiles_landed for p in team_players)
            changed = (
                dummy.missiles != new_missiles
                or dummy.missiles_fired != new_fired
                or dummy.missiles_landed != new_landed
            )
            if changed:
                dummy.missiles = new_missiles
                dummy.missiles_fired = new_fired
                dummy.missiles_landed = new_landed
                if self.emitter:
                    self.emitter.emit(
                        DATA_TYPE_PLAYER_MISSILES,
                        time_ms,
                        dummy.player_id,
                        dummy.missiles,
                        dummy.missiles_fired,
                        dummy.missiles_landed,
                    )
            return

        new_total = sum(getattr(p, attr, 0) for p in team_players)
        if getattr(dummy, attr) != new_total:
            setattr(dummy, attr, new_total)
            if self.emitter:
                self.emitter.emit(
                    event_type, time_ms, dummy.player_id, new_total
                )

    def recalculate_team(self, team_id: int, time_ms: int = 0) -> None:
        """Recalculates all stats for a specific team dummy player.

        Iterates through all supported stat types and emits changes.

        Args:
            team_id: Numerical primary key of the team.
            time_ms: Elapsed game time in milliseconds.

        Usage example:
            manager.recalculate_team(1, 0)
        """
        for event_type in STAT_TYPE_TO_ATTR:
            self.recalculate_stat(
                team_id=team_id,
                time_ms=time_ms,
                event_type=event_type,
            )

    def recalculate_all(self, time_ms: int = 0) -> None:
        """Recalculates all stats across all team dummy players.

        Iterates through all teams in game state.

        Args:
            time_ms: Elapsed game time in milliseconds.

        Usage example:
            manager.recalculate_all(0)
        """
        for team_id in list(self.game_state.teams.keys()):
            self.recalculate_team(team_id=team_id, time_ms=time_ms)

    def reset(self) -> None:
        """Resets manager state for a new session.

        Usage example:
            manager.reset()
        """
        pass
