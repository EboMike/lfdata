"""Diagnostics for replay state mismatches and ambiguous events.

This module provides diagnostic utilities to inspect players with score,
life, or ammo mismatches, analyze relevant team boosts and nearby state
transitions within a 2000ms window, and assess which boosts may have been
incorrectly applied or skipped.

Usage example:
    from lfdata.replay.diagnostics import LFReplayDiagnostics

    diagnostics = LFReplayDiagnostics(game=game, replay=replay)
    diagnostics.dump_mismatches(discrepancies=discrepancies)
"""

import dataclasses

from lfdata.model import GameEvent, LFGame, LFRole
from lfdata.replay.record import LFReplayEventRecord
from lfdata.replay.replay import LFReplaySystem
from lfdata.replay.state import LFReplayPlayerState


@dataclasses.dataclass(frozen=True)
class PlayerDiscrepancy:
    """Discrepancy container between simulated and expected TDF player metrics.

    Attributes:
        field: Metric attribute name string (e.g. 'score', 'lives', 'shots').
        computed: Simulated value integer computed by replay system.
        expected: Official expected value integer from TDF file.
    """

    field: str
    computed: int
    expected: int


def format_timestamp_ms(time_ms: int) -> str:
    """Formats millisecond game time into MM:SS.sss display format.

    Args:
        time_ms: Millisecond timestamp.

    Returns:
        str: Formatted string in MM:SS.sss format.

    Usage:
        formatted = format_timestamp_ms(170566)
    """
    total_ms = max(0, time_ms)
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) / 1000.0
    return f'{minutes:02d}:{seconds:06.3f}'


def get_state_label(state: int) -> str:
    """Returns a readable string label for an LF player state integer.

    Args:
        state: State integer (0 for Up, 2 for Resettable, 3 for Down).

    Returns:
        str: Readable state label string.

    Usage:
        label = get_state_label(3)
    """
    if state == 0:
        return 'Up'
    if state == 2:
        return 'Resettable'
    if state == 3:
        return 'Down'
    return f'Unknown({state})'


@dataclasses.dataclass(frozen=True)
class PlayerMismatchInfo:
    """Summary of discrepancies for a single player.

    Attributes:
        entity_id: Entity ID of the mismatched player.
        codename: Codename or display name of the player.
        lives_discrepancy: Discrepancy for lives if present, or None.
        shots_discrepancy: Discrepancy for shots/ammo if present, or None.
    """

    entity_id: str
    codename: str
    lives_discrepancy: PlayerDiscrepancy | None = None
    shots_discrepancy: PlayerDiscrepancy | None = None


@dataclasses.dataclass(frozen=True)
class GameTerminationInfo:
    """Information regarding game termination and duration completion.

    Attributes:
        scheduled_duration_ms: Scheduled mission duration from header, or None.
        game_ended_at_ms: Actual millisecond timestamp when game ended.
        ran_full_distance: True if game completed its full scheduled duration.
        elimination_time_ms: Timestamp if ended by team elimination, or None.
        eliminated_team_indices: List of eliminated team indices.
        reason: Explanation string for termination.
    """

    scheduled_duration_ms: int | None
    game_ended_at_ms: int
    ran_full_distance: bool
    elimination_time_ms: int | None
    eliminated_team_indices: list[int]
    reason: str


@dataclasses.dataclass(frozen=True)
class LateEventRecord:
    """An event near game end that changed a player's metric.

    Attributes:
        time_ms: Timestamp in milliseconds when the event occurred.
        delta_to_end_ms: Relative delta in ms to game end (negative before end).
        description: Printable description of the event action.
        delta: Value change caused by the event (e.g. -1 for shot/zap).
    """

    time_ms: int
    delta_to_end_ms: int
    description: str
    delta: int


@dataclasses.dataclass(frozen=True)
class LateEventCutoffAnalysis:
    """Analysis of whether discounting late events resolves a discrepancy.

    Attributes:
        field: Metric name string ('shots' or 'lives').
        diff: Discrepancy amount (computed - expected).
        events: List of late events that would need to be discounted.
        window_ms: Milliseconds before game end of earliest event, or None.
        can_be_prevented: True if discounting these events resolves discrepancy.
    """

    field: str
    diff: int
    events: list[LateEventRecord]
    window_ms: int | None
    can_be_prevented: bool


