from datetime import datetime
from lfdata.model import GameEntity, GameEvent, GameTeam, LFGame
from lfdata.replay.handlers import LFReplayHandlersMixin
from lfdata.replay.replay import LFReplaySystem


def test_handlers_mixin_integration() -> None:
    # Verify mixin class is inherited
    assert issubclass(LFReplaySystem, LFReplayHandlersMixin)

    # Initialize a mock game to verify handler method presence
    game = LFGame(
        game_id='test_handlers_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    # Teams
    t1 = GameTeam(
        game_id='test_handlers_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    game.teams = [t1]

    # Entities
    cmd = GameEntity(
        game_id='test_handlers_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    game.entities = [cmd]
    game.events = []

    replay = LFReplaySystem(game)

    # Verify method presence
    assert hasattr(replay, '_process_event_zap')
    assert hasattr(replay, '_process_event_missile')
    assert hasattr(replay, '_process_event_base_destroy')
    assert hasattr(replay, '_process_event_nuke_detonate')
    assert hasattr(replay, '_process_event_resupply')
    assert hasattr(replay, '_process_event_other')


def test_process_event_zap_hit_diff() -> None:
    game = LFGame(
        game_id='test_zap_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    t1 = GameTeam(
        game_id='test_zap_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_zap_game',
        team_index=1,
        desc='Earth Team',
        color_enum=12,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    p1 = GameEntity(
        game_id='test_zap_game',
        entity_id='P1',
        type='player',
        desc='Player1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Suit1',
    )
    p2 = GameEntity(
        game_id='test_zap_game',
        entity_id='P2',
        type='player',
        desc='Player2',
        team_index=1,
        level=1,
        category=1,
        battlesuit='Suit2',
    )
    p3 = GameEntity(
        game_id='test_zap_game',
        entity_id='P3',
        type='player',
        desc='Player3',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Suit3',
    )
    game.entities = [p1, p2, p3]
    game.events = []

    replay = LFReplaySystem(game)

    state_p1 = replay.game_state.players['P1']
    state_p2 = replay.game_state.players['P2']
    state_p3 = replay.game_state.players['P3']

    assert state_p1.hit_diff == 1.0
    assert state_p2.hit_diff == 1.0
    assert state_p3.hit_diff == 1.0

    # P1 zaps P2 (opponent)
    ev1 = GameEvent(
        game_id='test_zap_game',
        time=1000,
        event_type='0205',
        actor_entity_id='P1',
        target_entity_id='P2',
        action='zaps',
        raw_message='zaps',
    )
    replay._process_event_zap(ev1)

    assert state_p1.times_zapped_opponents == 1
    assert state_p1.times_zapped == 0
    assert state_p1.hit_diff == 1.0

    assert state_p2.times_zapped_opponents == 0
    assert state_p2.times_zapped == 1
    assert state_p2.hit_diff == 0.0

    # P1 zaps P3 (friendly fire on same team: team 0)
    ev_ff = GameEvent(
        game_id='test_zap_game',
        time=1500,
        event_type='0207',
        actor_entity_id='P1',
        target_entity_id='P3',
        action='zaps',
        raw_message='zaps',
    )
    replay._process_event_zap(ev_ff)

    # Friendly fire must NOT increment times_zapped_opponents
    assert state_p1.times_zapped_opponents == 1

    # P2 zaps P1 twice (opponents)
    ev2 = GameEvent(
        game_id='test_zap_game',
        time=2000,
        event_type='0205',
        actor_entity_id='P2',
        target_entity_id='P1',
        action='zaps',
        raw_message='zaps',
    )
    ev3 = GameEvent(
        game_id='test_zap_game',
        time=3000,
        event_type='0205',
        actor_entity_id='P2',
        target_entity_id='P1',
        action='zaps',
        raw_message='zaps',
    )
    replay._process_event_zap(ev2)
    replay._process_event_zap(ev3)

    assert state_p1.times_zapped_opponents == 1
    assert state_p1.times_zapped == 2
    assert state_p1.hit_diff == 0.5

    assert state_p2.times_zapped_opponents == 2
    assert state_p2.times_zapped == 1
    assert state_p2.hit_diff == 2.0

