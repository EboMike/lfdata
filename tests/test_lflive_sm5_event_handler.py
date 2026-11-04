from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_ACTIVATE_NUKE,
    SM5_EVENT_ACTIVATE_RAPID_FIRE,
    SM5_EVENT_DAMAGED_OPPONENT,
    SM5_EVENT_DAMAGED_TEAM,
    SM5_EVENT_DEACTIVATE_RAPID_FIRE,
    SM5_EVENT_DESTROY_BASE,
    SM5_EVENT_DETONATE_NUKE,
    SM5_EVENT_DOWNED_OPPONENT,
    SM5_EVENT_DOWNED_TEAM,
    SM5_EVENT_HIT_BASE,
    SM5_EVENT_MISSILE_BASE_DAMAGE,
    SM5_EVENT_MISSILE_BASE_DESTROY,
    SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
    SM5_EVENT_MISSILE_DAMAGE_TEAM,
    SM5_EVENT_MISSILE_DOWN_OPPONENT,
    SM5_EVENT_MISSILE_DOWN_TEAM,
    SM5_EVENT_PENALTY,
    SM5_EVENT_RESUPPLY_AMMO,
    SM5_EVENT_RESUPPLY_LIVES,
)
from lflive.constants import (
    DATA_TYPE_BASE_CAPTURED,
    DATA_TYPE_IMPORTANT_EVENT,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_RAPID_FIRE_STATE,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.emitter import OutputEmitter
from lflive.sm5_event_handler import SM5EventHandler
from lflive.state.game_state import LiveGameState


def test_sm5_event_handler_powers_and_bases() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    state.add_target(
        target_id=1, entity_id='#T1', name='Red Base', rgb='#ff0000'
    )
    p1 = state.add_player(
        player_id=1,
        entity_id='#P1',
        name='Ace',
        team_id=1,
        role='commander',
    )
    p1.special_points = 25

    emitter = OutputEmitter()
    handler = SM5EventHandler(game_state=state, emitter=emitter)

    assert handler._colored_player(p1) == '<font color="#ff0000">Ace</font>'
    assert handler._colored_player(None) == 'Unknown'
    assert (
        handler._colored_target(state.targets[1])
        == '<font color="#ff0000">Red Base</font>'
    )
    assert handler._colored_target(None) == 'base'

    # Rapid fire
    handler.handle_event(10000, SM5_EVENT_ACTIVATE_RAPID_FIRE, ['#P1'])
    assert p1.rapid_fire is True
    assert f'{DATA_TYPE_RAPID_FIRE_STATE}\t10000\t1\t1' in emitter.emitted_lines

    handler.handle_event(20000, SM5_EVENT_DEACTIVATE_RAPID_FIRE, ['#P1'])
    assert p1.rapid_fire is False
    assert f'{DATA_TYPE_RAPID_FIRE_STATE}\t20000\t1\t0' in emitter.emitted_lines

    # Nuke
    handler.handle_event(30000, SM5_EVENT_ACTIVATE_NUKE, ['#P1'])
    assert p1.special_points == 5
    assert (
        f'{DATA_TYPE_PLAYER_SPECIAL_POINTS}\t30000\t1\t5'
        in emitter.emitted_lines
    )
    assert any(
        ev.startswith(f'{DATA_TYPE_IMPORTANT_EVENT}\t30000')
        for ev in emitter.emitted_lines
    )

    handler.handle_event(34000, SM5_EVENT_DETONATE_NUKE, ['#P1'])
    assert p1.score == 500
    assert state.teams[1].score == 500
    assert f'{DATA_TYPE_PLAYER_SCORE}\t34000\t1\t500' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_SCORE}\t34000\t1\t500' in emitter.emitted_lines

    # Base hit & destruction
    handler.handle_event(40000, SM5_EVENT_HIT_BASE, ['#P1', '#T1'])
    assert any(
        'zaps <font color="#ff0000">Red Base</font>' in ev
        for ev in emitter.emitted_lines
    )

    handler.handle_event(45000, SM5_EVENT_DESTROY_BASE, ['#P1', '#T1'])
    assert p1.score == 1501
    assert p1.special_points == 10
    assert f'{DATA_TYPE_BASE_CAPTURED}\t45000\t1\t1' in emitter.emitted_lines

    handler.handle_event(50000, SM5_EVENT_MISSILE_BASE_DAMAGE, ['#P1', '#T1'])
    assert any(
        'missiles <font color="#ff0000">Red Base</font>' in ev
        for ev in emitter.emitted_lines
    )

    handler.handle_event(55000, SM5_EVENT_MISSILE_BASE_DESTROY, ['#P1', '#T1'])
    assert p1.score == 2502
    assert f'{DATA_TYPE_BASE_CAPTURED}\t55000\t1\t1' in emitter.emitted_lines


