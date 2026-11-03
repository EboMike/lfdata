from lflive.constants import (
    DATA_TYPE_GAME_START_TIME,
    DATA_TYPE_GAME_TYPE,
    DATA_TYPE_NEW_GAME,
    DATA_TYPE_PLAYER_DESCRIPTION,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_RANKING,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_STATE,
    DATA_TYPE_TEAM_DESCRIPTION,
    DATA_TYPE_TEAM_RANKING,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.emitter import OutputEmitter
from lflive.ingestor import TdfIngestor
from lflive.state.game_state import LiveGameState


def test_ingest_info_and_comments() -> None:
    state = LiveGameState()
    ingestor = TdfIngestor(game_state=state)
    ingestor.ingest_line(';0/info\tfile-version\tprogram-version\tcentre')
    ingestor.ingest_line('')
    ingestor.ingest_line('0\t2.005\t8.503\t4-43')
    assert state.game_type == 'SM5'


def test_ingest_mission_sm5_and_laserball() -> None:
    state = LiveGameState()
    ingestor = TdfIngestor(game_state=state)

    ingestor.ingest_line(
        '1\t5\tSpace Marines 5 Tournament\t20261103100000\t900000\t-1000'
    )
    assert state.game_type == 'SM5'
    assert state.start_time == '20261103100000'
    assert state.duration_seconds == 900

    ingestor.ingest_line('1\t10\tLaserball\t20261103110000\t720000\t-500')
    assert state.game_type == 'Laserball'
    assert state.start_time == '20261103110000'
    assert state.duration_seconds == 720


def test_ingest_teams_and_entities() -> None:
    state = LiveGameState(game_type='SM5')
    ingestor = TdfIngestor(game_state=state)

    ingestor.ingest_line('2\t0\tFire Team\t11\tFire\t#FF5000')
    ingestor.ingest_line('2\t1\tEarth Team\t13\tEarth\t#A0FF00')

    assert len(state.teams) == 2
    assert state.teams[1].name == 'Fire Team'
    assert state.teams[2].name == 'Earth Team'

    # Commander role category = 1 (or 5)
    ingestor.ingest_line('3\t0000001\t#P1\tplayer\tAce\t0\t0\t1\tMaverick')
    # Base entity
    ingestor.ingest_line('3\t0000002\t#B1\tbase\tFire Base\t0\t0\t0\tBaseSuit')
    # Generator target entity
    ingestor.ingest_line(
        '3\t0000003\t@66\tgenerator-target\tReactor\t0\t0\t0\tReactor'
    )

    player = state.get_player_by_entity('#P1')
    assert player is not None
    assert player.name == 'Ace'
    assert player.team_id == 1
    assert player.lives > 0
    assert player.shots > 0

    base = state.get_target_by_entity('#B1')
    assert base is not None
    assert base.name == 'Fire Base'
    assert base.rgb == '#FF5000'

    reactor = state.get_target_by_entity('@66')
    assert reactor is not None
    assert reactor.name == 'Reactor'
    assert reactor.rgb == '#FF5000'


def test_ingest_events_sm5() -> None:
    state = LiveGameState(game_type='SM5')
    ingestor = TdfIngestor(game_state=state)
    ingestor.ingest_line('2\t0\tFire Team\t11\tFire\t#FF5000')
    ingestor.ingest_line('3\t0000001\t#P1\tplayer\tAce\t0\t0\t1\tMaverick')
    player = state.get_player_by_entity('#P1')
    assert player is not None

    # Rapid fire on/off
    ingestor.ingest_line('4\t0001000\t0400\t#P1\tactivates rapid fire')
    assert player.rapid_fire is True
    assert state.current_time_ms == 1000

    ingestor.ingest_line('4\t0002000\t0401\t#P1\tdeactivates rapid fire')
    assert player.rapid_fire is False

    # Nuke activation and detonation
    player.special_points = 25
    ingestor.ingest_line('4\t0003000\t0404\t#P1\tactivates nuke')
    assert player.special_points == 5

    ingestor.ingest_line('4\t0007000\t0405\t#P1\tdetonates nuke')
    assert player.score == 500

    # Base destruction
    ingestor.ingest_line('4\t0008000\t0204\t#P1\tdestroys base\t#B1')
    assert player.score == 1501
    assert player.special_points == 10

    # Mission end
    ingestor.ingest_line('4\t0009000\t0101\t* Mission End *')
    assert state.is_game_over is True


def test_ingest_events_laserball() -> None:
    state = LiveGameState(game_type='Laserball')
    ingestor = TdfIngestor(game_state=state)
    ingestor.ingest_line('2\t0\tFire\t11\tFire\t#FF5000')
    ingestor.ingest_line('2\t1\tEarth\t13\tEarth\t#A0FF00')
    ingestor.ingest_line('3\t0000001\t#P1\tplayer\tP1\t0\t0\t0\tSuit')
    ingestor.ingest_line('3\t0000002\t#P2\tplayer\tP2\t1\t0\t0\tSuit')

    p1 = state.get_player_by_entity('#P1')
    p2 = state.get_player_by_entity('#P2')
    assert p1 is not None and p2 is not None

    # Round start
    ingestor.ingest_line('4\t0001000\t1105\t* Round Start *')
    assert state.is_in_round is True

    # Gets ball
    ingestor.ingest_line('4\t0002000\t1107\t#P1\tgets ball')
    assert state.ball_carrier_id == p1.player_id

    # Pass
    ingestor.ingest_line('4\t0003000\t1100\t#P1\tpasses to\t#P2')
    assert state.ball_carrier_id == p2.player_id

    # Block
    ingestor.ingest_line('4\t0004000\t1104\t#P1\tblocks\t#P2')
    assert p1.blocks == 1
    assert p2.state == 3

    # Steal
    ingestor.ingest_line('4\t0005000\t1103\t#P1\tsteals from\t#P2')
    assert p1.steals == 1
    assert state.ball_carrier_id == p1.player_id

    # Clear
    ingestor.ingest_line('4\t0006000\t1109\t#P1\tclears ball to\t#P2')
    assert p1.clears == 1
    assert state.ball_carrier_id == p2.player_id

    # Goal and assist
    ingestor.ingest_line('4\t0007000\t1102\t#P1\tassists')
    assert p1.assists == 1

    ingestor.ingest_line('4\t0007500\t1101\t#P2\tscores goal')
    assert p2.goals == 1
    assert state.teams[2].score == 1

    # Round end
    ingestor.ingest_line('4\t0008000\t1106\t* Round End *')
    assert state.is_in_round is False
    assert state.round_number == 2


def test_ingest_authoritative_records() -> None:
    state = LiveGameState(game_type='SM5')
    ingestor = TdfIngestor(game_state=state)
    ingestor.ingest_line('2\t0\tFire\t11\tFire\t#FF5000')
    ingestor.ingest_line('3\t0000001\t#P1\tplayer\tAce\t0\t0\t1\tSuit')
    player = state.get_player_by_entity('#P1')
    assert player is not None

    # Score update (Type 5)
    ingestor.ingest_line('5\t0001000\t#P1\t0\t100\t100')
    assert player.score == 100
    assert state.teams[1].score == 100

    # Operational state update (Type 9)
    ingestor.ingest_line('9\t0002000\t#P1\t2')
    assert player.state == 2

    # Lives update (Type 11)
    ingestor.ingest_line('11\t0003000\t#P1\t15\t14')
    assert player.lives == 14

    # Ammo update (Type 12)
    ingestor.ingest_line('12\t0004000\t#P1\t30\t29')
    assert player.shots == 29

    # Missiles update (Type 13)
    ingestor.ingest_line('13\t0005000\t#P1\t5\t4')
    assert player.missiles == 4

    # Player elimination to 0 lives sets state 4 (Dead)
    ingestor.ingest_line('11\t0006000\t#P1\t1\t0')
    assert player.lives == 0
    assert player.state == 4


def test_ingestor_reset() -> None:
    state = LiveGameState(game_type='SM5')
    ingestor = TdfIngestor(game_state=state)
    ingestor.ingest_line('2\t0\tFire\t11\tFire\t#FF5000')
    ingestor.ingest_line('3\t0000001\t#P1\tplayer\tAce\t0\t0\t1\tSuit')
    assert ingestor._next_player_id == 2

    ingestor.reset()
    assert ingestor._next_player_id == 1
    assert len(ingestor._entity_to_team_index) == 0


def test_ingestor_with_emitter() -> None:
    state = LiveGameState()
    emitter = OutputEmitter()
    ingestor = TdfIngestor(game_state=state, emitter=emitter)

    ingestor.ingest_line('1\t5\tSpace Marines 5\t20261103100000\t900000\t-1000')
    assert f'{DATA_TYPE_GAME_TYPE}\t0\tSM5\t900' in emitter.emitted_lines
    assert (
        f'{DATA_TYPE_GAME_START_TIME}\t0\t20261103100000'
        in emitter.emitted_lines
    )

    ingestor.ingest_line('2\t0\tFire Team\t11\tFire\t#FF5000')
    assert (
        f'{DATA_TYPE_TEAM_DESCRIPTION}\t0\t1\tFire Team\t#FF5000'
        in emitter.emitted_lines
    )

    ingestor.ingest_line('3\t0000001\t#P1\tplayer\tAce\t0\t0\t1\tMaverick')
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_DESCRIPTION}\t0\t1\tAce\t#P1\t1\t')
        for ev in emitter.emitted_lines
    )
    assert f'{DATA_TYPE_PLAYER_LIVES}\t0\t1\t15' in emitter.emitted_lines

    ingestor.ingest_line('5\t0001000\t#P1\t0\t100\t100')
    assert f'{DATA_TYPE_PLAYER_SCORE}\t1000\t1\t100' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_SCORE}\t1000\t1\t100' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_RANKING}\t1000\t1\t1' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_RANKING}\t1000\t1' in emitter.emitted_lines

    ingestor.ingest_line('9\t0002000\t#P1\t2')
    assert f'{DATA_TYPE_PLAYER_STATE}\t2000\t1\t2' in emitter.emitted_lines

    ingestor.ingest_line('12\t0003000\t#P1\t30\t28')
    assert f'{DATA_TYPE_PLAYER_SHOTS}\t3000\t1\t28' in emitter.emitted_lines

    ingestor.ingest_line('13\t0004000\t#P1\t5\t3')
    assert f'{DATA_TYPE_PLAYER_MISSILES}\t4000\t1\t3' in emitter.emitted_lines

    ingestor.ingest_line('11\t0005000\t#P1\t1\t0')
    assert f'{DATA_TYPE_PLAYER_LIVES}\t5000\t1\t0' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_STATE}\t5000\t1\t4' in emitter.emitted_lines

    ingestor.reset()
    assert f'{DATA_TYPE_NEW_GAME}\t0' in emitter.emitted_lines


