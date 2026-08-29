"""Game notability and highlight tagline evaluation for Space Marines 5 games.

This module evaluates SM5 games against a prioritized set of notable conditions
(draws, close games, high nuke counts, high hit diffs, high medic hits, lone
survivor status, and rapid team elimination) and generates concise highlight
taglines (3-5 words).

Usage example:
    from lfdata.model.gametypes.sm5_notability import Sm5NotabilityEvaluator

    evaluator = Sm5NotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player='CommanderTaco')
    print(f'Condition: {result.condition}, Tagline: {result.tagline}')
"""

import dataclasses
import enum
from typing import TYPE_CHECKING, Any

from lfdata.model.constants.role import LFRole

if TYPE_CHECKING:
    from lfdata.model.objects.entity import GameEntity
    from lfdata.model.objects.game import LFGame
    from lfdata.model.objects.player import Player


class Sm5NotabilityCondition(enum.Enum):
    """Enumeration of notable game conditions in SM5, in priority order.

    Attributes:
        priority: Relative priority integer (1 is highest, 7 is lowest).
        description: Readable summary of the notable condition.
    """

    DRAW = (1, 'The game ended in a draw with identical scores.')
    CLOSE_GAME = (2, 'The teams ended within 200 points of each other.')
    COMMANDER_NUKES = (3, 'The focus player was a commander with > 5 nukes.')
    HIGH_HIT_DIFF = (4, 'The focus player had a hit diff of 1.9 or more.')
    HIGH_MEDIC_HITS = (5, 'The focus player had 190 or more medic hits.')
    LONE_SURVIVOR = (6, 'The focus player was the lone survivor with 1-2 lives.')
    FAST_TEAM_ELIMINATION = (7, 'A team was eliminated in less than 8 minutes.')

    def __init__(self, priority: int, description: str) -> None:
        """Initializes the notability condition with metadata.

        Args:
            priority: Priority rank integer (1 is most notable).
            description: Description of the condition.
        """
        self.priority = priority
        self.description = description


@dataclasses.dataclass(frozen=True)
class Sm5NotabilityResult:
    """Result container for SM5 game notability and highlight tagline.

    Attributes:
        condition: Matching Sm5NotabilityCondition, or None if not notable.
        tagline: Concise highlight tagline string (3-5 words).
        details: Dictionary containing evaluation context details.
    """

    condition: Sm5NotabilityCondition | None
    tagline: str
    details: dict[str, Any] = dataclasses.field(default_factory=dict)


