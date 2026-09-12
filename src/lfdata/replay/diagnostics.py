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

from lfdata.model import GameEvent, LFGame
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

        for info in mismatches:
            self._dump_player_diagnostics(info)

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
