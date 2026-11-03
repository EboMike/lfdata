from lflive.models.target import LiveTarget


def test_target_instantiation() -> None:
    target = LiveTarget(
        id=12,
        target_id=1,
        entity_id='#010001',
        name='Fire Base',
        rgb='#ff0000',
    )
    assert target.id == 12
    assert target.target_id == 1
    assert target.entity_id == '#010001'
    assert target.name == 'Fire Base'
    assert target.rgb == '#ff0000'
