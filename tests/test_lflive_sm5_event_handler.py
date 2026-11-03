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

