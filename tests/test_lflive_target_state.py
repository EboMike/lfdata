from lflive.state.target_state import LiveTargetState


def test_target_state_fields() -> None:
    target = LiveTargetState(
        target_id=1,
        entity_id='#010001',
        name='Earth Base',
        rgb='#00ff00',
    )
    assert target.target_id == 1
    assert target.entity_id == '#010001'
    assert target.name == 'Earth Base'
    assert target.rgb == '#00ff00'
