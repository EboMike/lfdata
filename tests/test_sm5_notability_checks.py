from datetime import datetime

from lfdata.model import (
    GameEntity,
    GameEvent,
    GameTeam,
    LFGame,
    Sm5NotabilityCondition,
    Sm5Stats,
)
from lfdata.model.gametypes.sm5_notability_checks import Sm5NotabilityChecks


def _make_game(game_id: str = 'test_g') -> LFGame:
    game = LFGame(
        game_id=game_id,
        timestamp=datetime.now(),
        game_type='Space Marines 5',
    )
    game.normalized_game_type = 'SM5'
    game.teams = [
        GameTeam(
            game_id=game_id,
            team_index=0,
            desc='Red',
            color_enum=11,
            color_desc='Fire',
            color_rgb='#FF0000',
        ),
        GameTeam(
            game_id=game_id,
            team_index=1,
            desc='Green',
            color_enum=12,
            color_desc='Earth',
            color_rgb='#00FF00',
        ),
    ]
    game.entities = []
    game.events = []
    game.sm5_stats = []
    return game


def test_checks_team_scores_and_draw() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='P1',
        team_index=0,
        end_score=4500,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='P2',
        team_index=1,
        end_score=4500,
    )
    target = GameEntity(
        game_id=game.game_id,
        entity_id='T1',
        type='target',
        desc='Target',
        team_index=0,
        end_score=1000,
    )
    game.entities = [p1, p2, target]

    s0, s1 = checks.get_team_scores(game)
    assert s0 == 4500
    assert s1 == 4500

    draw_res = checks.check_draw(team0_score=s0, team1_score=s1)
    assert draw_res is not None
    assert draw_res.condition == Sm5NotabilityCondition.DRAW
    assert draw_res.tagline == 'Tied game'

    not_draw = checks.check_draw(team0_score=4500, team1_score=4600)
    assert not_draw is None


def test_checks_close_game() -> None:
    checks = Sm5NotabilityChecks()
    res = checks.check_close_game(team0_score=5150, team1_score=5000)
    assert res is not None
    assert res.condition == Sm5NotabilityCondition.CLOSE_GAME
    assert res.tagline == 'Game within 200 points'
    assert res.details['difference'] == 150

    none_res = checks.check_close_game(team0_score=5300, team1_score=5000)
    assert none_res is None


def test_checks_commander_nukes() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    cmdr = GameEntity(
        game_id=game.game_id,
        entity_id='C1',
        type='player',
        desc='Cmdr',
        team_index=0,
        category=1,  # Commander
        end_score=6000,
    )
    scout = GameEntity(
        game_id=game.game_id,
        entity_id='S1',
        type='player',
        desc='Scout',
        team_index=0,
        category=3,
        end_score=3000,
    )
    game.entities = [cmdr, scout]
    game.sm5_stats = [
        Sm5Stats(game_id=game.game_id, entity_id='C1', nukes_detonated=7),
        Sm5Stats(game_id=game.game_id, entity_id='S1', nukes_detonated=6),
    ]

    res = checks.check_commander_nukes(game, cmdr)
    assert res is not None
    assert res.condition == Sm5NotabilityCondition.COMMANDER_NUKES
    assert res.tagline == '7 commander nukes'

    # Non-commander cannot trigger commander nukes
    assert checks.check_commander_nukes(game, scout) is None
    # None entity returns None
    assert checks.check_commander_nukes(game, None) is None


def test_checks_high_hit_diff() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Shooter',
        team_index=0,
    )
    p1.game = game
    game.entities = [p1]
    game.sm5_stats = [
        Sm5Stats(
            game_id=game.game_id,
            entity_id='P1',
            shot_opponent=38,
            times_zapped=19,  # 38 / 19 = 2.0 >= 1.9
        )
    ]

    res = checks.check_high_hit_diff(p1)
    assert res is not None
    assert res.condition == Sm5NotabilityCondition.HIGH_HIT_DIFF
    assert res.tagline == '2.0 hit diff game'
    assert checks.check_high_hit_diff(None) is None


def test_checks_high_medic_hits() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Player',
        team_index=0,
    )
    game.entities = [p1]
    game.sm5_stats = [
        Sm5Stats(game_id=game.game_id, entity_id='P1', medic_hits=9)
    ]

    res = checks.check_high_medic_hits(game, p1)
    assert res is not None
    assert res.condition == Sm5NotabilityCondition.HIGH_MEDIC_HITS
    assert res.tagline == '9 medic hits'

    # Less than 9 hits
    game.sm5_stats[0].medic_hits = 8
    assert checks.check_high_medic_hits(game, p1) is None
    assert checks.check_high_medic_hits(game, None) is None


