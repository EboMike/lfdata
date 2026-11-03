from lflive.state.player_state import LivePlayerState


def test_player_state_defaults() -> None:
    player = LivePlayerState(
        player_id=1,
        entity_id='#1A2B3C',
        name='Ace',
        team_id=1,
    )
    assert player.player_id == 1
    assert player.entity_id == '#1A2B3C'
    assert player.name == 'Ace'
    assert player.team_id == 1
    assert player.role == ''
    assert player.lives == 0
    assert player.shots == 0
    assert player.missiles == 0
    assert player.special_points == 0
    assert player.hitpoints == 1
    assert player.score == 0
    assert player.goals == 0
    assert player.assists == 0
    assert player.blocks == 0
    assert player.clears == 0
    assert player.steals == 0
    assert player.state == 0
    assert player.rapid_fire is False
    assert player.ranking == 1


def test_player_state_ranking_score() -> None:
    player = LivePlayerState(
        player_id=1,
        entity_id='#1A',
        name='Striker',
        team_id=1,
        score=1500,
        goals=2,
        assists=1,
        clears=5,
        steals=10,
        blocks=4,
    )
    # SM5 ranking score uses score directly
    assert player.calculate_ranking_score(is_laserball=False) == 1500

    # Laserball calculation: (2 + 1) * 10000 + min(99, 15) * 100 + min(99, 4)
    # 30000 + 1500 + 4 = 31504
    assert player.calculate_ranking_score(is_laserball=True) == 31504


def test_player_state_custom_values() -> None:
    player = LivePlayerState(
        player_id=2,
        entity_id='#9Z8Y7X',
        name='Viper',
        team_id=2,
        role='commander',
        lives=15,
        shots=30,
        missiles=5,
        special_points=20,
        hitpoints=3,
        score=2000,
        goals=3,
        assists=1,
        blocks=8,
        clears=2,
        steals=4,
        state=2,
        rapid_fire=True,
    )
    assert player.role == 'commander'
    assert player.lives == 15
    assert player.shots == 30
    assert player.missiles == 5
    assert player.special_points == 20
    assert player.hitpoints == 3
    assert player.score == 2000
    assert player.goals == 3
    assert player.assists == 1
    assert player.blocks == 8
    assert player.clears == 2
    assert player.steals == 4
    assert player.state == 2
    assert player.rapid_fire is True
