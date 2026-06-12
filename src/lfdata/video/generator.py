"""Visual HUD elements generator for LF video frames."""

import bisect
import dataclasses
import random
import re
from typing import Any

import jinja2


from lfdata.model import GameEvent, LFGame, LFRole
from lfdata.replay import LFReplaySystem
from lfdata.replay.state import LFReplayPlayerState, LFReplayTeamState
from lfdata.video.element import UIElement, UIElementStyle
from lfdata.video.helpers import (
    DEFAULT_CONFIG,
    LFTeamTransition,
    _merge_configs,
    apply_animation,
    get_fade_alpha,
    get_visual_rank,
    resolve_animated_value,
    resolve_config_dict,
)


@dataclasses.dataclass
class LFResupplyTracker:
    """Tracks the last resupply event timestamp and actor name.

    Attributes:
        time_ms: The timestamp in milliseconds of the resupply.
        actor_name: The codename of the player who resupplied.
    """

    time_ms: int
    actor_name: str


@dataclasses.dataclass
class LFNukeInterval:
    """Represents a nuke activation interval and its activator name.

    Attributes:
        start_ms: The millisecond timestamp of the activation.
        end_ms: The millisecond timestamp of detonation or cancellation.
        nuker_name: The codename of the player who activated the nuke.
    """

    start_ms: int
    end_ms: int
    nuker_name: str


def _normalize_player_name(name: str) -> str:
    """Normalizes a player name by removing whitespaces and special characters.

    Args:
        name: The player name to normalize.

    Returns:
        str: The normalized alphanumeric lowercase string.
    """
    name = name.lower()
    name = name.replace('&nbsp;', '')
    return ''.join(c for c in name if c.isalnum())


