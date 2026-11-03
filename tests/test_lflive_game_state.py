from sqlalchemy import select
from lflive.db import LiveDatabase
from lflive.models import (
    LiveGameSession,
    LivePlayer,
    LiveSnapshot,
    LiveTarget,
    LiveTeam,
)
from lflive.state.game_state import LiveGameState


def test_game_state_initialization() -> None:
    state = LiveGameState(
        game_type='Laserball',
        duration_seconds=720,
        start_time='20261103000000123',
    )
    assert state.game_type == 'Laserball'
    assert state.duration_seconds == 720
    assert state.start_time == '20261103000000123'
    assert state.current_time_ms == 0
    assert state.is_game_over is False
    assert state.ball_carrier_id is None
    assert state.round_number == 1
    assert state.is_in_round is False


def test_add_entities_and_lookups() -> None:
    state = LiveGameState(game_type='SM5')
    team = state.add_team(
        team_id=1, name='Fire Team', color='Red', rgb='#ff0000'
    )
    assert team.team_id == 1
    assert state.add_team(1, 'Fire Team', 'Red', '#ff0000') is team

    player = state.add_player(
        player_id=10,
        entity_id='#1A2B3C',
        name='Ace',
        team_id=1,
        role='commander',
    )
    assert player.player_id == 10
    assert state.get_player_by_entity('#1A2B3C') is player
    assert state.get_player_by_entity('#UNKNOWN') is None

    target = state.add_target(
        target_id=20,
        entity_id='#010001',
        name='Earth Base',
        rgb='#00ff00',
    )
    assert target.target_id == 20
    assert state.get_target_by_entity('#010001') is target
    assert state.get_target_by_entity('#UNKNOWN') is None


def test_update_team_scores_sm5() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Earth', color='Green', rgb='#00ff00')

    p1 = state.add_player(1, '#P1', 'P1', 1)
    p2 = state.add_player(2, '#P2', 'P2', 1)
    p3 = state.add_player(3, '#P3', 'P3', 2)

    p1.score = 2500
    p2.score = 1500
    p3.score = 5000

    state.update_team_scores()

    assert state.teams[1].score == 4000
    assert state.teams[1].ranking == 2
    assert state.teams[2].score == 5000
    assert state.teams[2].ranking == 1


def test_update_team_scores_laserball() -> None:
    state = LiveGameState(game_type='Laserball')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    state.add_team(team_id=2, name='Earth', color='Green', rgb='#00ff00')

    p1 = state.add_player(1, '#P1', 'P1', 1)
    p2 = state.add_player(2, '#P2', 'P2', 2)

    p1.goals = 3
    p2.goals = 1

    state.update_team_scores()

    assert state.teams[1].score == 3
    assert state.teams[1].ranking == 1
    assert state.teams[2].score == 1
    assert state.teams[2].ranking == 2


def test_get_state_at_reconstruction() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    state.add_player(
        player_id=1,
        entity_id='#P1',
        name='Ace',
        team_id=1,
        role='commander',
    )
    state.add_target(target_id=1, entity_id='#B1', name='Base', rgb='#ff0000')

    state.record_change(1000, 'player', 1, 'score', '100')
    state.record_change(1500, 'player', 1, 'lives', '14')
    state.record_change(2000, 'player', 1, 'shots', '29')
    state.record_change(2500, 'player', 1, 'missiles', '4')
    state.record_change(3000, 'player', 1, 'special_points', '5')
    state.record_change(3500, 'player', 1, 'hitpoints', '2')
    state.record_change(4000, 'player', 1, 'goals', '1')
    state.record_change(4500, 'player', 1, 'assists', '1')
    state.record_change(5000, 'player', 1, 'blocks', '2')
    state.record_change(5500, 'player', 1, 'clears', '1')
    state.record_change(6000, 'player', 1, 'steals', '3')
    state.record_change(6500, 'player', 1, 'state', '3')
    state.record_change(7000, 'player', 1, 'rapid_fire', '1')
    state.record_change(7500, 'game', 0, 'ball_carrier_id', '1')
    state.record_change(8000, 'game', 0, 'is_game_over', '1')

    # Future changes after 5000 ms
    state.record_change(9000, 'player', 1, 'score', '9999')

    past_state = state.get_state_at(time_ms=5000)
    past_player = past_state.players[1]
    assert past_player.score == 100
    assert past_player.lives == 14
    assert past_player.shots == 29
    assert past_player.missiles == 4
    assert past_player.special_points == 5
    assert past_player.hitpoints == 2
    assert past_player.goals == 1
    assert past_player.assists == 1
    assert past_player.blocks == 2
    assert past_player.clears == 0  # Occurred at 5500 ms
    assert past_player.rapid_fire is False

    full_state = state.get_state_at(time_ms=8500)
    full_player = full_state.players[1]
    assert full_player.clears == 1
    assert full_player.steals == 3
    assert full_player.state == 3
    assert full_player.rapid_fire is True
    assert full_state.ball_carrier_id == 1
    assert full_state.is_game_over is True
    assert full_player.score == 100  # 9000 ms score change not applied


