from lflive.models.game_session import LiveGameSession


def test_game_session_instantiation() -> None:
    session = LiveGameSession(
        id=42,
        game_type='Laserball',
        start_time='20261102235500123',
        duration_seconds=1200,
        is_active=False,
    )
    assert session.id == 42
    assert session.game_type == 'Laserball'
    assert session.start_time == '20261102235500123'
    assert session.duration_seconds == 1200
    assert session.is_active is False
