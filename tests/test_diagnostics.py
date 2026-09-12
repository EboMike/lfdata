from unittest.mock import MagicMock

from lfdata.model import (
    GameEntity,
    GameEvent,
    LFGame,
    LFRole,
    PlayerStateHistory,
)
from lfdata.replay.diagnostics import (
    LFReplayDiagnostics,
    describe_player_state_at_ms,
    format_timestamp_ms,
    get_state_label,
)
from lfdata.replay.state import LFReplayPlayerState
from lfdata.replay.verification import PlayerDiscrepancy


def test_format_timestamp_ms() -> None:
    assert format_timestamp_ms(0) == '00:00.000'
    assert format_timestamp_ms(65432) == '01:05.432'
    assert format_timestamp_ms(-500) == '00:00.000'
    assert format_timestamp_ms(170566) == '02:50.566'


def test_get_state_label() -> None:
    assert get_state_label(0) == 'Up'
    assert get_state_label(2) == 'Resettable'
    assert get_state_label(3) == 'Down'
    assert get_state_label(99) == 'Unknown(99)'


def test_build_mismatch_infos() -> None:
    game = LFGame(game_id='test_diag_game', game_type='SM5')
    entity1 = GameEntity(
        game_id='test_diag_game',
        entity_id='player_1',
        type='player',
        desc='PlayerOne',
        team_index=0,
    )
    entity2 = GameEntity(
        game_id='test_diag_game',
        entity_id='player_2',
        type='player',
        desc='PlayerTwo',
        team_index=0,
    )
    game.entities = [entity1, entity2]

    replay = MagicMock()
    diagnostics = LFReplayDiagnostics(game=game, replay=replay)

    discrepancies = {
        'player_1': [
            PlayerDiscrepancy(field='lives', computed=22, expected=26),
            PlayerDiscrepancy(field='score', computed=1000, expected=1000),
        ],
        'player_2': [
            PlayerDiscrepancy(field='shots', computed=40, expected=30),
        ],
        'player_3': [
            PlayerDiscrepancy(field='score', computed=500, expected=600),
        ],
    }

    infos = diagnostics.build_mismatch_infos(discrepancies)
    assert len(infos) == 2
    assert infos[0].entity_id == 'player_1'
    assert infos[0].codename == 'PlayerOne'
    assert infos[0].lives_discrepancy is not None
    assert infos[0].lives_discrepancy.computed == 22
    assert infos[0].shots_discrepancy is None

    assert infos[1].entity_id == 'player_2'
    assert infos[1].codename == 'PlayerTwo'
    assert infos[1].shots_discrepancy is not None
    assert infos[1].shots_discrepancy.computed == 40
    assert infos[1].lives_discrepancy is None


def test_dump_mismatches_empty(capsys: object) -> None:
    game = LFGame(game_id='test_empty_game', game_type='SM5')
    replay = MagicMock()
    diagnostics = LFReplayDiagnostics(game=game, replay=replay)
    diagnostics.dump_mismatches({})
    captured = capsys.readouterr()
    assert captured.out == ''


def test_dump_mismatches_lives_discrepancy(capsys: object) -> None:
    game = LFGame(game_id='diag_test_game', game_type='SM5')
    p1 = GameEntity(
        game_id='diag_test_game',
        entity_id='player_1',
        type='player',
        desc='CommanderOne',
        team_index=0,
    )
    p2 = GameEntity(
        game_id='diag_test_game',
        entity_id='player_2',
        type='player',
        desc='MedicOne',
        team_index=0,
    )
    game.entities = [p1, p2]

    # Boost event at 170000ms
    boost_event = GameEvent(
        game_id='diag_test_game',
        time=170000,
        event_type='0512',
        actor_entity_id='player_2',
        action='resupplies team',
    )
    # Related zap event within 2000ms
    zap_event = GameEvent(
        game_id='diag_test_game',
        time=169200,
        event_type='0206',
        actor_entity_id='player_enemy',
        target_entity_id='player_1',
        action='zaps',
    )
    game.events = [zap_event, boost_event]

    # State history: went down at 169100 (900ms before boost)
    sh_down = PlayerStateHistory(
        game_id='diag_test_game',
        time=169100,
        entity_id='player_1',
        state=3,
    )
    game.state_history = [sh_down]

    p1_state = LFReplayPlayerState(
        'player_1',
        role=LFRole.COMMANDER,
        team_index=0,
        state_history=[sh_down],
    )
    p2_state = LFReplayPlayerState(
        'player_2',
        role=LFRole.MEDIC,
        team_index=0,
    )

    replay = MagicMock()
    replay.game_state.players = {
        'player_1': p1_state,
        'player_2': p2_state,
    }

    diagnostics = LFReplayDiagnostics(
        game=game, replay=replay, boost_grace_period_ms=700
    )

    discrepancies = {
        'player_1': [PlayerDiscrepancy(field='lives', computed=22, expected=26)]
    }

    diagnostics.dump_mismatches(discrepancies)
    captured = capsys.readouterr()

    assert 'DISCREPANCY DIAGNOSTICS & AMBIGUOUS EVENT ANALYSIS' in captured.out
    assert 'Player CommanderOne (player_1) - Team 0' in captured.out
    assert (
        'Lives mismatch: computed=22, expected=26 (difference: -4 lives)'
        in captured.out
    )
    assert (
        'Team Life Boost at 170000 ms (02:50.000) by MedicOne (player_2):'
        in captured.out
    )
    assert (
        '169100 ms (02:49.100): State 3 (Down) [delta: -900 ms]' in captured.out
    )
    assert '169200 ms (02:49.200): type=0206 action="zaps"' in captured.out
    assert (
        'Player was DOWN at boost time (went down at 169100 ms' in captured.out
    )
    assert 'exceeded 700 ms grace period by 200 ms' in captured.out
    assert 'This boost may have been incorrectly skipped' in captured.out


