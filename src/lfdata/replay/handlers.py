"""Mixin containing event handlers for the LF replay system."""

from typing import TYPE_CHECKING
from lfdata.model import GameEvent, LFRole

if TYPE_CHECKING:
    from lfdata.replay.replay import LFReplaySystem


class LFReplayHandlersMixin:
    """Mixin class containing event handlers for the LF replay system."""

    def _process_event_zap(self: "LFReplaySystem", event: GameEvent) -> str:
        """Processes zapping events.

        Args:
            event: The zapping event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        target = self.game_state.players.get(event.target_entity_id)

        self._decrement_shots(event.actor_entity_id)
        actor_name = self.entity_names.get(event.actor_entity_id, event.actor_entity_id)
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
                # Friendly fire: penalize actor
                actor.score -= 100
            else:
                actor.score += 100
                if not (actor.role == LFRole.SCOUT and actor.has_rapid_fire):
                    actor.special_points += 1

            # Target always loses 20 score (unless already eliminated)
            target.score -= 20

            # Check if target goes down or resets downtime
            if event.event_type in ["0206", "0208"]:
                if actor.team_index != target.team_index:
                    if not target.is_down(event.time):
                        target.lives = max(0, target.lives - 1)
                target.hp = 0
                target.downtime_ends_at = event.time + 8000
                target.resettable_starts_at = event.time + 4000
            else:
                target.hp = max(1, target.hp - 1)

        return f"{actor_name} zaps {target_name}"

    def _process_event_missile(self: "LFReplaySystem", event: GameEvent) -> str:
        """Processes missile zapping events.

        Args:
            event: The missile event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        target = self.game_state.players.get(event.target_entity_id)

        self._decrement_missiles(event.actor_entity_id)

        actor_name = self.entity_names.get(event.actor_entity_id, event.actor_entity_id)
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
                actor.score -= 500
            else:
                actor.score += 500
                if not (actor.role == LFRole.SCOUT and actor.has_rapid_fire):
                    actor.special_points += 2

            # Target always loses 100 score (unless already eliminated)
            target.score -= 100

            # Missile immediately downs target or resets downtime
            if actor.team_index != target.team_index:
                if not target.is_down(event.time):
                    target.lives = max(0, target.lives - 2)
            target.hp = 0
            target.downtime_ends_at = event.time + 8000
            target.resettable_starts_at = event.time + 4000

        return f"{actor_name} missiles {target_name}"

    def _process_event_base_destroy(self: "LFReplaySystem", event: GameEvent) -> str:
        """Processes base destruction/capture events.

        Args:
            event: The base destruction/capture event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(event.actor_entity_id, event.actor_entity_id)
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if event.event_type == "0303":
            self._decrement_missiles(event.actor_entity_id)
        elif event.event_type == "0204":
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
                actor.score += 1001
                if not (actor.role == LFRole.SCOUT and actor.has_rapid_fire):
                    actor.special_points += 5

        if event.event_type == "0B03":
            return f"{actor_name} is awarded {target_name}"
        return f"{actor_name} destroys {target_name}"

    def _process_event_nuke_detonate(self: "LFReplaySystem", event: GameEvent) -> str:
        """Processes nuke detonation events.

        Args:
            event: The nuke detonation event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(event.actor_entity_id, event.actor_entity_id)

        if actor and not actor.is_eliminated():
            actor.score += 500
            actor.nukes_detonated += 1
            for player in self.game_state.players.values():
                if player.team_index != actor.team_index and not player.is_eliminated():
                    player.lives = max(0, player.lives - 3)
                    player.hp = 0
                    player.downtime_ends_at = event.time + 8000
                    player.resettable_starts_at = event.time + 4000

        return f"{actor_name} detonates nuke"

    def _process_event_resupply(self: "LFReplaySystem", event: GameEvent) -> str:
        """Processes resupply (ammo, lives, team boosts) events.

        Args:
            event: The resupply event.

        Returns:
            str: The event description string.
        """
        actor = self.game_state.players.get(event.actor_entity_id)
        actor_name = self.entity_names.get(event.actor_entity_id, event.actor_entity_id)
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if actor and actor.is_eliminated():
            return ""

        if event.event_type in ("0500", "0502"):
            target = self.game_state.players.get(event.target_entity_id)
            if target and not target.is_eliminated():
                is_medic = (
                    actor.role == LFRole.MEDIC if actor else event.event_type == "0502"
                )
                if is_medic:
                    target.resupply_lives_from_medic()
                else:
                    target.resupply_shots_from_ammo()
                target.hp = 0
                target.downtime_ends_at = event.time + 8000
                target.resettable_starts_at = event.time + 4000
                if target.role == LFRole.SCOUT:
                    target.has_rapid_fire = False
            return f"{actor_name} resupplies {target_name}"

        if event.event_type in ("0510", "0512"):
            if actor:
                is_medic = (
                    actor.role == LFRole.MEDIC if actor else event.event_type == "0512"
                )
                if is_medic:
                    actor.special_points = max(0, actor.special_points - 15)
                else:
                    actor.special_points = max(0, actor.special_points - 10)

                for player in self.game_state.players.values():
                    if (
                        player.team_index == actor.team_index
                        and player.entity_id != actor.entity_id
                        and not player.is_eliminated()
                        and not player.is_down(event.time)
                    ):
                        if is_medic:
                            player.resupply_lives_from_medic()
                        else:
                            player.resupply_shots_from_ammo()
            return f"{actor_name} resupplies team"

        return ""

    def _process_event_other(self: "LFReplaySystem", event: GameEvent) -> str:
        """Processes other miscellaneous events.

        Args:
            event: The miscellaneous event.

        Returns:
            str: The event description string.
        """
        actor_name = self.entity_names.get(event.actor_entity_id, event.actor_entity_id)
        target_name = self.entity_names.get(
            event.target_entity_id, event.target_entity_id
        )

        if event.event_type == "0100":
            return "* Mission Start *"
        if event.event_type == "0101":
            return "* Mission End *"
        if event.event_type == "0201":
            self._decrement_shots(event.actor_entity_id)
            return f"{actor_name} misses"
        if event.event_type == "0202":
            self._decrement_shots(event.actor_entity_id)
            return f"{actor_name} misses base"
        if event.event_type == "0203":
            self._decrement_shots(event.actor_entity_id)
            return f"{actor_name} zaps {target_name}"
        if event.event_type == "0300":
            return f"{actor_name} locking {target_name}"
        if event.event_type == "0400":
            actor = self.game_state.players.get(event.actor_entity_id)
            if actor and not actor.is_eliminated():
                actor.special_points = max(0, actor.special_points - 15)
                actor.has_rapid_fire = True
            return f"{actor_name} activates rapid fire"
        if event.event_type == "0404":
            actor = self.game_state.players.get(event.actor_entity_id)
            if actor and not actor.is_eliminated():
                actor.special_points = max(0, actor.special_points - 20)
                actor.nukes_activated += 1
            return f"{actor_name} activates nuke"
        if event.event_type == "0600":
            actor = self.game_state.players.get(event.actor_entity_id)
            if actor and not actor.is_eliminated():
                gp = self.game.penalty
                penalty_val = gp if gp is not None else -1000
                actor.score += penalty_val
            return f"{actor_name} is penalized"
        if event.event_type == "0301":
            self._decrement_missiles(event.actor_entity_id)
            return f"{actor_name} misses base"
        if event.event_type == "0302":
            self._decrement_missiles(event.actor_entity_id)
            return f"{actor_name} zaps {target_name}"
        if event.event_type == "0304":
            self._decrement_missiles(event.actor_entity_id)
            return f"{actor_name} misses"
        if event.event_type == "0900":
            return f"{actor_name} completes an achievement!"
        if event.event_type == "0902":
            return f"{actor_name} earns a reward!"

        return event.action

    def _process_event_nuke_cancel(self: "LFReplaySystem", event: GameEvent) -> str:
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
        actor_name = self.entity_names.get(event.actor_entity_id, event.actor_entity_id)

        if actor and not actor.is_eliminated():
            actor.own_nuke_cancels += 1

            if event.action == "nuke cancel":
                # Find the zapping/missiling enemy event at the same time
                for ev in self.game.events:
                    if ev.time == event.time and ev.target_entity_id == actor.entity_id:
                        if ev.event_type in ("0206", "0306"):
                            enemy = self.game_state.players.get(ev.actor_entity_id)
                            if enemy and not enemy.is_eliminated():
                                enemy.nuke_cancels += 1
                            break

        action = event.action
        if action == "nuke cancel":
            suffix = "nuke canceled"
        elif action == "nuke cancel by friendly fire":
            suffix = "nuke canceled by friendly fire"
        elif action == "nuke cancel by own resup":
            suffix = "nuke canceled by own resup"
        elif action == "nuke cancel by enemy nuke":
            suffix = "nuke canceled by enemy nuke"
        elif action == "nuke activated too late":
            suffix = "nuke activated too late"
        else:
            suffix = action

        return f"{actor_name} {suffix}"
