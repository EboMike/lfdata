from lflive.state.team_state import LiveTeamState


def test_team_state_defaults() -> None:
    team = LiveTeamState(
        team_id=1,
        name='Fire',
        color='Red',
        rgb='#ff0000',
    )
    assert team.team_id == 1
    assert team.name == 'Fire'
    assert team.color == 'Red'
    assert team.rgb == '#ff0000'
    assert team.score == 0
    assert team.ranking == 1


def test_team_state_custom_values() -> None:
    team = LiveTeamState(
        team_id=2,
        name='Earth',
        color='Green',
        rgb='#00ff00',
        score=15000,
        ranking=2,
    )
    assert team.score == 15000
    assert team.ranking == 2

