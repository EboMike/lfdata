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

from typing import TYPE_CHECKING

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
    SM5_EVENT_MISS,
    SM5_EVENT_MISS_BASE,
    SM5_EVENT_MISSILE_BASE_DAMAGE,
    SM5_EVENT_MISSILE_BASE_DESTROY,
    SM5_EVENT_MISSILE_BASE_MISS,
    SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
    SM5_EVENT_MISSILE_DAMAGE_TEAM,
    SM5_EVENT_MISSILE_DOWN_OPPONENT,
    SM5_EVENT_MISSILE_DOWN_TEAM,
    SM5_EVENT_MISSILE_MISS,
    SM5_EVENT_PENALTY,
    SM5_EVENT_RESUPPLY_AMMO,
    SM5_EVENT_RESUPPLY_LIVES,
    SM5_EVENT_SHOT_EMPTY,
    SM5_EVENT_WARBOT_ZAP,
)
from lflive.constants import (
    DATA_TYPE_BASE_CAPTURED,
    DATA_TYPE_EVENT_SCROLLER,
    DATA_TYPE_MEDIC_HITS,
    DATA_TYPE_NUKES_ACTIVATED,
    DATA_TYPE_NUKES_DETONATED,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_RAPID_FIRE_STATE,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.emitter import OutputEmitter, format_colored_name
from lflive.state.game_state import LiveGameState
from lflive.state.player_state import LivePlayerState
from lflive.state.target_state import LiveTargetState

if TYPE_CHECKING:
    from lflive.ranking_manager import RankingManager


class SM5EventHandler:
    """Processes SM5-specific game events and emits protocol updates.

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
        """Initializes the SM5 event handler.

        Args:
            game_state: Active LiveGameState instance.
            emitter: Optional OutputEmitter instance.
            ranking_manager: Optional RankingManager instance.
        """
        self.game_state = game_state
        self.emitter = emitter
        self.ranking_manager = ranking_manager
        self._active_nuke_event_ids: dict[int, int] = {}
        self._next_event_id_counter: int = 1

    def reset(self) -> None:
        """Resets active power state trackers and sequential ID counters.

        Usage example:
            handler.reset()
        """
        self._active_nuke_event_ids.clear()
        self._next_event_id_counter = 1

    def _allocate_event_id(self) -> int:
        """Allocates a sequential event ID from emitter or local counter.

        Returns:
            int: Sequential unique event identifier.
        """
        if self.emitter:
            return self.emitter.next_important_event_id()
        eid = self._next_event_id_counter
        self._next_event_id_counter += 1
        return eid

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
        actor.nukes_activated += 1
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
            self.emitter.emit(
                DATA_TYPE_NUKES_ACTIVATED,
                time_ms,
                actor.player_id,
                actor.nukes_activated,
            )
            msg = f'{self._colored_player(actor)} activates nuke'
            self.emitter.emit(DATA_TYPE_EVENT_SCROLLER, time_ms, msg)
            event_id = self._allocate_event_id()
            self._active_nuke_event_ids[actor.player_id] = event_id
            self.emitter.emit_important_event(
                time_ms=time_ms,
                message=msg,
                event_id=event_id,
            )

    def _handle_nuke_detonate(
        self, time_ms: int, actor: LivePlayerState
    ) -> None:
        """Handles nuke detonation."""
        actor.score += SM5_SCORE_NUKE_DETONATE
        actor.nukes_detonated += 1
        self.game_state.record_change(
            time_ms, 'player', actor.player_id, 'score', str(actor.score)
        )
        self.game_state.update_team_scores()
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_SCORE, time_ms, actor.player_id, actor.score
            )
            self.emitter.emit(
                DATA_TYPE_NUKES_DETONATED,
                time_ms,
                actor.player_id,
                actor.nukes_detonated,
            )
            team = self.game_state.teams.get(actor.team_id)
            if team:
                self.emitter.emit(
                    DATA_TYPE_TEAM_SCORE, time_ms, team.team_id, team.score
                )
            msg = f'{self._colored_player(actor)} detonates nuke'
            self.emitter.emit(DATA_TYPE_EVENT_SCROLLER, time_ms, msg)
            event_id = self._active_nuke_event_ids.pop(actor.player_id, None)
            if event_id is None:
                event_id = self._allocate_event_id()
            self.emitter.emit_important_event(
                time_ms=time_ms,
                message=msg,
                event_id=event_id,
            )
            self._cancel_enemy_nukes(time_ms=time_ms, nuking_actor=actor)

        # Record enemy medic lives taken by nuke
        medic_nukes_added = 0
        for enemy in self.game_state.players.values():
            if (
                enemy.team_id != actor.team_id
                and enemy.role.lower() == 'medic'
                and enemy.lives > 0
            ):
                medic_nukes_added += min(3, enemy.lives)
        if medic_nukes_added > 0:
            actor.medic_nukes += medic_nukes_added
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_MEDIC_HITS,
                    time_ms,
                    actor.player_id,
                    actor.get_formatted_medic_hits(),
                )

        if self.ranking_manager:
            self.ranking_manager.update_rankings(time_ms=time_ms)

    def _cancel_enemy_nukes(
        self,
        time_ms: int,
        nuking_actor: LivePlayerState,
    ) -> None:
        """Cancels in-flight active nukes belonging to opponent teams.

        Args:
            time_ms: Elapsed game time in milliseconds.
            nuking_actor: Player state of the commander detonating a nuke.
        """
        if not self.emitter:
            return
        for other_pid, other_eid in list(self._active_nuke_event_ids.items()):
            other_player = self.game_state.players.get(other_pid)
            if other_player and other_player.team_id != nuking_actor.team_id:
                del self._active_nuke_event_ids[other_pid]
                cancel_msg = (
                    f"{self._colored_player(other_player)}'s nuke "
                    'canceled by enemy nuke'
                )
                self.emitter.emit_important_event(
                    time_ms=time_ms,
                    message=cancel_msg,
                    event_id=other_eid,
                )

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

        if code in (SM5_EVENT_DESTROY_BASE, SM5_EVENT_HIT_BASE):
            self._record_shot(time_ms=time_ms, actor=actor, hit=True)
        elif code in (
            SM5_EVENT_MISSILE_BASE_DAMAGE,
            SM5_EVENT_MISSILE_BASE_DESTROY,
        ):
            self._record_missile(time_ms=time_ms, actor=actor, landed=True)

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
            if self.ranking_manager:
                self.ranking_manager.update_rankings(time_ms=time_ms)
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

    def _record_missile(
        self, time_ms: int, actor: LivePlayerState, landed: bool
    ) -> None:
        """Records a fired missile and broadcasts updated stats.

        Args:
            time_ms: Elapsed game time in milliseconds.
            actor: Player state firing the missile.
            landed: True if the missile hit an entity, False if missed.
        """
        actor.missiles_fired += 1
        if landed:
            actor.missiles_landed += 1
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_MISSILES,
                time_ms,
                actor.player_id,
                actor.missiles,
                actor.missiles_fired,
                actor.missiles_landed,
            )

    def _record_medic_hit(
        self,
        time_ms: int,
        actor: LivePlayerState,
        target: LivePlayerState | None,
        is_missile: bool,
    ) -> None:
        """Records hit against a medic and broadcasts updated stats.

        Args:
            time_ms: Elapsed game time in milliseconds.
            actor: Player state delivering the hit.
            target: Hit player state.
            is_missile: True if delivered by a missile, False if by zap.
        """
        if not target or target.role.lower() != 'medic':
            return
        inc = (2 if target.lives > 1 else 1) if is_missile else 1
        if target.team_id != actor.team_id:
            actor.enemy_medic_hits += inc
        else:
            actor.own_medic_hits += inc
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_MEDIC_HITS,
                time_ms,
                actor.player_id,
                actor.get_formatted_medic_hits(),
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

        if code in (
            SM5_EVENT_DAMAGED_OPPONENT,
            SM5_EVENT_DOWNED_OPPONENT,
            SM5_EVENT_DAMAGED_TEAM,
            SM5_EVENT_DOWNED_TEAM,
            SM5_EVENT_WARBOT_ZAP,
        ):
            self._record_shot(time_ms=time_ms, actor=actor, hit=True)
            self._record_medic_hit(
                time_ms=time_ms, actor=actor, target=target, is_missile=False
            )
        elif code in (
            SM5_EVENT_MISS,
            SM5_EVENT_MISS_BASE,
            SM5_EVENT_SHOT_EMPTY,
        ):
            self._record_shot(time_ms=time_ms, actor=actor, hit=False)
        elif code in (
            SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
            SM5_EVENT_MISSILE_DOWN_OPPONENT,
            SM5_EVENT_MISSILE_DAMAGE_TEAM,
            SM5_EVENT_MISSILE_DOWN_TEAM,
        ):
            self._record_missile(time_ms=time_ms, actor=actor, landed=True)
            self._record_medic_hit(
                time_ms=time_ms, actor=actor, target=target, is_missile=True
            )
        elif code in (SM5_EVENT_MISSILE_MISS, SM5_EVENT_MISSILE_BASE_MISS):
            self._record_missile(time_ms=time_ms, actor=actor, landed=False)

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
            self._check_nuke_cancel_on_down(
                time_ms=time_ms, actor=actor, target=target
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
            self._check_nuke_cancel_on_down(
                time_ms=time_ms, actor=actor, target=target
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
            self._check_nuke_cancel_on_down(
                time_ms=time_ms, actor=actor, target=target
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
            self._check_nuke_cancel_on_down(
                time_ms=time_ms, actor=actor, target=target
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

    def _check_nuke_cancel_on_down(
        self,
        time_ms: int,
        actor: LivePlayerState,
        target: LivePlayerState | None,
    ) -> None:
        """Cancels an in-flight nuke if the target commander is downed.

        Args:
            time_ms: Elapsed game time in milliseconds.
            actor: Player state who downed the commander.
            target: Downed player state.
        """
        if not self.emitter or not target:
            return
        if target.player_id not in self._active_nuke_event_ids:
            return
        event_id = self._active_nuke_event_ids.pop(target.player_id)
        cancel_msg = (
            f"{self._colored_player(target)}'s nuke canceled by "
            f'{self._colored_player(actor)}'
        )
        self.emitter.emit_important_event(
            time_ms=time_ms,
            message=cancel_msg,
            event_id=event_id,
        )
