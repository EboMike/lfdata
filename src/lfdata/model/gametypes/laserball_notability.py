"""Game notability and highlight tagline evaluation for Laserball games.

This module evaluates Laserball games and player statistics to generate
highlight taglines and identify notable game conditions.

Usage example:
    from lfdata.model.gametypes.laserball_notability import (
        LaserballNotabilityEvaluator,
    )

    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player='Striker')
    print(f'Condition: {result.condition}, Tagline: {result.tagline}')
"""

from typing import TYPE_CHECKING

from lfdata.model.gametypes.laserball_constants import (
    LASERBALL_NOTABILITY_EXTRA_BLOCKS_THRESHOLD,
    LASERBALL_NOTABILITY_HIGH_HIT_DIFF_MIN,
    LASERBALL_NOTABILITY_MIN_ASSISTS,
    LASERBALL_NOTABILITY_MIN_CLEARS,
    LASERBALL_NOTABILITY_MIN_GOALS,
    LASERBALL_NOTABILITY_MIN_STEALS,
)
from lfdata.model.gametypes.laserball_notability_condition import (
    LaserballNotabilityCondition,
)
from lfdata.model.gametypes.laserball_notability_result import (
    LaserballNotabilityResult,
)

if TYPE_CHECKING:
    from lfdata.model.gametypes.laserball_stats import LaserballStats
    from lfdata.model.objects.entity import GameEntity
    from lfdata.model.objects.game import LFGame
    from lfdata.model.objects.player import Player

__all__ = [
    'LaserballNotabilityCondition',
    'LaserballNotabilityEvaluator',
    'LaserballNotabilityResult',
]


