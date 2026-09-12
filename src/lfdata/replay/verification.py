"""Verification of replay simulation final states against TDF values.

This module provides validation logic (LFReplayVerifier) that compares
simulated end-of-game player scores, lives, and SM5 stats against official
values recorded in TDF headers and stat records.

Usage example:
    from lfdata.replay import LFReplayVerifier

    verifier = LFReplayVerifier(game=game)
    is_valid = verifier.verify()
    if not is_valid:
        print('Verification discrepancies detected.')
"""

from lfdata.model import LFGame, Sm5Stats
from lfdata.replay.diagnostics import LFReplayDiagnostics, PlayerDiscrepancy
from lfdata.replay.replay import LFReplaySystem


class LFReplayVerifier:
    """Validator comparing replay simulation results against official TDF data.

    Attributes:
        game: Input LFGame database model instance to verify.
        boost_grace_period_ms: Grace period in milliseconds for boost
            eligibility.
        candidate_grace_periods_ms: List of grace period values in milliseconds
            to evaluate if discrepancies occur.
    """

    def __init__(
        self,
        game: LFGame,
        boost_grace_period_ms: int = 700,
        candidate_grace_periods_ms: list[int] | None = None,
    ) -> None:
        """Initializes the verifier.

        Args:
            game: The game to verify.
            boost_grace_period_ms: Grace period in milliseconds for boost
                eligibility (defaults to 700, representing 0.7 seconds).
            candidate_grace_periods_ms: Optional list of grace period values
                in milliseconds to evaluate if discrepancies are encountered.
                Defaults to 0ms to 2000ms in increments of 50ms.
        """
        self.game = game
        self.boost_grace_period_ms = boost_grace_period_ms
        self.candidate_grace_periods_ms: list[int] = (
            candidate_grace_periods_ms
            if candidate_grace_periods_ms is not None
            else list(range(0, 2050, 50))
        )

    def get_discrepancies(
        self, replay: LFReplaySystem
    ) -> dict[str, list[PlayerDiscrepancy]]:
        """Finds all status discrepancies between replay and TDF data.

        Args:
            replay: The simulated replay system.

        Returns:
            dict[str, list[PlayerDiscrepancy]]: A dictionary mapping player
                entity IDs to their list of discrepancies.

        Usage:
            discrepancies = verifier.get_discrepancies(replay)
        """
        discrepancies: dict[str, list[PlayerDiscrepancy]] = {}

        stats_by_player: dict[str, Sm5Stats] = {}
        if self.game.sm5_stats:
            for s in self.game.sm5_stats:
                stats_by_player[s.entity_id] = s

        for entity in self.game.entities:
            if entity.type != 'player':
                continue

            p_state = replay.game_state.players.get(entity.entity_id)
            if not p_state:
                continue

            p_discrepancies: list[PlayerDiscrepancy] = []

            if entity.end_score is not None:
                if p_state.score != entity.end_score:
                    p_discrepancies.append(
                        PlayerDiscrepancy(
                            field='score',
                            computed=p_state.score,
                            expected=entity.end_score,
                        )
                    )

            if entity.entity_id in stats_by_player:
                s = stats_by_player[entity.entity_id]
                if p_state.lives != s.lives_left:
                    p_discrepancies.append(
                        PlayerDiscrepancy(
                            field='lives',
                            computed=p_state.lives,
                            expected=s.lives_left,
                        )
                    )
                if p_state.shots != s.shots_left:
                    p_discrepancies.append(
                        PlayerDiscrepancy(
                            field='shots',
                            computed=p_state.shots,
                            expected=s.shots_left,
                        )
                    )

            if p_discrepancies:
                discrepancies[entity.entity_id] = p_discrepancies

        return discrepancies

    def check_grace_periods(
        self, candidate_grace_periods_ms: list[int] | None = None
    ) -> tuple[list[int], list[int]]:
        """Tests different grace period values to check if any resolve issues.

        Runs simulations with each candidate grace period without alignment
        and evaluates whether final stats match TDF data without discrepancies.

        Args:
            candidate_grace_periods_ms: Optional list of grace period values in
                milliseconds to evaluate. Defaults to
                self.candidate_grace_periods_ms.

        Returns:
            tuple[list[int], list[int]]: A tuple containing:
                - List of grace periods in milliseconds that worked.
                - List of grace periods in milliseconds that didn't work.

        Usage:
            worked, failed = verifier.check_grace_periods()
        """
        candidates = (
            candidate_grace_periods_ms
            if candidate_grace_periods_ms is not None
            else self.candidate_grace_periods_ms
        )
        working_gps: list[int] = []
        failing_gps: list[int] = []

        for gp_ms in candidates:
            replay = LFReplaySystem(
                self.game,
                align_stats=False,
                boost_grace_period_ms=gp_ms,
            )
            replay.run()
            if not self.get_discrepancies(replay):
                working_gps.append(gp_ms)
            else:
                failing_gps.append(gp_ms)

        return working_gps, failing_gps

    def verify(self) -> bool:
        """Runs the verification process and prints results.

        Returns:
            bool: True if there were no initial discrepancies, False otherwise.

        Usage:
            is_valid = verifier.verify()
        """
        print('Running initial replay simulation (no alignment)...')
        replay_no_align = LFReplaySystem(
            self.game,
            align_stats=False,
            boost_grace_period_ms=self.boost_grace_period_ms,
        )
        replay_no_align.run()

        discrepancies = self.get_discrepancies(replay_no_align)

        if not discrepancies:
            print('No discrepancies found between replay and TDF end states.')
            return True

        print('Discrepancies found:')
        for entity_id, p_discs in discrepancies.items():
            codename = next(
                (
                    e.desc
                    for e in self.game.entities
                    if e.entity_id == entity_id
                ),
                entity_id,
            )
            print(f'Player {codename} ({entity_id}):')
            for d in p_discs:
                print(
                    f'  - {d.field}: computed {d.computed} '
                    f'(expected {d.expected})'
                )

        diagnostics = LFReplayDiagnostics(
            game=self.game,
            replay=replay_no_align,
            boost_grace_period_ms=self.boost_grace_period_ms,
        )
        diagnostics.dump_mismatches(discrepancies=discrepancies)

        print('\nAttempting to resolve discrepancies using replay alignment...')
        replay_aligned = LFReplaySystem(
            self.game,
            align_stats=True,
            boost_grace_period_ms=self.boost_grace_period_ms,
        )
        replay_aligned.run()

        # Check if alignment succeeded
        aligned_discrepancies = self.get_discrepancies(replay_aligned)
        if not aligned_discrepancies:
            print('Stats aligned successfully.')
        else:
            print(
                'Warning: Alignment failed to fully resolve all discrepancies.'
            )

        if replay_aligned.resolved_ambiguities:
            print('\nParticular events (boosts) that caused discrepancies:')
            for dec in replay_aligned.resolved_ambiguities:
                time_ms = dec['time_ms']
                player_id = dec['player_id']
                codename = replay_aligned.entity_names.get(player_id, player_id)
                event_type_name = (
                    'Ammo Boost'
                    if dec['event_type'] == '0510'
                    else 'Life Boost'
                )
                print(
                    f'  - At {time_ms} ms: {codename} ({player_id}) '
                    f'{event_type_name} resolved to {dec["chosen"]} '
                    f'(default: {dec["default"]})'
                )
        else:
            print('\nNo specific boost override events could be determined.')

        print('\nEvaluating different grace period values...')
        worked_gps, failed_gps = self.check_grace_periods()
        if worked_gps:
            worked_str = ', '.join(f'{v} ms' for v in worked_gps)
            print(f'Grace period values that worked: {worked_str}')
        else:
            print('Grace period values that worked: none')

        if failed_gps:
            failed_str = ', '.join(f'{v} ms' for v in failed_gps)
            print(f"Grace period values that didn't work: {failed_str}")
        else:
            print("Grace period values that didn't work: none")

        return False
