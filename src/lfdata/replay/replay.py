"""Replay system orchestrator for simulating and recording LF game state
changes.
"""

from lfdata.model import GameEvent, LFGame, LFRole, LFTeamType
from lfdata.replay.handlers import LFReplayHandlersMixin
from lfdata.replay.record import LFReplayEventRecord
from lfdata.replay.state import (
    LFReplayGameState,
    LFReplayPlayerState,
    LFReplayTeamState,
)


class LFReplaySystem(LFReplayHandlersMixin):
    """Orchestrates the replay simulation from a parsed game."""

    def __init__(self, game: LFGame) -> None:
        """Initializes the replay system.

        Args:
            game: The LF game object containing teams, entities, and events.
        """
        self.game = game
        self._detect_and_inject_nuke_cancels()
        self.player_states: list[LFReplayPlayerState] = []
        self.team_states: list[LFReplayTeamState] = []
        self.entity_names: dict[str, str] = {
            e.entity_id: e.desc for e in game.entities
        }
        self._init_states()
        self.game_state = LFReplayGameState(
            self.player_states, self.team_states
        )
        self.records: list[LFReplayEventRecord] = []
        self.game_ended_at_ms: int | None = None

    def _init_states(self) -> None:
        """Initializes player and team states based on game metadata."""
        player_team_indices = {
            e.team_index for e in self.game.entities if e.type == 'player'
        }

        for team in self.game.teams:
            if team.team_index not in player_team_indices:
                continue
            try:
                team_type = LFTeamType.from_index(team.team_index)
                name = team_type.display_name
            except ValueError:
                name = team.desc
            self.team_states.append(
                LFReplayTeamState(
                    team_index=team.team_index,
                    name=name,
                    color_rgb=team.color_rgb,
                )
            )

        for entity in self.game.entities:
            if entity.type == 'player':
                try:
                    role = LFRole.from_id(entity.category)
                except ValueError:
                    role = LFRole.SCOUT
                self.player_states.append(
                    LFReplayPlayerState(
                        entity.entity_id, role, entity.team_index
                    )
                )

    def run(self) -> list[LFReplayEventRecord]:
        """Runs the game replay through all events in chronological order.

        Returns:
            list[LFReplayEventRecord]: The list of event records generated.
        """
        sorted_events = sorted(self.game.events, key=lambda e: e.time)

        for event in sorted_events:
            # First, update all player states for the current event time
            for player in self.game_state.players.values():
                player.update_downtime(event.time)

            player_snap, team_snap = self._take_snapshot()

            description = self._dispatch_event(event)

            self.game_state.update_team_scores_and_rankings()
            player_changes, team_changes = self._build_changes(
                player_snap, team_snap
            )

            record = LFReplayEventRecord(
                event_id=event.id or 0,
                time_ms=event.time,
                description=description,
                player_changes=player_changes,
                team_changes=team_changes,
            )
            self.records.append(record)

            if self._is_game_over():
                self.game_ended_at_ms = event.time
                break

        return self.records

    def _find_mission_end_ms(
        self, sorted_events: list[GameEvent]
    ) -> int | None:
        """Finds the mission end timestamp (0101) from the sorted events list.

        Args:
            sorted_events: Chronologically sorted list of game events.

        Returns:
            int | None: The mission end timestamp in milliseconds if found.
        """
        for ev in sorted_events:
            if ev.event_type == '0101':
                return ev.time
        return None

    def _is_nuke_detonated(
        self,
        sorted_events: list[GameEvent],
        index: int,
        nuker_id: str,
        activate_ms: int,
    ) -> bool:
        """Checks if a nuke was detonated within 10 seconds of activation.

        Args:
            sorted_events: Chronologically sorted list of game events.
            index: Current event index in the sorted list.
            nuker_id: Entity ID of the player activating the nuke.
            activate_ms: The millisecond timestamp when the nuke was activated.

        Returns:
            bool: True if detonated within 10 seconds, False otherwise.
        """
        for check_ev in sorted_events[index + 1 :]:
            if check_ev.time > activate_ms + 10000:
                break
            if (
                check_ev.event_type == '0405'
                and check_ev.actor_entity_id == nuker_id
            ):
                return True
        return False

    def _get_cancel_reason_for_event(
        self,
        check_ev: GameEvent,
        nuker_id: str,
        player_teams: dict[str, int],
    ) -> str | None:
        """Determines if an event cancels the nuke and returns the reason.

        Args:
            check_ev: The event to inspect.
            nuker_id: The entity ID of the player activating the nuke.
            player_teams: Mapping from player entity ID to team index.

        Returns:
            str | None: The cancel reason if the event cancels the nuke.
        """
        et = check_ev.event_type
        target = check_ev.target_entity_id
        actor = check_ev.actor_entity_id

        # 1. Player is downed
        if et in ('0206', '0208', '0306', '0308') and target == nuker_id:
            if actor and player_teams.get(actor) == player_teams.get(nuker_id):
                return 'nuke cancel by friendly fire'
            return 'nuke cancel'

        # 2. Cancel by resup
        if et in ('0500', '0502') and target == nuker_id:
            return 'nuke cancel by own resup'

        # 3. Cancel by enemy nuke
        if et == '0405' and actor != nuker_id:
            if actor and player_teams.get(actor) != player_teams.get(nuker_id):
                return 'nuke cancel by enemy nuke'

        # 4. Game end
        if et == '0101':
            return 'nuke activated too late'

        return None

    def _determine_nuke_cancel_details(
        self,
        sorted_events: list[GameEvent],
        index: int,
        nuker_id: str,
        activate_ms: int,
        player_teams: dict[str, int],
        mission_end_ms: int | None,
    ) -> tuple[int, str]:
        """Scans future events to determine why a nuke was canceled.

        Args:
            sorted_events: Chronologically sorted list of game events.
            index: Current event index in the sorted list.
            nuker_id: Entity ID of the player activating the nuke.
            activate_ms: The millisecond timestamp of the nuke activation.
            player_teams: Mapping from player entity ID to team index.
            mission_end_ms: The mission end timestamp in milliseconds, if any.

        Returns:
            tuple[int, str]: The cancel timestamp and cancel reason.
        """
        cancel_ms = activate_ms + 10000
        cancel_reason = 'nuke activated too late'

        if mission_end_ms is not None and mission_end_ms < cancel_ms:
            cancel_ms = mission_end_ms

        for check_ev in sorted_events[index + 1 :]:
            if check_ev.time > activate_ms + 10000:
                break

            reason = self._get_cancel_reason_for_event(
                check_ev=check_ev,
                nuker_id=nuker_id,
                player_teams=player_teams,
            )
            if reason is not None:
                cancel_reason = reason
                cancel_ms = check_ev.time
                break

        return cancel_ms, cancel_reason

    def _inject_cancel_event(
        self,
        cancel_ms: int,
        nuker_id: str,
        cancel_reason: str,
        injected_cancels: list[GameEvent],
    ) -> None:
        """Helper to create and append an inferred 'nuke_cancel' GameEvent.

        Args:
            cancel_ms: The cancel timestamp in milliseconds.
            nuker_id: Entity ID of the player activating the nuke.
            cancel_reason: The reason for nuke cancel.
            injected_cancels: List to append the inferred event to.
        """
        inferred_ev = GameEvent(
            game_id=self.game.game_id,
            time=cancel_ms,
            event_type='nuke_cancel',
            actor_entity_id=nuker_id,
            target_entity_id=None,
            action=cancel_reason,
            raw_message='',
        )
        injected_cancels.append(inferred_ev)

    def _detect_and_inject_nuke_cancels(self) -> None:
        """Detects nuke activations that did not detonate and injects cancels.

        Checks all nuke activations (0404) chronologically. If no detonation
        (0405) by the same player occurs within 10 seconds, it scans subsequent
        events to determine why it was canceled and at what timestamp. Then, it
        creates and appends an inferred 'nuke_cancel' GameEvent.
        """
        if any(e.event_type == 'nuke_cancel' for e in self.game.events):
            return

        player_teams = {
            e.entity_id: e.team_index
            for e in self.game.entities
            if e.type == 'player'
        }
        sorted_events = sorted(self.game.events, key=lambda e: e.time)
        mission_end_ms = self._find_mission_end_ms(sorted_events)
        injected_cancels = []

        for i, ev in enumerate(sorted_events):
            if ev.event_type != '0404':
                continue

            nuker_id = ev.actor_entity_id
            if not nuker_id:
                continue
            activate_ms = ev.time

            if self._is_nuke_detonated(sorted_events, i, nuker_id, activate_ms):
                continue

            cancel_ms, cancel_reason = self._determine_nuke_cancel_details(
                sorted_events=sorted_events,
                index=i,
                nuker_id=nuker_id,
                activate_ms=activate_ms,
                player_teams=player_teams,
                mission_end_ms=mission_end_ms,
            )

            self._inject_cancel_event(
                cancel_ms=cancel_ms,
                nuker_id=nuker_id,
                cancel_reason=cancel_reason,
                injected_cancels=injected_cancels,
            )

        self.game.events.extend(injected_cancels)

    def run_up_to(self, time_ms: int) -> None:
        """Simulates the game replay up to a specific millisecond timestamp.

        Args:
            time_ms: The millisecond timestamp to simulate up to (inclusive).
        """
        sorted_events = sorted(self.game.events, key=lambda e: e.time)

        for event in sorted_events:
            if event.time > time_ms:
                break

            for player in self.game_state.players.values():
                player.update_downtime(event.time)

            self._dispatch_event(event)
            self.game_state.update_team_scores_and_rankings()

            if self._is_game_over():
                self.game_ended_at_ms = event.time
                return

        # Final update to the target timestamp
        for player in self.game_state.players.values():
            player.update_downtime(time_ms)

    def _dispatch_event(self, event: GameEvent) -> str:
        """Dispatches a game event to its specific handler method.

        Args:
            event: The game event to dispatch.

        Returns:
            str: The event description string.
        """
        ev_type = event.event_type
        if ev_type in ['0205', '0206', '0207', '0208']:
            description = self._process_event_zap(event)
        elif ev_type in ['0306', '0308']:
            description = self._process_event_missile(event)
        elif ev_type in ['0204', '0303', '0B03']:
            description = self._process_event_base_destroy(event)
        elif ev_type == '0405':
            description = self._process_event_nuke_detonate(event)
        elif ev_type == 'nuke_cancel':
            description = self._process_event_nuke_cancel(event)
        elif ev_type in ['0500', '0502', '0510', '0512']:
            description = self._process_event_resupply(event)
        else:
            description = self._process_event_other(event)

        # Check team elimination after processing the event
        self._check_team_elimination(event.time)

        return description

    def _decrement_shots(self, actor_id: str | None) -> None:
        """Helper to decrement shots left for non-ammo players.

        Args:
            actor_id: The ID of the acting player.
        """
        if actor_id and actor_id in self.game_state.players:
            player = self.game_state.players[actor_id]
            if player.role != LFRole.AMMO and not player.is_eliminated():
                player.shots = max(0, player.shots - 1)

    def _decrement_missiles(self, actor_id: str | None) -> None:
        """Helper to decrement missiles left for player.

        Args:
            actor_id: The ID of the acting player.
        """
        if actor_id and actor_id in self.game_state.players:
            player = self.game_state.players[actor_id]
            if not player.is_eliminated():
                player.missiles = max(0, player.missiles - 1)

    def _take_snapshot(
        self,
    ) -> tuple[dict[str, dict[str, any]], dict[int, dict[str, any]]]:
        """Takes a snapshot of the current state of players and teams.

        Returns:
            tuple: A dictionary of player snapshots and team snapshots.
        """
        player_snap = {}
        for p in self.game_state.players.values():
            player_snap[p.entity_id] = {
                'score': p.score,
                'lives': p.lives,
                'shots': p.shots,
                'missiles': p.missiles,
                'special_points': p.special_points,
            }
        team_snap = {}
        for t in self.game_state.teams.values():
            team_snap[t.team_index] = {
                'score': t.score,
                'ranking': t.ranking,
            }
        return player_snap, team_snap

    def _build_changes(
        self,
        player_snap: dict[str, dict[str, any]],
        team_snap: dict[int, dict[str, any]],
    ) -> tuple[dict[str, dict[str, any]], dict[int, dict[str, any]]]:
        """Calculates state changes by comparing against the snapshots.

        Args:
            player_snap: Player state snapshot before the event.
            team_snap: Team state snapshot before the event.

        Returns:
            tuple: A dictionary of player state changes and team state changes.
        """
        player_changes = {}
        for p in self.game_state.players.values():
            old = player_snap[p.entity_id]
            changes = {}
            for attr in [
                'score',
                'lives',
                'shots',
                'missiles',
                'special_points',
            ]:
                new_val = getattr(p, attr)
                if new_val != old[attr]:
                    changes[attr] = new_val
            if changes:
                player_changes[p.entity_id] = changes

        team_changes = {}
        for t in self.game_state.teams.values():
            old = team_snap[t.team_index]
            changes = {}
            for attr in ['score', 'ranking']:
                new_val = getattr(t, attr)
                if new_val != old[attr]:
                    changes[attr] = new_val
            if changes:
                team_changes[t.team_index] = changes

        return player_changes, team_changes

    def _check_team_elimination(self, event_time: int) -> None:
        """Checks if any team has been completely eliminated.

        If a team is eliminated, all players of the other team(s) are awarded
        all bases they haven't captured yet.

        Args:
            event_time: The current event timestamp in milliseconds.
        """
        active_teams = set()
        for player in self.game_state.players.values():
            active_teams.add(player.team_index)

        eliminated_teams = set()
        for team_idx in active_teams:
            team_players = [
                p
                for p in self.game_state.players.values()
                if p.team_index == team_idx
            ]
            if all(p.is_eliminated() for p in team_players):
                eliminated_teams.add(team_idx)

        if eliminated_teams:
            all_bases = [
                e
                for e in self.game.entities
                if e.type
                in (
                    'standard-target',
                    'generator-target',
                )
            ]
            for player in self.game_state.players.values():
                if (
                    player.team_index not in eliminated_teams
                    and not player.is_eliminated()
                ):
                    for base in all_bases:
                        if (
                            base.team_index != player.team_index
                            and base.entity_id not in player.captured_bases
                        ):
                            player.captured_bases.add(base.entity_id)
                            player.score += 1001
                            if not (
                                player.role == LFRole.SCOUT
                                and player.has_rapid_fire
                            ):
                                player.special_points += 5

    def _is_game_over(self) -> bool:
        """Checks if the game has ended prematurely.

        Returns:
            bool: True if the game is over, False otherwise.
        """
        player_teams = {p.team_index for p in self.game_state.players.values()}
        if not player_teams:
            return False

        for team_idx in player_teams:
            team_players = [
                p
                for p in self.game_state.players.values()
                if p.team_index == team_idx
            ]
            if all(p.is_eliminated() for p in team_players):
                return True
        return False
