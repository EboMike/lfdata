import lflive.state


def test_state_init_exports() -> None:
    assert hasattr(lflive.state, 'LiveGameState')
    assert hasattr(lflive.state, 'LivePlayerState')
    assert hasattr(lflive.state, 'LiveTeamState')
    assert hasattr(lflive.state, 'LiveTargetState')
    assert hasattr(lflive.state, 'SnapshotEntry')
