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
    game = LFGame(
        game_id='test_rule_game', timestamp=datetime.now(), game_type='SM5'
    )

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
    game = LFGame(
        game_id='test_m_game', timestamp=datetime.now(), game_type='SM5'
    )
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
    assert cmd_state.penalties == 1
    assert cmd_state.hp == 0
    assert cmd_state.is_down(5000) is True
    assert cmd_state.downtime_ends_at_ms == 12000
    assert cmd_state.resettable_starts_at_ms == 8000


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
            if r.time_ms == 43000
            and r.description == 'Cmd1 nuke canceled by own resup'
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
            if r.time_ms == 90000
            and r.description == 'Cmd1 nuke activated too late'
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
        category=4,
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

    # M2 started with 20 SP, used 10 for boost -> should have 10 SP
    assert m2_state.special_points == 10

    # A2 started with 12 SP, used 15 for boost -> should have 0 SP
    assert a2_state.special_points == 0

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


def test_team_boost_within_grace_period() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    # Create game
    game = LFGame(
        game_id='test_grace_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    # Add teams
    t1 = GameTeam(
        game_id='test_grace_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_grace_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Add entities
    med = GameEntity(
        game_id='test_grace_game',
        entity_id='M1',
        type='player',
        desc='Med1',
        team_index=0,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    sct = GameEntity(
        game_id='test_grace_game',
        entity_id='S1',
        type='player',
        desc='Sct1',
        team_index=0,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    sct2 = GameEntity(
        game_id='test_grace_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=0,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    enemy = GameEntity(
        game_id='test_grace_game',
        entity_id='E2',
        type='player',
        desc='Enemy2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [med, sct, sct2, enemy]

    events = [
        GameEvent(
            game_id='test_grace_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Enemy zaps Sct1 at time 1000 ms.
        # Sct1 HP: 1 -> 0, DOWNED.
        # Downtime ends at 1000 + 8000 = 9000 ms.
        # Sct1 just_went_down_at_ms is set to 1000 ms.
        GameEvent(
            game_id='test_grace_game',
            time=1000,
            event_type='0206',
            actor_entity_id='E2',
            target_entity_id='S1',
            action='zaps',
            raw_message='',
        ),
        # Medic boosts team (life boost) at time 1500 ms.
        # Sct1 is down, but within 750ms grace period. Sct1 should be boosted!
        GameEvent(
            game_id='test_grace_game',
            time=1500,
            event_type='0512',
            actor_entity_id='M1',
            action='life_boost',
            raw_message='',
        ),
        # Enemy zaps Sct2 at time 3000 ms.
        # Sct2 HP: 1 -> 0, DOWNED.
        # Downtime ends at 3000 + 8000 = 11000 ms.
        GameEvent(
            game_id='test_grace_game',
            time=3000,
            event_type='0206',
            actor_entity_id='E2',
            target_entity_id='S2',
            action='zaps',
            raw_message='',
        ),
        # Medic boosts team (life boost) at time 4000 ms (1000ms > 750ms).
        # Sct2 is down and past grace period. Sct2 should NOT be boosted.
        GameEvent(
            game_id='test_grace_game',
            time=4000,
            event_type='0512',
            actor_entity_id='M1',
            action='life_boost',
            raw_message='',
        ),
        # Enemy zaps Sct1 at time 5000 ms (Sct1 is already down).
        # Sct1 downtime is reset to 5000 + 8000 = 13000 ms.
        # Since Sct1 was already down, just_went_down_at_ms should NOT update.
        GameEvent(
            game_id='test_grace_game',
            time=5000,
            event_type='0206',
            actor_entity_id='E2',
            target_entity_id='S1',
            action='zaps',
            raw_message='',
        ),
        # Medic boosts team (life boost) at time 5500 ms.
        # Elapsed since just_went_down_at_ms (1000ms) is 4500ms > 750ms.
        # Sct1 should NOT be boosted.
        GameEvent(
            game_id='test_grace_game',
            time=5500,
            event_type='0512',
            actor_entity_id='M1',
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

    # S1 start lives: 15.
    # 1. Downed at 1000 ms (-1 life -> 14 lives).
    # 2. Boosted at 1500 ms (+5 lives -> 19 lives).
    # 3. Downed again at 5000 ms (downtime reset, -1 life -> 18 lives).
    # 4. Boosted at 5500 ms (fails because already down, lives stay 18).
    assert s1_state.lives == 18

    # S2 start lives: 15.
    # 1. Boosted at 1500 ms (active, +5 lives -> 20 lives).
    # 2. Downed at 3000 ms (-1 life -> 19 lives).
    # 3. Boosted at 4000 ms (fails because elapsed > 750ms, lives stay 19).
    assert s2_state.lives == 19


def test_replay_stats_alignment() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent
    from lfdata.model.gametypes.sm5_stats import Sm5Stats

    # Create game
    game = LFGame(
        game_id='test_align_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_align_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_align_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    med = GameEntity(
        game_id='test_align_game',
        entity_id='M1',
        type='player',
        desc='Med1',
        team_index=0,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    sct = GameEntity(
        game_id='test_align_game',
        entity_id='S1',
        type='player',
        desc='Sct1',
        team_index=0,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    enemy = GameEntity(
        game_id='test_align_game',
        entity_id='E2',
        type='player',
        desc='Enemy2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [med, sct, enemy]

    events = [
        GameEvent(
            game_id='test_align_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # E2 zaps S1 at 1000ms. S1 down, lives: 15 -> 14.
        GameEvent(
            game_id='test_align_game',
            time=1000,
            event_type='0206',
            actor_entity_id='E2',
            target_entity_id='S1',
            action='zaps',
            raw_message='',
        ),
        # Medic boosts team (life boost) at time 1500 ms (500ms elapsed).
        # S1 is down, and elapsed = 500 ms (abs(500 - 750) = 250 <= 500 ms).
        # This makes S1 ambiguous!
        GameEvent(
            game_id='test_align_game',
            time=1500,
            event_type='0512',
            actor_entity_id='M1',
            action='life_boost',
            raw_message='',
        ),
    ]
    game.events = events

    # Add expected stats requiring S1 to receive the boost (lives = 19)
    s1_stats = Sm5Stats(
        game_id='test_align_game',
        entity_id='S1',
        lives_left=19,
        shots_left=30,
    )
    med_stats = Sm5Stats(
        game_id='test_align_game',
        entity_id='M1',
        lives_left=20,
        shots_left=15,
    )
    e2_stats = Sm5Stats(
        game_id='test_align_game',
        entity_id='E2',
        lives_left=15,
        shots_left=29,
    )
    game.sm5_stats = [s1_stats, med_stats, e2_stats]

    replay = LFReplaySystem(game)
    replay.run()

    # The simulation should align S1 lives to 19 (meaning choice was True)
    assert replay.game_state.players['S1'].lives == 19

    # Now let's try the same game but requiring S1 to NOT receive the boost
    game2 = LFGame(
        game_id='test_align_game_2',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    game2.teams = [t1, t2]
    game2.entities = [med, sct, enemy]
    game2.events = events

    s1_stats_no_boost = Sm5Stats(
        game_id='test_align_game_2',
        entity_id='S1',
        lives_left=14,  # Lives remain 14 (no boost)
        shots_left=30,
    )
    game2.sm5_stats = [s1_stats_no_boost, med_stats, e2_stats]

    replay2 = LFReplaySystem(game2)
    replay2.run()

    # The simulation should align S1 lives to 14 (meaning choice was False)
    assert replay2.game_state.players['S1'].lives == 14


def test_replay_recovery_boundary_alignment() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent
    from lfdata.model.gametypes.sm5_stats import Sm5Stats

    # Create game
    game = LFGame(
        game_id='test_recovery_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_recovery_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_recovery_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    med = GameEntity(
        game_id='test_recovery_game',
        entity_id='M1',
        type='player',
        desc='Med1',
        team_index=0,
        level=1,
        category=5,
        battlesuit='Medic',
    )
    sct = GameEntity(
        game_id='test_recovery_game',
        entity_id='S1',
        type='player',
        desc='Sct1',
        team_index=0,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    enemy = GameEntity(
        game_id='test_recovery_game',
        entity_id='E2',
        type='player',
        desc='Enemy2',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [med, sct, enemy]

    events = [
        GameEvent(
            game_id='test_recovery_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # E2 zaps S1 at 1000ms. S1 down, lives: 15 -> 14.
        # S1 downtime ends at 9000ms.
        GameEvent(
            game_id='test_recovery_game',
            time=1000,
            event_type='0206',
            actor_entity_id='E2',
            target_entity_id='S1',
            action='zaps',
            raw_message='',
        ),
        # Medic boosts team at time 8800 ms (200ms before downtime ends).
        # This is recovery boundary ambiguity.
        GameEvent(
            game_id='test_recovery_game',
            time=8800,
            event_type='0512',
            actor_entity_id='M1',
            action='life_boost',
            raw_message='',
        ),
    ]
    game.events = events

    # Add expected stats requiring S1 to receive the boost (lives = 19)
    s1_stats = Sm5Stats(
        game_id='test_recovery_game',
        entity_id='S1',
        lives_left=19,
        shots_left=30,
    )
    med_stats = Sm5Stats(
        game_id='test_recovery_game',
        entity_id='M1',
        lives_left=20,
        shots_left=15,
    )
    e2_stats = Sm5Stats(
        game_id='test_recovery_game',
        entity_id='E2',
        lives_left=15,
        shots_left=29,
    )
    game.sm5_stats = [s1_stats, med_stats, e2_stats]

    replay = LFReplaySystem(game)
    replay.run()

    assert replay.game_state.players['S1'].lives == 19


def test_replay_friendly_fire_and_resupply_lives() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id='test_ff_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_ff_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    game.teams = [t1]

    h1 = GameEntity(
        game_id='test_ff_game',
        entity_id='H1',
        type='player',
        desc='Heavy1',
        team_index=0,
        level=1,
        category=4,
        battlesuit='Heavy',
    )
    c1 = GameEntity(
        game_id='test_ff_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Commander',
    )
    game.entities = [h1, c1]

    events = [
        GameEvent(
            game_id='test_ff_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # H1 zaps C1 friendly fire downed team (0208)
        GameEvent(
            game_id='test_ff_game',
            time=1000,
            event_type='0208',
            actor_entity_id='H1',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
        # H1 missiles C1 friendly fire downed team (0308)
        GameEvent(
            game_id='test_ff_game',
            time=10000,
            event_type='0308',
            actor_entity_id='H1',
            target_entity_id='C1',
            action='missiles',
            raw_message='',
        ),
        # H1 resupplies C1 lives (0502)
        GameEvent(
            game_id='test_ff_game',
            time=20000,
            event_type='0502',
            actor_entity_id='H1',
            target_entity_id='C1',
            action='resupplies',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    # C1 starts with 15 lives.
    # Zap teammate (-1) -> 14.
    # Missile teammate (-2) -> 12.
    # Medic resupply (+4 for commander) -> 16.
    assert replay.game_state.players['C1'].lives == 16


def test_heavy_special_points_never_accumulate() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id='test_heavy_sp_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )

    t1 = GameTeam(
        game_id='test_heavy_sp_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_heavy_sp_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Heavy on team 0
    heavy = GameEntity(
        game_id='test_heavy_sp_game',
        entity_id='H1',
        type='player',
        desc='Heavy1',
        team_index=0,
        level=1,
        category=2,  # Heavy
        battlesuit='Heavy',
    )
    # Enemy commander on team 1
    enemy = GameEntity(
        game_id='test_heavy_sp_game',
        entity_id='C2',
        type='player',
        desc='Cmd2',
        team_index=1,
        level=1,
        category=1,
        battlesuit='Commander',
    )
    # Enemy base on team 1
    base = GameEntity(
        game_id='test_heavy_sp_game',
        entity_id='B2',
        type='standard-target',
        desc='Base2',
        team_index=1,
        level=1,
        category=9,
        battlesuit='',
    )
    game.entities = [heavy, enemy, base]

    events = [
        # Mission start
        GameEvent(
            game_id='test_heavy_sp_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Heavy zaps enemy Commander (gets score but NO SP!)
        GameEvent(
            game_id='test_heavy_sp_game',
            time=1000,
            event_type='0205',
            actor_entity_id='H1',
            target_entity_id='C2',
            action='zaps',
            raw_message='',
        ),
        # Heavy missiles enemy Commander (gets score but NO SP!)
        GameEvent(
            game_id='test_heavy_sp_game',
            time=2000,
            event_type='0306',
            actor_entity_id='H1',
            target_entity_id='C2',
            action='missiled',
            raw_message='',
        ),
        # Heavy captures enemy base (gets score but NO SP!)
        GameEvent(
            game_id='test_heavy_sp_game',
            time=3000,
            event_type='0204',
            actor_entity_id='H1',
            target_entity_id='B2',
            action='destroys base',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    replay.run()

    heavy_state = replay.game_state.players['H1']
    assert heavy_state.special_points == 0


def test_replay_missing_0101() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameEntity, GameEvent

    game = LFGame(
        game_id='test_missing_0101',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    p = GameEntity(
        game_id='test_missing_0101',
        entity_id='P1',
        type='player',
        desc='Player1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Commander',
    )
    game.entities = [p]
    game.events = [
        GameEvent(
            game_id='test_missing_0101',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        GameEvent(
            game_id='test_missing_0101',
            time=5000,
            event_type='0200',
            actor_entity_id='P1',
            action='zap',
            raw_message='',
        ),
    ]

    replay = LFReplaySystem(game)
    replay.run()

    # The last event time is 5000, so game_ended_at_ms should be 5000
    assert replay.game_ended_at_ms == 5000


def test_laserball_replay() -> None:
    from datetime import datetime
    from lfdata.model import GameEntity, GameEvent, GameTeam, LFGame

    game = LFGame(
        game_id='lb_replay_test',
        timestamp=datetime.now(),
        game_type='Laserball',
        penalty=-1000,
    )
    t1 = GameTeam(
        game_id='lb_replay_test',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='lb_replay_test',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#A0FF00',
    )
    game.teams = [t1, t2]

    p1 = GameEntity(
        game_id='lb_replay_test',
        entity_id='P1',
        type='player',
        desc='RedCarrier',
        team_index=0,
    )
    p2 = GameEntity(
        game_id='lb_replay_test',
        entity_id='P2',
        type='player',
        desc='RedTeammate',
        team_index=0,
    )
    e1 = GameEntity(
        game_id='lb_replay_test',
        entity_id='E1',
        type='player',
        desc='GreenDefender',
        team_index=1,
    )
    base1 = GameEntity(
        game_id='lb_replay_test',
        entity_id='BASE_G',
        type='base',
        desc='Green Base',
        team_index=1,
    )
    game.entities = [p1, p2, e1, base1]

    events = [
        # Mission start
        GameEvent(
            game_id='lb_replay_test',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Round 1 start
        GameEvent(
            game_id='lb_replay_test',
            time=1000,
            event_type='1105',
            action='Round start',
            raw_message='',
        ),
        # P1 receives ball
        GameEvent(
            game_id='lb_replay_test',
            time=2000,
            event_type='1107',
            actor_entity_id='P1',
            action='gets ball',
            raw_message='',
        ),
        # P1 passes to P2
        GameEvent(
            game_id='lb_replay_test',
            time=5000,
            event_type='1100',
            actor_entity_id='P1',
            target_entity_id='P2',
            action='passes to',
            raw_message='',
        ),
        # E1 blocks P1
        GameEvent(
            game_id='lb_replay_test',
            time=6000,
            event_type='1104',
            actor_entity_id='E1',
            target_entity_id='P1',
            action='blocks',
            raw_message='',
        ),
        # P1 resets on base at 8000
        GameEvent(
            game_id='lb_replay_test',
            time=8000,
            event_type='110B',
            actor_entity_id='P1',
            target_entity_id='BASE_G',
            action='resets on base',
            raw_message='',
        ),
        # P2 scores a goal
        GameEvent(
            game_id='lb_replay_test',
            time=10000,
            event_type='1101',
            actor_entity_id='P2',
            action='scores a goal',
            raw_message='',
        ),
        # P1 assisted P2
        GameEvent(
            game_id='lb_replay_test',
            time=10000,
            event_type='1102',
            actor_entity_id='P1',
            target_entity_id='P2',
            action='assists',
            raw_message='',
        ),
        # Round 1 end
        GameEvent(
            game_id='lb_replay_test',
            time=11000,
            event_type='1106',
            action='Round end',
            raw_message='',
        ),
        # Round 2 start
        GameEvent(
            game_id='lb_replay_test',
            time=15000,
            event_type='1105',
            action='Round start',
            raw_message='',
        ),
        # E1 gets ball
        GameEvent(
            game_id='lb_replay_test',
            time=16000,
            event_type='1107',
            actor_entity_id='E1',
            action='gets ball',
            raw_message='',
        ),
        # P1 steals from E1
        GameEvent(
            game_id='lb_replay_test',
            time=20000,
            event_type='1103',
            actor_entity_id='P1',
            target_entity_id='E1',
            action='steals from',
            raw_message='',
        ),
        # P1 clears to P2
        GameEvent(
            game_id='lb_replay_test',
            time=25000,
            event_type='1109',
            actor_entity_id='P1',
            target_entity_id='P2',
            action='clears to',
            raw_message='',
        ),
        # Mission end
        GameEvent(
            game_id='lb_replay_test',
            time=30000,
            event_type='0101',
            action='end',
            raw_message='',
        ),
    ]
    game.events = events

    replay = LFReplaySystem(game)
    records = replay.run()
    assert len(records) == len(events)

    p1_state = replay.game_state.players['P1']
    p2_state = replay.game_state.players['P2']
    e1_state = replay.game_state.players['E1']

    # Roles should be None in Laserball
    assert p1_state.role is None
    assert p2_state.role is None
    assert e1_state.role is None

    # Players should never be eliminated
    assert not p1_state.is_eliminated()
    assert not p2_state.is_eliminated()
    assert not e1_state.is_eliminated()

    # Check P1 stats:
    # 0 goals, 1 assist, 1 pass, 1 steal, 1 clear, 0 blocks
    # 1 times_zapped (blocked by E1)
    assert p1_state.goals == 0
    assert p1_state.assists == 1
    assert p1_state.passes == 1
    assert p1_state.steals == 1
    assert p1_state.clears == 1
    assert p1_state.blocks == 0
    assert p1_state.times_zapped == 1
    assert p1_state.times_zapped_opponents == 1  # 1 steal against opponent
    # P1 score: (0+1)*10000 + (1+1)*100 + 0 = 10200
    assert p1_state.score == 10200
    # P1 hit diff: 1 opponent hit / 1 time zapped = 1.0
    assert p1_state.hit_diff == 1.0

    # Check P2 stats:
    # 1 goal, 0 assists, 0 passes, 0 steals, 0 clears, 0 blocks
    assert p2_state.goals == 1
    assert p2_state.score == 10000
    assert p2_state.has_ball is True  # received clear at 25000

    # Check E1 stats:
    # 1 block, 0 goals, 1 time zapped (stolen from)
    assert e1_state.blocks == 1
    assert e1_state.times_zapped == 1
    assert e1_state.score == 1
    assert e1_state.hit_diff == 1.0

    # Team scores in Laserball: based on goals!
    # Team 0 (Fire) has 1 goal -> score 1
    # Team 1 (Earth) has 0 goals -> score 0
    team_0 = replay.game_state.teams[0]
    team_1 = replay.game_state.teams[1]
    assert team_0.score == 1
    assert team_0.ranking == 1
    assert team_1.score == 0
    assert team_1.ranking == 2
