"""Visual HUD elements generator for LF video frames."""

import bisect
from typing import Any

from lfdata.model import GameEvent, LFGame, LFRole
from lfdata.replay import LFReplaySystem
from lfdata.replay.state import LFReplayPlayerState, LFReplayTeamState
from lfdata.video.element import UIElement, UIElementStyle
from lfdata.video.helpers import (
    DEFAULT_CONFIG,
    _merge_configs,
    apply_animation,
    get_fade_alpha,
    get_visual_rank,
)


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
            self.config = DEFAULT_CONFIG
        else:
            self.config = _merge_configs(DEFAULT_CONFIG, config)

        self.snapshots: list[
            tuple[
                int,
                dict[str, LFReplayPlayerState],
                dict[int, LFReplayTeamState],
            ]
        ] = []
        self.event_log: list[dict[str, Any]] = []
        self.player_event_log: list[dict[str, Any]] = []
        self._last_ammo_resup: tuple[int, str] | None = None
        self._last_medic_resup: tuple[int, str] | None = None
        self.team_transitions: dict[int, list[tuple[int, float, int]]] = {}
        self.game_ended_at_ms: int | None = None

        self._precompute_replay()

    def _find_player_entity_id(self) -> str | None:
        """Finds the entity ID matching the player codename.

        Returns:
            str | None: The entity ID if found, otherwise None.
        """
        if not self.player_name:
            return None
        for entity in self.game.entities:
            if (
                entity.type == 'player'
                and entity.desc.lower() == self.player_name.lower()
            ):
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
        new_p.captured_bases = set(p.captured_bases)
        new_p.has_rapid_fire = p.has_rapid_fire
        new_p.nukes_activated = p.nukes_activated
        new_p.nukes_detonated = p.nukes_detonated
        new_p.nuke_cancels = p.nuke_cancels
        new_p.own_nuke_cancels = p.own_nuke_cancels
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
                            'is_important': True,
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
                    (event_time_ms, v_curr, t.ranking)
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
                '0100',
                '0101',
                '0404',
                '0405',
                '0204',
                '0303',
                '0B03',
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
        self.nuke_intervals: list[tuple[int, int, str]] = []
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
            self.nuke_intervals.append((t_start, t_end, nuker_name))

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

            elif et in ('0306', '0308'):
                if actor_id == self.entity_id:
                    t_state = replay.game_state.players.get(target_id or '')
                    self_state = replay.game_state.players.get(self.entity_id)
                    if t_state and self_state:
                        if t_state.team_index == self_state.team_index:
                            msg = f'FRIENDLY missile {target_name}'
                        else:
                            msg = f'Missiled {target_name}'
                elif target_id == self.entity_id:
                    a_state = replay.game_state.players.get(actor_id or '')
                    self_state = replay.game_state.players.get(self.entity_id)
                    if a_state and self_state:
                        if a_state.team_index == self_state.team_index:
                            msg = f'FRIENDLY missile by {actor_name}'
                        else:
                            msg = f'Missiled by {actor_name}'

            elif et in ('0500', '0502') and target_id == self.entity_id:
                if et == '0500':
                    self._last_ammo_resup = (event.time, actor_name)
                    if (
                        self._last_medic_resup
                        and event.time - self._last_medic_resup[0] <= 1000
                    ):
                        msg = (
                            f'Double-resupply by {actor_name} and '
                            f'{self._last_medic_resup[1]}'
                        )
                    else:
                        msg = f'Resupplied shots by {actor_name}'
                else:
                    self._last_medic_resup = (event.time, actor_name)
                    if (
                        self._last_ammo_resup
                        and event.time - self._last_ammo_resup[0] <= 1000
                    ):
                        msg = (
                            f'Double-resupply by {self._last_ammo_resup[1]} '
                            f'and {actor_name}'
                        )
                    else:
                        msg = f'Resupplied lives by {actor_name}'

            elif et in ('0510', '0512') and actor_id != self.entity_id:
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
                        not prev_self.is_down(event.time)
                        and prev_self.lives > 0
                    ):
                        if et == '0510':
                            msg = f'Shot-boosted by {actor_name}'
                        else:
                            msg = f'Life-boosted by {actor_name}'

            if msg:
                self.player_event_log.append(
                    {
                        'time': event.time,
                        'desc': msg,
                        'actor_id': actor_id,
                        'target_id': target_id,
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
                and player.lives % 5 == 0
            ):
                p_name = self.entity_names.get(pid, pid)
                t_state = replay.game_state.teams.get(player.team_index)
                t_name = (
                    t_state.name if t_state else f'Team {player.team_index}'
                )
                self.event_log.append(
                    {
                        'time': event.time,
                        'desc': f'{t_name} {p_name} has {player.lives} lives',
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

        return UIElement(
            element_type=elem_type,
            position=pos_compat,
            text=text,
            style=style,
            x=x,
            y=y,
            align=align,
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
            )
            if el_missiles:
                elements.append(el_missiles)

        if p_state.max_hp > 1:
            el_hp = self._create_ui_element(
                'player_hitpoints',
                element_type='counter',
                current_value=p_state.hp,
                max_value=p_state.max_hp,
            )
            if el_hp:
                elements.append(el_hp)

        el_pspec = self._create_ui_element(
            'player_special_points',
            element_type='counter',
            current_value=p_state.special_points,
            max_value=100,
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

    def _add_player_event_hud_element(
        self,
        elements: list[UIElement],
        time_ms: int,
        anim: str,
    ) -> None:
        """Adds recent player-specific event HUD element if active.

        Args:
            elements: List of visual elements to append to.
            time_ms: Current millisecond timestamp.
            anim: Animation function name.
        """
        if not self.entity_id:
            return

        el_config = self.config.get('elements', {}).get('player_events', {})
        fade_time_s = el_config.get('fade_out_time')
        if fade_time_s is None:
            fade_time_s = self.config.get('fade_out_time', 3.0)
        fade_time_ms = int(fade_time_s * 1000)

        active_p_events = []
        for ev in self.player_event_log:
            if time_ms - fade_time_ms <= ev['time'] <= time_ms:
                active_p_events.append(ev)

        if active_p_events:
            recent_ev = active_p_events[-1]
            elapsed_ms = time_ms - recent_ev['time']
            alpha = get_fade_alpha(elapsed_ms, fade_time_ms, anim)
            el_pevent = self._create_ui_element(
                'player_events',
                text=recent_ev['desc'],
                element_type='text',
                alpha=alpha,
            )
            if el_pevent:
                elements.append(el_pevent)

    def _add_game_event_hud_element(
        self,
        elements: list[UIElement],
        time_ms: int,
        anim: str,
    ) -> None:
        """Adds recent important game event HUD element if active.

        Args:
            elements: List of visual elements to append to.
            time_ms: Current millisecond timestamp.
            anim: Animation function name.
        """
        # First, check if there is an active nuke activation interval
        active_nuke_msg = None
        for start_ms, end_ms, player_name in self.nuke_intervals:
            if start_ms <= time_ms < end_ms:
                active_nuke_msg = f'{player_name} activates nuke'
                break

        if active_nuke_msg:
            el_gevent = self._create_ui_element(
                'game_events',
                text=active_nuke_msg,
                element_type='text',
                alpha=1.0,
            )
            if el_gevent:
                elements.append(el_gevent)
            return

        # Otherwise, check important game events with 5s fade
        el_config = self.config.get('elements', {}).get('game_events', {})
        fade_time_s = el_config.get('fade_out_time')
        if fade_time_s is None:
            fade_time_s = self.config.get('fade_out_time', 5.0)
        fade_time_ms = int(fade_time_s * 1000)

        active_g_events = []
        for ev in self.event_log:
            if time_ms - fade_time_ms <= ev['time'] <= time_ms:
                if ev['is_important']:
                    active_g_events.append(ev)

        if active_g_events:
            recent_ev = active_g_events[-1]
            elapsed_ms = time_ms - recent_ev['time']
            alpha = get_fade_alpha(elapsed_ms, fade_time_ms, anim)
            el_gevent = self._create_ui_element(
                'game_events',
                text=recent_ev['desc'],
                element_type='text',
                alpha=alpha,
            )
            if el_gevent:
                elements.append(el_gevent)

    def _add_event_hud_elements(
        self,
        elements: list[UIElement],
        players: dict[str, LFReplayPlayerState],
        teams: dict[int, LFReplayTeamState],
        time_ms: int,
    ) -> None:
        """Adds recent event notification HUD elements.

        Args:
            elements: List of visual elements to append to.
            players: Current player states.
            teams: Current team states.
            time_ms: Current millisecond timestamp.
        """
        anim = self.config.get('animation', 'ease-in-out')

        self._add_player_event_hud_element(
            elements=elements,
            time_ms=time_ms,
            anim=anim,
        )
        self._add_game_event_hud_element(
            elements=elements,
            time_ms=time_ms,
            anim=anim,
        )

        player_to_color: dict[str, str] = {}
        for pid, player in players.items():
            name = self.entity_names.get(pid, pid)
            t_state = teams.get(player.team_index)
            color = t_state.color_rgb if t_state else '#ffffff'
            player_to_color[name] = color

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

        Args:
            time_ms: The millisecond timestamp.

        Returns:
            list[UIElement]: The list of active UI HUD elements.
        """
        players, teams = self._get_state_at(time_ms)
        elements: list[UIElement] = []

        self._add_global_hud_elements(
            elements=elements, teams=teams, players=players, time_ms=time_ms
        )
        self._add_player_hud_elements(
            elements=elements, players=players, time_ms=time_ms
        )
        self._add_event_hud_elements(
            elements=elements, players=players, teams=teams, time_ms=time_ms
        )

        return elements