class Sm5NotabilityEvaluator:
    """Evaluates SM5 games for notability conditions and highlight taglines."""

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
        5. Focus player medic hits >= 190
        6. Focus player lone survivor on team with 1-2 lives left
        7. Team eliminated in less than 8 minutes
        Fallback: "{rounded_score} {role} game"

        Args:
            game: The SM5 LFGame model to evaluate.
            focus_player: Optional focus player entity, model, or name.

        Returns:
            Sm5NotabilityResult: Evaluation result with condition and tagline.
        """
        focus_entity = self._resolve_focus_player(game, focus_player)
        team0_score, team1_score = self._get_team_scores(game)

        # 1. Draw
        result = self._check_draw(team0_score, team1_score)
        if result is not None:
            return result

        # 2. Close game
        result = self._check_close_game(team0_score, team1_score)
        if result is not None:
            return result

        # 3. Commander nukes
        result = self._check_commander_nukes(game, focus_entity)
        if result is not None:
            return result

        # 4. High hit diff
        result = self._check_high_hit_diff(focus_entity)
        if result is not None:
            return result

        # 5. High medic hits
        result = self._check_high_medic_hits(game, focus_entity)
        if result is not None:
            return result

        # 6. Lone survivor
        result = self._check_lone_survivor(game, focus_entity)
        if result is not None:
            return result

        # 7. Fast team elimination (< 8 minutes)
        result = self._check_fast_team_elimination(game)
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

        # Check if already a GameEntity
        if hasattr(focus_player, 'entity_id') and hasattr(
            focus_player, 'type'
        ):
            return focus_player  # type: ignore[return-value]

        # Check if a Player model
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

        # String identifier: match entity_id, desc, or battlesuit
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

    def _get_team_scores(self, game: 'LFGame') -> tuple[int, int]:
        """Calculates final scores for Team 0 and Team 1.

        Args:
            game: The game object.

        Returns:
            tuple[int, int]: Scores for team index 0 and team index 1.
        """
        score_team0 = 0
        score_team1 = 0

        for entity in game.entities:
            if entity.type != 'player':
                continue
            score = entity.end_score or 0
            if entity.team_index == 0:
                score_team0 += score
            elif entity.team_index == 1:
                score_team1 += score

        return score_team0, score_team1

    def _check_draw(
        self, team0_score: int, team1_score: int
    ) -> Sm5NotabilityResult | None:
        """Checks if the game ended in a draw.

        Args:
            team0_score: Score for Team 0.
            team1_score: Score for Team 1.

        Returns:
            Sm5NotabilityResult | None: Result if drawn, None otherwise.
        """
        if team0_score == team1_score:
            return Sm5NotabilityResult(
                condition=Sm5NotabilityCondition.DRAW,
                tagline='Tied game',
                details={
                    'team0_score': team0_score,
                    'team1_score': team1_score,
                },
            )
        return None

    def _check_close_game(
        self, team0_score: int, team1_score: int
    ) -> Sm5NotabilityResult | None:
        """Checks if the game ended within 200 points of each other.

        Args:
            team0_score: Score for Team 0.
            team1_score: Score for Team 1.

        Returns:
            Sm5NotabilityResult | None: Result if close, None otherwise.
        """
        diff = abs(team0_score - team1_score)
        if 0 < diff <= 200:
            return Sm5NotabilityResult(
                condition=Sm5NotabilityCondition.CLOSE_GAME,
                tagline='Game within 200 points',
                details={
                    'team0_score': team0_score,
                    'team1_score': team1_score,
                    'difference': diff,
                },
            )
        return None

    def _check_commander_nukes(
        self,
        game: 'LFGame',
        focus_entity: 'GameEntity | None',
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player was a commander with > 5 nukes.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if focus_entity is None:
            return None

        # Verify Commander role
        if focus_entity.category != LFRole.COMMANDER.role_id:
            return None

        for stat in game.sm5_stats:
            if stat.entity_id == focus_entity.entity_id:
                nukes = stat.nukes_detonated or 0
                if nukes > 5:
                    return Sm5NotabilityResult(
                        condition=Sm5NotabilityCondition.COMMANDER_NUKES,
                        tagline=f'{nukes} commander nukes',
                        details={
                            'nukes_detonated': nukes,
                        },
                    )
        return None

    def _check_high_hit_diff(
        self, focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player has a hit diff of 1.9 or more.

        Args:
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if focus_entity is None:
            return None

        diff = focus_entity.hit_diff
        if diff is not None and diff >= 1.9:
            return Sm5NotabilityResult(
                condition=Sm5NotabilityCondition.HIGH_HIT_DIFF,
                tagline=f'{diff:.1f} hit diff game',
                details={'hit_diff': diff},
            )
        return None

    def _check_high_medic_hits(
        self,
        game: 'LFGame',
        focus_entity: 'GameEntity | None',
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player has 190 or more medic hits.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if focus_entity is None:
            return None

        for stat in game.sm5_stats:
            if stat.entity_id == focus_entity.entity_id:
                medic_hits = stat.medic_hits or 0
                if medic_hits >= 190:
                    return Sm5NotabilityResult(
                        condition=Sm5NotabilityCondition.HIGH_MEDIC_HITS,
                        tagline=f'{medic_hits} medic hits',
                        details={'medic_hits': medic_hits},
                    )
        return None

    def _check_lone_survivor(
        self,
        game: 'LFGame',
        focus_entity: 'GameEntity | None',
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player was the lone survivor with 1-2 lives left.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if focus_entity is None:
            return None

        stats_by_id = {s.entity_id: s for s in game.sm5_stats}
        focus_stat = stats_by_id.get(focus_entity.entity_id)
        lives = focus_stat.lives_left or 0 if focus_stat else 0
        if lives not in (1, 2):
            return None

        teammates = [
            e
            for e in game.entities
            if e.type == 'player'
            and e.team_index == focus_entity.team_index
            and e.entity_id != focus_entity.entity_id
        ]
        if not teammates:
            return None

        for teammate in teammates:
            stat = stats_by_id.get(teammate.entity_id)
            if stat is None or (stat.lives_left or 0) > 0:
                return None

        lives_str = '1 life' if lives == 1 else '2 lives'
        return Sm5NotabilityResult(
            condition=Sm5NotabilityCondition.LONE_SURVIVOR,
            tagline=f'Lone survivor with {lives_str}',
            details={'lives_left': lives},
        )

    def _check_fast_team_elimination(
        self, game: 'LFGame'
    ) -> Sm5NotabilityResult | None:
        """Checks if any team was eliminated in less than 8 minutes.

        Args:
            game: The game object.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        stats_by_id = {s.entity_id: s for s in game.sm5_stats}
        eliminated_team_idx: int | None = None

        for team_idx in (0, 1):
            team_players = [
                e
                for e in game.entities
                if e.type == 'player' and e.team_index == team_idx
            ]
            if not team_players:
                continue
            if all(
                stats_by_id.get(p.entity_id) is not None
                and (stats_by_id[p.entity_id].lives_left or 0) == 0
                for p in team_players
            ):
                eliminated_team_idx = team_idx
                break

        if eliminated_team_idx is None:
            return None

        # Determine elimination timestamp
        elim_ms: int | None = None

        if game.events:
            from lfdata.replay.replay import LFReplaySystem

            replay = LFReplaySystem(game, align_stats=False)
            replay.run()
            elim_ms = replay.first_team_elimination_time_ms

        if elim_ms is None and game.duration is not None:
            elim_ms = game.duration

        if elim_ms is not None and elim_ms < 480_000:
            minutes = max(1, int(elim_ms / 60000))
            return Sm5NotabilityResult(
                condition=Sm5NotabilityCondition.FAST_TEAM_ELIMINATION,
                tagline=f'Elim in {minutes} minutes',
                details={
                    'eliminated_team': eliminated_team_idx,
                    'elimination_time_ms': elim_ms,
                },
            )

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
            # Fall back to top-scoring player
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
