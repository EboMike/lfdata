from datetime import datetime, timezone

import pytest

from lfdata.model import (
    GameEntity,
    GameTeam,
    LaserballNotabilityCondition,
    LaserballNotabilityEvaluator,
    LaserballStats,
    LFGame,
    Player,
    Sm5NotabilityCondition,
)


def _create_laserball_game(game_id: str = 'lb_test_game') -> LFGame:
    game = LFGame(
        game_id=game_id,
        timestamp=datetime.now(timezone.utc),
        game_type='Laserball',
    )
    t1 = GameTeam(
        game_id=game_id,
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF0000',
    )
    t2 = GameTeam(
        game_id=game_id,
        team_index=1,
        desc='Earth Team',
        color_enum=12,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]
    return game


def test_goals_condition_singular_and_plural() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # 1 goal -> singular
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=1,
            blocks=10,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.GOALS
    assert result.tagline == '1 goal'

    # 3 goals -> plural
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=3,
            blocks=10,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.GOALS
    assert result.tagline == '3 goals'


def test_goals_condition_with_extra_blocks() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # Exactly 20 blocks -> no extra blocks appended
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=1,
            blocks=20,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.tagline == '1 goal'

    # 25 blocks (> 20) -> extra blocks appended
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=2,
            blocks=25,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.tagline == '2 goals, 25 blocks'


def test_assists_condition_singular_plural_and_blocks() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # 1 assist -> singular
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=1,
            blocks=5,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.ASSISTS
    assert result.tagline == '1 assist'

    # 2 assists with > 20 blocks
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=2,
            blocks=22,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.ASSISTS
    assert result.tagline == '2 assists, 22 blocks'


def test_steals_condition_multiple_required() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # 1 steal is not multiple -> falls through
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=1,
            blocks=5,
            times_blocked=10,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    # hit diff = (5 + 1) / 10 = 0.6 <= 1.4, clears = 0 -> fallback
    assert result.condition == LaserballNotabilityCondition.BLOCKS_SUMMARY
    assert result.tagline == '5/10 blocks'

    # 2 steals -> multiple steals condition matches
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=2,
            blocks=5,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.STEALS
    assert result.tagline == '2 steals'

    # 3 steals with > 20 blocks
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=3,
            blocks=24,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.STEALS
    assert result.tagline == '3 steals, 24 blocks'


def test_high_hit_diff_condition() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # Hit diff exactly 1.4 -> not over 1.4 -> falls through
    # hits = 14, times_blocked = 10 -> 1.4
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            blocks=14,
            times_blocked=10,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.BLOCKS_SUMMARY
    assert result.tagline == '14/10 blocks'

    # Hit diff 1.5 -> matches
    # hits = 15, times_blocked = 10 -> 1.5
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            blocks=15,
            times_blocked=10,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.HIGH_HIT_DIFF
    assert result.tagline == '1.5 hit diff'

    # Hit diff with > 20 blocks
    # hits = 25, times_blocked = 10 -> 2.5 hit diff
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            blocks=25,
            times_blocked=10,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.HIGH_HIT_DIFF
    assert result.tagline == '2.5 hit diff, 25 blocks'


def test_clears_condition() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # 1 clear -> not more than once
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            clears=1,
            blocks=10,
            times_blocked=10,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.BLOCKS_SUMMARY
    assert result.tagline == '10/10 blocks'

    # 2 clears -> matches
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            clears=2,
            blocks=10,
            times_blocked=10,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.CLEARS
    assert result.tagline == '2 clears'

    # 3 clears with > 20 blocks
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            clears=3,
            blocks=26,
            times_blocked=26,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.CLEARS
    assert result.tagline == '3 clears, 26 blocks'


def test_fallback_blocks_summary_condition() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # No conditions met, 10 blocks and 30 blocked times
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            clears=0,
            blocks=10,
            times_blocked=30,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.BLOCKS_SUMMARY
    assert result.tagline == '10/30 blocks'

    # When times_zapped is used instead of times_blocked
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=0,
            clears=0,
            blocks=8,
            times_blocked=0,
            times_zapped=15,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.tagline == '8/15 blocks'