class VisualElementGenerator:
    """Generates the list of UI elements for a player at a specific time."""

    def __init__(
        self,
        game: LFGame,
        player_name: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initializes the HUD element generator.

        Args:
            game: The LFGame data object.
            player_name: The codename of the player to focus the HUD on,
                or None.
            config: Optional configuration override dictionary.
        """
        self.game = game
        self.player_name = player_name
        self.entity_id = self._find_player_entity_id()
        self.entity_names = {e.entity_id: e.desc for e in game.entities}

        if config is None:
            self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = _merge_configs(DEFAULT_CONFIG, config)

        if self.player_name:
            self.config['player_name'] = self.player_name

        self.snapshots: list[
            tuple[
                int,
                dict[str, LFReplayPlayerState],
                dict[int, LFReplayTeamState],
            ]
        ] = []
        self.event_log: list[dict[str, Any]] = []
        self.player_event_log: list[dict[str, Any]] = []
        self._last_ammo_resup: LFResupplyTracker | None = None
        self._last_medic_resup: LFResupplyTracker | None = None
        self._last_ammo_resup_by_me: dict[str, int] = {}
        self._last_medic_resup_by_me: dict[str, int] = {}
        self.team_transitions: dict[int, list[LFTeamTransition]] = {}
        self.game_ended_at_ms: int | None = None
        self.current_time_ms: int = 0

        self._jinja_env = jinja2.Environment()
        self._jinja_cache: dict[
            tuple[str, frozenset[tuple[str, str]]], str
        ] = {}
        self.current_variables: dict[str, str] = {}

        self._precompute_replay()
        self.camera_shakes: list[dict[str, Any]] = []
        self.nuke_flashes: list[int] = []
        self.missile_flashes_ms: list[int] = []
        self._detect_camera_shakes()

    def _find_player_entity_id(self) -> str | None:
        """Finds the entity ID matching the player codename.

        Returns:
            str | None: The entity ID if found, otherwise None.
        """
        if not self.player_name:
            return None
        norm_search = _normalize_player_name(self.player_name)
        for entity in self.game.entities:
            if entity.type == 'player':
                if _normalize_player_name(entity.desc) == norm_search:
                    self.player_name = entity.desc
                    return entity.entity_id
        return None

    def _copy_player_state(self, p: LFReplayPlayerState) -> LFReplayPlayerState:
        """Deep-copies essential fields of a player state.

        Args:
            p: The source player state.

        Returns:
            LFReplayPlayerState: The cloned player state.
        """
        new_p = LFReplayPlayerState(p.entity_id, p.role, p.team_index)
        new_p.lives = p.lives
        new_p.shots = p.shots
        new_p.missiles = p.missiles
        new_p.score = p.score
        new_p.special_points = p.special_points
        new_p.max_hp = p.max_hp
        new_p.hp = p.hp
        new_p.downtime_ends_at_ms = p.downtime_ends_at_ms
        new_p.resettable_starts_at_ms = p.resettable_starts_at_ms
        new_p.just_went_down_at_ms = p.just_went_down_at_ms
        new_p.captured_bases = set(p.captured_bases)
        new_p.has_rapid_fire = p.has_rapid_fire
        new_p.nukes_activated = p.nukes_activated
        new_p.nukes_detonated = p.nukes_detonated
        new_p.nuke_cancels = p.nuke_cancels
        new_p.own_nuke_cancels = p.own_nuke_cancels
        new_p.penalties = p.penalties
        return new_p

    def _copy_team_state(self, t: LFReplayTeamState) -> LFReplayTeamState:
        """Deep-copies essential fields of a team state.

        Args:
            t: The source team state.

        Returns:
            LFReplayTeamState: The cloned team state.
        """
        new_t = LFReplayTeamState(t.team_index, t.name, t.color_rgb)
        new_t.score = t.score
        new_t.ranking = t.ranking
        return new_t

    def _log_eliminated_teams(
        self,
        replay: LFReplaySystem,
        event_time_ms: int,
        eliminated_teams: set[int],
    ) -> None:
        """Checks for newly eliminated teams and adds an event log entry.

        Args:
            replay: The replay system instance.
            event_time_ms: The current event timestamp in milliseconds.
            eliminated_teams: The set of already eliminated team indices.
        """
        active_teams = {
            p.team_index for p in replay.game_state.players.values()
        }
        for team_idx in active_teams:
            if team_idx not in eliminated_teams:
                team_players = [
                    p
                    for p in replay.game_state.players.values()
                    if p.team_index == team_idx
                ]
                if team_players and all(
                    p.is_eliminated() for p in team_players
                ):
                    eliminated_teams.add(team_idx)
                    team_name = replay.game_state.teams[team_idx].name
                    self.event_log.append(
                        {
                            'time': event_time_ms,
                            'desc': f'Team {team_name} Eliminated',
                            'is_important': False,
                            'actor_id': None,
                            'target_id': None,
                        }
                    )

    def _track_rank_transitions(
        self,
        replay: LFReplaySystem,
        event_time_ms: int,
        team_ranks: dict[int, int],
        last_trans_time_ms: dict[int, int],
        visual_rank_at_last_trans: dict[int, float],
    ) -> None:
        """Tracks visual rank changes for each team and updates transitions
        list.

        Args:
            replay: The replay system instance.
            event_time_ms: The current event timestamp in milliseconds.
            team_ranks: Dictionary mapping team ID to its current rank.
            last_trans_time_ms: Dictionary mapping team ID to last transition.
            visual_rank_at_last_trans: Dictionary mapping team ID to its rank.
        """
        anim = self.config.get('animation', 'ease-in-out')
        for tid, t in replay.game_state.teams.items():
            if t.ranking != team_ranks[tid]:
                t_last_ms = last_trans_time_ms[tid]
                v_last = visual_rank_at_last_trans[tid]
                target_last = team_ranks[tid]

                elapsed_ms = event_time_ms - t_last_ms
                if elapsed_ms < 1000:
                    p = elapsed_ms / 1000.0
                    p_anim = apply_animation(p, anim)
                    v_curr = v_last + (target_last - v_last) * p_anim
                else:
                    v_curr = float(target_last)

                self.team_transitions[tid].append(
                    LFTeamTransition(
                        event_time_ms=event_time_ms,
                        visual_rank=v_curr,
                        ranking=t.ranking,
                    )
                )
                last_trans_time_ms[tid] = event_time_ms
                visual_rank_at_last_trans[tid] = v_curr
                team_ranks[tid] = t.ranking

    def _init_precompute(
        self, replay: LFReplaySystem
    ) -> tuple[dict[int, int], dict[int, int], dict[int, float], set[int]]:
        """Initializes data structures and first snapshot for precomputation.

        Args:
            replay: The LFReplaySystem.

        Returns:
            tuple[dict[int, int], dict[int, int], dict[int, float], set[int]]:
                Initial team ranks, last transition times, visual ranks,
                and eliminated teams set.
        """
        self.snapshots.append(
            (
                0,
                {
                    pid: self._copy_player_state(p)
                    for pid, p in replay.game_state.players.items()
                },
                {
                    tid: self._copy_team_state(t)
                    for tid, t in replay.game_state.teams.items()
                },
            )
        )

        team_ranks = {
            tid: t.ranking for tid, t in replay.game_state.teams.items()
        }
        self.team_transitions = {tid: [] for tid in team_ranks}
        last_trans_time_ms = {tid: 0 for tid in team_ranks}
        visual_rank_at_last_trans = {
            tid: float(t.ranking) for tid, t in replay.game_state.teams.items()
        }
        eliminated_teams: set[int] = set()
        return (
            team_ranks,
            last_trans_time_ms,
            visual_rank_at_last_trans,
            eliminated_teams,
        )

    def _process_replay_events(
        self,
        replay: LFReplaySystem,
        sorted_events: list[GameEvent],
        team_ranks: dict[int, int],
        last_trans_time_ms: dict[int, int],
        visual_rank_at_last_trans: dict[int, float],
        eliminated_teams: set[int],
    ) -> None:
        """Processes the list of events to build replay snapshots.

        Args:
            replay: The LFReplaySystem.
            sorted_events: Sorted game events.
            team_ranks: Current ranking of teams.
            last_trans_time_ms: Last transition times in milliseconds.
            visual_rank_at_last_trans: Visual rank at last transition.
            eliminated_teams: Set of team indices already eliminated.
        """
        for event in sorted_events:
            for player in replay.game_state.players.values():
                player.update_downtime(event.time)

            desc = replay._dispatch_event(event)
            replay.game_state.update_team_scores_and_rankings()

            self._log_eliminated_teams(replay, event.time, eliminated_teams)

            self.snapshots.append(
                (
                    event.time,
                    {
                        pid: self._copy_player_state(p)
                        for pid, p in replay.game_state.players.items()
                    },
                    {
                        tid: self._copy_team_state(t)
                        for tid, t in replay.game_state.teams.items()
                    },
                )
            )

            is_important = event.event_type in [
                '0404',
                '0405',
                'nuke_cancel',
            ]
            if desc and 'misses' not in desc:
                self.event_log.append(
                    {
                        'time': event.time,
                        'desc': desc,
                        'is_important': is_important,
                        'actor_id': event.actor_entity_id,
                        'target_id': event.target_entity_id,
                    }
                )

            self._process_hud_event_triggers(event, replay, desc)

            self._track_rank_transitions(
                replay=replay,
                event_time_ms=event.time,
                team_ranks=team_ranks,
                last_trans_time_ms=last_trans_time_ms,
                visual_rank_at_last_trans=visual_rank_at_last_trans,
            )
            if event.event_type == '0101':
                replay.game_ended_at_ms = event.time
                break

    def _precompute_replay(self) -> None:
        """Runs simulation once, caching snapshots and transition times."""
        replay = LFReplaySystem(self.game)
        (
            team_ranks,
            last_trans_time_ms,
            visual_rank_at_last_trans,
            eliminated_teams,
        ) = self._init_precompute(replay)

        sorted_events = sorted(self.game.events, key=lambda e: e.time)
        self._process_replay_events(
            replay=replay,
            sorted_events=sorted_events,
            team_ranks=team_ranks,
            last_trans_time_ms=last_trans_time_ms,
            visual_rank_at_last_trans=visual_rank_at_last_trans,
            eliminated_teams=eliminated_teams,
        )

        self.game_ended_at_ms = replay.game_ended_at_ms
        self._precompute_nuke_intervals(sorted_events)

    def _precompute_nuke_intervals(
        self, sorted_events: list[GameEvent]
    ) -> None:
        """Precomputes active nuke intervals during the game.

        Args:
            sorted_events: Chronologically sorted game events list.
        """
        self.nuke_intervals: list[LFNukeInterval] = []
        activations = [ev for ev in sorted_events if ev.event_type == '0404']

        for act in activations:
            nuker_id = act.actor_entity_id
            if not nuker_id:
                continue
            t_start = act.time
            t_end = self.game.duration or 0
            if self.game_ended_at_ms is not None:
                t_end = self.game_ended_at_ms

            for ev in sorted_events:
                if ev.time > t_start and ev.actor_entity_id == nuker_id:
                    if ev.event_type in ('0405', 'nuke_cancel'):
                        t_end = ev.time
                        break

            nuker_name = self.entity_names.get(nuker_id, nuker_id)
            self.nuke_intervals.append(
                LFNukeInterval(
                    start_ms=t_start, end_ms=t_end, nuker_name=nuker_name
                )
            )

    def _process_hud_event_triggers(
        self,
        event: GameEvent,
        replay: LFReplaySystem,
        desc: str,
    ) -> None:
        """Processes and logs player-specific and important global HUD events.

        Args:
            event: The parsed GameEvent.
            replay: The active LFReplaySystem.
            desc: The default event description.
        """
        if len(self.snapshots) < 2:
            return

        prev_players = self.snapshots[-2][1]
        actor_id = event.actor_entity_id
        target_id = event.target_entity_id

        actor_name = self.entity_names.get(actor_id or '', actor_id or '')
        target_name = self.entity_names.get(target_id or '', target_id or '')

        if self.entity_id:
            msg = None
            et = event.event_type

            if et in ('0205', '0206', '0207', '0208'):
                if actor_id == self.entity_id:
                    t_state = replay.game_state.players.get(target_id or '')
                    self_state = replay.game_state.players.get(self.entity_id)
                    if t_state and self_state:
                        if t_state.team_index == self_state.team_index:
                            msg = f'FRIENDLY zap {target_name}'
                        else:
                            msg = f'Zapped {target_name}'
                elif target_id == self.entity_id:
                    a_state = replay.game_state.players.get(actor_id or '')
                    self_state = replay.game_state.players.get(self.entity_id)
                    if a_state and self_state:
                        if a_state.team_index == self_state.team_index:
                            msg = f'FRIENDLY zap by {actor_name}'
                        else:
                            msg = f'Zapped by {actor_name}'

            elif et == '0300':
                if actor_id == self.entity_id:
                    t_state = replay.game_state.players.get(target_id or '')
                    self_state = replay.game_state.players.get(self.entity_id)
                    if t_state and self_state:
                        if t_state.team_index == self_state.team_index:
                            msg = f'FRIENDLY lock {target_name}'
                        else:
                            msg = f'Locking {target_name}'
                    else:
                        msg = f'Locking {target_name}'
                elif target_id == self.entity_id:
                    a_state = replay.game_state.players.get(actor_id or '')
                    self_state = replay.game_state.players.get(self.entity_id)
                    if a_state and self_state:
                        if a_state.team_index == self_state.team_index:
                            msg = f'FRIENDLY lock by {actor_name}'
                        else:
                            msg = f'Locked by {actor_name}'
                    else:
                        msg = f'Locked by {actor_name}'

            elif et in ('0306', '0308', '0304', '0301', '0302', '0303'):
                found_lock = None
                for ev_entry in reversed(self.player_event_log):
                    if (
                        ev_entry.get('event_type') == '0300'
                        and ev_entry.get('actor_id') == actor_id
                        and 'follow_up_time' not in ev_entry
                    ):
                        if target_id is not None:
                            if ev_entry.get('target_id') == target_id:
                                found_lock = ev_entry
                                break
                        else:
                            found_lock = ev_entry
                            break

                follow_up_msg = None
                if et == '0306':
                    if actor_id == self.entity_id:
                        t_state = replay.game_state.players.get(target_id or '')
                        self_state = replay.game_state.players.get(
                            self.entity_id
                        )
                        if t_state and self_state:
                            if t_state.team_index == self_state.team_index:
                                follow_up_msg = (
                                    f'FRIENDLY missile {target_name}'
                                )
                            else:
                                follow_up_msg = f'Missiled {target_name}'
                    elif target_id == self.entity_id:
                        a_state = replay.game_state.players.get(actor_id or '')
                        self_state = replay.game_state.players.get(
                            self.entity_id
                        )
                        if a_state and self_state:
                            if a_state.team_index == self_state.team_index:
                                follow_up_msg = (
                                    f'FRIENDLY missile by {actor_name}'
                                )
                            else:
                                follow_up_msg = f'Missiled by {actor_name}'
                elif et == '0308':
                    if actor_id == self.entity_id:
                        follow_up_msg = f'FRIENDLY missile {target_name}'
                    elif target_id == self.entity_id:
                        follow_up_msg = f'FRIENDLY missile by {actor_name}'
                elif et == '0304':
                    if actor_id == self.entity_id:
                        follow_up_msg = 'Missile MISSES'
                    else:
                        if (
                            found_lock
                            and found_lock.get('target_id') == self.entity_id
                        ):
                            a_state = replay.game_state.players.get(
                                actor_id or ''
                            )
                            self_state = replay.game_state.players.get(
                                self.entity_id
                            )
                            if a_state and self_state:
                                if a_state.team_index == self_state.team_index:
                                    follow_up_msg = (
                                        f'FRIENDLY missile from {actor_name} '
                                        'MISSES'
                                    )
                                else:
                                    follow_up_msg = (
                                        f'Missile from {actor_name} MISSES'
                                    )
                elif et in ('0301', '0302', '0303'):
                    if actor_id == self.entity_id:
                        if et == '0301':
                            follow_up_msg = f'Missile misses {target_name}'
                        else:
                            follow_up_msg = f'Missiled {target_name}'

                if found_lock and follow_up_msg:
                    el_config = self.config.get('elements', {}).get(
                        'player_events', {}
                    )
                    fade_time_s = el_config.get('fade_out_time')
                    if fade_time_s is None:
                        fade_time_s = self.config.get('fade_out_time', 3.0)
                    fade_time_ms = int(fade_time_s * 1000)

                    found_lock['follow_up_desc'] = follow_up_msg
                    found_lock['follow_up_time'] = event.time
                    found_lock['duration'] = (
                        event.time - found_lock['time']
                    ) + fade_time_ms
                elif follow_up_msg:
                    if et in ('0306', '0308') or (
                        et == '0304' and actor_id == self.entity_id
                    ):
                        msg = follow_up_msg

            elif et in ('0500', '0502'):
                msg = self._process_hud_resupply_event(
                    event=event,
                    et=et,
                    actor_id=actor_id,
                    target_id=target_id,
                    actor_name=actor_name,
                    target_name=target_name,
                )

            elif et in ('0510', '0512'):
                msg = self._process_hud_boost_event(
                    event=event,
                    et=et,
                    actor_id=actor_id,
                    actor_name=actor_name,
                    prev_players=prev_players,
                    replay=replay,
                )

            if msg:
                self.player_event_log.append(
                    {
                        'time': event.time,
                        'desc': msg,
                        'actor_id': actor_id,
                        'target_id': target_id,
                        'event_type': et,
                    }
                )

        for pid, player in replay.game_state.players.items():
            prev_player = prev_players.get(pid)
            if not prev_player:
                continue

            if prev_player.lives > 0 and player.lives == 0:
                p_name = self.entity_names.get(pid, pid)
                self.event_log.append(
                    {
                        'time': event.time,
                        'desc': f'{p_name} eliminated',
                        'is_important': True,
                        'actor_id': None,
                        'target_id': pid,
                    }
                )

            elif (
                player.role == LFRole.MEDIC
                and player.lives < prev_player.lives
                and player.lives > 0
                and any(
                    val % 5 == 0
                    for val in range(player.lives, prev_player.lives)
                )
            ):
                p_name = self.entity_names.get(pid, pid)
                desc = f'Medic {p_name} has {player.lives} lives left'
                self.event_log.append(
                    {
                        'time': event.time,
                        'desc': desc,
                        'is_important': True,
                        'actor_id': None,
                        'target_id': pid,
                    }
                )

    def _get_state_at(
        self, time_ms: int
    ) -> tuple[dict[str, LFReplayPlayerState], dict[int, LFReplayTeamState]]:
        """Retrieves and interpolates player/team states at time_ms.

        Args:
            time_ms: The millisecond timestamp.

        Returns:
            tuple: Cloned player and team states at the timestamp.
        """
        times = [snap[0] for snap in self.snapshots]
        idx = bisect.bisect_right(times, time_ms)
        if idx == 0:
            _, players, teams = self.snapshots[0]
        else:
            _, players, teams = self.snapshots[idx - 1]

        cloned_players = {
            pid: self._copy_player_state(p) for pid, p in players.items()
        }
        cloned_teams = {
            tid: self._copy_team_state(t) for tid, t in teams.items()
        }

        for player in cloned_players.values():
            player.update_downtime(time_ms)

        return cloned_players, cloned_teams

    def _resolve_element_style(
        self, el_config: dict[str, Any]
    ) -> UIElementStyle:
        """Resolves styling properties from configuration.

        Args:
            el_config: Dictionary containing element configuration.

        Returns:
            UIElementStyle: The resolved style.
        """
        style_config = el_config.get('style', {})
        global_style = {
            'font': self.config.get('font', 'GoogleSans-Bold'),
            'style': self.config.get('style', 'normal'),
            'size': self.config.get('size', 20),
            'color': self.config.get('color', '#ffffffff'),
            'background_color': self.config.get(
                'background_color', '#00000000'
            ),
        }

        font = style_config.get('font', global_style['font'])
        style_type = style_config.get('style', global_style['style'])
        size = style_config.get(
            'size', el_config.get('size', global_style['size'])
        )
        color = style_config.get('color', global_style['color'])
        bg_color = style_config.get(
            'background_color', global_style['background_color']
        )

        return UIElementStyle(
            font=font,
            style=style_type,
            size=size,
            color=color,
            background_color=bg_color,
        )

    def _translate_position_compat(
        self, x: float | None, y: float | None
    ) -> str:
        """Translates coordinate pairs to legacy position strings for compat.

        Args:
            x: Relative X coordinate.
            y: Relative Y coordinate.

        Returns:
            str: The legacy position description string.
        """
        if x == 0.1 and y == 0.9:
            return 'bottom left'
        if x == 0.9 and y == 0.5:
            return 'top right'
        if x == 0.5 and (y == 0.05 or y == 0.09):
            return 'top center'
        if x == 0.9 and y == 0.05:
            return 'top right'
        if x in (0.2, 0.4, 0.6, 0.8) and y == 0.13:
            return 'top left'
        return ''

    def _parse_indicator_interval(self, val: Any) -> int | None:
        """Parses a visual indicator interval from configuration value.

        Args:
            val: The configuration value (int or str).

        Returns:
            int | None: The parsed interval integer, or None if invalid/none.
        """
        if val is None:
            return None
        if isinstance(val, int):
            return val if val > 0 else None
        if isinstance(val, str):
            val_clean = val.strip().lower()
            if val_clean in ('none', 'null', ''):
                return None
            match = re.search(r'\d+', val_clean)
            if match:
                parsed = int(match.group())
                return parsed if parsed > 0 else None
        return None

    def _process_hud_resupply_event(
        self,
        event: GameEvent,
        et: str,
        actor_id: str | None,
        target_id: str | None,
        actor_name: str,
        target_name: str,
    ) -> str | None:
        """Processes a resupply event and returns the message description.

        Analyzes individual resupply events (0500 and 0502) to determine if the
        current player is either receiving a resupply or giving one to a
        teammate. Handles double-resupply detection for both directions.

        Args:
            event: The parsed GameEvent.
            et: The event type string (e.g. '0500', '0502').
            actor_id: The entity ID of the actor player, or None.
            target_id: The entity ID of the target player, or None.
            actor_name: The codename of the actor player.
            target_name: The codename of the target player.

        Returns:
            str | None: The event message description, or None if no message
                should be added.
        """
        msg: str | None = None
        if target_id == self.entity_id:
            if et == '0500':
                self._last_ammo_resup = LFResupplyTracker(
                    time_ms=event.time, actor_name=actor_name
                )
                if (
                    self._last_medic_resup
                    and event.time - self._last_medic_resup.time_ms <= 1000
                ):
                    msg = (
                        f'Double-resupply by {actor_name} and '
                        f'{self._last_medic_resup.actor_name}'
                    )
                    if self._update_double_resupply_event(
                        prev_time=self._last_medic_resup.time_ms,
                        event_time=event.time,
                        double_resup_msg=msg,
                        target_id=self.entity_id,
                    ):
                        msg = None
                else:
                    msg = f'Resupplied shots by {actor_name}'
            else:
                self._last_medic_resup = LFResupplyTracker(
                    time_ms=event.time, actor_name=actor_name
                )
                if (
                    self._last_ammo_resup
                    and event.time - self._last_ammo_resup.time_ms <= 1000
                ):
                    msg = (
                        f'Double-resupply by '
                        f'{self._last_ammo_resup.actor_name} '
                        f'and {actor_name}'
                    )
                    if self._update_double_resupply_event(
                        prev_time=self._last_ammo_resup.time_ms,
                        event_time=event.time,
                        double_resup_msg=msg,
                        target_id=self.entity_id,
                    ):
                        msg = None
                else:
                    msg = f'Resupplied lives by {actor_name}'

        elif actor_id == self.entity_id and target_id:
            if et == '0500':
                self._last_ammo_resup_by_me[target_id] = event.time
                prev_medic = self._last_medic_resup_by_me.get(target_id)
                if prev_medic and event.time - prev_medic <= 1000:
                    msg = f'Double-resupplied {target_name}'
                    if self._update_double_resupply_event(
                        prev_time=prev_medic,
                        event_time=event.time,
                        double_resup_msg=msg,
                        target_id=target_id,
                    ):
                        msg = None
                else:
                    msg = f'Resupplied shots for {target_name}'
            else:
                self._last_medic_resup_by_me[target_id] = event.time
                prev_ammo = self._last_ammo_resup_by_me.get(target_id)
                if prev_ammo and event.time - prev_ammo <= 1000:
                    msg = f'Double-resupplied {target_name}'
                    if self._update_double_resupply_event(
                        prev_time=prev_ammo,
                        event_time=event.time,
                        double_resup_msg=msg,
                        target_id=target_id,
                    ):
                        msg = None
                else:
                    msg = f'Resupplied lives for {target_name}'
        return msg

    def _process_hud_boost_event(
        self,
        event: GameEvent,
        et: str,
        actor_id: str | None,
        actor_name: str,
        prev_players: dict[str, LFReplayPlayerState],
        replay: LFReplaySystem,
    ) -> str | None:
        """Processes a team boost event and returns the message description.

        Analyzes team boost events (0510 and 0512) to check if the current
        player is the one performing the boost or is on the receiving team.

        Args:
            event: The parsed GameEvent.
            et: The event type string (e.g. '0510', '0512').
            actor_id: The entity ID of the actor player, or None.
            actor_name: The codename of the actor player.
            prev_players: The dict of player states from the previous tick.
            replay: The active replay simulation system.

        Returns:
            str | None: The event message description, or None if no message
                should be added.
        """
        msg: str | None = None
        if actor_id == self.entity_id:
            if et == '0510':
                msg = 'Ammo-boosted team'
            else:
                msg = 'Life-boosted team'
        elif actor_id != self.entity_id:
            a_state = replay.game_state.players.get(actor_id or '')
            self_state = replay.game_state.players.get(self.entity_id)
            prev_self = prev_players.get(self.entity_id)
            if (
                a_state
                and self_state
                and prev_self
                and a_state.team_index == self_state.team_index
            ):
                if (
                    prev_self.can_receive_resupply(event.time)
                    and prev_self.lives > 0
                ):
                    if et == '0510':
                        msg = f'Shot-boosted by {actor_name}'
                    else:
                        msg = f'Life-boosted by {actor_name}'
        return msg

    def _update_double_resupply_event(
        self,
        prev_time: int,
        event_time: int,
        double_resup_msg: str,
        target_id: str | None = None,
    ) -> bool:
        """Finds and updates a previous single resupply with a double resupply.

        Searches the player event log in reverse to find a matching resupply
        event that occurred at prev_time. If found, updates it to a double
        resupply description and adjusts its duration.

        Args:
            prev_time: The timestamp of the previous resupply event.
            event_time: The timestamp of the current double resupply event.
            double_resup_msg: The double resupply description string.
            target_id: The optional entity ID of the target player to match.

        Returns:
            bool: True if the previous event was found and updated, else False.
        """
        el_config: dict[str, Any] = self.config.get('elements', {}).get(
            'player_events', {}
        )
        fade_time_s: float | None = el_config.get('fade_out_time')
        if fade_time_s is None:
            fade_time_s = self.config.get('fade_out_time', 3.0)
        fade_time_ms: int = int(fade_time_s * 1000)

        for ev in reversed(self.player_event_log):
            if (
                ev['time'] == prev_time
                and ev['desc'].startswith('Resupplied ')
                and (target_id is None or ev['target_id'] == target_id)
            ):
                ev['double_resup_desc'] = double_resup_msg
                ev['double_resup_time'] = event_time
                ev['duration'] = (event_time - prev_time) + fade_time_ms
                return True
        return False

    def _build_variables_blob(
        self,
        game_time_ms: int,
        players: dict[str, LFReplayPlayerState],
    ) -> dict[str, str]:
        """Builds a dictionary of text variables for Jinja rendering.

        Args:
            game_time_ms: The current game time in milliseconds.
            players: The dictionary of player states.

        Returns:
            dict[str, str]: A dictionary mapping variable names to their values.
        """
        variables = {
            'game_type': f'Game Type: {self.game.game_type}',
            'normalized_game_type': self.game.normalized_game_type or '',
        }

        # Date of the game
        el_config_date = self.config.get('elements', {}).get('date_of_game', {})
        format_str = el_config_date.get('format')
        date_text = ''
        if self.game.timestamp:
            if format_str:
                try:
                    date_text = self.game.timestamp.strftime(format_str)
                except Exception:
                    date_text = self.game.timestamp.strftime('%Y-%m-%d')
            else:
                month_str = str(self.game.timestamp.month)
                day_str = str(self.game.timestamp.day)
                year_str = self.game.timestamp.strftime('%y')
                date_text = f'{month_str}/{day_str}/{year_str}'
        elif self.game.start:
            date_text = self.game.start
        variables['date_of_game'] = date_text

        # User defined texts
        for i in range(1, 13):
            key = f'user_defined_text_{i}'
            el_config_user = self.config.get('elements', {}).get(key, {})
            user_text = el_config_user.get('text', '')
            variables[key] = user_text

        # Centre/Arena name
        variables['centre_name'] = (
            self.game.arena_name or self.game.centre or ''
        )

        # Time variable
        actual_duration_ms = self.game.duration
        if self.game_ended_at_ms is not None:
            actual_duration_ms = self.game_ended_at_ms

        display_ms = game_time_ms
        if actual_duration_ms is not None and display_ms > actual_duration_ms:
            display_ms = actual_duration_ms

        total_seconds = display_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        time_text = f'{minutes:02d}:{seconds:02d}'
        variables['time'] = time_text

        # Player-specific variables
        if self.entity_id and self.entity_id in players:
            p_state = players[self.entity_id]
            variables['player_name'] = self.player_name or ''
            variables['player_role'] = p_state.role.display_name
            variables['player_score'] = str(p_state.score)
        else:
            variables['player_name'] = ''
            variables['player_role'] = ''
            variables['player_score'] = ''

        return variables

    def _render_jinja_text(
        self,
        template_str: str,
        local_vars: dict[str, str],
    ) -> str:
        """Renders a Jinja template string using the local variables cache.

        Args:
            template_str: The Jinja template string to render.
            local_vars: The variables dictionary.

        Returns:
            str: The rendered text string.
        """
        cache_key = (template_str, frozenset(local_vars.items()))
        if cache_key in self._jinja_cache:
            return self._jinja_cache[cache_key]

        try:
            template = self._jinja_env.from_string(template_str)
            rendered = template.render(local_vars)
        except Exception as e:
            # Fall back to template_str if rendering fails
            print(f'Warning: Jinja rendering failed: {e}')
            rendered = template_str

        self._jinja_cache[cache_key] = rendered
        return rendered

    def _create_ui_element(
        self, element_key: str, text: str | None = None, **kwargs: Any
    ) -> UIElement | None:
        """Resolves configuration and styling to construct a UIElement.

        Args:
            element_key: Key of the element in the configuration.
            text: The optional text string of the element.
            kwargs: Extra attributes for initialization.

        Returns:
            UIElement | None: The element if enabled, otherwise None.
        """
        el_config = self.config.get('elements', {}).get(element_key, {})
        if not el_config.get('enabled', True):
            return None

        style = self._resolve_element_style(el_config)
        x = el_config.get('x')
        y = el_config.get('y')
        align = el_config.get('align')
        extents = el_config.get('extents')
        icon = el_config.get('icon')

        pos_compat = self._translate_position_compat(x, y)

        kwargs_copy = dict(kwargs)
        elem_type = kwargs_copy.pop('element_type', 'text')

        if 'extents' not in kwargs_copy and extents is not None:
            kwargs_copy['extents'] = extents
        if 'icon' not in kwargs_copy and icon is not None:
            kwargs_copy['icon'] = icon

        kwarg_indicator = kwargs_copy.pop('indicator_interval', None)

        config_indicator = (
            el_config.get('indicator_interval')
            or el_config.get('indicator')
            or el_config.get('interval')
            or el_config.get('indicators')
        )
        if config_indicator is not None:
            indicator_interval = self._parse_indicator_interval(
                config_indicator
            )
        else:
            indicator_interval = kwarg_indicator

        text_val = text if text is not None else el_config.get('text')

        formatted_text = None
        if elem_type == 'text':
            formatted_text = el_config.get('formatted_text')
            if formatted_text is None or formatted_text == '':
                formatted_text = f'{{{{ {element_key} }}}}'

            local_vars = dict(self.current_variables)
            raw_val = text_val if text_val is not None else ''
            local_vars[element_key] = raw_val

            text_val = self._render_jinja_text(
                template_str=formatted_text,
                local_vars=local_vars,
            )

        pregame_delay = self.config.get('pregame_delay_ms', 0)
        video_end_ms = self.config.get('video_end_ms')
        if video_end_ms is None:
            actual_duration_ms = self.game.duration
            if self.game_ended_at_ms is not None:
                actual_duration_ms = self.game_ended_at_ms
            if actual_duration_ms is None:
                actual_duration_ms = 0
            extra_footage_ms = self.config.get('extra_footage_ms', 10000)
            video_end_ms = actual_duration_ms + extra_footage_ms + pregame_delay

        visible_start = kwargs_copy.pop(
            'visible_start_ms',
            el_config.get('visible_start_ms', pregame_delay),
        )
        visible_end = kwargs_copy.pop(
            'visible_end_ms',
            el_config.get('visible_end_ms', video_end_ms),
        )
        if visible_end is None or visible_end == 0:
            visible_end = video_end_ms
        fade_in = kwargs_copy.pop(
            'fade_in_ms',
            el_config.get('fade_in_ms', 0),
        )
        fade_out = kwargs_copy.pop(
            'fade_out_ms',
            el_config.get('fade_out_ms', 0),
        )

        return UIElement(
            element_type=elem_type,
            position=pos_compat,
            text=text_val,
            style=style,
            x=x,
            y=y,
            align=align,
            indicator_interval=indicator_interval,
            visible_start_ms=visible_start,
            visible_end_ms=visible_end,
            fade_in_ms=fade_in,
            fade_out_ms=fade_out,
            formatted_text=formatted_text,
            **kwargs_copy,
        )

    def _compile_player_scoreboard_data(
        self,
        team_players: list[LFReplayPlayerState],
        time_ms: int,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Compiles players stats and calculates team totals.

        Args:
            team_players: List of team players.
            time_ms: Current millisecond timestamp.

        Returns:
            tuple[list[dict[str, Any]], dict[str, int]]:
                The compiled player data dictionaries and the totals dictionary.
        """
        players_data = []
        tot_score = 0
        tot_lives = 0
        tot_shots = 0
        tot_missiles = 0
        tot_spec = 0
        tot_hp = 0

        for p in team_players:
            codename = self.entity_names.get(p.entity_id, p.entity_id)
            players_data.append(
                {
                    'codename': codename,
                    'role_name': p.role.display_name,
                    'score': p.score,
                    'lives': p.lives,
                    'shots': p.shots,
                    'missiles': p.missiles,
                    'special_points': p.special_points,
                    'hp': p.hp,
                    'max_hp': p.max_hp,
                    'is_down': p.is_down(time_ms),
                    'is_eliminated': p.is_eliminated(),
                    'penalties': p.penalties,
                }
            )
            tot_score += p.score
            tot_lives += p.lives
            tot_shots += p.shots
            tot_missiles += p.missiles
            tot_spec += p.special_points
            if p.max_hp > 1:
                tot_hp += p.hp

        totals = {
            'score': tot_score,
            'lives': tot_lives,
            'shots': tot_shots,
            'missiles': tot_missiles,
            'special_points': tot_spec,
            'hp': tot_hp,
        }
        return players_data, totals

    def _build_team_scoreboard_data(
        self,
        team: LFReplayTeamState,
        players: dict[str, LFReplayPlayerState],
        time_ms: int,
    ) -> dict[str, Any]:
        """Builds scoreboard stats data for a single team.

        Args:
            team: The team state object.
            players: Dictionary containing player states.
            time_ms: Current millisecond timestamp.

        Returns:
            dict[str, Any]: Compiled team scoreboard dictionary.
        """
        anim = self.config.get('animation', 'ease-in-out')
        trans_list = self.team_transitions.get(team.team_index, [])
        vr = get_visual_rank(
            team.team_index, time_ms, trans_list, team.ranking, anim
        )

        team_players = [
            p for p in players.values() if p.team_index == team.team_index
        ]
        team_players.sort(key=lambda p: p.score, reverse=True)

        players_data, totals = self._compile_player_scoreboard_data(
            team_players, time_ms
        )

        return {
            'team_index': team.team_index,
            'team_name': team.name,
            'team_score': team.score,
            'color_rgb': team.color_rgb,
            'players': players_data,
            'visual_rank': vr,
            'totals': totals,
        }

    def _create_scoreboard_element(
        self,
        teams: dict[int, LFReplayTeamState],
        players: dict[str, LFReplayPlayerState],
        time_ms: int,
    ) -> UIElement | None:
        """Constructs the scoreboard element containing animated ranks.

        Args:
            teams: Map of team index to team state.
            players: Map of player ID to player state.
            time_ms: The current millisecond timestamp.

        Returns:
            UIElement | None: The scoreboard element if enabled.
        """
        el_config = self.config.get('elements', {}).get('scoreboard', {})
        if not el_config.get('enabled', True):
            return None

        teams_data = [
            self._build_team_scoreboard_data(
                team=t, players=players, time_ms=time_ms
            )
            for t in teams.values()
        ]

        return self._create_ui_element(
            'scoreboard',
            element_type='scoreboard',
            scoreboard_data={'teams': teams_data},
        )

    def _add_global_hud_elements(
        self,
        elements: list[UIElement],
        teams: dict[int, LFReplayTeamState],
        players: dict[str, LFReplayPlayerState],
        time_ms: int,
    ) -> None:
        """Adds global HUD elements like game type, time, and scoreboard.

        Args:
            elements: List of visual elements to append to.
            teams: Current team states.
            players: Current player states.
            time_ms: Current millisecond timestamp.
        """
        el_game_type = self._create_ui_element(
            'game_type',
            text=f'Game Type: {self.game.game_type}',
            element_type='text',
        )
        if el_game_type:
            elements.append(el_game_type)

        el_norm_game_type = self._create_ui_element(
            'normalized_game_type',
            text=self.game.normalized_game_type or '',
            element_type='text',
        )
        if el_norm_game_type:
            elements.append(el_norm_game_type)

        actual_duration_ms = self.game.duration
        if self.game_ended_at_ms is not None:
            actual_duration_ms = self.game_ended_at_ms

        display_ms = time_ms
        if actual_duration_ms is not None and display_ms > actual_duration_ms:
            display_ms = actual_duration_ms

        total_seconds = display_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        time_text = f'{minutes:02d}:{seconds:02d}'

        el_time = self._create_ui_element(
            'time', text=time_text, element_type='text'
        )
        if el_time:
            elements.append(el_time)

        el_sb = self._create_scoreboard_element(
            teams=teams, players=players, time_ms=time_ms
        )
        if el_sb:
            elements.append(el_sb)

        el_config_date = self.config.get('elements', {}).get('date_of_game', {})
        format_str = el_config_date.get('format')
        date_text = ''
        if self.game.timestamp:
            if format_str:
                try:
                    date_text = self.game.timestamp.strftime(format_str)
                except Exception:
                    date_text = self.game.timestamp.strftime('%Y-%m-%d')
            else:
                month_str = str(self.game.timestamp.month)
                day_str = str(self.game.timestamp.day)
                year_str = self.game.timestamp.strftime('%y')
                date_text = f'{month_str}/{day_str}/{year_str}'
        elif self.game.start:
            date_text = self.game.start

        if date_text:
            el_date = self._create_ui_element(
                'date_of_game',
                text=date_text,
                element_type='text',
            )
            if el_date:
                elements.append(el_date)

        for i in range(1, 13):
            el_user = self._create_ui_element(
                f'user_defined_text_{i}',
                element_type='text',
            )
            if el_user:
                elements.append(el_user)

        centre_text = self.game.arena_name or self.game.centre or ''
        el_centre = self._create_ui_element(
            'centre_name',
            text=centre_text,
            element_type='text',
        )
        if el_centre:
            elements.append(el_centre)

    def _add_player_stats_hud_elements(
        self,
        elements: list[UIElement],
        p_state: LFReplayPlayerState,
    ) -> None:
        """Adds text stats and Counter HUD elements for the focused player.

        Args:
            elements: List of visual elements to append to.
            p_state: Player state of the focused player.
        """
        stats_defs = [
            ('player_name', f'{self.player_name}'),
            ('player_role', f'{p_state.role.display_name}'),
            ('player_score', f'{p_state.score}'),
        ]
        for key, text in stats_defs:
            el = self._create_ui_element(key, text=text, element_type='text')
            if el:
                elements.append(el)

        el_lives = self._create_ui_element(
            'player_lives',
            element_type='counter',
            current_value=p_state.lives,
            max_value=p_state.role.max_lives,
        )
        if el_lives:
            elements.append(el_lives)

        if p_state.role.max_shots > 0:
            el_shots = self._create_ui_element(
                'player_shots',
                element_type='counter',
                current_value=p_state.shots,
                max_value=p_state.role.max_shots,
            )
            if el_shots:
                elements.append(el_shots)

        if p_state.role.start_missiles > 0:
            el_missiles = self._create_ui_element(
                'player_missiles',
                element_type='counter',
                current_value=p_state.missiles,
                max_value=p_state.role.start_missiles,
                indicator_interval=1,
            )
            if el_missiles:
                elements.append(el_missiles)

        if p_state.max_hp > 1:
            el_hp = self._create_ui_element(
                'player_hitpoints',
                element_type='counter',
                current_value=p_state.hp,
                max_value=p_state.max_hp,
                indicator_interval=1,
            )
            if el_hp:
                elements.append(el_hp)

        if p_state.role != LFRole.HEAVY:
            if p_state.role == LFRole.COMMANDER:
                sp_interval = 20
            elif p_state.role in (LFRole.SCOUT, LFRole.AMMO):
                sp_interval = 15
            elif p_state.role == LFRole.MEDIC:
                sp_interval = 10
            else:
                sp_interval = None

            el_pspec = self._create_ui_element(
                'player_special_points',
                element_type='counter',
                current_value=p_state.special_points,
                max_value=99,
                indicator_interval=sp_interval,
            )
            if el_pspec:
                elements.append(el_pspec)

    def _add_player_downtime_hud_element(
        self,
        elements: list[UIElement],
        p_state: LFReplayPlayerState,
        time_ms: int,
    ) -> None:
        """Adds a downtime bar HUD element if the player is currently down.

        Args:
            elements: List of visual elements to append to.
            p_state: Player state of the focused player.
            time_ms: Current millisecond timestamp.
        """
        if p_state.is_down(time_ms):
            safe_rem_ms = max(0, p_state.resettable_starts_at_ms - time_ms)
            res_base_ms = max(time_ms, p_state.resettable_starts_at_ms)
            resettable_rem_ms = max(
                0, p_state.downtime_ends_at_ms - res_base_ms
            )

            el_dt = self._create_ui_element(
                'downtime',
                element_type='downtime_bar',
                safe_ms=safe_rem_ms,
                resettable_ms=resettable_rem_ms,
            )
            if el_dt:
                elements.append(el_dt)

    def _add_player_hud_elements(
        self,
        elements: list[UIElement],
        players: dict[str, LFReplayPlayerState],
        time_ms: int,
    ) -> None:
        """Adds player-specific HUD elements if a target player is focused.

        Args:
            elements: List of visual elements to append to.
            players: Current player states.
            time_ms: Current millisecond timestamp.
        """
        if not self.entity_id or self.entity_id not in players:
            return

        p_state = players[self.entity_id]
        self._add_player_stats_hud_elements(elements, p_state)
        self._add_player_downtime_hud_element(elements, p_state, time_ms)

    def _get_active_multiline_lines(
        self,
        event_list: list[dict[str, Any]],
        time_ms: int,
        fade_time_ms: int,
        max_lines: int = 3,
        is_game_events: bool = False,
    ) -> list[dict[str, Any] | None]:
        """Simulates event timeline to allocate events to lines/slots.

        Tracks slots and expires events dynamically as time advances.

        Args:
            event_list: A list of logged event dicts containing 'time' and
                'desc'.
            time_ms: The target timestamp in milliseconds.
            fade_time_ms: The default display duration in milliseconds.
            max_lines: Maximum number of slots to display.
            is_game_events: True to enable dynamic nuke durations.

        Returns:
            list[dict[str, Any] | None]: List of slots with active events.
        """
        sorted_events = sorted(event_list, key=lambda e: e['time'])
        slots: list[dict[str, Any] | None] = [None] * max_lines

        for ev in sorted_events:
            ev_time = ev['time']
            if ev_time > time_ms:
                break

            for i in range(max_lines):
                slot = slots[i]
                if slot is not None and slot['end'] <= ev_time:
                    slots[i] = None

            is_nuke_act = False
            duration = ev.get('duration', fade_time_ms)

            if is_game_events and ev.get('is_important'):
                if 'activates nuke' in ev['desc']:
                    is_nuke_act = True
                    t_end = time_ms
                    for interval in self.nuke_intervals:
                        if interval.start_ms == ev_time:
                            t_end = interval.end_ms
                            break
                    duration = t_end - ev_time

            if duration <= 0:
                continue

            slot_idx = -1
            for i in range(max_lines):
                if slots[i] is None:
                    slot_idx = i
                    break

            if slot_idx != -1:
                text: str = ev['desc']
                if (
                    'double_resup_desc' in ev
                    and time_ms >= ev['double_resup_time']
                ):
                    text = ev['double_resup_desc']
                elif 'follow_up_desc' in ev and time_ms >= ev['follow_up_time']:
                    text = ev['follow_up_desc']

                slots[slot_idx] = {
                    'text': text,
                    'start': ev_time,
                    'end': ev_time + duration,
                    'is_nuke_act': is_nuke_act,
                    'duration': duration,
                }

        for i in range(max_lines):
            slot = slots[i]
            if slot is not None and slot['end'] <= time_ms:
                slots[i] = None

        return slots

    def _add_player_event_hud_element(
        self,
        elements: list[UIElement],
        time_ms: int,
        anim: str,
        player_to_color: dict[str, str] | None = None,
    ) -> None:
        """Adds recent player-specific event HUD elements if active.

        Args:
            elements: List of visual elements to append to.
            time_ms: Current millisecond timestamp.
            anim: Animation function name.
            player_to_color: Optional player names to hex colors dictionary.
        """
        if not self.entity_id:
            return

        el_config = self.config.get('elements', {}).get('player_events', {})
        if not el_config.get('enabled', True):
            return

        fade_time_s = el_config.get('fade_out_time')
        if fade_time_s is None:
            fade_time_s = self.config.get('fade_out_time', 3.0)
        fade_time_ms = int(fade_time_s * 1000)

        slots = self._get_active_multiline_lines(
            event_list=self.player_event_log,
            time_ms=time_ms,
            fade_time_ms=fade_time_ms,
            max_lines=3,
            is_game_events=False,
        )

        base_y = el_config.get('y', 0.2)
        font_size = el_config.get('style', {}).get('size', 18)
        line_height = (font_size * 1.3) / 800

        for line_idx, slot in enumerate(slots):
            if slot is not None:
                elapsed = time_ms - slot['start']
                alpha = get_fade_alpha(elapsed, slot['duration'], anim)
                y_offset = base_y + line_idx * line_height
                el = self._create_ui_element(
                    'player_events',
                    text=slot['text'],
                    element_type='text',
                    alpha=alpha,
                    player_to_color=player_to_color,
                )
                if el:
                    el.y = y_offset
                    elements.append(el)

    def _add_game_event_hud_element(
        self,
        elements: list[UIElement],
        time_ms: int,
        anim: str,
        player_to_color: dict[str, str] | None = None,
    ) -> None:
        """Adds recent important game event HUD elements if active.

        Args:
            elements: List of visual elements to append to.
            time_ms: Current millisecond timestamp.
            anim: Animation function name.
            player_to_color: Optional player names to hex colors dictionary.
        """
        el_config = self.config.get('elements', {}).get('game_events', {})
        if not el_config.get('enabled', True):
            return

        fade_time_s = el_config.get('fade_out_time')
        if fade_time_s is None:
            fade_time_s = self.config.get('fade_out_time', 5.0)
        fade_time_ms = int(fade_time_s * 1000)

        important_events = [
            ev for ev in self.event_log if ev.get('is_important')
        ]

        slots = self._get_active_multiline_lines(
            event_list=important_events,
            time_ms=time_ms,
            fade_time_ms=fade_time_ms,
            max_lines=3,
            is_game_events=True,
        )

        base_y = el_config.get('y', 0.25)
        font_size = el_config.get('style', {}).get('size', 20)
        line_height = (font_size * 1.3) / 800

        for line_idx, slot in enumerate(slots):
            if slot is not None:
                if slot['is_nuke_act']:
                    alpha = 1.0
                else:
                    elapsed = time_ms - slot['start']
                    alpha = get_fade_alpha(elapsed, slot['duration'], anim)

                y_offset = base_y + line_idx * line_height
                el = self._create_ui_element(
                    'game_events',
                    text=slot['text'],
                    element_type='text',
                    alpha=alpha,
                    player_to_color=player_to_color,
                )
                if el:
                    el.y = y_offset
                    elements.append(el)

    def _add_event_hud_elements(
        self,
        elements: list[UIElement],
        players: dict[str, LFReplayPlayerState],
        teams: dict[int, LFReplayTeamState],
        time_ms: int,
    ) -> None:
        """Adds all event elements to HUD (scroller, player events, game events).

        Args:
            elements: List of visual elements to append to.
            players: Dictionary of player states.
            teams: Dictionary of team states.
            time_ms: Current millisecond timestamp.
        """
        anim = self.config.get('animation', 'ease-in-out')

        player_to_color: dict[str, str] = {}
        for pid, player in players.items():
            name = self.entity_names.get(pid, pid)
            t_state = teams.get(player.team_index)
            color = t_state.color_rgb if t_state else '#ffffff'
            player_to_color[name] = color

        player_events_in_color = self.config.get('player_events_in_color', True)
        color_map = player_to_color if player_events_in_color else None

        self._add_player_event_hud_element(
            elements=elements,
            time_ms=time_ms,
            anim=anim,
            player_to_color=color_map,
        )
        self._add_game_event_hud_element(
            elements=elements,
            time_ms=time_ms,
            anim=anim,
            player_to_color=color_map,
        )

        el_scroller = self._create_ui_element(
            'all_game_events',
            element_type='event_scroller',
            events_data=list(self.event_log),
            player_to_color=player_to_color,
        )
        if el_scroller:
            elements.append(el_scroller)

    def generate_at(self, time_ms: int) -> list[UIElement]:
        """Generates HUD elements at a specific millisecond timestamp.

        Calculates the active user interface elements for the current game
        state, including global, player-specific, and event-log elements.

        Args:
            time_ms: The millisecond timestamp.

        Returns:
            list[UIElement]: The list of active UI HUD elements.
        """
        self.current_time_ms = time_ms
        orig_config = self.config

        # Get pregame delay and game duration to resolve animated properties
        pregame_delay_ms = orig_config.get('pregame_delay_ms', 0)
        if (
            isinstance(pregame_delay_ms, dict)
            and 'keyframes' in pregame_delay_ms
        ):
            pregame_delay_ms = resolve_animated_value(
                pregame_delay_ms,
                time_ms,
                pregame_delay_ms=0,
                game_duration_ms=self.game.duration or 0,
            )

        actual_duration_ms = self.game.duration
        if self.game_ended_at_ms is not None:
            actual_duration_ms = self.game_ended_at_ms
        if actual_duration_ms is None:
            actual_duration_ms = 0

        self.config = resolve_config_dict(
            orig_config,
            time_ms,
            pregame_delay_ms=pregame_delay_ms,
            game_duration_ms=actual_duration_ms,
        )

        try:
            game_time_ms = max(0, time_ms - pregame_delay_ms)

            if (
                self.game_ended_at_ms is not None
                and game_time_ms > self.game_ended_at_ms
            ):
                game_time_ms = self.game_ended_at_ms

            players, teams = self._get_state_at(game_time_ms)
            self.current_variables = self._build_variables_blob(
                game_time_ms=game_time_ms,
                players=players,
            )
            elements: list[UIElement] = []

            self._add_global_hud_elements(
                elements=elements,
                teams=teams,
                players=players,
                time_ms=game_time_ms,
            )
            self._add_player_hud_elements(
                elements=elements, players=players, time_ms=game_time_ms
            )
            self._add_event_hud_elements(
                elements=elements,
                players=players,
                teams=teams,
                time_ms=game_time_ms,
            )

            # Apply camera shake
            total_strength = 0.0
            for shake in self.camera_shakes:
                start = shake['start_ms']
                duration = shake['duration_ms']
                if start <= game_time_ms < start + duration:
                    elapsed = game_time_ms - start
                    factor = 1.0 - (elapsed / duration)
                    total_strength += shake['strength'] * factor

            if total_strength > 0.0:
                dx = random.uniform(-total_strength, total_strength)
                dy = random.uniform(-total_strength, total_strength)
                for el in elements:
                    if el.x is not None:
                        el.x += dx
                    if el.y is not None:
                        el.y += dy

            # Update alpha of each element based on visibility and fading
            for el in elements:
                if (
                    time_ms < el.visible_start_ms
                    or time_ms >= el.visible_end_ms
                ):
                    el.alpha = 0.0
                else:
                    multiplier = 1.0
                    if (
                        el.fade_in_ms > 0
                        and time_ms < el.visible_start_ms + el.fade_in_ms
                    ):
                        multiplier = (
                            time_ms - el.visible_start_ms
                        ) / el.fade_in_ms
                    elif (
                        el.fade_out_ms > 0
                        and time_ms >= el.visible_end_ms - el.fade_out_ms
                    ):
                        multiplier = (
                            el.visible_end_ms - time_ms
                        ) / el.fade_out_ms
                    el.alpha *= max(0.0, min(1.0, multiplier))

            return elements
        finally:
            self.config = orig_config

    def _detect_camera_shakes(self) -> None:
        """Precomputes camera shakes from the game's event history."""
        if not self.entity_id:
            return

        player_entity = next(
            (e for e in self.game.entities if e.entity_id == self.entity_id),
            None,
        )
        if not player_entity:
            return

        player_team_idx = player_entity.team_index

        for event in self.game.events:
            # 1. Player is missiled (0.01 strength, 500 ms duration)
            if (
                event.event_type in ('0306', '0308')
                and event.target_entity_id == self.entity_id
            ):
                self.camera_shakes.append(
                    {
                        'start_ms': event.time,
                        'duration_ms': 500,
                        'strength': 0.01,
                    }
                )
                self.missile_flashes_ms.append(event.time)

            # 2. Enemy commander detonates a nuke (0.03 strength, 1000 ms duration)
            elif event.event_type == '0405':
                actor_id = event.actor_entity_id
                actor_entity = next(
                    (e for e in self.game.entities if e.entity_id == actor_id),
                    None,
                )
                if (
                    actor_entity
                    and actor_entity.type == 'player'
                    and actor_entity.team_index != player_team_idx
                    and actor_entity.category == 1  # Commander
                ):
                    self.camera_shakes.append(
                        {
                            'start_ms': event.time,
                            'duration_ms': 1000,
                            'strength': 0.03,
                        }
                    )
                    self.nuke_flashes.append(event.time)
