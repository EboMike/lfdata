from lflive.constants import (
    DATA_TYPE_BASE_DESCRIPTION,
    DATA_TYPE_PLAYER_DESCRIPTION,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_TEAM_DESCRIPTION,
)
from lflive.emitter import OutputEmitter
from lflive.entity_registrar import EntityRegistrar
from lflive.state.game_state import LiveGameState


def test_entity_registrar() -> None:
    state = LiveGameState(game_type='SM5')
    emitter = OutputEmitter()
    reg = EntityRegistrar(game_state=state, emitter=emitter)

    team = reg.register_team(
        team_index=0, name='Fire Team', color='Fire', rgb='#FF5000'
    )
    assert team.team_id == 1
    assert team.name == 'Fire Team'
    assert (
        f'{DATA_TYPE_TEAM_DESCRIPTION}\t0\t1\tFire Team\t#FF5000'
        in emitter.emitted_lines
    )

    player = reg.register_player(
        entity_id='#P1', codename='Ace', team_index=0, category=1
    )
    assert player.player_id == 1
    assert player.name == 'Ace'
    assert player.team_id == 1
    assert any(
        ev.startswith(f'{DATA_TYPE_PLAYER_DESCRIPTION}\t0\t1\tAce\t#P1\t1\t')
        for ev in emitter.emitted_lines
    )
    assert f'{DATA_TYPE_PLAYER_LIVES}\t0\t1\t15' in emitter.emitted_lines

    target = reg.register_target(
        entity_id='#B1', name='Fire Base', team_index=0
    )
    assert target.target_id == 1
    assert (
        f'{DATA_TYPE_BASE_DESCRIPTION}\t0\t1\tFire Base\t#FF5000'
        in emitter.emitted_lines
    )

    reg.reset()
    assert reg.next_player_id == 1
    assert reg.next_target_id == 1
    assert len(reg.entity_to_team_index) == 0