def test_checks_lone_survivor_rules() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='P1',
        team_index=0,
    )
    p2 = GameEntity(
        game_id=game.game_id,
        entity_id='P2',
        type='player',
        desc='P2',
        team_index=0,
    )
    game.entities = [p1, p2]
    game.sm5_stats = [
        Sm5Stats(game_id=game.game_id, entity_id='P1', lives_left=2),
        Sm5Stats(game_id=game.game_id, entity_id='P2', lives_left=0),
    ]

    # Critical: 2 lives left
    crit = checks.check_lone_survivor_critical(game, p1)
    assert crit is not None
    assert crit.condition == Sm5NotabilityCondition.LONE_SURVIVOR_CRITICAL
    assert crit.tagline == 'Lone survivor with 2 lives'

    # 1 life left
    game.sm5_stats[0].lives_left = 1
    crit1 = checks.check_lone_survivor_critical(game, p1)
    assert crit1 is not None
    assert crit1.tagline == 'Lone survivor with 1 life'

    # General lone survivor (e.g. 5 lives left)
    game.sm5_stats[0].lives_left = 5
    assert checks.check_lone_survivor_critical(game, p1) is None
    gen = checks.check_lone_survivor(game, p1)
    assert gen is not None
    assert gen.condition == Sm5NotabilityCondition.LONE_SURVIVOR
    assert gen.tagline == 'Lone survivor on team'

    # None cases
    assert checks.check_lone_survivor_critical(game, None) is None
    assert checks.check_lone_survivor(game, None) is None


def test_checks_almost_eliminated_opponents() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='P1',
        team_index=0,
    )
    e1 = GameEntity(
        game_id=game.game_id,
        entity_id='E1',
        type='player',
        desc='E1',
        team_index=1,
    )
    e2 = GameEntity(
        game_id=game.game_id,
        entity_id='E2',
        type='player',
        desc='E2',
        team_index=1,
    )
    game.entities = [p1, e1, e2]
    game.sm5_stats = [
        Sm5Stats(game_id=game.game_id, entity_id='P1', lives_left=15),
        Sm5Stats(game_id=game.game_id, entity_id='E1', lives_left=2),
        Sm5Stats(game_id=game.game_id, entity_id='E2', lives_left=1),
    ]

    # Focus player view: 3 combined opponent lives
    res = checks.check_almost_eliminated_opponents(game, p1)
    assert res is not None
    assert res.condition == Sm5NotabilityCondition.ALMOST_ELIMINATED_OPPONENTS
    assert res.tagline == 'Opponents down to 3 lives'

    # 1 combined opponent life
    game.sm5_stats[1].lives_left = 1
    game.sm5_stats[2].lives_left = 0
    res1 = checks.check_almost_eliminated_opponents(game, p1)
    assert res1 is not None
    assert res1.tagline == 'Opponents down to 1 life'

    # 0 lives (eliminated, not almost eliminated)
    game.sm5_stats[1].lives_left = 0
    assert checks.check_almost_eliminated_opponents(game, p1) is None

    # No focus player view
    game.sm5_stats[1].lives_left = 4
    no_focus = checks.check_almost_eliminated_opponents(game, None)
    assert no_focus is not None
    assert no_focus.tagline == 'Team down to 4 lives'


def test_checks_medic_zapped_medic() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    m1 = GameEntity(
        game_id=game.game_id,
        entity_id='M1',
        type='player',
        desc='MedicRed',
        team_index=0,
        category=5,  # Medic
    )
    m2 = GameEntity(
        game_id=game.game_id,
        entity_id='M2',
        type='player',
        desc='MedicGreen',
        team_index=1,
        category=5,  # Medic
    )
    game.entities = [m1, m2]
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

    res = checks.check_medic_zapped_medic(game, m1)
    assert res is not None
    assert res.condition == Sm5NotabilityCondition.MEDIC_ZAPPED_MEDIC
    assert res.tagline == '3 medic-on-medic hits'

    # Non-medic or target non-medic
    assert checks.check_medic_zapped_medic(game, None) is None


def test_checks_never_zapped_and_low_times_zapped() -> None:
    checks = Sm5NotabilityChecks()
    game = _make_game()
    p1 = GameEntity(
        game_id=game.game_id,
        entity_id='P1',
        type='player',
        desc='Ghost',
        team_index=0,
    )
    game.entities = [p1]
    game.sm5_stats = [
        Sm5Stats(game_id=game.game_id, entity_id='P1', times_zapped=0)
    ]

    never = checks.check_never_zapped(game, p1)
    assert never is not None
    assert never.condition == Sm5NotabilityCondition.NEVER_ZAPPED
    assert never.tagline == 'Never zapped'

    # Low zapped (1 time)
    game.sm5_stats[0].times_zapped = 1
    assert checks.check_never_zapped(game, p1) is None
    low1 = checks.check_low_times_zapped(game, p1)
    assert low1 is not None
    assert low1.condition == Sm5NotabilityCondition.LOW_TIMES_ZAPPED
    assert low1.tagline == 'Zapped only once'

    # Low zapped (4 times)
    game.sm5_stats[0].times_zapped = 4
    low4 = checks.check_low_times_zapped(game, p1)
    assert low4 is not None
    assert low4.tagline == 'Zapped only 4 times'

    # 5 times (not low)
    game.sm5_stats[0].times_zapped = 5
    assert checks.check_low_times_zapped(game, p1) is None
    assert checks.check_never_zapped(game, None) is None
    assert checks.check_low_times_zapped(game, None) is None
