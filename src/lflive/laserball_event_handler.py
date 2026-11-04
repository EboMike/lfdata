"""Laserball event processor for lflive.

This module provides `LaserballEventHandler`, which handles in-game Laserball
actions (rounds, possession, scoring, contests) and emits protocol events.

Usage example:
    from lflive.emitter import OutputEmitter
    from lflive.laserball_event_handler import LaserballEventHandler
    from lflive.state.game_state import LiveGameState

    state = LiveGameState(game_type='Laserball')
    emitter = OutputEmitter()
    handler = LaserballEventHandler(game_state=state, emitter=emitter)
    handler.handle_event(1000, '1105', [])
"""

from typing import TYPE_CHECKING

from lfdata.model.gametypes.laserball_events import (
    LASERBALL_EVENT_ASSIST,
    LASERBALL_EVENT_BLOCK,
    LASERBALL_EVENT_CLEAR,
    LASERBALL_EVENT_GETS_BALL,
    LASERBALL_EVENT_GOAL,
    LASERBALL_EVENT_PASS,
    LASERBALL_EVENT_ROUND_END,
    LASERBALL_EVENT_ROUND_START,
    LASERBALL_EVENT_STEAL,
)
from lflive.constants import (
    DATA_TYPE_BALL_CARRIER,
    DATA_TYPE_EVENT_SCROLLER,
    DATA_TYPE_PLAYER_ASSISTS,
    DATA_TYPE_PLAYER_BLOCKS,
    DATA_TYPE_PLAYER_GOALS,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_STATE,
    DATA_TYPE_PLAYER_STEALS,
    DATA_TYPE_ROUND_BEGINS,
    DATA_TYPE_ROUND_END,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.emitter import OutputEmitter, format_colored_name
from lflive.state.game_state import LiveGameState
from lflive.state.player_state import LivePlayerState

if TYPE_CHECKING:
    from lflive.ranking_manager import RankingManager


class LaserballEventHandler:
    """Processes Laserball-specific game events and emits protocol updates.

    Attributes:
        game_state: The active LiveGameState container.
        emitter: Optional OutputEmitter for consumer protocol events.
        ranking_manager: Optional RankingManager for ranking updates.
    """

    def __init__(
        self,
        game_state: LiveGameState,
        emitter: OutputEmitter | None = None,
        ranking_manager: 'RankingManager | None' = None,
    ) -> None:
        """Initializes the Laserball event handler.

        Args:
            game_state: Active LiveGameState instance.
            emitter: Optional OutputEmitter instance.
            ranking_manager: Optional RankingManager instance.
        """
        self.game_state = game_state
        self.emitter = emitter
        self.ranking_manager = ranking_manager

    def _colored_player(self, player: LivePlayerState | None) -> str:
        """Returns player name wrapped in HTML team color font tag."""
        if not player:
            return 'Unknown'
        team = self.game_state.teams.get(player.team_id)
        rgb = team.rgb if team else None
        return format_colored_name(name=player.name, rgb=rgb)

    def _extract_target_entity_id(self, varies: list[str]) -> str | None:
        """Extracts the target entity ID from variable event arguments.

        Args:
            varies: Variable arguments list from TDF record type 4.

        Returns:
            str | None: The target entity ID string if present, else None.
        """
        if len(varies) >= 3:
            return varies[2].strip()
        if len(varies) == 2:
            candidate = varies[1].strip()
            if (
                candidate.startswith(('#', '@'))
                or candidate in self.game_state.players_by_entity
                or candidate in self.game_state.targets_by_entity
            ):
                return candidate
        return None

    def handle_event(
        self,
        time_ms: int,
        code: str,
        varies: list[str],
    ) -> None:
        """Dispatches Laserball events by event category.

        Args:
            time_ms: Elapsed game time in milliseconds.
            code: 4-character event code string.
            varies: Variable event argument list.

        Usage example:
            handler.handle_event(1000, '1105', [])
        """
        if code == LASERBALL_EVENT_ROUND_START:
            self._handle_round_start(time_ms=time_ms)
        elif code == LASERBALL_EVENT_ROUND_END:
            self._handle_round_end(time_ms=time_ms)
        elif code in (LASERBALL_EVENT_GETS_BALL, LASERBALL_EVENT_PASS):
            self._handle_possession(time_ms=time_ms, code=code, varies=varies)
        elif code in (LASERBALL_EVENT_GOAL, LASERBALL_EVENT_ASSIST):
            self._handle_scoring(time_ms=time_ms, code=code, varies=varies)
        elif code in (
            LASERBALL_EVENT_BLOCK,
            LASERBALL_EVENT_STEAL,
            LASERBALL_EVENT_CLEAR,
        ):
            self._handle_contest(time_ms=time_ms, code=code, varies=varies)

    def _handle_round_start(self, time_ms: int) -> None:
        """Handles round begin lifecycle."""
        self.game_state.is_in_round = True
        if self.emitter:
            self.emitter.emit(DATA_TYPE_ROUND_BEGINS, time_ms)
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER, time_ms, '* Round Begins *'
            )
        if self.ranking_manager:
            self.ranking_manager.update_rankings(time_ms=time_ms)

    def _handle_round_end(self, time_ms: int) -> None:
        """Handles round finish lifecycle."""
        self.game_state.is_in_round = False
        self.game_state.round_number += 1
        if self.emitter:
            self.emitter.emit(DATA_TYPE_ROUND_END, time_ms)
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER, time_ms, '* Round End *'
            )

    def _handle_possession(
        self,
        time_ms: int,
        code: str,
        varies: list[str],
    ) -> None:
        """Handles Laserball ball pickups and passes."""
        if not varies:
            return
        if code == LASERBALL_EVENT_GETS_BALL:
            carrier = self.game_state.get_player_by_entity(entity_id=varies[0])
            if carrier:
                self.game_state.ball_carrier_id = carrier.player_id
                self.game_state.record_change(
                    time_ms,
                    'game',
                    0,
                    'ball_carrier_id',
                    str(carrier.player_id),
                )
                if self.emitter:
                    self.emitter.emit(
                        DATA_TYPE_BALL_CARRIER, time_ms, carrier.player_id
                    )
                    self.emitter.emit(
                        DATA_TYPE_EVENT_SCROLLER,
                        time_ms,
                        f'{self._colored_player(carrier)} gets the ball',
                    )
        elif code == LASERBALL_EVENT_PASS:
            target_id = self._extract_target_entity_id(varies=varies)
            carrier = (
                self.game_state.get_player_by_entity(entity_id=target_id)
                if target_id
                else None
            )
            actor = self.game_state.get_player_by_entity(entity_id=varies[0])
            if carrier:
                self.game_state.ball_carrier_id = carrier.player_id
                self.game_state.record_change(
                    time_ms,
                    'game',
                    0,
                    'ball_carrier_id',
                    str(carrier.player_id),
                )
                if self.emitter:
                    self.emitter.emit(
                        DATA_TYPE_BALL_CARRIER, time_ms, carrier.player_id
                    )
                    act_txt = self._colored_player(actor)
                    car_txt = self._colored_player(carrier)
                    self.emitter.emit(
                        DATA_TYPE_EVENT_SCROLLER,
                        time_ms,
                        f'{act_txt} passes to {car_txt}',
                    )

    def _handle_scoring(
        self,
        time_ms: int,
        code: str,
        varies: list[str],
    ) -> None:
        """Handles Laserball goal and assist events."""
        if not varies:
            return
        player = self.game_state.get_player_by_entity(entity_id=varies[0])
        if not player:
            return
        if code == LASERBALL_EVENT_GOAL:
            player.goals += 1
            self.game_state.ball_carrier_id = None
            self.game_state.record_change(
                time_ms, 'player', player.player_id, 'goals', str(player.goals)
            )
            self.game_state.record_change(
                time_ms, 'game', 0, 'ball_carrier_id', '0'
            )
            self.game_state.update_team_scores()
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_GOALS,
                    time_ms,
                    player.player_id,
                    player.goals,
                )
                self.emitter.emit(DATA_TYPE_BALL_CARRIER, time_ms, 0)
                team = self.game_state.teams.get(player.team_id)
                if team:
                    self.emitter.emit(
                        DATA_TYPE_TEAM_SCORE, time_ms, team.team_id, team.score
                    )
                self.emitter.emit(
                    DATA_TYPE_EVENT_SCROLLER,
                    time_ms,
                    f'{self._colored_player(player)} scores a goal',
                )
        elif code == LASERBALL_EVENT_ASSIST:
            player.assists += 1
            self.game_state.record_change(
                time_ms,
                'player',
                player.player_id,
                'assists',
                str(player.assists),
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_ASSISTS,
                    time_ms,
                    player.player_id,
                    player.assists,
                )
                self.emitter.emit(
                    DATA_TYPE_EVENT_SCROLLER,
                    time_ms,
                    f'{self._colored_player(player)} gets an assist',
                )
        if self.ranking_manager:
            self.ranking_manager.update_rankings(time_ms=time_ms)

    def _handle_contest(
        self,
        time_ms: int,
        code: str,
        varies: list[str],
    ) -> None:
        """Handles Laserball blocks, steals, and clears."""
        if not varies:
            return
        actor = self.game_state.get_player_by_entity(entity_id=varies[0])
        target_id = self._extract_target_entity_id(varies=varies)
        target = (
            self.game_state.get_player_by_entity(entity_id=target_id)
            if target_id
            else None
        )

        if code == LASERBALL_EVENT_BLOCK and actor:
            self._handle_block(time_ms=time_ms, actor=actor, target=target)
        elif code == LASERBALL_EVENT_STEAL and actor:
            self._handle_steal(time_ms=time_ms, actor=actor, target=target)
        elif code == LASERBALL_EVENT_CLEAR and actor:
            self._handle_clear(time_ms=time_ms, actor=actor, target=target)

        if self.ranking_manager:
            self.ranking_manager.update_rankings(time_ms=time_ms)

    def _record_shot(
        self, time_ms: int, actor: LivePlayerState, hit: bool
    ) -> None:
        """Records a fired shot and broadcasts updated stats.

        Args:
            time_ms: Elapsed game time in milliseconds.
            actor: Player state firing the shot.
            hit: True if the shot hit an entity, False if missed.
        """
        actor.shots_fired += 1
        if hit:
            actor.shots_hit += 1
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_SHOTS,
                time_ms,
                actor.player_id,
                actor.shots,
                actor.shots_fired,
                actor.shots_hit,
                actor.get_accuracy_string(),
            )

    def _handle_block(
        self,
        time_ms: int,
        actor: LivePlayerState,
        target: LivePlayerState | None,
    ) -> None:
        """Handles Laserball block."""
        actor.blocks += 1
        self._record_shot(time_ms=time_ms, actor=actor, hit=True)
        self.game_state.record_change(
            time_ms, 'player', actor.player_id, 'blocks', str(actor.blocks)
        )
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_BLOCKS, time_ms, actor.player_id, actor.blocks
            )
        if target:
            target.state = 3
            self.game_state.record_change(
                time_ms, 'player', target.player_id, 'state', '3'
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_STATE, time_ms, target.player_id, 3
                )
        if self.emitter:
            act_str = self._colored_player(actor)
            tar_str = self._colored_player(target)
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_str} blocks {tar_str}',
            )

    def _handle_steal(
        self,
        time_ms: int,
        actor: LivePlayerState,
        target: LivePlayerState | None,
    ) -> None:
        """Handles Laserball steal."""
        actor.steals += 1
        self._record_shot(time_ms=time_ms, actor=actor, hit=True)
        self.game_state.ball_carrier_id = actor.player_id
        self.game_state.record_change(
            time_ms, 'player', actor.player_id, 'steals', str(actor.steals)
        )
        self.game_state.record_change(
            time_ms, 'game', 0, 'ball_carrier_id', str(actor.player_id)
        )
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_STEALS, time_ms, actor.player_id, actor.steals
            )
            self.emitter.emit(DATA_TYPE_BALL_CARRIER, time_ms, actor.player_id)
        if target:
            target.state = 3
            self.game_state.record_change(
                time_ms, 'player', target.player_id, 'state', '3'
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_STATE, time_ms, target.player_id, 3
                )
        if self.emitter:
            act_str = self._colored_player(actor)
            tar_str = self._colored_player(target)
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_str} steals from {tar_str}',
            )

    def _handle_clear(
        self,
        time_ms: int,
        actor: LivePlayerState,
        target: LivePlayerState | None,
    ) -> None:
        """Handles Laserball clear."""
        actor.clears += 1
        self._record_shot(time_ms=time_ms, actor=actor, hit=True)
        self.game_state.record_change(
            time_ms, 'player', actor.player_id, 'clears', str(actor.clears)
        )
        if self.emitter:
            act_str = self._colored_player(actor)
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER, time_ms, f'{act_str} clears'
            )
        if target:
            self.game_state.ball_carrier_id = target.player_id
            self.game_state.record_change(
                time_ms, 'game', 0, 'ball_carrier_id', str(target.player_id)
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_BALL_CARRIER, time_ms, target.player_id
                )