def test_condition_prioritization() -> None:
    game = _create_laserball_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
    )
    game.entities = [p1]

    # Has 1 goal and 5 assists -> goal takes priority
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=1,
            assists=5,
            blocks=5,
        )
    ]
    evaluator = LaserballNotabilityEvaluator()
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.GOALS
    assert result.tagline == '1 goal'

    # Has 0 goals, 1 assist, 4 steals -> assist takes priority
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=1,
            steals=4,
            blocks=5,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.ASSISTS
    assert result.tagline == '1 assist'

    # Has 0 goals, 0 assists, 2 steals, 2.5 hit diff -> steals takes priority
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=0,
            assists=0,
            steals=2,
            blocks=25,
            times_blocked=10,
        )
    ]
    result = evaluator.evaluate(game, focus_player=p1)
    assert result.condition == LaserballNotabilityCondition.STEALS
    assert result.tagline == '2 steals, 25 blocks'


def test_focus_player_resolution() -> None:
    game = _create_laserball_game()
    player_model = Player(id=42, codename='StrikerX', real_name='Alex Smith')
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Alex S',
        team_index=0,
        player_id=42,
        player=player_model,
        battlesuit='SuitAlpha',
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Bob D',
        team_index=1,
        battlesuit='SuitBeta',
    )
    game.entities = [p1, p2]

    # Stats: P1 has 2 goals, P2 has 1 goal
    game.laserball_stats = [
        LaserballStats(
            game_id=game.game_id,
            entity_id='P1',
            goals=2,
            blocks=5,
        ),
        LaserballStats(
            game_id=game.game_id,
            entity_id='P2',
            goals=1,
            blocks=5,
        ),
    ]

    evaluator = LaserballNotabilityEvaluator()

    # Resolution by entity_id
    r1 = evaluator.evaluate(game, focus_player='P1')
    assert r1.tagline == '2 goals'

    # Resolution by desc
    r2 = evaluator.evaluate(game, focus_player='Bob D')
    assert r2.tagline == '1 goal'

    # Resolution by battlesuit
    r3 = evaluator.evaluate(game, focus_player='SuitAlpha')
    assert r3.tagline == '2 goals'

    # Resolution by codename
    r4 = evaluator.evaluate(game, focus_player='StrikerX')
    assert r4.tagline == '2 goals'

    # Resolution by real_name
    r5 = evaluator.evaluate(game, focus_player='Alex Smith')
    assert r5.tagline == '2 goals'

    # Resolution by Player instance
    r6 = evaluator.evaluate(game, focus_player=player_model)
    assert r6.tagline == '2 goals'

    # Resolution when focus_player is None -> picks P1 because P1 has higher score
    r_default = evaluator.evaluate(game, focus_player=None)
    assert r_default.tagline == '2 goals'

    # When entity not found
    r_none = evaluator.evaluate(game, focus_player='UnknownPlayer')
    assert r_none.condition is None
    assert r_none.tagline == 'Laserball game'


def test_game_methods_differentiate_game_types() -> None:
    # 1. Laserball game calls Laserball evaluator
    lb_game = _create_laserball_game()
    p1 = GameEntity(
        game_id=lb_game.game_id,
        entity_id='P1',
        type='player',
        desc='Striker',
        team_index=0,
    )
    lb_game.entities = [p1]
    lb_game.laserball_stats = [
        LaserballStats(
            game_id=lb_game.game_id,
            entity_id='P1',
            goals=2,
            blocks=10,
        )
    ]
    assert lb_game.get_notability(focus_player=p1) == (
        LaserballNotabilityCondition.GOALS
    )
    assert lb_game.get_highlight_tagline(focus_player=p1) == '2 goals'

    # 2. SM5 game calls SM5 evaluator
    sm5_game = LFGame(
        game_id='sm5_test',
        timestamp=datetime.now(timezone.utc),
        game_type='SM5',
    )
    sm5_p1 = GameEntity(
        game_id=sm5_game.game_id,
        entity_id='C1',
        type='player',
        desc='Cmdr',
        team_index=0,
        category=1,
        end_score=5000,
    )
    sm5_p2 = GameEntity(
        game_id=sm5_game.game_id,
        entity_id='C2',
        type='player',
        desc='EnemyCmdr',
        team_index=1,
        category=1,
        end_score=5000,
    )
    sm5_game.entities = [sm5_p1, sm5_p2]
    assert sm5_game.get_notability() == Sm5NotabilityCondition.DRAW
    assert sm5_game.get_highlight_tagline() == 'Tied game'

    # 3. Unsupported game type raises NotImplementedError
    unsupported_game = LFGame(
        game_id='unsupported',
        timestamp=datetime.now(timezone.utc),
        game_type='UnknownType',
    )
    with pytest.raises(NotImplementedError):
        unsupported_game.get_notability()
    with pytest.raises(NotImplementedError):
        unsupported_game.get_highlight_tagline()
