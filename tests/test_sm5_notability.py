from datetime import datetime
from pathlib import Path
import pytest

from lfdata.importer import parse_tdf
from lfdata.model import (
    GameEntity,
    GameEvent,
    GameTeam,
    LFGame,
    Player,
    Sm5NotabilityCondition,
    Sm5NotabilityEvaluator,
    Sm5Stats,
)


def _create_sm5_game(
    game_id: str = 'g_test',
    normalized_game_type: str = 'SM5',
) -> LFGame:
    game = LFGame(
        game_id=game_id,
        timestamp=datetime.now(),
        game_type='Space Marines 5',
    )
    game.normalized_game_type = normalized_game_type
    game.teams = [
        GameTeam(
            game_id=game_id,
            team_index=0,
            desc='Fire Team',
            color_enum=11,
            color_desc='Fire',
            color_rgb='#FF0000',
        ),
        GameTeam(
            game_id=game_id,
            team_index=1,
            desc='Earth Team',
            color_enum=12,
            color_desc='Earth',
            color_rgb='#00FF00',
        ),
    ]
    game.entities = []
    game.events = []
    game.sm5_stats = []
    return game


def test_draw_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
        category=1,
        end_score=5000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Player 2',
        team_index=1,
        category=2,
        end_score=5000,
    )
    game.entities = [p1, p2]

    assert game.get_notability() == Sm5NotabilityCondition.DRAW
    assert game.get_highlight_tagline() == 'Tied game'


def test_close_game_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player 1',
        team_index=0,
        category=1,
        end_score=5150,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Player 2',
        team_index=1,
        category=2,
        end_score=5000,
    )
    game.entities = [p1, p2]

    assert game.get_notability() == Sm5NotabilityCondition.CLOSE_GAME
    assert game.get_highlight_tagline() == 'Game within 200 points'


def test_commander_nukes_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='CmdrTaco',
        team_index=0,
        category=1,  # Commander
        end_score=8000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Enemy',
        team_index=1,
        category=3,
        end_score=3000,
    )
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        nukes_detonated=6,
        times_zapped=10,
        shot_opponent=10,
    )
    game.sm5_stats = [stat_p1]

    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.COMMANDER_NUKES
    )
    assert game.get_highlight_tagline(focus_player=p1) == '6 commander nukes'


def test_high_hit_diff_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Sharpshooter',
        team_index=0,
        category=3,  # Scout
        end_score=8000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=3000,
    )
    p1.game = game
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        shot_opponent=42,
        times_zapped=20,  # 42 / 20 = 2.1
    )
    game.sm5_stats = [stat_p1]

    assert (
        game.get_notability(focus_player='Sharpshooter')
        == Sm5NotabilityCondition.HIGH_HIT_DIFF
    )
    assert (
        game.get_highlight_tagline(focus_player='Sharpshooter')
        == '2.1 hit diff game'
    )


def test_high_medic_hits_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='SuperMedic',
        team_index=0,
        category=5,  # Medic
        end_score=8000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=3000,
    )
    p1.game = game
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        medic_hits=195,
        shot_opponent=10,
        times_zapped=10,
    )
    game.sm5_stats = [stat_p1]

    assert (
        game.get_notability(focus_player='SuperMedic')
        == Sm5NotabilityCondition.HIGH_MEDIC_HITS
    )
    assert (
        game.get_highlight_tagline(focus_player='SuperMedic')
        == '195 medic hits'
    )


def test_lone_survivor_condition_1_life() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Survivor',
        team_index=0,
        category=3,
        end_score=8000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='DownTeammate',
        team_index=0,
        category=4,
        end_score=4000,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='P3',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=3000,
    )
    p1.game = game
    game.entities = [p1, p2, enemy]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        lives_left=1,
        shot_opponent=10,
        times_zapped=10,
    )
    stat_p2 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P2',
        lives_left=0,
    )
    stat_enemy = Sm5Stats(
        game_id=game.game_id,
        entity_id='P3',
        lives_left=5,
    )
    game.sm5_stats = [stat_p1, stat_p2, stat_enemy]

    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.LONE_SURVIVOR
    )
    assert (
        game.get_highlight_tagline(focus_player=p1)
        == 'Lone survivor with 1 life'
    )


