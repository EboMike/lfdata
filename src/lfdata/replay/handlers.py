"""Mixin containing event handlers for the LF replay system.

This module defines event handler methods (zaps, misses, nukes, resupplies, base captures,
penalties) for processing individual `GameEvent` records during replay playback.

Usage example:
    # Used internally as a mixin by LFReplaySystem:
    # class LFReplaySystem(LFReplayHandlersMixin): ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from lfdata.model import GameEvent, LFRole
from lfdata.model.gametypes.sm5_constants import (
    DEFAULT_BOOST_GRACE_PERIOD_MS,
    DEFAULT_MISSION_PENALTY,
    SM5_BASE_CAPTURE_SCORE,
    SM5_BASE_CAPTURE_SPECIAL_POINTS,
    SM5_BEACON_CLAIM_SHOTS_LOST,
    SM5_DOWNTIME_SAFE_MS,
    SM5_DOWNTIME_TOTAL_MS,
    SM5_LIVES_LOST_MISSILED,
    SM5_LIVES_LOST_ZAPPED,
    SM5_NUKE_LIVES_LOST,
    SM5_SCORE_MISSILE_ENEMY,
    SM5_SCORE_MISSILE_TEAM,
    SM5_SCORE_MISSILED_PENALTY,
    SM5_SCORE_NUKE_DETONATE,
    SM5_SCORE_ZAP_ENEMY,
    SM5_SCORE_ZAP_TEAM,
    SM5_SCORE_ZAPPED_PENALTY,
    SM5_SPECIAL_POINTS_AMMO_BOOST,
    SM5_SPECIAL_POINTS_MEDIC_BOOST,
    SM5_SPECIAL_POINTS_MISSILE_ENEMY,
    SM5_SPECIAL_POINTS_NUKE,
    SM5_SPECIAL_POINTS_RAPID_FIRE,
    SM5_SPECIAL_POINTS_ZAP_ENEMY,
)

if TYPE_CHECKING:
    from lfdata.replay.replay import LFReplaySystem
    from lfdata.replay.state import LFReplayPlayerState


class LFReplayHandlersMixin:
    """Mixin class providing event processing dispatchers for LFReplaySystem.

    Encapsulates rules for handling zaps, missile hits, medic/ammo resupplies,
    base captures, nuke activations/detonations/cancels, and penalties.
    """

    def _process_event_zap(self: 'LFReplaySystem', event: GameEvent) -> str:
        """Processes zapping events.

        Args:
            event: The zapping event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        target = self.game_state.players.get(event.target_entity_id)

        self._decrement_shots(event.actor_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if (
            actor
            and target
            and not actor.is_eliminated()
            and not target.is_eliminated()
        ):
            target.times_zapped += 1
            if actor.team_index == target.team_index:
                # Friendly fire: penalize actor
                actor.score += SM5_SCORE_ZAP_TEAM
            else:
                actor.times_zapped_opponents += 1
                actor.score += SM5_SCORE_ZAP_ENEMY
                if (
                    not (actor.role == LFRole.SCOUT and actor.has_rapid_fire)
                    and actor.role != LFRole.HEAVY
                ):
                    actor.special_points += SM5_SPECIAL_POINTS_ZAP_ENEMY

            # Target always loses score (unless already eliminated)
            target.score += SM5_SCORE_ZAPPED_PENALTY

            # Check if target goes down or resets downtime
            if event.event_type in ['0206', '0208']:
                was_already_down = target.is_down(event.time)
                target.lives = max(0, target.lives - SM5_LIVES_LOST_ZAPPED)
                if target.has_authoritative_state:
                    target.update_downtime(event.time)
                else:
                    target.hp = 0
                    target.downtime_ends_at_ms = (
                        event.time + SM5_DOWNTIME_TOTAL_MS
                    )
                    target.resettable_starts_at_ms = (
                        event.time + SM5_DOWNTIME_SAFE_MS
                    )
                    if not was_already_down:
                        target.just_went_down_at_ms = event.time
            else:
                target.hp = max(1, target.hp - 1)

        return f'{actor_name} zaps {target_name}'

    def _process_event_missile(self: 'LFReplaySystem', event: GameEvent) -> str:
        """Processes missile zapping events.

        Args:
            event: The missile event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        target = self.game_state.players.get(event.target_entity_id)

        self._decrement_missiles(event.actor_entity_id)

        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if (
            actor
            and target
            and not actor.is_eliminated()
            and not target.is_eliminated()
        ):
            if actor.team_index == target.team_index:
                # Friendly fire missile: penalize actor
                actor.score += SM5_SCORE_MISSILE_TEAM
            else:
                actor.score += SM5_SCORE_MISSILE_ENEMY
                if (
                    not (actor.role == LFRole.SCOUT and actor.has_rapid_fire)
                    and actor.role != LFRole.HEAVY
                ):
                    actor.special_points += SM5_SPECIAL_POINTS_MISSILE_ENEMY

            # Target always loses score (unless already eliminated)
            target.score += SM5_SCORE_MISSILED_PENALTY

            # Missile immediately downs target or resets downtime
            was_already_down = target.is_down(event.time)
            target.lives = max(0, target.lives - SM5_LIVES_LOST_MISSILED)
            if target.has_authoritative_state:
                target.update_downtime(event.time)
            else:
                target.hp = 0
                target.downtime_ends_at_ms = event.time + SM5_DOWNTIME_TOTAL_MS
                target.resettable_starts_at_ms = (
                    event.time + SM5_DOWNTIME_SAFE_MS
                )
                if not was_already_down:
                    target.just_went_down_at_ms = event.time

        return f'{actor_name} missiles {target_name}'

    def _process_event_base_destroy(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str:
        """Processes base destruction/capture events.

        Args:
            event: The base destruction/capture event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if event.event_type == '0303':
            self._decrement_missiles(event.actor_entity_id)
        elif event.event_type == '0204':
            self._decrement_shots(event.actor_entity_id)

        target_entity = None
        for entity in self.game.entities:
            if entity.entity_id == event.target_entity_id:
                target_entity = entity
                break

        if actor and not actor.is_eliminated() and target_entity:
            if (
                target_entity.team_index != actor.team_index
                and event.target_entity_id not in actor.captured_bases
            ):
                actor.captured_bases.add(event.target_entity_id)
                actor.score += SM5_BASE_CAPTURE_SCORE
                if (
                    not (actor.role == LFRole.SCOUT and actor.has_rapid_fire)
                    and actor.role != LFRole.HEAVY
                ):
                    actor.special_points += SM5_BASE_CAPTURE_SPECIAL_POINTS

        if event.event_type == '0B03':
            return f'{actor_name} is awarded {target_name}'
        return f'{actor_name} destroys {target_name}'

    def _process_event_nuke_detonate(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str:
        """Processes nuke detonation events.

        Args:
            event: The nuke detonation event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )

        if actor and not actor.is_eliminated():
            actor.score += SM5_SCORE_NUKE_DETONATE
            actor.nukes_detonated += 1
            for player in self.game_state.players.values():
                if (
                    player.team_index != actor.team_index
                    and not player.is_eliminated()
                ):
                    was_already_down = player.is_down(event.time)
                    player.lives = max(0, player.lives - SM5_NUKE_LIVES_LOST)
                    if player.has_authoritative_state:
                        player.update_downtime(event.time)
                    else:
                        player.hp = 0
                        player.downtime_ends_at_ms = (
                            event.time + SM5_DOWNTIME_TOTAL_MS
                        )
                        player.resettable_starts_at_ms = (
                            event.time + SM5_DOWNTIME_SAFE_MS
                        )
                        if not was_already_down:
                            player.just_went_down_at_ms = event.time

        return f'{actor_name} detonates nuke'

    def _process_individual_resupply(
        self: 'LFReplaySystem',
        event: GameEvent,
        actor: 'LFReplayPlayerState' | None,
        actor_name: str,
        target_name: str,
    ) -> str:
        """Processes an individual resupply event.

        Args:
            event: The resupply event.
            actor: The actor player state.
            actor_name: Display name of the actor.
            target_name: Display name of the target.

        Returns:
            str: The event description string.
        """
        target = self.game_state.players.get(event.target_entity_id)
        if target and not target.is_eliminated():
            is_medic = event.event_type == '0502'
            if is_medic:
                target.resupply_lives_from_medic()
            else:
                target.resupply_shots_from_ammo()
            was_already_down = target.is_down(event.time)
            if target.has_authoritative_state:
                target.update_downtime(event.time)
            else:
                target.hp = 0
                target.downtime_ends_at_ms = event.time + SM5_DOWNTIME_TOTAL_MS
                target.resettable_starts_at_ms = (
                    event.time + SM5_DOWNTIME_SAFE_MS
                )
                if not was_already_down:
                    target.just_went_down_at_ms = event.time
            if target.role == LFRole.SCOUT:
                target.has_rapid_fire = False
        return f'{actor_name} resupplies {target_name}'

    def _process_team_resupply(
        self: 'LFReplaySystem',
        event: GameEvent,
        actor: 'LFReplayPlayerState' | None,
        actor_name: str,
    ) -> str:
        """Processes a team resupply event.

        Args:
            event: The resupply event.
            actor: The actor player state.
            actor_name: Display name of the actor.

        Returns:
            str: The event description string.
        """
        if actor:
            is_medic = event.event_type == '0512'
            if is_medic:
                actor.special_points = max(
                    0, actor.special_points - SM5_SPECIAL_POINTS_MEDIC_BOOST
                )
            else:
                actor.special_points = max(
                    0, actor.special_points - SM5_SPECIAL_POINTS_AMMO_BOOST
                )

            for player in self.game_state.players.values():
                if (
                    player.team_index == actor.team_index
                    and player.entity_id != actor.entity_id
                    and not player.is_eliminated()
                ):
                    default_val = player.can_receive_resupply(
                        event.time,
                        grace_period_ms=getattr(
                            self,
                            'boost_grace_period_ms',
                            DEFAULT_BOOST_GRACE_PERIOD_MS,
                        ),
                    )
                    is_ambig = self._is_player_boost_ambiguous(
                        player, event.time
                    )
                    if is_ambig:
                        key = (event.time, player.entity_id)
                        if key not in self._encountered_points:
                            self._encountered_points.append(key)
                        if key in self._resupply_choices:
                            should_boost = self._resupply_choices[key]
                        else:
                            should_boost = default_val

                        if should_boost != default_val:
                            self.resolved_ambiguities.append(
                                {
                                    'time_ms': event.time,
                                    'player_id': player.entity_id,
                                    'default': default_val,
                                    'chosen': should_boost,
                                    'event_type': event.event_type,
                                }
                            )
                    else:
                        should_boost = default_val

                    if should_boost:
                        if is_medic:
                            player.resupply_lives_from_medic()
                        else:
                            player.resupply_shots_from_ammo()
        return f'{actor_name} resupplies team'

    def _process_event_resupply(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str:
        """Processes resupply (ammo, lives, team boosts) events.

        Args:
            event: The resupply event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if actor and actor.is_eliminated():
            return ''

        if event.event_type in ('0500', '0502'):
            return self._process_individual_resupply(
                event=event,
                actor=actor,
                actor_name=actor_name,
                target_name=target_name,
            )

        if event.event_type in ('0510', '0512'):
            return self._process_team_resupply(
                event=event, actor=actor, actor_name=actor_name
            )

        return ''

    def _process_misc_mission_events(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str | None:
        """Processes miscellaneous mission start/end and penalty events.

        Args:
            event: The game event.

        Returns:
            str | None: The event description or None if not handled.
        """
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        if event.event_type == '0100':
            return '* Mission Start *'
        if event.event_type == '0101':
            return '* Mission End *'
        if event.event_type == '0600':
            actor = self.game_state.players.get(event.actor_entity_id)
            if actor and not actor.is_eliminated():
                gp = self.game.penalty
                penalty_val = gp if gp is not None else DEFAULT_MISSION_PENALTY
                actor.score += penalty_val
                actor.penalties += 1
                was_already_down = actor.is_down(event.time)
                if actor.has_authoritative_state:
                    actor.update_downtime(event.time)
                else:
                    actor.hp = 0
                    actor.downtime_ends_at_ms = (
                        event.time + SM5_DOWNTIME_TOTAL_MS
                    )
                    target_resettable = event.time + SM5_DOWNTIME_SAFE_MS
                    actor.resettable_starts_at_ms = target_resettable
                    if not was_already_down:
                        actor.just_went_down_at_ms = event.time
            return f'{actor_name} is penalized'
        return None

    def _process_misc_action_events(
        self: 'LFReplaySystem',
        event: GameEvent,
        actor_name: str,
        target_name: str,
    ) -> str | None:
        """Processes miscellaneous shot, lock, and missile events.

        Args:
            event: The game event.
            actor_name: The actor's display name.
            target_name: The target's display name.

        Returns:
            str | None: The event description or None if not handled.
        """
        if event.event_type == '0201':
            self._decrement_shots(event.actor_entity_id)
            return f'{actor_name} misses'
        if event.event_type == '0202':
            self._decrement_shots(event.actor_entity_id)
            return f'{actor_name} misses base'
        if event.event_type == '0203':
            self._decrement_shots(event.actor_entity_id)
            return f'{actor_name} zaps {target_name}'
        if event.event_type == '0209':
            return f'{actor_name} zaps {target_name}'
        if event.event_type == '0B00':
            self._decrement_shots(
                event.actor_entity_id, count=SM5_BEACON_CLAIM_SHOTS_LOST
            )
            return f'{actor_name} claims a beacon'
        if event.event_type == '0300':
            return f'{actor_name} locking {target_name}'
        if event.event_type == '0301':
            self._decrement_missiles(event.actor_entity_id)
            return f'{actor_name} misses base'
        if event.event_type == '0302':
            self._decrement_missiles(event.actor_entity_id)
            return f'{actor_name} zaps {target_name}'
        if event.event_type == '0304':
            self._decrement_missiles(event.actor_entity_id)
            return f'{actor_name} misses'
        return None

    def _process_event_other(self: 'LFReplaySystem', event: GameEvent) -> str:
        """Processes other miscellaneous events.

        Args:
            event: The miscellaneous event.

        Returns:
            str: The event description string.
        """
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        res_mission = self._process_misc_mission_events(event)
        if res_mission is not None:
            return res_mission

        res_action = self._process_misc_action_events(
            event, actor_name, target_name
        )
        if res_action is not None:
            return res_action

        if event.event_type == '0400':
            actor = self.game_state.players.get(event.actor_entity_id)
            if actor and not actor.is_eliminated():
                actor.special_points = max(
                    0, actor.special_points - SM5_SPECIAL_POINTS_RAPID_FIRE
                )
                actor.has_rapid_fire = True
            return f'{actor_name} activates rapid fire'
        if event.event_type == '0404':
            actor = self.game_state.players.get(event.actor_entity_id)
            if actor and not actor.is_eliminated():
                actor.special_points = max(
                    0, actor.special_points - SM5_SPECIAL_POINTS_NUKE
                )
                actor.nukes_activated += 1
            return f'{actor_name} activates nuke'
        if event.event_type == '0900':
            return f'{actor_name} completes an achievement!'
        if event.event_type == '0902':
            return f'{actor_name} earns a reward!'

        return event.action

    def _update_nuke_cancel_stats(
        self: 'LFReplaySystem',
        event: GameEvent,
        actor: 'LFReplayPlayerState',
    ) -> None:
        """Updates player statistics when a nuke is canceled.

        Args:
            event: The nuke cancel event.
            actor: The actor player state.
        """
        actor.own_nuke_cancels += 1

        if event.action == 'nuke cancel':
            # Find the zapping/missiling enemy event at the same time
            for ev in self.game.events:
                if (
                    ev.time == event.time
                    and ev.target_entity_id == actor.entity_id
                ):
                    if ev.event_type in ('0206', '0306'):
                        enemy = self.game_state.players.get(ev.actor_entity_id)
                        if enemy and not enemy.is_eliminated():
                            enemy.nuke_cancels += 1
                        break

    def _get_nuke_cancel_suffix(self, action: str) -> str:
        """Determines the nuke cancel suffix based on event action.

        Args:
            action: The nuke cancel action string.

        Returns:
            str: The nuke cancel description suffix.
        """
        if action == 'nuke cancel':
            return 'nuke canceled'
        if action == 'nuke cancel by friendly fire':
            return 'nuke canceled by friendly fire'
        if action == 'nuke cancel by own resup':
            return 'nuke canceled by own resup'
        if action == 'nuke cancel by enemy nuke':
            return 'nuke canceled by enemy nuke'
        if action == 'nuke activated too late':
            return 'nuke activated too late'
        return action

    def _process_event_nuke_cancel(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str:
        """Processes nuke cancel events and updates cancel statistics.

        Increments the commander's own_nuke_cancels count. If the cancel is due
        to being zapped or missiled by an enemy, it finds the event that caused
        the cancel and increments the zapper's nuke_cancels count. Then, returns
        the display string.

        Args:
            event: The nuke cancel event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )

        if actor and not actor.is_eliminated():
            self._update_nuke_cancel_stats(event=event, actor=actor)

        suffix = self._get_nuke_cancel_suffix(event.action)
        return f'{actor_name} {suffix}'

    def _apply_laserball_downtime(
        self: 'LFReplaySystem',
        target: 'LFReplayPlayerState',
        event_time: int,
    ) -> None:
        """Applies downtime to a player tagged in Laserball.

        Downtime is 8 seconds: 4 seconds safe, 4 seconds resettable.

        Args:
            target: The player entity state being downed.
            event_time: Millisecond timestamp when the tag occurred.
        """
        was_already_down = target.is_down(event_time)
        if target.has_authoritative_state:
            target.update_downtime(event_time)
        else:
            target.hp = 0
            target.downtime_ends_at_ms = event_time + 8000
            target.resettable_starts_at_ms = event_time + 4000
            if not was_already_down:
                target.just_went_down_at_ms = event_time

    def _process_laserball_round_events(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str | None:
        """Processes round start, round end, and gets-ball events.

        Args:
            event: The Laserball round event.

        Returns:
            str | None: Description string, or None if not a round event.
        """
        if event.event_type == '1105':
            self._last_laserball_passer = None
            self._last_laserball_pass_target = None
            return '* Round Start *'
        if event.event_type == '1106':
            self._last_laserball_passer = None
            self._last_laserball_pass_target = None
            for p in self.game_state.players.values():
                p.has_ball = False
            return '* Round End *'
        if event.event_type == '1107':
            self._last_laserball_passer = None
            self._last_laserball_pass_target = None
            actor = self.game_state.players.get(event.actor_entity_id)
            actor_name = self.entity_names.get(
                event.actor_entity_id, event.actor_entity_id
            )
            for p in self.game_state.players.values():
                p.has_ball = False
            if actor:
                actor.has_ball = True
            return f'{actor_name} gets ball'
        return None

    def _process_laserball_carrier_events(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str | None:
        """Processes pass, clear, and fail-clear events.

        Args:
            event: The Laserball carrier event.

        Returns:
            str | None: Description string, or None if not a carrier event.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        target = self.game_state.players.get(event.target_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if event.event_type == '1100':
            if actor:
                actor.has_ball = False
                actor.passes += 1
            if target:
                target.has_ball = True
            self._last_laserball_passer = actor
            self._last_laserball_pass_target = target
            return f'{actor_name} passes to {target_name}'

        if event.event_type == '1109':
            if actor:
                actor.has_ball = False
                actor.clears += 1
            if target:
                target.has_ball = True
            self._last_laserball_passer = None
            self._last_laserball_pass_target = None
            if target:
                return f'{actor_name} clears to {target_name}'
            return f'{actor_name} clears the ball'

        if event.event_type == '110A':
            return f'{actor_name} fails clear'

        return None

    def _process_laserball_scoring_events(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str | None:
        """Processes goal and assist events.

        Args:
            event: The Laserball scoring event.

        Returns:
            str | None: Description string, or None if not a scoring event.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )

        if event.event_type == '1101':
            self._last_assisted_scorer = None
            self._last_assisted_passer = None
            if actor:
                actor.goals += 1
                actor.score = actor.goals
                actor.has_ball = False
                if (
                    self._last_laserball_passer is not None
                    and self._last_laserball_pass_target == actor
                    and self._last_laserball_passer != actor
                ):
                    self._last_laserball_passer.assists += 1
                    self._last_assisted_scorer = actor
                    self._last_assisted_passer = self._last_laserball_passer
            self._last_laserball_passer = None
            self._last_laserball_pass_target = None
            return f'{actor_name} scores a goal'

        if event.event_type == '1102':
            target_name = self.entity_names.get(
                event.target_entity_id, event.target_entity_id
            )
            # Avoid double-counting if automatically awarded on 1101
            already_awarded = (
                self._last_assisted_passer is not None
                and self._last_assisted_passer == actor
                and self._last_assisted_scorer is not None
                and self._last_assisted_scorer.entity_id
                == event.target_entity_id
            )
            if not already_awarded and actor:
                actor.assists += 1
            self._last_assisted_scorer = None
            self._last_assisted_passer = None
            return f'{actor_name} assists {target_name}'

        return None

    def _process_laserball_combat_events(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str | None:
        """Processes steal, block, and reset-on-base events.

        Args:
            event: The Laserball combat/action event.

        Returns:
            str | None: Description string, or None if not a combat event.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        target = self.game_state.players.get(event.target_entity_id)
        actor_name = self.entity_names.get(
            event.actor_entity_id, event.actor_entity_id
        )
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if event.event_type == '1103':
            if actor:
                actor.steals += 1
                actor.has_ball = True
                actor.times_zapped_opponents += 1
            if target:
                target.has_ball = False
                target.times_zapped += 1
                target.times_blocked += 1
                self._apply_laserball_downtime(target, event.time)
            self._last_laserball_passer = None
            self._last_laserball_pass_target = None
            return f'{actor_name} steals from {target_name}'

        if event.event_type == '1104':
            if actor:
                actor.blocks += 1
                actor.times_zapped_opponents += 1
            if target:
                target.times_zapped += 1
                target.times_blocked += 1
                self._apply_laserball_downtime(target, event.time)
            return f'{actor_name} blocks {target_name}'

        if event.event_type == '110B':
            if actor:
                actor.downtime_ends_at_ms = event.time
                actor.resettable_starts_at_ms = event.time
                actor.just_went_down_at_ms = None
            return f'{actor_name} resets on base'

        return None

    def _process_event_laserball(
        self: 'LFReplaySystem', event: GameEvent
    ) -> str:
        """Processes Laserball game events.

        Dispatches to round, carrier, scoring, or combat handlers.

        Args:
            event: The Laserball game event.

        Returns:
            str: The event description string.
        """
        res = self._process_laserball_round_events(event)
        if res is not None:
            return res

        res = self._process_laserball_carrier_events(event)
        if res is not None:
            return res

        res = self._process_laserball_scoring_events(event)
        if res is not None:
            return res

        res = self._process_laserball_combat_events(event)
        if res is not None:
            return res

        return event.action