def describe_player_state_at_ms(
    player: LFReplayPlayerState, current_time_ms: int
) -> tuple[str, bool]:
    """Describes player state at timestamp and whether they can be up soon.

    Args:
        player: Replay player state instance.
        current_time_ms: Millisecond timestamp to inspect.

    Returns:
        tuple[str, bool]: State description string and boolean indicating if
            player is Up or can be Up within a few seconds (<= 5000ms).

    Usage:
        desc, can_be_up = describe_player_state_at_ms(player, 680952)
    """
    if player.is_eliminated():
        return f'Eliminated ({player.lives} lives)', False

    if player.has_authoritative_state:
        st = player.get_state_at(current_time_ms)
        if st == 0:
            return 'Up (State 0)', True
        if st == 2:
            return 'Resettable (State 2) - can reset immediately', True
        down_start = player.get_down_start_time_ms(current_time_ms)
        if down_start is not None:
            elapsed_ms = current_time_ms - down_start
            if elapsed_ms >= 4000:
                return 'Resettable (State 3, safe time elapsed)', True
            rem_ms = 4000 - elapsed_ms
            if rem_ms <= 5000:
                return f'Down (State 3, {rem_ms} ms until resettable)', True
            return f'Down (State 3, {rem_ms} ms until resettable)', False
        return 'Down (State 3)', False

    if not player.is_down(current_time_ms):
        return 'Up', True
    if player.is_resettable(current_time_ms):
        return 'Resettable - can reset immediately', True
    rem_ms = max(0, player.downtime_ends_at_ms - current_time_ms)
    if rem_ms <= 5000:
        return f'Down ({rem_ms} ms remaining)', True
    return f'Down ({rem_ms} ms remaining)', False