def test_lone_survivor_condition_2_lives() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Survivor',
        team_index=0,
        category=3,
        end_score=8000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='DownTeammate',
        team_index=0,
        category=4,
        end_score=4000,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='P3',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=3000,
    )
    p1.game = game
    game.entities = [p1, p2, enemy]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        lives_left=2,
        shot_opponent=10,
        times_zapped=10,
    )
    stat_p2 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P2',
        lives_left=0,
    )
    game.sm5_stats = [stat_p1, stat_p2]

    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.LONE_SURVIVOR
    )
    assert (
        game.get_highlight_tagline(focus_player=p1)
        == 'Lone survivor with 2 lives'
    )


def test_fast_team_elimination_condition() -> None:
    game = _create_sm5_game()
    game.duration = 420000  # 7 minutes (< 8 minutes)
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Winner',
        team_index=0,
        category=1,
        end_score=8000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Loser',
        team_index=1,
        category=2,
        end_score=1000,
    )
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        lives_left=10,
        shot_opponent=10,
        times_zapped=10,
    )
    stat_p2 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P2',
        lives_left=0,
    )
    game.sm5_stats = [stat_p1, stat_p2]

    assert game.get_notability() == Sm5NotabilityCondition.FAST_TEAM_ELIMINATION
    assert game.get_highlight_tagline() == 'Elim in 7 minutes'


def test_priority_order() -> None:
    # Game where both DRAW and COMMANDER_NUKES are met
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Cmdr',
        team_index=0,
        category=1,
        end_score=5000,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=5000,
    )
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        nukes_detonated=8,
        shot_opponent=10,
        times_zapped=10,
    )
    game.sm5_stats = [stat_p1]

    # DRAW (priority 1) beats COMMANDER_NUKES (priority 3)
    assert game.get_notability(focus_player=p1) == Sm5NotabilityCondition.DRAW
    assert game.get_highlight_tagline(focus_player=p1) == 'Tied game'


def test_fallback_tagline() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='CmdrTaco',
        team_index=0,
        category=1,  # Commander
        end_score=12800,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=5000,
    )
    p1.game = game
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        nukes_detonated=2,
        shot_opponent=10,
        times_zapped=10,  # hit diff 1.0 < 1.9
        medic_hits=50,
        lives_left=10,
    )
    game.sm5_stats = [stat_p1]

    assert game.get_notability(focus_player=p1) is None
    assert game.get_highlight_tagline(focus_player=p1) == '13K Commander game'


def test_fallback_tagline_scout() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Scouty',
        team_index=0,
        category=3,  # Scout
        end_score=5708,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=2000,
    )
    p1.game = game
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        shot_opponent=10,
        times_zapped=10,
        lives_left=15,
    )
    game.sm5_stats = [stat_p1]

    assert game.get_notability(focus_player=p1) is None
    assert game.get_highlight_tagline(focus_player=p1) == '6K Scout game'


def test_focus_player_resolution_by_player_object() -> None:
    game = _create_sm5_game()
    player_model = Player(id=42, real_name='John Doe', codename='Viper')
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Viper',
        team_index=0,
        category=1,
        end_score=8000,
        player_id=42,
    )
    p1.player = player_model
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=2000,
    )
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        nukes_detonated=6,
        shot_opponent=10,
        times_zapped=10,
    )
    game.sm5_stats = [stat_p1]

    # Resolve via Player ORM object
    assert (
        game.get_notability(focus_player=player_model)
        == Sm5NotabilityCondition.COMMANDER_NUKES
    )
    # Resolve via codename string
    assert (
        game.get_notability(focus_player='Viper')
        == Sm5NotabilityCondition.COMMANDER_NUKES
    )


def test_non_sm5_raises_not_implemented_error() -> None:
    game = _create_sm5_game(normalized_game_type='Laserball')
    with pytest.raises(NotImplementedError):
        game.get_notability()

    with pytest.raises(NotImplementedError):
        game.get_highlight_tagline()


def test_real_tdf_evaluation() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    game = parse_tdf(real_path)

    # Assess from perspective of player #fwqiZ (Commander on Fire team)
    tagline = game.get_highlight_tagline(focus_player='#fwqiZ')
    assert isinstance(tagline, str)
    assert len(tagline.split()) >= 2
