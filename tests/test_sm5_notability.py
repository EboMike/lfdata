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
        medic_hits=10,  # >= 9 hits
        shot_opponent=10,
        times_zapped=10,
    )
    game.sm5_stats = [stat_p1]

    assert (
        game.get_notability(focus_player='SuperMedic')
        == Sm5NotabilityCondition.HIGH_MEDIC_HITS
    )
    assert (
        game.get_highlight_tagline(focus_player='SuperMedic') == '10 medic hits'
    )


def test_lone_survivor_critical_condition_1_life() -> None:
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
        == Sm5NotabilityCondition.LONE_SURVIVOR_CRITICAL
    )
    assert (
        game.get_highlight_tagline(focus_player=p1)
        == 'Lone survivor with 1 life'
    )


def test_lone_survivor_critical_condition_2_lives() -> None:
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
    p1.game = game
    game.entities = [p1, p2]
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
        == Sm5NotabilityCondition.LONE_SURVIVOR_CRITICAL
    )
    assert (
        game.get_highlight_tagline(focus_player=p1)
        == 'Lone survivor with 2 lives'
    )


def test_lone_survivor_general_condition() -> None:
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
    p1.game = game
    game.entities = [p1, p2]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        lives_left=6,  # > 2 lives
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
        game.get_highlight_tagline(focus_player=p1) == 'Lone survivor on team'
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


def test_almost_eliminated_opponents_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Hero',
        team_index=0,
        category=1,
        end_score=8000,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='E1',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=2000,
    )
    p1.game = game
    game.entities = [p1, enemy]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        lives_left=12,
        shot_opponent=10,
        times_zapped=10,
    )
    stat_enemy = Sm5Stats(
        game_id=game.game_id,
        entity_id='E1',
        lives_left=3,  # 3 lives <= 5
    )
    game.sm5_stats = [stat_p1, stat_enemy]

    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.ALMOST_ELIMINATED_OPPONENTS
    )
    assert (
        game.get_highlight_tagline(focus_player=p1)
        == 'Opponents down to 3 lives'
    )


def test_almost_eliminated_opponents_no_focus_player() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='P1',
        team_index=0,
        end_score=8000,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='E1',
        type='player',
        desc='Enemy',
        team_index=1,
        end_score=2000,
    )
    game.entities = [p1, enemy]
    game.sm5_stats = [
        Sm5Stats(game_id=game.game_id, entity_id='P1', lives_left=10),
        Sm5Stats(game_id=game.game_id, entity_id='E1', lives_left=1),
    ]

    assert (
        game.get_notability()
        == Sm5NotabilityCondition.ALMOST_ELIMINATED_OPPONENTS
    )
    assert game.get_highlight_tagline() == 'Team down to 1 life'


def test_medic_zapped_medic_condition() -> None:
    game = _create_sm5_game()
    m1 = GameEntity(
        game_id=game.game_id,
        entity_id='M1',
        type='player',
        desc='Medic1',
        team_index=0,
        category=5,  # Medic
        end_score=7000,
    )
    m2 = GameEntity(
        game_id=game.game_id,
        entity_id='M2',
        type='player',
        desc='Medic2',
        team_index=1,
        category=5,  # Medic
        end_score=4000,
    )
    m1.game = game
    game.entities = [m1, m2]
    stat_m1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='M1',
        times_zapped=10,
        lives_left=10,
    )
    stat_m2 = Sm5Stats(
        game_id=game.game_id,
        entity_id='M2',
        times_zapped=10,
        lives_left=10,
    )
    game.sm5_stats = [stat_m1, stat_m2]
    game.events = [
        GameEvent(
            game_id=game.game_id,
            time=1000,
            event_type='0205',
            actor_entity_id='M1',
            target_entity_id='M2',
            action='zaps',
            raw_message='',
        ),
        GameEvent(
            game_id=game.game_id,
            time=2000,
            event_type='0206',
            actor_entity_id='M1',
            target_entity_id='M2',
            action='zaps',
            raw_message='',
        ),
        GameEvent(
            game_id=game.game_id,
            time=3000,
            event_type='0205',
            actor_entity_id='M1',
            target_entity_id='M2',
            action='zaps',
            raw_message='',
        ),
    ]

    assert (
        game.get_notability(focus_player=m1)
        == Sm5NotabilityCondition.MEDIC_ZAPPED_MEDIC
    )
    assert (
        game.get_highlight_tagline(focus_player=m1)
        == 'Zapped enemy medic 3 times'
    )


