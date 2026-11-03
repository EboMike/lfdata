from lflive.state.snapshot_entry import SnapshotEntry


def test_snapshot_entry() -> None:
    entry = SnapshotEntry(
        time_ms=1500,
        entity_type='player',
        entity_id=1,
        field_name='score',
        value='500',
    )
    assert entry.time_ms == 1500
    assert entry.entity_type == 'player'
    assert entry.entity_id == 1
    assert entry.field_name == 'score'
    assert entry.value == '500'

