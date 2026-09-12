"""Game notability and highlight tagline evaluation for Space Marines 5 games.

This module coordinates evaluating SM5 games against a prioritized set of
notable conditions and generates concise highlight taglines (3-5 words).

Usage example:
    from lfdata.model.gametypes.sm5_notability import Sm5NotabilityEvaluator

    evaluator = Sm5NotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player='CommanderTaco')
    print(f'Condition: {result.condition}, Tagline: {result.tagline}')
"""

from typing import TYPE_CHECKING

from lfdata.model.constants.role import LFRole
from lfdata.model.gametypes.sm5_notability_checks import Sm5NotabilityChecks
from lfdata.model.gametypes.sm5_notability_condition import (
    Sm5NotabilityCondition,
)
from lfdata.model.gametypes.sm5_notability_result import Sm5NotabilityResult

if TYPE_CHECKING:
    from lfdata.model.objects.entity import GameEntity
    from lfdata.model.objects.game import LFGame
    from lfdata.model.objects.player import Player

# Re-export for public API backwards compatibility
__all__ = [
    'Sm5NotabilityCondition',
    'Sm5NotabilityEvaluator',
    'Sm5NotabilityResult',
]


class Sm5NotabilityEvaluator:
    """Evaluates SM5 games for notability conditions and highlight taglines."""

    def __init__(self) -> None:
        """Initializes the evaluator with condition checking routines."""
        self._checks = Sm5NotabilityChecks()

    def evaluate(
        self,
        game: 'LFGame',
        focus_player: 'GameEntity | Player | str | None' = None,
    ) -> Sm5NotabilityResult:
        """Evaluates game notability and determines the highlight tagline.

        Checks conditions in priority order:
        1. Draw (identical scores)
        2. Close game (within 200 points)
        3. Commander nuked > 5 times
        4. Focus player hit diff >= 1.9
        5. Focus player medic hits >= 9
        6. Focus player lone survivor with 1-2 lives left
        7. Focus player lone survivor on team (>= 3 lives)
        8. Team eliminated in less than 8 minutes
        9. Opponents almost eliminated (1-5 combined lives left)
        10. Focus player medic zapped other medic >= 3 times
        11. Focus player was never zapped
        12. Focus player was zapped less than 5 times
        Fallback: "{rounded_score} {role} game"

        Args:
            game: The SM5 LFGame model to evaluate.
            focus_player: Optional focus player entity, model, or name.

        Returns:
            Sm5NotabilityResult: Evaluation result with condition and tagline.
        """
        focus_entity = self._resolve_focus_player(game, focus_player)
        team0_score, team1_score = self._checks.get_team_scores(game)

        # 1. Draw
        result = self._checks.check_draw(team0_score, team1_score)
        if result is not None:
            return result

        # 2. Close game
        result = self._checks.check_close_game(team0_score, team1_score)
        if result is not None:
            return result

        # 3. Commander nukes
        result = self._checks.check_commander_nukes(game, focus_entity)
        if result is not None:
            return result

        # 4. High hit diff
        result = self._checks.check_high_hit_diff(focus_entity)
        if result is not None:
            return result

        # 5. High medic hits
        result = self._checks.check_high_medic_hits(game, focus_entity)
        if result is not None:
            return result

        # 6. Lone survivor with 1-2 lives
        result = self._checks.check_lone_survivor_critical(game, focus_entity)
        if result is not None:
            return result

        # 7. Lone survivor on team (>= 3 lives)
        result = self._checks.check_lone_survivor(game, focus_entity)
        if result is not None:
            return result

        # 8. Fast team elimination (< 8 minutes)
        result = self._checks.check_fast_team_elimination(game)
        if result is not None:
            return result

        # 9. Opponents almost eliminated (1-5 lives)
        result = self._checks.check_almost_eliminated_opponents(
            game, focus_entity
        )
        if result is not None:
            return result

        # 10. Medic zapped other medic >= 3 times
        result = self._checks.check_medic_zapped_medic(game, focus_entity)
        if result is not None:
            return result

        # 11. Never zapped
        result = self._checks.check_never_zapped(game, focus_entity)
        if result is not None:
            return result

        # 12. Zapped less than 5 times
        result = self._checks.check_low_times_zapped(game, focus_entity)
        if result is not None:
            return result

        # Fallback when not notable
        fallback_tagline = self._generate_fallback_tagline(game, focus_entity)
        return Sm5NotabilityResult(
            condition=None,
            tagline=fallback_tagline,
            details={
                'team0_score': team0_score,
                'team1_score': team1_score,
            },
        )

    def _resolve_focus_player(
        self,
        game: 'LFGame',
        focus_player: 'GameEntity | Player | str | None',
    ) -> 'GameEntity | None':
        """Resolves a focus player parameter to a GameEntity instance.

        Args:
            game: The game containing entities.
            focus_player: Entity, Player, ID, or codename string.

        Returns:
            GameEntity | None: The matching entity, or None if not resolved.
        """
        if focus_player is None:
            return None

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

    def _generate_fallback_tagline(
        self,
        game: 'LFGame',
        focus_entity: 'GameEntity | None',
    ) -> str:
        """Generates the fallback tagline '{rounded_score} {role} game'.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            str: Fallback tagline.
        """
        entity = focus_entity
        if entity is None:
            players = [e for e in game.entities if e.type == 'player']
            if players:
                entity = max(players, key=lambda e: e.end_score or 0)

        if entity is None:
            return 'SM5 game'

        score = entity.end_score or 0
        rounded_k = round(score / 1000)

        role_name = 'Player'
        if entity.category is not None:
            try:
                role_name = LFRole.from_id(entity.category).display_name
            except ValueError:
                pass

        return f'{rounded_k}K {role_name} game'
