"""Space Marines 5 (SM5) game event processor for lflive.

This module provides `SM5EventHandler`, which handles in-game SM5 actions
(powers, base destructions, combat zaps, missiles, resupplies, penalties) and
emits protocol events.

Usage example:
    from lflive.emitter import OutputEmitter
    from lflive.sm5_event_handler import SM5EventHandler
    from lflive.state.game_state import LiveGameState

    state = LiveGameState(game_type='SM5')
    emitter = OutputEmitter()
    handler = SM5EventHandler(game_state=state, emitter=emitter)
    handler.handle_event(1000, '0400', ['#P1'])
"""

from lfdata.model.gametypes.sm5_constants import (
    SM5_BASE_CAPTURE_SCORE,
    SM5_BASE_CAPTURE_SPECIAL_POINTS,
    SM5_MAX_SPECIAL_POINTS,
    SM5_SCORE_NUKE_DETONATE,
    SM5_SPECIAL_POINTS_NUKE,
)
from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_ACTIVATE_NUKE,
    SM5_EVENT_ACTIVATE_RAPID_FIRE,
    SM5_EVENT_DAMAGED_OPPONENT,
    SM5_EVENT_DAMAGED_TEAM,
    SM5_EVENT_DEACTIVATE_RAPID_FIRE,
    SM5_EVENT_DESTROY_BASE,
    SM5_EVENT_DETONATE_NUKE,
    SM5_EVENT_DOWNED_OPPONENT,
    SM5_EVENT_DOWNED_TEAM,
    SM5_EVENT_HIT_BASE,
    SM5_EVENT_MISSILE_BASE_DAMAGE,
    SM5_EVENT_MISSILE_BASE_DESTROY,
    SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
    SM5_EVENT_MISSILE_DAMAGE_TEAM,
    SM5_EVENT_MISSILE_DOWN_OPPONENT,
    SM5_EVENT_MISSILE_DOWN_TEAM,
    SM5_EVENT_PENALTY,
    SM5_EVENT_RESUPPLY_AMMO,
    SM5_EVENT_RESUPPLY_LIVES,
)
from lflive.constants import (
    DATA_TYPE_BASE_CAPTURED,
    DATA_TYPE_EVENT_SCROLLER,
    DATA_TYPE_IMPORTANT_EVENT,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_RAPID_FIRE_STATE,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.emitter import OutputEmitter, format_colored_name
from lflive.state.game_state import LiveGameState
from lflive.state.player_state import LivePlayerState
from lflive.state.target_state import LiveTargetState


class SM5EventHandler:
    """Processes SM5-specific game events and emits protocol updates.

    Attributes:
        game_state: The active LiveGameState container.
        emitter: Optional OutputEmitter for consumer protocol events.
    """

    def __init__(
        self,
        game_state: LiveGameState,
        emitter: OutputEmitter | None = None,
    ) -> None:
        """Initializes the SM5 event handler.

        Args:
            game_state: Active LiveGameState instance.
            emitter: Optional OutputEmitter instance.
        """
        self.game_state = game_state
        self.emitter = emitter

    def _colored_player(self, player: LivePlayerState | None) -> str:
        """Returns player name wrapped in HTML team color font tag."""
        if not player:
            return 'Unknown'
        team = self.game_state.teams.get(player.team_id)
        rgb = team.rgb if team else None
        return format_colored_name(name=player.name, rgb=rgb)

    def _colored_target(self, target: LiveTargetState | None) -> str:
        """Returns target name wrapped in HTML target color font tag."""
        if not target:
            return 'base'
        return format_colored_name(name=target.name, rgb=target.rgb)

    def handle_event(
        self,
        time_ms: int,
        code: str,
        varies: list[str],
    ) -> None:
        """Dispatches an incoming SM5 event to its specific category handler.

        Args:
            time_ms: Elapsed game time in milliseconds.
            code: 4-character event code string.
            varies: Variable event arguments.

        Usage example:
            handler.handle_event(1000, '0400', ['#P1'])
        """
        if not varies:
            return
        actor = self.game_state.get_player_by_entity(entity_id=varies[0])
        if not actor:
            return

        if code in (
            SM5_EVENT_ACTIVATE_RAPID_FIRE,
            SM5_EVENT_DEACTIVATE_RAPID_FIRE,
            SM5_EVENT_ACTIVATE_NUKE,
            SM5_EVENT_DETONATE_NUKE,
        ):
            self._handle_powers(time_ms=time_ms, code=code, actor=actor)
        elif code in (
            SM5_EVENT_DESTROY_BASE,
            SM5_EVENT_MISSILE_BASE_DESTROY,
            SM5_EVENT_HIT_BASE,
            SM5_EVENT_MISSILE_BASE_DAMAGE,
        ):
            self._handle_bases(
                time_ms=time_ms, code=code, actor=actor, varies=varies
            )
        else:
            self._handle_combat(
                time_ms=time_ms, code=code, actor=actor, varies=varies
            )

    def _handle_powers(
        self,
        time_ms: int,
        code: str,
        actor: LivePlayerState,
    ) -> None:
        """Handles SM5 special powers (rapid fire and nukes)."""
        if code == SM5_EVENT_ACTIVATE_RAPID_FIRE:
            actor.rapid_fire = True
            self.game_state.record_change(
                time_ms, 'player', actor.player_id, 'rapid_fire', '1'
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_RAPID_FIRE_STATE, time_ms, actor.player_id, 1
                )
                self.emitter.emit(
                    DATA_TYPE_EVENT_SCROLLER,
                    time_ms,
                    f'{self._colored_player(actor)} activates rapid fire',
                )
        elif code == SM5_EVENT_DEACTIVATE_RAPID_FIRE:
            actor.rapid_fire = False
            self.game_state.record_change(
                time_ms, 'player', actor.player_id, 'rapid_fire', '0'
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_RAPID_FIRE_STATE, time_ms, actor.player_id, 0
                )
        elif code == SM5_EVENT_ACTIVATE_NUKE:
            self._handle_nuke_activate(time_ms=time_ms, actor=actor)
        elif code == SM5_EVENT_DETONATE_NUKE:
            self._handle_nuke_detonate(time_ms=time_ms, actor=actor)

    def _handle_nuke_activate(
        self, time_ms: int, actor: LivePlayerState
    ) -> None:
        """Handles nuke power activation."""
        actor.special_points = max(
            0, actor.special_points - SM5_SPECIAL_POINTS_NUKE
        )
        self.game_state.record_change(
            time_ms,
            'player',
            actor.player_id,
            'special_points',
            str(actor.special_points),
        )
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_SPECIAL_POINTS,
                time_ms,
                actor.player_id,
                actor.special_points,
            )
            msg = f'{self._colored_player(actor)} activates nuke'
            self.emitter.emit(DATA_TYPE_EVENT_SCROLLER, time_ms, msg)
            self.emitter.emit(DATA_TYPE_IMPORTANT_EVENT, time_ms, msg)

    def _handle_nuke_detonate(
        self, time_ms: int, actor: LivePlayerState
    ) -> None:
        """Handles nuke detonation."""
        actor.score += SM5_SCORE_NUKE_DETONATE
        self.game_state.record_change(
            time_ms, 'player', actor.player_id, 'score', str(actor.score)
        )
        self.game_state.update_team_scores()
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_SCORE, time_ms, actor.player_id, actor.score
            )
            team = self.game_state.teams.get(actor.team_id)
            if team:
                self.emitter.emit(
                    DATA_TYPE_TEAM_SCORE, time_ms, team.team_id, team.score
                )
            msg = f'{self._colored_player(actor)} detonates nuke'
            self.emitter.emit(DATA_TYPE_EVENT_SCROLLER, time_ms, msg)
            self.emitter.emit(DATA_TYPE_IMPORTANT_EVENT, time_ms, msg)

    def _extract_target_entity_id(self, varies: list[str]) -> str | None:
        """Extracts the target entity ID from variable event arguments.

        In standard TDF streams, variable arguments for two-entity interactions
        follow the pattern [actor_id, action_text, target_id]. For compatibility
        with abbreviated test payloads, [actor_id, target_id] is also supported.

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

    def _handle_bases(
        self,
        time_ms: int,
        code: str,
        actor: LivePlayerState,
        varies: list[str],
    ) -> None:
        """Handles SM5 base hits and base destructions."""
        target_id = self._extract_target_entity_id(varies=varies)
        target = (
            self.game_state.get_target_by_entity(target_id)
            if target_id
            else None
        )
        target_pk = target.target_id if target else 1
        t_name = self._colored_target(target)
        act_name = self._colored_player(actor)

        if code in (SM5_EVENT_DESTROY_BASE, SM5_EVENT_MISSILE_BASE_DESTROY):
            actor.score += SM5_BASE_CAPTURE_SCORE
            actor.special_points = min(
                SM5_MAX_SPECIAL_POINTS,
                actor.special_points + SM5_BASE_CAPTURE_SPECIAL_POINTS,
            )
            self.game_state.record_change(
                time_ms, 'player', actor.player_id, 'score', str(actor.score)
            )
            self.game_state.record_change(
                time_ms,
                'player',
                actor.player_id,
                'special_points',
                str(actor.special_points),
            )
            self.game_state.update_team_scores()
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_BASE_CAPTURED, time_ms, actor.player_id, target_pk
                )
                self.emitter.emit(
                    DATA_TYPE_PLAYER_SCORE,
                    time_ms,
                    actor.player_id,
                    actor.score,
                )
                self.emitter.emit(
                    DATA_TYPE_PLAYER_SPECIAL_POINTS,
                    time_ms,
                    actor.player_id,
                    actor.special_points,
                )
                team = self.game_state.teams.get(actor.team_id)
                if team:
                    self.emitter.emit(
                        DATA_TYPE_TEAM_SCORE, time_ms, team.team_id, team.score
                    )
                self.emitter.emit(
                    DATA_TYPE_EVENT_SCROLLER,
                    time_ms,
                    f'{act_name} destroys {t_name}',
                )
        elif code == SM5_EVENT_HIT_BASE and self.emitter:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} zaps {t_name}',
            )
        elif code == SM5_EVENT_MISSILE_BASE_DAMAGE and self.emitter:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} missiles {t_name}',
            )

    def _handle_combat(
        self,
        time_ms: int,
        code: str,
        actor: LivePlayerState,
        varies: list[str],
    ) -> None:
        """Handles SM5 zaps, missiles, resupplies, and penalties."""
        target_id = self._extract_target_entity_id(varies=varies)
        target = (
            self.game_state.get_player_by_entity(target_id)
            if target_id
            else None
        )
        if not self.emitter:
            return

        act_name = self._colored_player(actor)
        if target:
            tar_name = self._colored_player(target)
        else:
            target_obj = (
                self.game_state.get_target_by_entity(target_id)
                if target_id
                else None
            )
            if target_obj:
                tar_name = self._colored_target(target_obj)
            else:
                tar_name = 'Unknown'

        if code == SM5_EVENT_DAMAGED_OPPONENT:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} zaps {tar_name}',
            )
        elif code == SM5_EVENT_DOWNED_OPPONENT:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} downs {tar_name}',
            )
        elif code == SM5_EVENT_DAMAGED_TEAM:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} zaps teammate {tar_name}',
            )
        elif code == SM5_EVENT_DOWNED_TEAM:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} downs teammate {tar_name}',
            )
        elif code == SM5_EVENT_MISSILE_DAMAGE_OPPONENT:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} missiles {tar_name}',
            )
        elif code == SM5_EVENT_MISSILE_DOWN_OPPONENT:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} downs {tar_name} with missile',
            )
        elif code == SM5_EVENT_MISSILE_DAMAGE_TEAM:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} missiles teammate {tar_name}',
            )
        elif code == SM5_EVENT_MISSILE_DOWN_TEAM:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} downs teammate {tar_name} with missile',
            )
        elif code == SM5_EVENT_RESUPPLY_AMMO:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} resupplies ammo to {tar_name}',
            )
        elif code == SM5_EVENT_RESUPPLY_LIVES:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} resupplies lives to {tar_name}',
            )
        elif code == SM5_EVENT_PENALTY:
            self.emitter.emit(
                DATA_TYPE_EVENT_SCROLLER,
                time_ms,
                f'{act_name} gets a penalty',
            )
