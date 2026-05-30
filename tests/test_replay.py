from pathlib import Path

from lfdata.importer import TdfImporter
from lfdata.replay.replay import LFReplaySystem


def test_replay_system_with_real_game() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    importer = TdfImporter(real_path)
    game = importer.parse()

    replay = LFReplaySystem(game)
    records = replay.run()

    assert len(records) > 0
    assert records[0].time_ms == 0
    assert records[0].description == '* Mission Start *'

    zap_record = next((r for r in records if 'zaps' in r.description), None)
    assert zap_record is not None
    assert len(zap_record.player_changes) > 0

    for player in replay.game_state.players.values():
        assert player.lives >= 0
        assert player.shots >= 0
        assert player.special_points >= 0


def test_replay_system_rules() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    # 1. Create a game
    game = LFGame(game_id='test_rule_game', timestamp=datetime.now(), game_type='SM5')

    # 2. Add two teams
    t1 = GameTeam(
        game_id='test_rule_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_rule_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # 3. Add entities
    # Commander on team 0
    cmd = GameEntity(
        game_id='test_rule_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Scout on team 1
    sct = GameEntity(
        game_id='test_rule_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    # Medic on team 1
    med = GameEntity(
        game_id='test_rule_game',
        entity_id='M2',
        type='player',
        desc='Med2',
        team_index=1,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    game.entities = [cmd, sct, med]

    # 4. Add events
    events = [
        # Mission start
        GameEvent(
            game_id='test_rule_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Scout zaps Commander (DAMAGED_OPPONENT - Commander has 3 HP,
        # so HP becomes 2, no life lost)
        GameEvent(
            game_id='test_rule_game',
            time=1000,
            event_type='0205',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # Scout zaps Commander again (DAMAGED_OPPONENT - Commander HP becomes 1)
        GameEvent(
            game_id='test_rule_game',
            time=2000,
            event_type='0205',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # Scout zaps Commander again (DOWNED_OPPONENT - Commander HP
        # becomes 0, goes down, loses 1 life)
        GameEvent(
            game_id='test_rule_game',
            time=3000,
            event_type='0206',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # Scout locks and missiles Commander at time 12000 (after
        # downtime ends at 11000)
        # Downs Commander, takes 2 lives
        GameEvent(
            game_id='test_rule_game',
            time=12000,
            event_type='0306',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='missiled',
            raw_message='',
        ),
        # Team Life Boost from Medic on team 1 (time 13000).
        # Scout is active (time 13000), so Scout is resupplied.
        # Commander is on team 0, so not resupplied.
        # Medic is the actor, so not resupplied.
        GameEvent(
            game_id='test_rule_game',
            time=13000,
            event_type='0512',
            actor_entity_id='M2',
            action='life_boost',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    # Verify state after events:
    players = replay.game_state.players
    cmd_state = players['C1']
    sct_state = players['S2']
    med_state = players['M2']

    # Commander started with 15 lives.
    # Got downed once at 3000 (-1 life -> 14 lives).
    # Got missiled at 12000 (-2 lives -> 12 lives).
    assert cmd_state.lives == 12
    assert cmd_state.hp == 0
    assert cmd_state.downtime_ends_at_ms == 20000  # 12000 + 8000

    # Scout started with 15 lives.
    # Medic resupplied lives to team at 13000.
    # Scout gained 5 lives (from 15 to 20).
    assert sct_state.lives == 20
    # Medic itself should NOT gain lives.
    assert med_state.lives == 20


def test_replay_missile_decrements_and_penalties() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    # Create game
    game = LFGame(game_id='test_m_game', timestamp=datetime.now(), game_type='SM5')
    game.penalty = -500

    # Teams
    t1 = GameTeam(
        game_id='test_m_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    game.teams = [t1]

    # Entities
    cmd = GameEntity(
        game_id='test_m_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    base = GameEntity(
        game_id='test_m_game',
        entity_id='B1',
        type='standard-target',
        desc='Blue Base',
        team_index=1,
        level=1,
        category=0,
        battlesuit='',
    )
    game.entities = [cmd, base]

    events = [
        # Mission start
        GameEvent(
            game_id='test_m_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Missile miss at 1000 ms (decrements missiles)
        GameEvent(
            game_id='test_m_game',
            time=1000,
            event_type='0304',
            actor_entity_id='C1',
            action='miss',
            raw_message='',
        ),
        # Missile base miss at 2000 ms (decrements missiles)
        GameEvent(
            game_id='test_m_game',
            time=2000,
            event_type='0301',
            actor_entity_id='C1',
            target_entity_id='B1',
            action='miss base',
            raw_message='',
        ),
        # Missile base damage at 3000 ms (decrements missiles)
        GameEvent(
            game_id='test_m_game',
            time=3000,
            event_type='0302',
            actor_entity_id='C1',
            target_entity_id='B1',
            action='damage base',
            raw_message='',
        ),
        # Penalty at 4000 ms (adds penalty -500 to score)
        GameEvent(
            game_id='test_m_game',
            time=4000,
            event_type='0600',
            actor_entity_id='C1',
            action='penalty',
            raw_message='',
        ),
        # Missile base destroy at 5000 ms (decrements missiles, awards capture)
        GameEvent(
            game_id='test_m_game',
            time=5000,
            event_type='0303',
            actor_entity_id='C1',
            target_entity_id='B1',
            action='destroys',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    cmd_state = replay.game_state.players['C1']
    # Commmander starts with 5 missiles.
    # Fires 4: at 1000 (0304), 2000 (0301), 3000 (0302), and 5000 (0303).
    # Resulting missiles: 5 - 4 = 1.
    assert cmd_state.missiles == 1

    # Score:
    # Capturing base awards 1001 points.
    # Penalty deducts 500 points.
    # Total score should be 501.
    assert cmd_state.score == 501
    assert 'B1' in cmd_state.captured_bases


def test_medic_and_nuke_life_rules() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id='test_medic_nuke_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_medic_nuke_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_medic_nuke_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Commander on team 0
    cmd = GameEntity(
        game_id='test_medic_nuke_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Medic on team 1
    med = GameEntity(
        game_id='test_medic_nuke_game',
        entity_id='M2',
        type='player',
        desc='Med2',
        team_index=1,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    # Scout on team 1
    sct = GameEntity(
        game_id='test_medic_nuke_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [cmd, med, sct]

    events = [
        # Mission start
        GameEvent(
            game_id='test_medic_nuke_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Commander zaps Medic (Medic is downed and loses 1 life)
        GameEvent(
            game_id='test_medic_nuke_game',
            time=1000,
            event_type='0206',
            actor_entity_id='C1',
            target_entity_id='M2',
            action='zaps',
            raw_message='',
        ),
        # Commander missiles Medic at time 10000 (after downtime ends)
        # Medic is downed by missile and loses 2 lives
        GameEvent(
            game_id='test_medic_nuke_game',
            time=10000,
            event_type='0306',
            actor_entity_id='C1',
            target_entity_id='M2',
            action='missiled',
            raw_message='',
        ),
        # Commander detonates nuke at time 20000 (after downtime ends)
        # Scout and Medic are downed and lose 3 lives each
        GameEvent(
            game_id='test_medic_nuke_game',
            time=20000,
            event_type='0405',
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    players = replay.game_state.players
    med_state = players['M2']
    sct_state = players['S2']

    # Medic starts with 20 lives. Zap (-1), missile (-2), nuke (-3) -> 14 lives.
    assert med_state.lives == 14
    assert med_state.hp == 0
    assert med_state.downtime_ends_at_ms == 28000  # 20000 + 8000

    # Scout starts with 15 lives. Detonating nuke at 20000 takes 3 lives.
    # So Scout should have 12 lives.
    assert sct_state.lives == 12
    assert sct_state.hp == 0


def test_team_boost_not_down() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id='test_boost_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_boost_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_boost_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Commander on team 0
    cmd = GameEntity(
        game_id='test_boost_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Medic on team 1
    med = GameEntity(
        game_id='test_boost_game',
        entity_id='M2',
        type='player',
        desc='Med2',
        team_index=1,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    # Scout 1 on team 1
    s1 = GameEntity(
        game_id='test_boost_game',
        entity_id='S1',
        type='player',
        desc='Sct1',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    # Scout 2 on team 1
    s2 = GameEntity(
        game_id='test_boost_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [cmd, med, s1, s2]

    events = [
        # Mission start
        GameEvent(
            game_id='test_boost_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Commander zaps S2 (S2 is downed)
        GameEvent(
            game_id='test_boost_game',
            time=1000,
            event_type='0206',
            actor_entity_id='C1',
            target_entity_id='S2',
            action='zaps',
            raw_message='',
        ),
        # Medic resupplies team (life boost) at time 2000
        # S1 is active, so S1's lives should increase from 15 to 18
        # S2 is down, so S2's lives should remain 14
        GameEvent(
            game_id='test_boost_game',
            time=2000,
            event_type='0512',
            actor_entity_id='M2',
            action='life_boost',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    players = replay.game_state.players
    s1_state = players['S1']
    s2_state = players['S2']

    # S1 was active, should receive boost: 15 + 5 = 20 lives
    assert s1_state.lives == 20

    # S2 was down, should NOT receive boost: 15 - 1 = 14 lives
    assert s2_state.lives == 14


def test_scout_rapid_fire_sp_rules() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id='test_rapid_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_rapid_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_rapid_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Scout 1 on team 0
    s1 = GameEntity(
        game_id='test_rapid_game',
        entity_id='S1',
        type='player',
        desc='Sct1',
        team_index=0,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    # Enemy Scout 2 on team 1
    s2 = GameEntity(
        game_id='test_rapid_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    # Medic on team 0
    med = GameEntity(
        game_id='test_rapid_game',
        entity_id='M1',
        type='player',
        desc='Med1',
        team_index=0,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    # Base on team 1
    base = GameEntity(
        game_id='test_rapid_game',
        entity_id='B2',
        type='standard-target',
        desc='Base2',
        team_index=1,
        level=1,
        category=9,
        battlesuit='',
    )
    game.entities = [s1, s2, med, base]

    events = [
        # Mission start
        GameEvent(
            game_id='test_rapid_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # 1. Scout zaps enemy Scout (gets 1 SP)
        GameEvent(
            game_id='test_rapid_game',
            time=1000,
            event_type='0205',
            actor_entity_id='S1',
            target_entity_id='S2',
            action='zaps',
            raw_message='',
        ),
    ]

    # We want Scout to have at least 15 SP to activate rapid fire
    # A Scout zaps enemy Scout 15 times to get 15 SP (total 16 SP)
    for t in range(2000, 17000, 1000):
        events.append(
            GameEvent(
                game_id='test_rapid_game',
                time=t,
                event_type='0205',
                actor_entity_id='S1',
                target_entity_id='S2',
                action='zaps',
                raw_message='',
            )
        )

    # Time 17000: Scout S1 has 16 SP. Activates rapid fire (costs 15 SP,
    # has_rapid_fire becomes True)
    events.extend(
        [
            GameEvent(
                game_id='test_rapid_game',
                time=17000,
                event_type='0400',
                actor_entity_id='S1',
                action='activates rapid fire',
                raw_message='',
            ),
            # Time 18000: Scout zaps enemy Scout again (with rapid fire,
            # gets score but NO SP!)
            GameEvent(
                game_id='test_rapid_game',
                time=18000,
                event_type='0205',
                actor_entity_id='S1',
                target_entity_id='S2',
                action='zaps',
                raw_message='',
            ),
            # Time 19000: Scout S1 captures a base (with rapid fire,
            # gets score but NO SP!)
            GameEvent(
                game_id='test_rapid_game',
                time=19000,
                event_type='0204',
                actor_entity_id='S1',
                target_entity_id='B2',
                action='destroys base',
                raw_message='',
            ),
            # Time 20000: Medic resupplies S1 (clears rapid fire!)
            GameEvent(
                game_id='test_rapid_game',
                time=20000,
                event_type='0502',
                actor_entity_id='M1',
                target_entity_id='S1',
                action='resupplies lives',
                raw_message='',
            ),
            # Time 30000: Scout zaps enemy Scout again (after rapid fire
            # cleared, gets SP!)
            GameEvent(
                game_id='test_rapid_game',
                time=30000,
                event_type='0205',
                actor_entity_id='S1',
                target_entity_id='S2',
                action='zaps',
                raw_message='',
            ),
        ]
    )
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    s1_state = replay.game_state.players['S1']

    # Trace of S1 SP:
    # 1. 16 zaps before rapid fire -> 16 SP
    # 2. Activate rapid fire -> 16 - 15 = 1 SP. has_rapid_fire = True
    # 3. Zap S2 under rapid fire -> still 1 SP.
    # 4. Destroy base under rapid fire -> still 1 SP.
    # 5. Medic resupplies S1 -> has_rapid_fire = False
    # 6. Zap S2 post rapid fire -> 1 + 1 = 2 SP.
    assert s1_state.has_rapid_fire is False
    assert s1_state.special_points == 2


def test_nuke_cancel_scenarios() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    # Create game
    game = LFGame(
        game_id='test_nuke_cancel_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    t1 = GameTeam(
        game_id='test_nuke_cancel_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_nuke_cancel_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Entities:
    # Cmd1 on team 0
    c1 = GameEntity(
        game_id='test_nuke_cancel_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Teammate Scout on team 0
    s1 = GameEntity(
        game_id='test_nuke_cancel_game',
        entity_id='S1',
        type='player',
        desc='Sct1',
        team_index=0,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    # Enemy Commander on team 1
    c2 = GameEntity(
        game_id='test_nuke_cancel_game',
        entity_id='C2',
        type='player',
        desc='Cmd2',
        team_index=1,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Enemy Scout on team 1
    s2 = GameEntity(
        game_id='test_nuke_cancel_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [c1, s1, c2, s2]

    events = [
        # Mission start
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # --- Scenario 1: Enemy downing cancel ---
        # Time 1000: Cmd1 activates nuke
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=1000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Time 3000: Enemy Scout S2 downs Cmd1 (0206)
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=3000,
            event_type='0206',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # --- Scenario 2: Friendly fire downing cancel ---
        # Time 20000: Cmd1 is back up, activates nuke again
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=20000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Time 22000: Teammate S1 downs Cmd1 (0208)
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=22000,
            event_type='0208',
            actor_entity_id='S1',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # --- Scenario 3: Cancel by own resup ---
        # Time 40000: Cmd1 is back up, activates nuke again
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=40000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Time 43000: Teammate resupplies Cmd1 (0500)
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=43000,
            event_type='0500',
            actor_entity_id='S1',
            target_entity_id='C1',
            action='resupplies',
            raw_message='',
        ),
        # --- Scenario 4: Cancel by enemy nuke ---
        # Time 60000: Cmd1 is back up, activates nuke again
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=60000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Time 61000: Enemy Commander C2 detonates nuke (0405)
        # C2 must have activated nuke first at 55000 (successful detonate)
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=55000,
            event_type='0404',
            actor_entity_id='C2',
            action='activates nuke',
            raw_message='',
        ),
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=61000,
            event_type='0405',
            actor_entity_id='C2',
            action='detonates nuke',
            raw_message='',
        ),
        # --- Scenario 5: Timeout (Nuke activated too late / expires) ---
        # Time 80000: Cmd1 is back up, activates nuke again.
        # No detonation or canceling event occurs. Should expire at 90000.
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=80000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Time 95000: Just some random event to make game run past 90000
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=95000,
            event_type='0201',
            actor_entity_id='S1',
            action='misses',
            raw_message='',
        ),
        # Mission end
        GameEvent(
            game_id='test_nuke_cancel_game',
            time=100000,
            event_type='0101',
            action='end',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    records = replay.run()

    # Verify cancels were injected and generated correct descriptions
    # Time 3000: Cmd1 nuke canceled (downed by S2)
    s1_cancel = next(
        (
            r
            for r in records
            if r.time_ms == 3000 and r.description == 'Cmd1 nuke canceled'
        ),
        None,
    )
    assert s1_cancel is not None

    # Time 22000: Cmd1 nuke canceled by friendly fire (downed by S1)
    s2_cancel = next(
        (
            r
            for r in records
            if r.time_ms == 22000
            and r.description == 'Cmd1 nuke canceled by friendly fire'
        ),
        None,
    )
    assert s2_cancel is not None

    # Time 43000: Cmd1 nuke canceled by own resup (resupplied by S1)
    s3_cancel = next(
        (
            r
            for r in records
            if r.time_ms == 43000 and r.description == 'Cmd1 nuke canceled by own resup'
        ),
        None,
    )
    assert s3_cancel is not None

    # Time 61000: Cmd1 nuke canceled by enemy nuke (C2 detonates)
    s4_cancel = next(
        (
            r
            for r in records
            if r.time_ms == 61000
            and r.description == 'Cmd1 nuke canceled by enemy nuke'
        ),
        None,
    )
    assert s4_cancel is not None

    # Time 90000: Cmd1 nuke activated too late (expires after 10s)
    s5_cancel = next(
        (
            r
            for r in records
            if r.time_ms == 90000 and r.description == 'Cmd1 nuke activated too late'
        ),
        None,
    )
    assert s5_cancel is not None

    # Verify stat counters
    c1_state = replay.game_state.players['C1']
    s2_state = replay.game_state.players['S2']
    c2_state = replay.game_state.players['C2']

    # C1 activated 5 times (1000, 20000, 40000, 60000, 80000)
    assert c1_state.nukes_activated == 5
    # C1 detonated 0 times
    assert c1_state.nukes_detonated == 0
    # C1 had own nuke canceled 5 times
    assert c1_state.own_nuke_cancels == 5

    # S2 zapped Cmd1 at 3000 (Scenario 1), canceling Cmd1's nuke.
    # S2's nuke_cancels should be 1.
    assert s2_state.nuke_cancels == 1

    # C2 activated 1 time (55000), detonated 1 time (61000)
    assert c2_state.nukes_activated == 1
    assert c2_state.nukes_detonated == 1
    assert c2_state.own_nuke_cancels == 0


def test_team_boost_rules() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id='test_team_boost_rules_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    t1 = GameTeam(
        game_id='test_team_boost_rules_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_team_boost_rules_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Entities:
    # Cmd1 on team 0 (enemy target)
    c1 = GameEntity(
        game_id='test_team_boost_rules_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Medic M2 on team 1
    m2 = GameEntity(
        game_id='test_team_boost_rules_game',
        entity_id='M2',
        type='player',
        desc='Med2',
        team_index=1,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    # Ammo A2 on team 1
    a2 = GameEntity(
        game_id='test_team_boost_rules_game',
        entity_id='A2',
        type='player',
        desc='Ammo2',
        team_index=1,
        level=1,
        category=2,
        battlesuit='Ammo',
    )
    # Scout S2 on team 1
    s2 = GameEntity(
        game_id='test_team_boost_rules_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [c1, m2, a2, s2]

    # Build events to award SP to M2, A2, and S2
    events = [
        GameEvent(
            game_id='test_team_boost_rules_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    # M2 zaps C1 20 times (giving M2 20 SP)
    # A2 zaps C1 12 times (giving A2 12 SP)
    # S2 zaps C1 16 times (giving S2 16 SP)
    t = 1000
    for _ in range(20):
        events.append(
            GameEvent(
                game_id='test_team_boost_rules_game',
                time=t,
                event_type='0205',
                actor_entity_id='M2',
                target_entity_id='C1',
                action='zaps',
                raw_message='',
            )
        )
        t += 100
    for _ in range(12):
        events.append(
            GameEvent(
                game_id='test_team_boost_rules_game',
                time=t,
                event_type='0205',
                actor_entity_id='A2',
                target_entity_id='C1',
                action='zaps',
                raw_message='',
            )
        )
        t += 100
    for _ in range(16):
        events.append(
            GameEvent(
                game_id='test_team_boost_rules_game',
                time=t,
                event_type='0205',
                actor_entity_id='S2',
                target_entity_id='C1',
                action='zaps',
                raw_message='',
            )
        )
        t += 100

    # S2 activates rapid fire (costs 15 SP, has 1 SP left)
    events.append(
        GameEvent(
            game_id='test_team_boost_rules_game',
            time=t,
            event_type='0400',
            actor_entity_id='S2',
            action='activates rapid fire',
            raw_message='',
        )
    )
    t += 1000

    # Medic M2 triggers life boost (0512) -> costs 15 SP, S2 receives lives
    events.append(
        GameEvent(
            game_id='test_team_boost_rules_game',
            time=t,
            event_type='0512',
            actor_entity_id='M2',
            action='life_boost',
            raw_message='',
        )
    )
    t += 1000

    # Ammo A2 triggers ammo boost (0510) -> costs 10 SP, S2 receives shots
    events.append(
        GameEvent(
            game_id='test_team_boost_rules_game',
            time=t,
            event_type='0510',
            actor_entity_id='A2',
            action='ammo_boost',
            raw_message='',
        )
    )
    t += 1000

    game.events = events
    replay = LFReplaySystem(game)
    replay.run()

    m2_state = replay.game_state.players['M2']
    a2_state = replay.game_state.players['A2']
    s2_state = replay.game_state.players['S2']

    # M2 started with 20 SP, used 15 for boost -> should have 5 SP
    assert m2_state.special_points == 5

    # A2 started with 12 SP, used 10 for boost -> should have 2 SP
    assert a2_state.special_points == 2

    # S2 had rapid fire. S2 was boosted but should RETAIN rapid fire!
    assert s2_state.has_rapid_fire is True

    # S2 received life boost (lives go from 15 to 20)
    assert s2_state.lives == 20

    # S2 received ammo boost (shots go from 30 - 16 + 10 = 24)
    assert s2_state.shots == 24


def test_zap_and_missile_downed_player_authoritative() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    # Create game
    game = LFGame(
        game_id='test_resettable_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_resettable_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_resettable_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Commander on team 0 (15 lives, 3 HP)
    cmd = GameEntity(
        game_id='test_resettable_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Scout on team 1 (15 lives, 1 HP)
    sct = GameEntity(
        game_id='test_resettable_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [cmd, sct]

    events = [
        # Mission start
        GameEvent(
            game_id='test_resettable_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Scout zaps Commander (Commander HP: 3 -> 2)
        GameEvent(
            game_id='test_resettable_game',
            time=1000,
            event_type='0205',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # Scout zaps Commander again (Commander HP: 2 -> 1)
        GameEvent(
            game_id='test_resettable_game',
            time=2000,
            event_type='0205',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # Scout zaps Commander again (Commander HP: 1 -> 0, DOWNED, loses 1 life,
        # down until 3000 + 8000 = 11000, resettable at 3000 + 4000 = 7000)
        GameEvent(
            game_id='test_resettable_game',
            time=3000,
            event_type='0206',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # Scout missiles Commander at 6000 ms (Commander is currently down).
        # Since TDF is authoritative, target loses 2 lives, no matter what!
        # Downtime resets to 6000 + 8000 = 14000 ms.
        GameEvent(
            game_id='test_resettable_game',
            time=6000,
            event_type='0306',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='missiles',
            raw_message='',
        ),
        # Scout zaps Commander at 9000 ms (Commander is still down).
        # Since TDF is authoritative, target loses 1 life, no matter what!
        # Downtime resets to 9000 + 8000 = 17000 ms.
        GameEvent(
            game_id='test_resettable_game',
            time=9000,
            event_type='0206',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    players = replay.game_state.players
    cmd_state = players['C1']

    # Commander starts with 15 lives.
    # 1. Downed at 3000 ms (0206) -> 14 lives
    # 2. Missiled at 6000 ms (0306) -> 12 lives (deducted even though down!)
    # 3. Zapped at 9000 ms (0206) -> 11 lives (deducted even though down!)
    assert cmd_state.lives == 11
    # Downtime should be reset to 9000 + 8000 = 17000 ms
    assert cmd_state.downtime_ends_at_ms == 17000
    assert cmd_state.resettable_starts_at_ms == 13000


