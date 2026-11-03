from lflive.models.snapshot import LiveSnapshot


def test_snapshot_instantiation() -> None:
    snapshot = LiveSnapshot(
        id=55,
        time_ms=12500,
        entity_type='player',
        entity_id=2,
        field_name='score',
        value='1001',
    )
    assert snapshot.id == 55
    assert snapshot.time_ms == 12500
    assert snapshot.entity_type == 'player'
    assert snapshot.entity_id == 2
    assert snapshot.field_name == 'score'
    assert snapshot.value == '1001'