def test_sm5_event_handler_combat() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Blue', color='Blue', rgb='#0000ff')
    state.add_player(
        player_id=1, entity_id='#P1', name='Ace', team_id=1, role='commander'
    )
    state.add_player(
        player_id=2, entity_id='#P2', name='Boba', team_id=2, role='scout'
    )

    emitter = OutputEmitter()
    handler = SM5EventHandler(game_state=state, emitter=emitter)

    codes = [
        (SM5_EVENT_DAMAGED_OPPONENT, 'zaps'),
        (SM5_EVENT_DOWNED_OPPONENT, 'downs'),
        (SM5_EVENT_DAMAGED_TEAM, 'zaps teammate'),
        (SM5_EVENT_DOWNED_TEAM, 'downs teammate'),
        (SM5_EVENT_MISSILE_DAMAGE_OPPONENT, 'missiles'),
        (SM5_EVENT_MISSILE_DOWN_OPPONENT, 'downs'),
        (SM5_EVENT_MISSILE_DAMAGE_TEAM, 'missiles teammate'),
        (SM5_EVENT_MISSILE_DOWN_TEAM, 'downs teammate'),
        (SM5_EVENT_RESUPPLY_AMMO, 'resupplies ammo to'),
        (SM5_EVENT_RESUPPLY_LIVES, 'resupplies lives to'),
        (SM5_EVENT_PENALTY, 'gets a penalty'),
    ]

    for idx, (code, kw) in enumerate(codes):
        t_ms = 60000 + idx * 1000
        handler.handle_event(
            t_ms, code, ['#P1', '#P2'] if code != SM5_EVENT_PENALTY else ['#P1']
        )
        assert any(kw in ev for ev in emitter.emitted_lines)


def test_sm5_event_handler_three_part_varies() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Blue', color='Blue', rgb='#0000ff')
    state.add_target(
        target_id=1, entity_id='@66', name='Red Base', rgb='#ff0000'
    )
    state.add_player(
        player_id=1, entity_id='#P1', name='Ace', team_id=1, role='commander'
    )
    state.add_player(
        player_id=2, entity_id='#P2', name='Boba', team_id=2, role='scout'
    )

    emitter = OutputEmitter()
    handler = SM5EventHandler(game_state=state, emitter=emitter)

    # Standard TDF 3-part combat event: [actor, action_text, target]
    handler.handle_event(
        1000, SM5_EVENT_DAMAGED_OPPONENT, ['#P1', ' zaps ', '#P2']
    )
    assert any(
        '<font color="#ff0000">Ace</font> zaps <font color="#0000ff">Boba</font>'
        in ev
        for ev in emitter.emitted_lines
    )
    assert not any('Unknown' in ev for ev in emitter.emitted_lines)

    # Standard TDF 3-part base event: [actor, action_text, target]
    handler.handle_event(
        2000, SM5_EVENT_DESTROY_BASE, ['#P1', ' destroys ', '@66']
    )
    assert any(
        '<font color="#ff0000">Ace</font> destroys <font color="#ff0000">Red Base</font>'
        in ev
        for ev in emitter.emitted_lines
    )


def test_sm5_event_handler_with_ranking_manager() -> None:
    from lflive.constants import (
        DATA_TYPE_PLAYER_RANKING,
        DATA_TYPE_TEAM_RANKING,
    )
    from lflive.ranking_manager import RankingManager

    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Blue', color='Blue', rgb='#0000ff')
    state.add_player(1, '#P1', 'Ace', 1, 'commander')
    state.add_player(2, '#P2', 'Bravo', 2, 'scout')

    emitter = OutputEmitter()
    ranking_mgr = RankingManager(game_state=state, emitter=emitter)
    handler = SM5EventHandler(
        game_state=state, emitter=emitter, ranking_manager=ranking_mgr
    )

    handler.handle_event(1000, SM5_EVENT_DETONATE_NUKE, ['#P1'])
    assert f'{DATA_TYPE_PLAYER_RANKING}\t1000\t1\t1' in emitter.emitted_lines
    assert f'{DATA_TYPE_PLAYER_RANKING}\t1000\t2\t2' in emitter.emitted_lines
    assert f'{DATA_TYPE_TEAM_RANKING}\t1000\t1,2' in emitter.emitted_lines


