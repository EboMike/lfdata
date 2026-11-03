from lflive.models.player import LivePlayer


def test_player_instantiation() -> None:
    player = LivePlayer(
        id=99,
        player_id=3,
        entity_id='#1A2B3C',
        name='Ace',
        team_id=2,
        role='commander',
        lives=15,
        shots=60,
        missiles=5,
        special_points=25,
        hitpoints=3,
        score=3500,
        goals=4,
        assists=2,
        blocks=10,
        clears=3,
        steals=5,
        state=0,
        rapid_fire=True,
    )
    assert player.id == 99
    assert player.player_id == 3
    assert player.entity_id == '#1A2B3C'
    assert player.name == 'Ace'
    assert player.team_id == 2
    assert player.role == 'commander'
    assert player.lives == 15
    assert player.shots == 60
    assert player.missiles == 5
    assert player.special_points == 25
    assert player.hitpoints == 3
    assert player.score == 3500
    assert player.goals == 4
    assert player.assists == 2
    assert player.blocks == 10
    assert player.clears == 3
    assert player.steals == 5
    assert player.state == 0
    assert player.rapid_fire is True

