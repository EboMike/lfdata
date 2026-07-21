"""Verification of replay simulation final states against TDF values."""

import dataclasses

from lfdata.model import LFGame, Sm5Stats
from lfdata.replay.replay import LFReplaySystem


@dataclasses.dataclass(frozen=True)
class PlayerDiscrepancy:
    """Represents a discrepancy between a player's computed and expected state.

    Attributes:
        field: The name of the field (e.g., 'score', 'lives', 'shots').
        computed: The value computed by the replay simulation.
        expected: The expected value from the TDF file.
    """

    field: str
    computed: int
    expected: int


class LFReplayVerifier:
    """Verifier for comparing replay simulation end states with TDF data."""

    def __init__(self, game: LFGame) -> None:
        """Initializes the verifier.

        Args:
            game: The game to verify.
        """
        self.game = game

    def get_discrepancies(
        self, replay: LFReplaySystem
    ) -> dict[str, list[PlayerDiscrepancy]]:
        """Finds all status discrepancies between replay and TDF data.

        Args:
            replay: The simulated replay system.

        Returns:
            dict[str, list[PlayerDiscrepancy]]: A dictionary mapping player
                entity IDs to their list of discrepancies.
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

            p_discrepancies = []

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

    def verify(self) -> bool:
        """Runs the verification process and prints results.

        Returns:
            bool: True if there were no initial discrepancies, False otherwise.
        """
        print('Running initial replay simulation (no alignment)...')
        replay_no_align = LFReplaySystem(self.game, align_stats=False)
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

        print('\nAttempting to resolve discrepancies using replay alignment...')
        replay_aligned = LFReplaySystem(self.game, align_stats=True)
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

        return False
