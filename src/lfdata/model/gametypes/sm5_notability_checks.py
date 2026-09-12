"""Condition checkers for Space Marines 5 game notability rules.

This module provides the Sm5NotabilityChecks class, implementing individual
verification checks for game and player notability conditions in SM5 games.

Usage example:
    from lfdata.model.gametypes.sm5_notability_checks import (
        Sm5NotabilityChecks,
    )

    checks = Sm5NotabilityChecks()
    result = checks.check_draw(team0_score=5000, team1_score=5000)
"""

from typing import TYPE_CHECKING, Any

from lfdata.model.constants.role import LFRole
from lfdata.model.gametypes.sm5_notability_condition import (
    Sm5NotabilityCondition,
)
from lfdata.model.gametypes.sm5_notability_result import Sm5NotabilityResult

if TYPE_CHECKING:
    from lfdata.model.objects.entity import GameEntity
    from lfdata.model.objects.game import LFGame


class Sm5NotabilityChecks:
    """Evaluates individual notability rules for SM5 games and players."""

    def get_team_scores(self, game: 'LFGame') -> tuple[int, int]:
        """Calculates final scores for Team 0 and Team 1.

        Args:
            game: The game object.

        Returns:
            tuple[int, int]: Scores for team index 0 and team index 1.
        """
        score0, score1 = 0, 0
        for entity in game.entities:
            if entity.type != 'player':
                continue
            score = entity.end_score or 0
            if entity.team_index == 0:
                score0 += score
            elif entity.team_index == 1:
                score1 += score
        return score0, score1

    def check_draw(
        self, team0_score: int, team1_score: int
    ) -> Sm5NotabilityResult | None:
        """Checks if the game ended in a draw.

        Args:
            team0_score: Score for Team 0.
            team1_score: Score for Team 1.

        Returns:
            Sm5NotabilityResult | None: Result if drawn, None otherwise.
        """
        if team0_score != team1_score:
            return None
        return Sm5NotabilityResult(
            condition=Sm5NotabilityCondition.DRAW,
            tagline='Tied game',
            details={'team0_score': team0_score, 'team1_score': team1_score},
        )

    def check_close_game(
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

    def check_commander_nukes(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player was a commander with > 5 nukes.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if (
            focus_entity is None
            or focus_entity.category != LFRole.COMMANDER.role_id
        ):
            return None
        for stat in game.sm5_stats:
            if stat.entity_id == focus_entity.entity_id:
                nukes = stat.nukes_detonated or 0
                if nukes > 5:
                    return Sm5NotabilityResult(
                        condition=Sm5NotabilityCondition.COMMANDER_NUKES,
                        tagline=f'{nukes} commander nukes',
                        details={'nukes_detonated': nukes},
                    )
        return None

    def check_high_hit_diff(
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

    def check_high_medic_hits(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player has 9 or more medic hits.

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
                hits = stat.medic_hits or 0
                if hits >= 9:
                    return Sm5NotabilityResult(
                        condition=Sm5NotabilityCondition.HIGH_MEDIC_HITS,
                        tagline=f'{hits} medic hits',
                        details={'medic_hits': hits},
                    )
        return None

    def _get_survivor_lives(
        self, game: 'LFGame', focus_entity: 'GameEntity'
    ) -> int | None:
        """Returns lives left if focus player is lone survivor on their team.

        Args:
            game: The game object.
            focus_entity: The focus player entity.

        Returns:
            int | None: Remaining lives if lone survivor, None otherwise.
        """
        stats_by_id = {s.entity_id: s for s in game.sm5_stats}
        focus_stat = stats_by_id.get(focus_entity.entity_id)
        lives = (focus_stat.lives_left or 0) if focus_stat else 0
        if lives <= 0:
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

        for mate in teammates:
            stat = stats_by_id.get(mate.entity_id)
            if stat is None or (stat.lives_left or 0) > 0:
                return None
        return lives

    def check_lone_survivor_critical(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player was the lone survivor with 1-2 lives.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if focus_entity is None:
            return None
        lives = self._get_survivor_lives(game, focus_entity)
        if lives not in (1, 2):
            return None
        lives_str = '1 life' if lives == 1 else '2 lives'
        return Sm5NotabilityResult(
            condition=Sm5NotabilityCondition.LONE_SURVIVOR_CRITICAL,
            tagline=f'Lone survivor with {lives_str}',
            details={'lives_left': lives},
        )

    def check_lone_survivor(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player was the only player on team to survive.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if focus_entity is None:
            return None
        lives = self._get_survivor_lives(game, focus_entity)
        if lives is None or lives <= 0:
            return None
        return Sm5NotabilityResult(
            condition=Sm5NotabilityCondition.LONE_SURVIVOR,
            tagline='Lone survivor on team',
            details={'lives_left': lives},
        )

    def check_fast_team_elimination(
        self, game: 'LFGame'
    ) -> Sm5NotabilityResult | None:
        """Checks if any team was eliminated in less than 8 minutes.

        Args:
            game: The game object.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        stats_by_id = {s.entity_id: s for s in game.sm5_stats}
        elim_team: int | None = None

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
                elim_team = team_idx
                break

        if elim_team is None:
            return None

        elim_ms = self._get_elimination_time_ms(game)
        if elim_ms is not None and elim_ms < 480_000:
            minutes = max(1, int(elim_ms / 60000))
            return Sm5NotabilityResult(
                condition=Sm5NotabilityCondition.FAST_TEAM_ELIMINATION,
                tagline=f'Elim in {minutes} minutes',
                details={
                    'eliminated_team': elim_team,
                    'elimination_time_ms': elim_ms,
                },
            )
        return None

    def _get_elimination_time_ms(self, game: 'LFGame') -> int | None:
        """Determines the timestamp in milliseconds when a team was eliminated.

        Args:
            game: The game object.

        Returns:
            int | None: Elimination time in ms, or None if undetermined.
        """
        if game.events:
            from lfdata.replay.replay import LFReplaySystem

            replay = LFReplaySystem(game, align_stats=False)
            replay.run()
            if replay.first_team_elimination_time_ms is not None:
                return replay.first_team_elimination_time_ms
        return game.duration

    def _get_team_lives(
        self,
        game: 'LFGame',
        team_idx: int,
        stats_by_id: dict[str, Any],
    ) -> int:
        """Returns the total lives left for players on a specific team.

        Args:
            game: The game object.
            team_idx: The team index integer.
            stats_by_id: Mapping of entity_id to stats object.

        Returns:
            int: Combined lives remaining.
        """
        return sum(
            (stats_by_id[p.entity_id].lives_left or 0)
            for p in game.entities
            if p.type == 'player'
            and p.team_index == team_idx
            and p.entity_id in stats_by_id
        )

    def check_almost_eliminated_opponents(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the opposing team had only 1 to 5 combined lives left.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        stats_by_id = {s.entity_id: s for s in game.sm5_stats}
        if focus_entity is not None:
            opp_team = 1 - focus_entity.team_index
            lives = self._get_team_lives(game, opp_team, stats_by_id)
            if 0 < lives <= 5:
                tag = (
                    'Opponents down to 1 life'
                    if lives == 1
                    else f'Opponents down to {lives} lives'
                )
                return Sm5NotabilityResult(
                    condition=(
                        Sm5NotabilityCondition.ALMOST_ELIMINATED_OPPONENTS
                    ),
                    tagline=tag,
                    details={'opponent_lives_left': lives},
                )
            return None

        for idx in (0, 1):
            lives = self._get_team_lives(game, idx, stats_by_id)
            if 0 < lives <= 5:
                tag = (
                    'Team down to 1 life'
                    if lives == 1
                    else f'Team down to {lives} lives'
                )
                return Sm5NotabilityResult(
                    condition=(
                        Sm5NotabilityCondition.ALMOST_ELIMINATED_OPPONENTS
                    ),
                    tagline=tag,
                    details={'team_lives_left': lives, 'team_index': idx},
                )
        return None

    def check_medic_zapped_medic(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if focus player is medic and zapped enemy medic >= 3 times.

        Args:
            game: The game object.
            focus_entity: The focus player entity, if any.

        Returns:
            Sm5NotabilityResult | None: Result if matched, None otherwise.
        """
        if (
            focus_entity is None
            or focus_entity.category != LFRole.MEDIC.role_id
        ):
            return None

        enemy_medics = {
            e.entity_id
            for e in game.entities
            if e.type == 'player'
            and e.team_index != focus_entity.team_index
            and e.category == LFRole.MEDIC.role_id
        }
        if not enemy_medics:
            return None

        zaps = sum(
            1
            for ev in game.events
            if ev.actor_entity_id == focus_entity.entity_id
            and ev.target_entity_id in enemy_medics
            and ev.event_type in ('0205', '0206')
        )
        if zaps >= 3:
            return Sm5NotabilityResult(
                condition=Sm5NotabilityCondition.MEDIC_ZAPPED_MEDIC,
                tagline=f'Zapped enemy medic {zaps} times',
                details={'medic_zaps': zaps},
            )
        return None

    def check_never_zapped(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player was never zapped.

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
                if (stat.times_zapped or 0) == 0:
                    return Sm5NotabilityResult(
                        condition=Sm5NotabilityCondition.NEVER_ZAPPED,
                        tagline='Never zapped in game',
                        details={'times_zapped': 0},
                    )
        return None

    def check_low_times_zapped(
        self, game: 'LFGame', focus_entity: 'GameEntity | None'
    ) -> Sm5NotabilityResult | None:
        """Checks if the focus player was zapped less than 5 times.

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
                zapped = stat.times_zapped or 0
                if zapped < 5:
                    tag = (
                        'Zapped only 1 time'
                        if zapped == 1
                        else f'Zapped only {zapped} times'
                    )
                    return Sm5NotabilityResult(
                        condition=Sm5NotabilityCondition.LOW_TIMES_ZAPPED,
                        tagline=tag,
                        details={'times_zapped': zapped},
                    )
        return None
