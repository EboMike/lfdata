from lflive.models.team import LiveTeam


def test_team_instantiation() -> None:
    team = LiveTeam(
        id=7,
        team_id=1,
        name='Earth Team',
        color='Green',
        rgb='#00ff00',
        score=24500,
    )
    assert team.id == 7
    assert team.team_id == 1
    assert team.name == 'Earth Team'
    assert team.color == 'Green'
    assert team.rgb == '#00ff00'
    assert team.score == 24500