class LFReplayDiagnostics:
    """Analyzer and diagnostic reporter for replay simulation discrepancies.

    Inspects discrepancies, correlates them with team boost events, evaluates
    player state transitions within a ±2000ms window, and prints detailed
    diagnostic assessments of possibly misapplied boosts.

    Attributes:
        game: Input LFGame database model instance.
        replay: Simulated LFReplaySystem instance.
        boost_grace_period_ms: Grace period in milliseconds for boost
            eligibility.
    """

    def __init__(
        self,
        game: LFGame,
        replay: LFReplaySystem,
        boost_grace_period_ms: int = 700,
    ) -> None:
        """Initializes the diagnostics analyzer.

        Args:
            game: The game database model.
            replay: The simulated replay system.
            boost_grace_period_ms: Grace period in milliseconds for boost
                eligibility (defaults to 700).

        Usage:
            diag = LFReplayDiagnostics(game, replay, boost_grace_period_ms=700)
        """
        self.game = game
        self.replay = replay
        self.boost_grace_period_ms = boost_grace_period_ms
        self._metric_deltas: (
            dict[tuple[str, str], list[tuple[LFReplayEventRecord, int]]] | None
        ) = None

    def _build_player_metric_deltas(
        self,
    ) -> dict[tuple[str, str], list[tuple[LFReplayEventRecord, int]]]:
        """Calculates per-record metric deltas for each player.

        Returns:
            dict[tuple[str, str], list[tuple[LFReplayEventRecord, int]]]:
                Mapping of (entity_id, field) to list of (record, delta) pairs.
        """
        if self._metric_deltas is not None:
            return self._metric_deltas

        curr_vals: dict[str, dict[str, int]] = {}
        for p in self.replay.game_state.players.values():
            curr_vals[p.entity_id] = {
                'shots': p.role.start_shots,
                'lives': p.role.start_lives,
            }

        result: dict[
            tuple[str, str], list[tuple[LFReplayEventRecord, int]]
        ] = {}
        for rec in self.replay.records:
            for pid, ch in rec.player_changes.items():
                if pid not in curr_vals:
                    continue
                for field in ('shots', 'lives'):
                    if field in ch:
                        delta = ch[field] - curr_vals[pid][field]
                        curr_vals[pid][field] = ch[field]
                        if delta != 0:
                            key = (pid, field)
                            result.setdefault(key, []).append((rec, delta))

        self._metric_deltas = result
        return result

    def analyze_late_event_cutoff(
        self,
        entity_id: str,
        field: str,
        diff: int,
        end_time_ms: int,
        max_window_ms: int = 15000,
    ) -> LateEventCutoffAnalysis:
        """Analyzes if discounting late events could resolve the discrepancy.

        Args:
            entity_id: Player entity ID.
            field: Metric name ('shots' or 'lives').
            diff: Difference (computed - expected).
            end_time_ms: Timestamp in milliseconds when the game ended.
            max_window_ms: Window in milliseconds before game end to inspect
                (defaults to 15000 ms / 15 seconds).

        Returns:
            LateEventCutoffAnalysis: Result of the late cutoff analysis.

        Usage:
            res = diag.analyze_late_event_cutoff('p1', 'shots', -2, 680000)
        """
        all_deltas = self._build_player_metric_deltas()
        records_and_deltas = all_deltas.get((entity_id, field), [])

        matching_events: list[LateEventRecord] = []
        accumulated = 0
        target_amount = abs(diff)

        for rec, delta in reversed(records_and_deltas):
            if rec.time_ms > end_time_ms:
                continue
            time_before_end_ms = end_time_ms - rec.time_ms
            if time_before_end_ms > max_window_ms:
                break

            if (diff < 0 and delta < 0) or (diff > 0 and delta > 0):
                change_mag = abs(delta)
                matching_events.append(
                    LateEventRecord(
                        time_ms=rec.time_ms,
                        delta_to_end_ms=-time_before_end_ms,
                        description=rec.description,
                        delta=delta,
                    )
                )
                accumulated += change_mag
                if accumulated >= target_amount:
                    break

        can_prevent = accumulated == target_amount
        window_ms = None
        if matching_events:
            window_ms = end_time_ms - matching_events[-1].time_ms

        return LateEventCutoffAnalysis(
            field=field,
            diff=diff,
            events=matching_events,
            window_ms=window_ms,
            can_be_prevented=can_prevent,
        )

    def _dump_late_event_cutoff(
        self, analysis: LateEventCutoffAnalysis, end_time_ms: int
    ) -> None:
        """Prints late-game event cutoff diagnostic analysis.

        Args:
            analysis: LateEventCutoffAnalysis result record.
            end_time_ms: Timestamp in milliseconds when the game ended.
        """
        field_name = analysis.field
        diff = analysis.diff

        print('\n  Late-Game Event Cutoff Analysis:')
        if analysis.can_be_prevented and analysis.window_ms is not None:
            count = len(analysis.events)
            seconds = analysis.window_ms / 1000.0
            earliest_ms = analysis.events[-1].time_ms
            earliest_str = format_timestamp_ms(earliest_ms)
            noun = 'event' if count == 1 else 'events'
            print(
                f'    - LIKELY RESOLUTION: If the last {count} {field_name} '
                f'{noun} in the final {seconds:.1f} seconds '
                f'(after {earliest_ms} ms [{earliest_str}]) were NOT counted, '
                f'the {diff:+d} {field_name} discrepancy would be '
                'completely prevented.'
            )
            print('    - Events that would be discounted:')
            for ev in reversed(analysis.events):
                ev_str = format_timestamp_ms(ev.time_ms)
                print(
                    f'      * {ev.time_ms} ms ({ev_str}) '
                    f'[{ev.delta_to_end_ms} ms before game end]: '
                    f'{ev.description} (delta: {ev.delta:+d} {field_name})'
                )
        elif analysis.events:
            count = len(analysis.events)
            print(
                f'    - In the final 15.0 seconds of the game, {count} '
                f'event(s) affected {field_name}, but discounting them does '
                f'not match the discrepancy of {diff:+d} {field_name}.'
            )
        else:
            print(
                f'    - No {field_name}-modifying events occurred for this '
                'player in the final 15.0 seconds of the game. The '
                'discrepancy cannot be explained by discounting late-game '
                'events.'
            )

    def build_mismatch_infos(
        self, discrepancies: dict[str, list[PlayerDiscrepancy]]
    ) -> list[PlayerMismatchInfo]:
        """Extracts PlayerMismatchInfo list from discrepancy mapping.

        Args:
            discrepancies: Mapping of player entity IDs to their discrepancies.

        Returns:
            list[PlayerMismatchInfo]: Formatted list of player mismatch records.

        Usage:
            infos = diag.build_mismatch_infos(discrepancies)
        """
        results: list[PlayerMismatchInfo] = []
        for entity_id, p_discs in discrepancies.items():
            codename = next(
                (
                    e.desc
                    for e in self.game.entities
                    if e.entity_id == entity_id
                ),
                entity_id,
            )
            lives_disc = next(
                (d for d in p_discs if d.field == 'lives'),
                None,
            )
            shots_disc = next(
                (d for d in p_discs if d.field == 'shots'),
                None,
            )
            if lives_disc or shots_disc:
                results.append(
                    PlayerMismatchInfo(
                        entity_id=entity_id,
                        codename=codename,
                        lives_discrepancy=lives_disc,
                        shots_discrepancy=shots_disc,
                    )
                )
        return results

    def analyze_game_termination(self) -> GameTerminationInfo:
        """Analyzes how the game ended and whether it ran its full distance.

        Returns:
            GameTerminationInfo: Data object summarizing termination details.

        Usage:
            term_info = diag.analyze_game_termination()
        """
        end_ms = getattr(self.replay, 'game_ended_at_ms', None)
        if not isinstance(end_ms, int):
            end_ms = None
        if end_ms is None:
            for ev in self.game.events:
                if ev.event_type == '0101':
                    end_ms = ev.time
                    break
            if end_ms is None and self.game.events:
                end_ms = max(e.time for e in self.game.events)
            if end_ms is None:
                end_ms = self.game.duration or 0

        scheduled_ms = self.game.duration
        elim_ms = getattr(self.replay, 'first_team_elimination_time_ms', None)
        if not isinstance(elim_ms, int):
            elim_ms = None

        eliminated_teams: list[int] = []
        all_teams = {
            p.team_index for p in self.replay.game_state.players.values()
        }
        for team_idx in all_teams:
            team_players = [
                p
                for p in self.replay.game_state.players.values()
                if p.team_index == team_idx
            ]
            if team_players and all(p.is_eliminated() for p in team_players):
                eliminated_teams.append(team_idx)

        tolerance_ms = 5000
        if scheduled_ms is not None and scheduled_ms > 0:
            if elim_ms is not None or eliminated_teams:
                ran_full = False
                reason = (
                    f'Ended short due to team elimination at '
                    f'{elim_ms or end_ms} ms'
                )
            elif end_ms >= scheduled_ms - tolerance_ms:
                ran_full = True
                reason = 'Ran full distance (completed scheduled duration)'
            else:
                ran_full = False
                reason = (
                    'Ended short (early termination without team elimination)'
                )
        else:
            ran_full = False
            reason = 'Game duration not specified in header'

        return GameTerminationInfo(
            scheduled_duration_ms=scheduled_ms,
            game_ended_at_ms=end_ms,
            ran_full_distance=ran_full,
            elimination_time_ms=elim_ms,
            eliminated_team_indices=sorted(eliminated_teams),
            reason=reason,
        )

    def _dump_game_termination(self, info: GameTerminationInfo) -> None:
        """Prints game termination summary.

        Args:
            info: GameTerminationInfo record to print.
        """
        print('\nGame Termination Analysis:')
        end_str = format_timestamp_ms(info.game_ended_at_ms)
        if info.scheduled_duration_ms:
            sched_str = format_timestamp_ms(info.scheduled_duration_ms)
            print(
                f'  Scheduled Duration: {info.scheduled_duration_ms} ms '
                f'({sched_str})'
            )
            print(
                f'  Actual Game End:    {info.game_ended_at_ms} ms ({end_str})'
            )
            if info.ran_full_distance:
                print('  Result: The game ran its full distance.')
            else:
                diff_ms = max(
                    0, info.scheduled_duration_ms - info.game_ended_at_ms
                )
                diff_str = format_timestamp_ms(diff_ms)
                print(
                    f'  Result: The game ended short by {diff_ms} ms '
                    f'({diff_str}).'
                )
                if info.eliminated_team_indices:
                    teams_str = ', '.join(
                        f'Team {t}' for t in info.eliminated_team_indices
                    )
                    elim_time_str = ''
                    if info.elimination_time_ms:
                        et_str = format_timestamp_ms(info.elimination_time_ms)
                        elim_time_str = (
                            f' at {info.elimination_time_ms} ms ({et_str})'
                        )
                    print(
                        f'  Reason: Team elimination{elim_time_str} '
                        f'({teams_str} eliminated).'
                    )
                else:
                    print(f'  Reason: {info.reason}.')
        else:
            print(f'  Actual Game End: {info.game_ended_at_ms} ms ({end_str})')
            print(f'  Result: {info.reason}.')

    def dump_mismatches(
        self, discrepancies: dict[str, list[PlayerDiscrepancy]]
    ) -> None:
        """Prints detailed diagnostics for all players with discrepancies.

        Args:
            discrepancies: Mapping of player entity IDs to their discrepancies.

        Returns:
            None.

        Usage:
            diag.dump_mismatches(discrepancies)
        """
        mismatches = self.build_mismatch_infos(discrepancies)
        if not mismatches:
            return

        separator = '=' * 72
        print('\n' + separator)
        print('DISCREPANCY DIAGNOSTICS & AMBIGUOUS EVENT ANALYSIS')
        print(separator)

        term_info = self.analyze_game_termination()
        self._dump_game_termination(term_info)

        for info in mismatches:
            self._dump_player_diagnostics(info)
            if info.lives_discrepancy:
                diff = (
                    info.lives_discrepancy.computed
                    - info.lives_discrepancy.expected
                )
                lives_cutoff = self.analyze_late_event_cutoff(
                    entity_id=info.entity_id,
                    field='lives',
                    diff=diff,
                    end_time_ms=term_info.game_ended_at_ms,
                )
                self._dump_late_event_cutoff(
                    analysis=lives_cutoff,
                    end_time_ms=term_info.game_ended_at_ms,
                )
            if info.shots_discrepancy:
                diff = (
                    info.shots_discrepancy.computed
                    - info.shots_discrepancy.expected
                )
                shots_cutoff = self.analyze_late_event_cutoff(
                    entity_id=info.entity_id,
                    field='shots',
                    diff=diff,
                    end_time_ms=term_info.game_ended_at_ms,
                )
                self._dump_late_event_cutoff(
                    analysis=shots_cutoff,
                    end_time_ms=term_info.game_ended_at_ms,
                )
            self._dump_post_game_eligibility(
                info, end_time_ms=term_info.game_ended_at_ms
            )

    def _dump_player_diagnostics(self, info: PlayerMismatchInfo) -> None:
        """Dumps diagnostics for a specific mismatched player.

        Args:
            info: Discrepancy info for the player.
        """
        player = self.replay.game_state.players.get(info.entity_id)
        if not player:
            return

        sub_sep = '-' * 72
        print(f'\n{sub_sep}')
        print(
            f'Player {info.codename} ({info.entity_id})'
            f' - Team {player.team_index}'
        )
        print(sub_sep)

        if info.lives_discrepancy:
            d = info.lives_discrepancy
            diff = d.computed - d.expected
            print(
                f'Lives mismatch: computed={d.computed}, expected={d.expected} '
                f'(difference: {diff:+d} lives)'
            )
            self._analyze_boost_type(
                player=player,
                event_type='0512',
                boost_name='Team Life Boost',
                diff_amount=diff,
                field_name='lives',
            )

        if info.shots_discrepancy:
            d = info.shots_discrepancy
            diff = d.computed - d.expected
            print(
                f'Ammo mismatch: computed={d.computed}, expected={d.expected} '
                f'(difference: {diff:+d} shots)'
            )
            self._analyze_boost_type(
                player=player,
                event_type='0510',
                boost_name='Team Ammo Boost',
                diff_amount=diff,
                field_name='shots',
            )

    def _analyze_boost_type(
        self,
        player: LFReplayPlayerState,
        event_type: str,
        boost_name: str,
        diff_amount: int,
        field_name: str,
    ) -> None:
        """Analyzes all team boosts of a given type for a player.

        Args:
            player: The player state.
            event_type: Event type code string ('0512' or '0510').
            boost_name: Display name of the boost.
            diff_amount: Computed minus expected value.
            field_name: Field name ('lives' or 'shots').
        """
        boost_events: list[GameEvent] = []
        for event in self.game.events:
            if event.event_type == event_type:
                actor = self.replay.game_state.players.get(
                    event.actor_entity_id or ''
                )
                if actor and actor.team_index == player.team_index:
                    boost_events.append(event)

        print(
            f'\nFound {len(boost_events)} {boost_name} event(s) '
            "on player's team:"
        )
        if not boost_events:
            print('  (No matching boost events found)')
            return

        for idx, boost in enumerate(boost_events, start=1):
            self._dump_single_boost_analysis(
                player=player,
                boost=boost,
                boost_index=idx,
                boost_name=boost_name,
                diff_amount=diff_amount,
                field_name=field_name,
            )

    def _dump_single_boost_analysis(
        self,
        player: LFReplayPlayerState,
        boost: GameEvent,
        boost_index: int,
        boost_name: str,
        diff_amount: int,
        field_name: str,
    ) -> None:
        """Analyzes and dumps a single boost event and surrounding activity.

        Args:
            player: The player state.
            boost: The boost game event.
            boost_index: 1-based index of the boost.
            boost_name: Display name of the boost.
            diff_amount: Computed minus expected value.
            field_name: Field name ('lives' or 'shots').
        """
        b_time_ms = boost.time
        b_str = format_timestamp_ms(b_time_ms)
        actor_name = next(
            (
                e.desc
                for e in self.game.entities
                if e.entity_id == boost.actor_entity_id
            ),
            boost.actor_entity_id,
        )

        print(
            f'\n[{boost_index}] {boost_name} at {b_time_ms} ms ({b_str}) '
            f'by {actor_name} ({boost.actor_entity_id}):'
        )

        # 1. State changes within 2000 ms before and after
        self._dump_state_changes(player=player, boost_time_ms=b_time_ms)

        # 2. Other events involving player within 2000 ms before and after
        self._dump_related_events(
            player=player, boost=boost, boost_time_ms=b_time_ms
        )

        # 3. Assessment of whether boost was applied or skipped
        self._dump_boost_assessment(
            player=player,
            boost_time_ms=b_time_ms,
            diff_amount=diff_amount,
            field_name=field_name,
        )

    def _dump_state_changes(
        self, player: LFReplayPlayerState, boost_time_ms: int
    ) -> None:
        """Prints state changes within ±2000ms of a boost timestamp.

        Args:
            player: The player state.
            boost_time_ms: Timestamp of the boost in milliseconds.
        """
        print('  State changes within 2000 ms:')
        state_entries = []
        if self.game.state_history:
            for sh in self.game.state_history:
                if (
                    sh.entity_id == player.entity_id
                    and abs(sh.time - boost_time_ms) <= 2000
                ):
                    state_entries.append(sh)

        if not state_entries:
            print('    (No state changes recorded within 2000 ms)')
            return

        for sh in state_entries:
            delta_ms = sh.time - boost_time_ms
            sh_str = format_timestamp_ms(sh.time)
            label = get_state_label(sh.state)
            print(
                f'    - {sh.time} ms ({sh_str}): State {sh.state} ({label}) '
                f'[delta: {delta_ms:+d} ms]'
            )

    def _dump_related_events(
        self, player: LFReplayPlayerState, boost: GameEvent, boost_time_ms: int
    ) -> None:
        """Prints related player events within ±2000ms of a boost timestamp.

        Args:
            player: The player state.
            boost: The boost game event.
            boost_time_ms: Timestamp of the boost in milliseconds.
        """
        print('  Other events regarding player within 2000 ms:')
        related: list[GameEvent] = []
        for e in self.game.events:
            if e is not boost and abs(e.time - boost_time_ms) <= 2000:
                if (
                    e.actor_entity_id == player.entity_id
                    or e.target_entity_id == player.entity_id
                ):
                    related.append(e)

        if not related:
            print('    (No other events recorded within 2000 ms)')
            return

        for e in related:
            delta_ms = e.time - boost_time_ms
            e_str = format_timestamp_ms(e.time)
            print(
                f'    - {e.time} ms ({e_str}): type={e.event_type} '
                f'action="{e.action}" actor={e.actor_entity_id} '
                f'target={e.target_entity_id} [delta: {delta_ms:+d} ms]'
            )

    def _dump_boost_assessment(
        self,
        player: LFReplayPlayerState,
        boost_time_ms: int,
        diff_amount: int,
        field_name: str,
    ) -> None:
        """Prints diagnostic assessment of boost eligibility and application.

        Args:
            player: The player state.
            boost_time_ms: Timestamp of the boost in milliseconds.
            diff_amount: Computed minus expected metric count.
            field_name: Name of the field ('lives' or 'shots').
        """
        is_down = player.is_down(boost_time_ms)
        down_start_ms = player.get_down_start_time_ms(boost_time_ms)

        print('  Assessment:')
        if is_down and down_start_ms is not None:
            elapsed_ms = boost_time_ms - down_start_ms
            down_str = format_timestamp_ms(down_start_ms)
            gp_ms = self.boost_grace_period_ms
            outside_by_ms = elapsed_ms - gp_ms

            print(
                f'    - Player was DOWN at boost time (went down at '
                f'{down_start_ms} ms [{down_str}], '
                f'{elapsed_ms} ms before boost).'
            )
            if elapsed_ms <= gp_ms:
                print(
                    f'    - Boost WAS applied in simulation (within '
                    f'{gp_ms} ms grace period).'
                )
                if diff_amount > 0:
                    print(
                        f'    - LIKELY PROBLEM: Computed {field_name} are '
                        f'higher than expected (+{diff_amount}). This boost '
                        'may have been incorrectly applied if the player '
                        'was already ineligible.'
                    )
            else:
                print(
                    f'    - Boost was NOT applied in simulation (exceeded '
                    f'{gp_ms} ms grace period by {outside_by_ms} ms).'
                )
                if diff_amount < 0:
                    print(
                        f'    - LIKELY PROBLEM: Computed {field_name} are '
                        f'lower than expected ({diff_amount}). This boost '
                        'may have been incorrectly skipped if the actual '
                        f'hardware grace period was at least {elapsed_ms} ms.'
                    )
        else:
            print(
                '    - Player was UP at boost time '
                '(boost applied in simulation).'
            )
            if diff_amount > 0:
                print(
                    f'    - Computed {field_name} are higher than expected '
                    f'(+{diff_amount}).'
                )

    def _dump_post_game_lives_eligibility(
        self,
        player: LFReplayPlayerState,
        diff: int,
        p_desc: str,
        p_can_up: bool,
        end_time_ms: int,
    ) -> None:
        """Evaluates and prints post-game lives reconciliation eligibility.

        Args:
            player: The player state.
            diff: Lives difference (computed - expected).
            p_desc: Player state description.
            p_can_up: Whether player can be Up within seconds of game end.
            end_time_ms: Game end timestamp in milliseconds.
        """
        if diff >= 0:
            return

        medics = [
            p
            for p in self.replay.game_state.players.values()
            if p.team_index == player.team_index and p.role == LFRole.MEDIC
        ]
        if not medics:
            print("    - No Medic found on player's team.")
            return

        gain = player.role.medic_lives_gain
        needed_lives = abs(diff)

        for medic in medics:
            m_entity = next(
                (
                    e
                    for e in self.game.entities
                    if e.entity_id == medic.entity_id
                ),
                None,
            )
            m_name = m_entity.desc if m_entity else medic.entity_id
            m_desc, m_can_up = describe_player_state_at_ms(medic, end_time_ms)

            print(
                f'    - Teammate Medic {m_name} ({medic.entity_id}): {m_desc}'
            )
            if not medic.is_eliminated() and m_can_up and p_can_up:
                print(
                    '    - Both player and Medic were eligible to be Up '
                    'in the seconds after game end: YES'
                )
                print(
                    f'    - Medic resupply gain for {player.role.name}: '
                    f'+{gain} lives'
                )
                if gain == needed_lives:
                    print(
                        f'    - ELIGIBLE: A single medic resupply (+{gain} '
                        'lives) in the seconds after game end would exactly '
                        f'account for the {diff} lives discrepancy.'
                    )
                else:
                    print(
                        f'    - PARTIALLY ELIGIBLE: Medic resupply (+{gain} '
                        f'lives) was possible, but discrepancy is {diff} lives.'
                    )
            elif medic.is_eliminated():
                print(
                    f'    - NOT ELIGIBLE: Medic {m_name} was eliminated at '
                    'game end.'
                )
            else:
                print(
                    '    - NOT ELIGIBLE: Player or Medic was down and could '
                    'not be Up within seconds of game end.'
                )

    def _dump_post_game_ammo_eligibility(
        self,
        player: LFReplayPlayerState,
        diff: int,
        p_desc: str,
        p_can_up: bool,
        end_time_ms: int,
    ) -> None:
        """Evaluates and prints post-game ammo reconciliation eligibility.

        Args:
            player: The player state.
            diff: Shots difference (computed - expected).
            p_desc: Player state description.
            p_can_up: Whether player can be Up within seconds of game end.
            end_time_ms: Game end timestamp in milliseconds.
        """
        if diff > 0:
            print(f'    - Player remaining shots at game end: {player.shots}')
            if not player.is_eliminated() and p_can_up and player.shots >= diff:
                print(
                    f'    - ELIGIBLE: Player was alive with {player.shots} '
                    f'shots remaining and could be Up ({p_desc}). The player '
                    f'could easily have fired {diff} shot(s) in the seconds '
                    'after game end to account for the discrepancy.'
                )
            elif player.shots < diff:
                print(
                    f'    - NOT ELIGIBLE: Player had only {player.shots} shots '
                    f'remaining, but needed {diff} shots.'
                )
            else:
                print(
                    '    - NOT ELIGIBLE: Player was eliminated or down and '
                    'could not fire shots after game end.'
                )
        elif diff < 0:
            ammo_carriers = [
                p
                for p in self.replay.game_state.players.values()
                if p.team_index == player.team_index and p.role == LFRole.AMMO
            ]
            if not ammo_carriers:
                print("    - No Ammo Carrier found on player's team.")
                return

            gain = player.role.ammo_shots_gain
            for ac in ammo_carriers:
                ac_entity = next(
                    (
                        e
                        for e in self.game.entities
                        if e.entity_id == ac.entity_id
                    ),
                    None,
                )
                ac_name = ac_entity.desc if ac_entity else ac.entity_id
                ac_desc, ac_can_up = describe_player_state_at_ms(
                    ac, end_time_ms
                )

                print(
                    f'    - Teammate Ammo Carrier {ac_name} ({ac.entity_id}): '
                    f'{ac_desc}'
                )
                if not ac.is_eliminated() and ac_can_up and p_can_up:
                    print(
                        f'    - ELIGIBLE: Ammo Carrier resupply (+{gain} '
                        f'shots) was possible (discrepancy is {diff} shots).'
                    )
                else:
                    print(
                        '    - NOT ELIGIBLE: Ammo Carrier was eliminated or '
                        'could not resupply after game end.'
                    )

    def _dump_post_game_eligibility(
        self, info: PlayerMismatchInfo, end_time_ms: int
    ) -> None:
        """Prints post-game discrepancy reconciliation eligibility.

        Args:
            info: Player mismatch record.
            end_time_ms: Timestamp in ms when game ended.
        """
        player = self.replay.game_state.players.get(info.entity_id)
        if not player:
            return

        end_str = format_timestamp_ms(end_time_ms)
        p_desc, p_can_up = describe_player_state_at_ms(player, end_time_ms)

        print(
            '\n  Post-Game Discrepancy Reconciliation '
            '(within seconds of game end):'
        )
        print(
            f'    - Player state at game end ({end_time_ms} ms [{end_str}]): '
            f'{p_desc}'
        )

        if info.lives_discrepancy:
            diff = (
                info.lives_discrepancy.computed
                - info.lives_discrepancy.expected
            )
            self._dump_post_game_lives_eligibility(
                player=player,
                diff=diff,
                p_desc=p_desc,
                p_can_up=p_can_up,
                end_time_ms=end_time_ms,
            )

        if info.shots_discrepancy:
            diff = (
                info.shots_discrepancy.computed
                - info.shots_discrepancy.expected
            )
            self._dump_post_game_ammo_eligibility(
                player=player,
                diff=diff,
                p_desc=p_desc,
                p_can_up=p_can_up,
                end_time_ms=end_time_ms,
            )