def test_never_zapped_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Ninja',
        team_index=0,
        category=2,  # Heavy
        end_score=7500,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='E1',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=2000,
    )
    p1.game = game
    game.entities = [p1, enemy]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        times_zapped=0,
        lives_left=15,
    )
    stat_enemy = Sm5Stats(
        game_id=game.game_id,
        entity_id='E1',
        times_zapped=10,
        lives_left=10,
    )
    game.sm5_stats = [stat_p1, stat_enemy]

    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.NEVER_ZAPPED
    )
    assert game.get_highlight_tagline(focus_player=p1) == 'Never zapped in game'


def test_low_times_zapped_condition() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Dodger',
        team_index=0,
        category=3,  # Scout
        end_score=7500,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='E1',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=2000,
    )
    p1.game = game
    game.entities = [p1, enemy]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        times_zapped=2,  # < 5 and > 0
        lives_left=15,
    )
    stat_enemy = Sm5Stats(
        game_id=game.game_id,
        entity_id='E1',
        times_zapped=10,
        lives_left=10,
    )
    game.sm5_stats = [stat_p1, stat_enemy]

    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.LOW_TIMES_ZAPPED
    )
    assert game.get_highlight_tagline(focus_player=p1) == 'Zapped only 2 times'


def test_low_times_zapped_condition_singular() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Dodger',
        team_index=0,
        category=3,
        end_score=7500,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='E1',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=2000,
    )
    p1.game = game
    game.entities = [p1, enemy]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        times_zapped=1,
        lives_left=15,
    )
    stat_enemy = Sm5Stats(
        game_id=game.game_id,
        entity_id='E1',
        times_zapped=10,
        lives_left=10,
    )
    game.sm5_stats = [stat_p1, stat_enemy]

    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.LOW_TIMES_ZAPPED
    )
    assert game.get_highlight_tagline(focus_player=p1) == 'Zapped only 1 time'


def test_priority_order_never_zapped_vs_low_zapped() -> None:
    game = _create_sm5_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Ghost',
        team_index=0,
        category=2,
        end_score=7000,
    )
    enemy = GameEntity(
        game_id=game.game_id,
        entity_id='E1',
        type='player',
        desc='Enemy',
        team_index=1,
        category=2,
        end_score=2000,
    )
    p1.game = game
    game.entities = [p1, enemy]
    stat_p1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P1',
        times_zapped=0,
        lives_left=15,
    )
    stat_enemy = Sm5Stats(
        game_id=game.game_id,
        entity_id='E1',
        times_zapped=10,
        lives_left=10,
    )
    game.sm5_stats = [stat_p1, stat_enemy]

    # NEVER_ZAPPED (11) beats LOW_TIMES_ZAPPED (12)
    assert (
        game.get_notability(focus_player=p1)
        == Sm5NotabilityCondition.NEVER_ZAPPED
    )


def test_priority_order_medic_zapped_vs_never_zapped() -> None:
    game = _create_sm5_game()
    m1 = GameEntity(
        game_id=game.game_id,
        entity_id='M1',
        type='player',
        desc='Medic1',
        team_index=0,
        category=5,  # Medic
        end_score=7000,
    )
    m2 = GameEntity(
        game_id=game.game_id,
        entity_id='M2',
        type='player',
        desc='Medic2',
        team_index=1,
        category=5,  # Medic
        end_score=4000,
    )
    m1.game = game
    game.entities = [m1, m2]
    stat_m1 = Sm5Stats(
        game_id=game.game_id,
        entity_id='M1',
        times_zapped=0,  # Never zapped
        lives_left=10,
    )
    stat_m2 = Sm5Stats(
        game_id=game.game_id,
        entity_id='M2',
        times_zapped=10,
        lives_left=10,
    )
    game.sm5_stats = [stat_m1, stat_m2]
    game.events = [
        GameEvent(
            game_id=game.game_id,
            time=1000 * i,
            event_type='0205',
            actor_entity_id='M1',
            target_entity_id='M2',
            action='zaps',
            raw_message='',
        )
        for i in range(1, 4)
    ]

    # MEDIC_ZAPPED_MEDIC (10) beats NEVER_ZAPPED (11)
    assert (
        game.get_notability(focus_player=m1)
        == Sm5NotabilityCondition.MEDIC_ZAPPED_MEDIC
    )


def test_priority_order() -> None:
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
        medic_hits=5,  # < 9
        lives_left=10,
    )
    stat_p2 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P2',
        lives_left=10,  # > 5 opponent lives
        times_zapped=10,
    )
    game.sm5_stats = [stat_p1, stat_p2]

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
    stat_p2 = Sm5Stats(
        game_id=game.game_id,
        entity_id='P2',
        times_zapped=10,
        lives_left=10,
    )
    game.sm5_stats = [stat_p1, stat_p2]

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