def test_ingestor_ranking_events() -> None:
    state = LiveGameState()
    emitter = OutputEmitter()
    ingestor = TdfIngestor(game_state=state, emitter=emitter)

    ingestor.ingest_line('1\t5\tSM5\t20261103100000\t900000\t-1000')
    ingestor.ingest_line('2\t0\tFire\t11\tFire\t#FF5000')
    ingestor.ingest_line('2\t1\tIce\t12\tIce\t#0000FF')
    ingestor.ingest_line('3\t0000001\t#P1\tplayer\tP1\t0\t0\t1\tScout')
    ingestor.ingest_line('3\t0000002\t#P2\tplayer\tP2\t1\t0\t1\tScout')
    ingestor.ingest_line('3\t0000003\t#P3\tplayer\tP3\t0\t0\t1\tScout')

    # Mission start emits initial ranking
    ingestor.ingest_line('4\t0000000\t0100\t* Mission Start *')
    assert f'{DATA_TYPE_PLAYER_RANKING}\t0\t1\t1,3' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_RANKING}\t0\t2\t2' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_RANKING}\t0\t1,2' in emitter.emitted_lines

    emitter.clear()
    # P3 scores and overtakes P1 within team 1
    ingestor.ingest_line('5\t0005000\t#P3\t0\t500\t500')
    assert f'{DATA_TYPE_PLAYER_RANKING}\t5000\t1\t3,1' in emitter.emitted_lines
    assert not any(
        ev.startswith(f'{DATA_TYPE_PLAYER_RANKING}\t5000\t2')
        for ev in emitter.emitted_lines
    )