def test_dump_mismatches_ammo_discrepancy(capsys: object) -> None:
    game = LFGame(game_id='ammo_test_game', game_type='SM5')
    p1 = GameEntity(
        game_id='ammo_test_game',
        entity_id='player_1',
        type='player',
        desc='ScoutOne',
        team_index=1,
    )
    p2 = GameEntity(
        game_id='ammo_test_game',
        entity_id='player_2',
        type='player',
        desc='AmmoCarrier',
        team_index=1,
    )
    game.entities = [p1, p2]

    # Ammo boost event at 100000ms
    boost_event = GameEvent(
        game_id='ammo_test_game',
        time=100000,
        event_type='0510',
        actor_entity_id='player_2',
        action='resupplies team',
    )
    game.events = [boost_event]
    game.state_history = []

    p1_state = LFReplayPlayerState(
        'player_1',
        role=LFRole.SCOUT,
        team_index=1,
    )
    p2_state = LFReplayPlayerState(
        'player_2',
        role=LFRole.AMMO,
        team_index=1,
    )

    replay = MagicMock()
    replay.game_state.players = {
        'player_1': p1_state,
        'player_2': p2_state,
    }

    diagnostics = LFReplayDiagnostics(
        game=game, replay=replay, boost_grace_period_ms=700
    )

    discrepancies = {
        'player_1': [PlayerDiscrepancy(field='shots', computed=45, expected=35)]
    }

    diagnostics.dump_mismatches(discrepancies)
    captured = capsys.readouterr()

    assert (
        'Ammo mismatch: computed=45, expected=35 (difference: +10 shots)'
        in captured.out
    )
    assert (
        'Team Ammo Boost at 100000 ms (01:40.000) by AmmoCarrier (player_2):'
        in captured.out
    )
    assert 'Player was UP at boost time' in captured.out
    assert 'Computed shots are higher than expected (+10)' in captured.out


def test_describe_player_state_at_ms() -> None:
    p_elim = LFReplayPlayerState('p1', role=LFRole.SCOUT, team_index=0)
    p_elim.lives = 0
    desc, can_up = describe_player_state_at_ms(p_elim, 100000)
    assert 'Eliminated' in desc
    assert not can_up

    sh_up = PlayerStateHistory(game_id='g', time=50000, entity_id='p2', state=0)
    p_auth_up = LFReplayPlayerState(
        'p2', role=LFRole.COMMANDER, team_index=0, state_history=[sh_up]
    )
    desc, can_up = describe_player_state_at_ms(p_auth_up, 60000)
    assert 'Up' in desc
    assert can_up

    sh_res = PlayerStateHistory(
        game_id='g', time=50000, entity_id='p3', state=2
    )
    p_auth_res = LFReplayPlayerState(
        'p3', role=LFRole.COMMANDER, team_index=0, state_history=[sh_res]
    )
    desc, can_up = describe_player_state_at_ms(p_auth_res, 60000)
    assert 'Resettable' in desc
    assert can_up

    sh_down = PlayerStateHistory(
        game_id='g', time=58000, entity_id='p4', state=3
    )
    p_auth_down = LFReplayPlayerState(
        'p4', role=LFRole.COMMANDER, team_index=0, state_history=[sh_down]
    )
    desc, can_up = describe_player_state_at_ms(p_auth_down, 60000)
    assert 'Down' in desc
    assert can_up

    p_nonauth = LFReplayPlayerState('p5', role=LFRole.HEAVY, team_index=0)
    desc, can_up = describe_player_state_at_ms(p_nonauth, 60000)
    assert 'Up' in desc
    assert can_up