class LaserballNotabilityEvaluator:
    """Evaluates Laserball games for notability conditions and taglines."""

    def evaluate(
        self,
        game: 'LFGame',
        focus_player: 'GameEntity | Player | str | None' = None,
    ) -> LaserballNotabilityResult:
        """Evaluates game notability and determines the highlight tagline.

        Checks conditions in priority order:
        1. Focus player had at least one goal: '{goals} goals' (or '1 goal')
        2. Focus player had at least one assist: '{assists} assists' (or '1 assist')
        3. Focus player had multiple steals: '{steals} steals'
        4. Focus player hit diff over 1.4: '{hit_diff} hit diff'
        5. Focus player cleared more than once: '{clears} clears'
        In any of these cases, if blocks > 20, appends ', {blocks} blocks'.
        Fallback: '{blocks}/{blocked_by_others} blocks'.

        Args:
            game: The Laserball LFGame model to evaluate.
            focus_player: Optional focus player entity, model, or identifier.

        Returns:
            LaserballNotabilityResult: Evaluation result with condition and tagline.
        """
        focus_entity = self._resolve_focus_player(game, focus_player)
        if focus_entity is None:
            return LaserballNotabilityResult(
                condition=None,
                tagline='Laserball game',
            )

        stats = self._get_player_stats(game, focus_entity.entity_id)
        if stats is None:
            return LaserballNotabilityResult(
                condition=None,
                tagline='Laserball game',
            )

        goals = stats.goals or 0
        assists = stats.assists or 0
        steals = stats.steals or 0
        clears = stats.clears or 0
        blocks = stats.blocks or 0
        hit_diff = stats.hit_diff
        extra = self._extra_blocks(stats)

        # 1. At least one goal
        if goals >= LASERBALL_NOTABILITY_MIN_GOALS:
            base = '1 goal' if goals == 1 else f'{goals} goals'
            return LaserballNotabilityResult(
                condition=LaserballNotabilityCondition.GOALS,
                tagline=f'{base}{extra}',
                details={'goals': goals, 'blocks': blocks},
            )

        # 2. At least one assist
        if assists >= LASERBALL_NOTABILITY_MIN_ASSISTS:
            base = '1 assist' if assists == 1 else f'{assists} assists'
            return LaserballNotabilityResult(
                condition=LaserballNotabilityCondition.ASSISTS,
                tagline=f'{base}{extra}',
                details={'assists': assists, 'blocks': blocks},
            )

        # 3. Multiple steals
        if steals >= LASERBALL_NOTABILITY_MIN_STEALS:
            return LaserballNotabilityResult(
                condition=LaserballNotabilityCondition.STEALS,
                tagline=f'{steals} steals{extra}',
                details={'steals': steals, 'blocks': blocks},
            )

        # 4. Hit diff over 1.4
        if (
            hit_diff is not None
            and hit_diff > LASERBALL_NOTABILITY_HIGH_HIT_DIFF_MIN
        ):
            return LaserballNotabilityResult(
                condition=LaserballNotabilityCondition.HIGH_HIT_DIFF,
                tagline=f'{hit_diff:.1f} hit diff{extra}',
                details={'hit_diff': hit_diff, 'blocks': blocks},
            )

        # 5. Cleared more than once
        if clears >= LASERBALL_NOTABILITY_MIN_CLEARS:
            return LaserballNotabilityResult(
                condition=LaserballNotabilityCondition.CLEARS,
                tagline=f'{clears} clears{extra}',
                details={'clears': clears, 'blocks': blocks},
            )

        # Fallback: '{blocks}/{blocked_by_others} blocks'
        blocked_by_others = stats.times_blocked or stats.times_zapped or 0
        return LaserballNotabilityResult(
            condition=LaserballNotabilityCondition.BLOCKS_SUMMARY,
            tagline=f'{blocks}/{blocked_by_others} blocks',
            details={'blocks': blocks, 'blocked_by_others': blocked_by_others},
        )

    def _extra_blocks(self, stats: 'LaserballStats') -> str:
        """Returns extra blocks text if the player had over 20 blocks.

        Args:
            stats: Player laserball stats.

        Returns:
            str: Appended block count string or empty string.
        """
        blocks = stats.blocks or 0
        if blocks > LASERBALL_NOTABILITY_EXTRA_BLOCKS_THRESHOLD:
            return f', {blocks} blocks'
        return ''

    def _get_player_stats(
        self, game: 'LFGame', entity_id: str
    ) -> 'LaserballStats | None':
        """Retrieves stats for an entity, running replay simulation if needed.

        Args:
            game: The game instance.
            entity_id: The target entity ID.

        Returns:
            LaserballStats | None: The player's stats or None.
        """
        if not game.laserball_stats and game.events:
            from lfdata.replay import LFReplaySystem

            LFReplaySystem(game).playback()

        for stat in game.laserball_stats:
            if stat.entity_id == entity_id:
                return stat
        return None

    def _resolve_focus_player(
        self,
        game: 'LFGame',
        focus_player: 'GameEntity | Player | str | None',
    ) -> 'GameEntity | None':
        """Resolves a focus player parameter to a GameEntity instance.

        If focus_player is None, picks the top player in the game.

        Args:
            game: The game containing entities and stats.
            focus_player: Entity, Player, ID, or codename string.

        Returns:
            GameEntity | None: The matching entity, or None if not found.
        """
        if focus_player is None:
            return self._pick_default_focus_player(game)

        if hasattr(focus_player, 'entity_id') and hasattr(focus_player, 'type'):
            return focus_player  # type: ignore[return-value]

        if hasattr(focus_player, 'id') and not hasattr(
            focus_player, 'entity_id'
        ):
            for entity in game.entities:
                if (
                    entity.player_id == focus_player.id  # type: ignore[union-attr]
                    or entity.player == focus_player
                ):
                    return entity
            return None

        target_str = str(focus_player).strip().lower()
        for entity in game.entities:
            if entity.type != 'player':
                continue
            if entity.entity_id.lower() == target_str:
                return entity
            if entity.desc.lower() == target_str:
                return entity
            if entity.battlesuit and entity.battlesuit.lower() == target_str:
                return entity
            if entity.player:
                if (
                    entity.player.codename
                    and entity.player.codename.lower() == target_str
                ):
                    return entity
                if (
                    entity.player.real_name
                    and entity.player.real_name.lower() == target_str
                ):
                    return entity

        return None

    def _pick_default_focus_player(self, game: 'LFGame') -> 'GameEntity | None':
        """Picks a default focus player when none was explicitly provided.

        Args:
            game: The game containing entities and stats.

        Returns:
            GameEntity | None: Highest scoring player entity, or first player.
        """
        if game.laserball_stats:
            best_stat = max(
                game.laserball_stats,
                key=lambda s: (s.score, s.goals or 0, s.assists or 0),
            )
            for entity in game.entities:
                if entity.entity_id == best_stat.entity_id:
                    return entity

        players = [e for e in game.entities if e.type == 'player']
        if players:
            return max(players, key=lambda e: e.end_score or 0)
        return None