def test_flush_to_database() -> None:
    db = LiveDatabase(':memory:')
    state = LiveGameState(
        game_type='SM5',
        duration_seconds=900,
        start_time='20261103001000',
    )
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    p = state.add_player(1, '#P1', 'Ace', 1, 'commander')
    p.score = 500
    state.add_target(1, '#B1', 'Base', '#ff0000')
    state.record_change(1000, 'player', 1, 'score', '500')

    state.flush_to_database(db=db)

    with db.get_session() as session:
        sess = session.scalars(select(LiveGameSession)).first()
        assert sess is not None
        assert sess.game_type == 'SM5'
        assert sess.duration_seconds == 900

        teams = session.scalars(select(LiveTeam)).all()
        assert len(teams) == 1
        assert teams[0].name == 'Fire'

        players = session.scalars(select(LivePlayer)).all()
        assert len(players) == 1
        assert players[0].score == 500

        targets = session.scalars(select(LiveTarget)).all()
        assert len(targets) == 1
        assert targets[0].name == 'Base'

        snapshots = session.scalars(select(LiveSnapshot)).all()
        assert len(snapshots) == 1
        assert snapshots[0].value == '500'

    # Test incremental snapshot flush
    state.record_change(2000, 'player', 1, 'score', '1000')
    state.flush_to_database(db=db)

    with db.get_session() as session:
        snapshots = session.scalars(select(LiveSnapshot)).all()
        assert len(snapshots) == 2


def test_player_and_team_rankings_sm5() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(1, 'Fire', 'Red', '#ff0000')
    state.add_team(2, 'Ice', 'Blue', '#0000ff')
    p1 = state.add_player(1, '#P1', 'Ace', 1)
    p2 = state.add_player(2, '#P2', 'Bravo', 2)
    p3 = state.add_player(3, '#P3', 'Charlie', 1)

    p1.score = 500
    p2.score = 1500
    p3.score = 1000

    ranks = state.update_player_rankings()
    assert ranks == {1: [3, 1], 2: [2]}
    assert p3.ranking == 1
    assert p1.ranking == 2
    assert p2.ranking == 1

    state.update_team_scores()
    assert state.get_team_ranking() == [
        1,
        2,
    ]  # Team 1: 1500, Team 2: 1500; lower team_id wins tie


def test_player_and_team_rankings_laserball() -> None:
    state = LiveGameState(game_type='Laserball')
    state.add_team(1, 'Alpha', 'Red', '#ff0000')
    state.add_team(2, 'Beta', 'Blue', '#0000ff')
    p1 = state.add_player(1, '#P1', 'P1', 1)
    p2 = state.add_player(2, '#P2', 'P2', 2)

    p1.goals = 1
    p1.assists = 0
    p2.goals = 1
    p2.assists = 1

    player_ranks = state.update_player_rankings()
    assert player_ranks == {1: [1], 2: [2]}
    assert p1.ranking == 1
    assert p2.ranking == 1

    state.update_team_scores()
    # Both teams 1 goal; team 2 has higher player ranking scores
    assert state.get_team_ranking() == [2, 1]


def test_reset() -> None:
    state = LiveGameState(game_type='SM5')
    state.add_team(1, 'Fire', 'Red', '#ff0000')
    state.add_player(1, '#P1', 'Ace', 1)
    state.add_target(1, '#B1', 'Base', '#ff0000')
    state.record_change(1000, 'player', 1, 'score', '100')
    state.current_time_ms = 5000
    state.is_game_over = True
    state.ball_carrier_id = 1

    state.reset()

    assert state.current_time_ms == 0
    assert state.is_game_over is False
    assert state.ball_carrier_id is None
    assert len(state.teams) == 0
    assert len(state.players) == 0
    assert len(state.targets) == 0
    assert len(state.snapshots) == 0