def test_nuke_events_sequential_id_and_replacement() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    state.add_player(1, '#P1', 'Ace', 1, 'commander')
    p1 = state.players[1]
    p1.special_points = 25

    emitter = OutputEmitter()
    handler = SM5EventHandler(game_state=state, emitter=emitter)

    handler.handle_event(10000, SM5_EVENT_ACTIVATE_NUKE, ['#P1'])
    act_lines = [
        line for line in emitter.emitted_lines
        if line.startswith(f'{DATA_TYPE_IMPORTANT_EVENT}\t10000')
    ]
    assert len(act_lines) == 1
    assert act_lines[0] == (
        f'{DATA_TYPE_IMPORTANT_EVENT}\t10000\t1\t'
        '<font color="#ff0000">Ace</font> activates nuke'
    )

    handler.handle_event(14000, SM5_EVENT_DETONATE_NUKE, ['#P1'])
    det_lines = [
        line for line in emitter.emitted_lines
        if line.startswith(f'{DATA_TYPE_IMPORTANT_EVENT}\t14000')
    ]
    assert len(det_lines) == 1
    # Sequential ID 1 reused for the detonation replacement message
    assert det_lines[0] == (
        f'{DATA_TYPE_IMPORTANT_EVENT}\t14000\t1\t'
        '<font color="#ff0000">Ace</font> detonates nuke'
    )

    # Next activation receives sequential ID 2
    p1.special_points = 20
    handler.handle_event(20000, SM5_EVENT_ACTIVATE_NUKE, ['#P1'])
    act_lines_2 = [
        line for line in emitter.emitted_lines
        if line.startswith(f'{DATA_TYPE_IMPORTANT_EVENT}\t20000')
    ]
    assert len(act_lines_2) == 1
    assert act_lines_2[0] == (
        f'{DATA_TYPE_IMPORTANT_EVENT}\t20000\t2\t'
        '<font color="#ff0000">Ace</font> activates nuke'
    )


def test_nuke_canceled_on_down_reuses_sequential_id() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Blue', color='Blue', rgb='#0000ff')
    state.add_player(1, '#P1', 'Ace', 1, 'commander')
    state.add_player(2, '#P2', 'Bravo', 2, 'scout')
    state.players[1].special_points = 20

    emitter = OutputEmitter()
    handler = SM5EventHandler(game_state=state, emitter=emitter)

    handler.handle_event(10000, SM5_EVENT_ACTIVATE_NUKE, ['#P1'])
    assert (
        f'{DATA_TYPE_IMPORTANT_EVENT}\t10000\t1\t'
        '<font color="#ff0000">Ace</font> activates nuke'
    ) in emitter.emitted_lines

    # Bravo downs Ace while nuke is active
    handler.handle_event(
        13000,
        SM5_EVENT_DOWNED_OPPONENT,
        ['#P2', 'downs', '#P1'],
    )
    assert (
        f'{DATA_TYPE_IMPORTANT_EVENT}\t13000\t1\t'
        '<font color="#ff0000">Ace</font>\'s nuke canceled by '
        '<font color="#0000ff">Bravo</font>'
    ) in emitter.emitted_lines


def test_nuke_canceled_by_enemy_nuke() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Red', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Blue', color='Blue', rgb='#0000ff')
    state.add_player(1, '#P1', 'Ace', 1, 'commander')
    state.add_player(2, '#P2', 'Bravo', 2, 'commander')
    state.players[1].special_points = 20
    state.players[2].special_points = 20

    emitter = OutputEmitter()
    handler = SM5EventHandler(game_state=state, emitter=emitter)

    # Ace activates nuke (ID 1)
    handler.handle_event(10000, SM5_EVENT_ACTIVATE_NUKE, ['#P1'])
    # Bravo activates nuke (ID 2)
    handler.handle_event(11000, SM5_EVENT_ACTIVATE_NUKE, ['#P2'])

    # Ace detonates nuke at 14000
    handler.handle_event(14000, SM5_EVENT_DETONATE_NUKE, ['#P1'])

    # Ace's detonation replaces ID 1
    assert (
        f'{DATA_TYPE_IMPORTANT_EVENT}\t14000\t1\t'
        '<font color="#ff0000">Ace</font> detonates nuke'
    ) in emitter.emitted_lines
    # Bravo's in-flight nuke replaced with cancel under ID 2
    assert (
        f'{DATA_TYPE_IMPORTANT_EVENT}\t14000\t2\t'
        '<font color="#0000ff">Bravo</font>\'s nuke canceled by enemy nuke'
    ) in emitter.emitted_lines


def test_sm5_event_handler_reset() -> None:
    state = LiveGameState(game_type='SM5')
    handler = SM5EventHandler(game_state=state)
    handler._next_event_id_counter = 10
    handler._active_nuke_event_ids[1] = 5
    handler.reset()
    assert handler._next_event_id_counter == 1
    assert len(handler._active_nuke_event_ids) == 0