def test_analyze_game_termination_full_distance() -> None:
    game = LFGame(game_id='term_game_full', game_type='SM5', duration=900000)
    replay = MagicMock()
    replay.game_ended_at_ms = 900004
    replay.first_team_elimination_time_ms = None
    p1 = LFReplayPlayerState('p1', role=LFRole.SCOUT, team_index=0)
    replay.game_state.players = {'p1': p1}

    diag = LFReplayDiagnostics(game=game, replay=replay)
    info = diag.analyze_game_termination()

    assert info.ran_full_distance is True
    assert info.game_ended_at_ms == 900004
    assert info.scheduled_duration_ms == 900000
    assert 'Ran full distance' in info.reason


def test_analyze_game_termination_elimination() -> None:
    game = LFGame(game_id='term_game_elim', game_type='SM5', duration=900000)
    replay = MagicMock()
    replay.game_ended_at_ms = 680000
    replay.first_team_elimination_time_ms = 670000
    p1 = LFReplayPlayerState('p1', role=LFRole.SCOUT, team_index=0)
    p2 = LFReplayPlayerState('p2', role=LFRole.SCOUT, team_index=1)
    p2.lives = 0
    replay.game_state.players = {'p1': p1, 'p2': p2}

    diag = LFReplayDiagnostics(game=game, replay=replay)
    info = diag.analyze_game_termination()

    assert info.ran_full_distance is False
    assert info.elimination_time_ms == 670000
    assert 1 in info.eliminated_team_indices
    assert 'team elimination' in info.reason.lower()


def test_analyze_game_termination_early() -> None:
    game = LFGame(game_id='term_game_early', game_type='SM5', duration=900000)
    replay = MagicMock()
    replay.game_ended_at_ms = 500000
    replay.first_team_elimination_time_ms = None
    p1 = LFReplayPlayerState('p1', role=LFRole.SCOUT, team_index=0)
    replay.game_state.players = {'p1': p1}

    diag = LFReplayDiagnostics(game=game, replay=replay)
    info = diag.analyze_game_termination()

    assert info.ran_full_distance is False
    assert 'early termination' in info.reason.lower()


def test_post_game_eligibility_lives(capsys: object) -> None:
    game = LFGame(game_id='post_game_lives', game_type='SM5', duration=900000)
    p1_entity = GameEntity(
        game_id='post_game_lives',
        entity_id='p1',
        type='player',
        desc='CmdrOne',
        team_index=0,
    )
    medic_entity = GameEntity(
        game_id='post_game_lives',
        entity_id='m1',
        type='player',
        desc='MedOne',
        team_index=0,
    )
    game.entities = [p1_entity, medic_entity]
    game.events = []
    game.state_history = []

    p1 = LFReplayPlayerState('p1', role=LFRole.COMMANDER, team_index=0)
    medic = LFReplayPlayerState('m1', role=LFRole.MEDIC, team_index=0)
    medic.lives = 5

    replay = MagicMock()
    replay.game_ended_at_ms = 600000
    replay.first_team_elimination_time_ms = None
    replay.game_state.players = {'p1': p1, 'm1': medic}

    diag = LFReplayDiagnostics(game=game, replay=replay)
    discrepancies = {
        'p1': [PlayerDiscrepancy(field='lives', computed=22, expected=26)]
    }
    diag.dump_mismatches(discrepancies)
    captured = capsys.readouterr()

    assert 'Post-Game Discrepancy Reconciliation' in captured.out
    assert 'Teammate Medic MedOne (m1): Up' in captured.out
    assert 'Both player and Medic were eligible to be Up' in captured.out
    assert 'Medic resupply gain for COMMANDER: +4 lives' in captured.out
    assert 'ELIGIBLE: A single medic resupply (+4 lives)' in captured.out


def test_post_game_eligibility_ammo(capsys: object) -> None:
    game = LFGame(game_id='post_game_ammo', game_type='SM5', duration=900000)
    p1_entity = GameEntity(
        game_id='post_game_ammo',
        entity_id='p1',
        type='player',
        desc='ScoutOne',
        team_index=1,
    )
    game.entities = [p1_entity]
    game.events = []
    game.state_history = []

    p1 = LFReplayPlayerState('p1', role=LFRole.SCOUT, team_index=1)
    p1.shots = 15

    replay = MagicMock()
    replay.game_ended_at_ms = 600000
    replay.first_team_elimination_time_ms = None
    replay.game_state.players = {'p1': p1}

    diag = LFReplayDiagnostics(game=game, replay=replay)
    discrepancies = {
        'p1': [PlayerDiscrepancy(field='shots', computed=12, expected=10)]
    }
    diag.dump_mismatches(discrepancies)
    captured = capsys.readouterr()

    assert 'Post-Game Discrepancy Reconciliation' in captured.out
    assert 'Player remaining shots at game end: 15' in captured.out
    assert (
        'ELIGIBLE: Player was alive with 15 shots remaining and could be Up'
        in captured.out
    )
    assert 'could easily have fired 2 shot(s)' in captured.out
