from lfdata.model import LFRole
from lfdata.replay.state import (
    LFReplayGameState,
    LFReplayPlayerState,
    LFReplayTeamState,
)


def test_player_state_initialization() -> None:
    commander = LFReplayPlayerState(
        entity_id='#1', role=LFRole.COMMANDER, team_index=0
    )
    assert commander.lives == 15
    assert commander.shots == 30
    assert commander.missiles == 5

    scout = LFReplayPlayerState(entity_id='#2', role=LFRole.SCOUT, team_index=1)
    assert scout.lives == 15
    assert scout.shots == 30
    assert scout.missiles == 0

    heavy = LFReplayPlayerState(entity_id='#3', role=LFRole.HEAVY, team_index=0)
    assert heavy.lives == 10
    assert heavy.shots == 20
    assert heavy.missiles == 5


def test_team_state_initialization() -> None:
    team = LFReplayTeamState(team_index=0, name='Fire Team')
    assert team.team_index == 0
    assert team.name == 'Fire Team'
    assert team.score == 0
    assert team.ranking == 1


def test_game_state_updates() -> None:
    p1 = LFReplayPlayerState(
        entity_id='#1', role=LFRole.COMMANDER, team_index=0
    )
    p2 = LFReplayPlayerState(entity_id='#2', role=LFRole.SCOUT, team_index=1)
    t1 = LFReplayTeamState(team_index=0, name='Fire Team')
    t2 = LFReplayTeamState(team_index=1, name='Earth Team')

    game_state = LFReplayGameState(players=[p1, p2], teams=[t1, t2])

    p1.score = 500
    p2.score = 1000
    game_state.update_team_scores_and_rankings()

    assert t1.score == 500
    assert t2.score == 1000
    assert t1.ranking == 2
    assert t2.ranking == 1


def test_player_downtime_and_elimination() -> None:
    p = LFReplayPlayerState(entity_id='#1', role=LFRole.COMMANDER, team_index=0)
    assert not p.is_eliminated()
    assert not p.is_down(1000)

    # Put player down
    p.hp = 0
    p.downtime_ends_at_ms = 8000
    p.resettable_starts_at_ms = 4000

    assert p.is_down(3000)  # In safe phase
    assert p.is_down(5000)  # In resettable phase
    assert not p.is_down(8000)  # Downtime expired

    p.update_downtime(8500)
    assert p.hp == p.max_hp

    # Eliminate player
    p.lives = 0
    assert p.is_eliminated()
    p.update_downtime(9000)
    assert p.hp == 0

    # Zap but not down (Commander hitpoints go from 3 to 2)
    p2 = LFReplayPlayerState(
        entity_id='#2', role=LFRole.COMMANDER, team_index=0
    )
    p2.hp = 2
    # Calling update_downtime should NOT restore it because player is not down
    p2.update_downtime(2000)
    assert p2.hp == 2


def test_player_resupply_checks() -> None:
    p = LFReplayPlayerState(entity_id='#1', role=LFRole.SCOUT, team_index=0)

    # Lives resupply
    p.lives = 10
    p.resupply_lives_from_medic()
    assert p.lives == 15

    # Shots resupply
    p.shots = 20
    p.resupply_shots_from_ammo()
    assert p.shots == 30

    # Eliminated player cannot resupply
    p.lives = 0
    p.resupply_lives_from_medic()
    assert p.lives == 0


def test_player_special_points_clamping() -> None:
    p = LFReplayPlayerState(entity_id='#1', role=LFRole.SCOUT, team_index=0)
    assert p.special_points == 0

    p.special_points = 50
    assert p.special_points == 50

    p.special_points = 100
    assert p.special_points == 99

    p.special_points = -10
    assert p.special_points == 0


def test_player_authoritative_state_history() -> None:
    from lfdata.model import PlayerStateHistory

    history = [
        PlayerStateHistory(game_id='g1', time=0, entity_id='#1', state=0),
        PlayerStateHistory(game_id='g1', time=1000, entity_id='#1', state=3),
        PlayerStateHistory(game_id='g1', time=5000, entity_id='#1', state=2),
        PlayerStateHistory(game_id='g1', time=9000, entity_id='#1', state=0),
    ]

    p = LFReplayPlayerState(
        entity_id='#1',
        role=LFRole.COMMANDER,
        team_index=0,
        state_history=history,
    )

    assert p.has_authoritative_state

    # t=500 -> state 0 (up)
    assert p.get_state_at(500) == 0
    assert not p.is_down(500)
    assert not p.is_resettable(500)
    assert p.can_receive_resupply(500)
    p.update_downtime(500)
    assert p.hp == p.max_hp

    # t=1500 -> state 3 (down non-resettable), went down at t=1000 (elapsed 500ms <= 750ms)
    assert p.get_state_at(1500) == 3
    assert p.is_down(1500)
    assert not p.is_resettable(1500)
    assert p.can_receive_resupply(1500)
    p.update_downtime(1500)
    assert p.hp == 0

    # t=3000 -> state 3, went down at t=1000 (elapsed 2000ms > 750ms)
    assert p.get_state_at(3000) == 3
    assert p.is_down(3000)
    assert not p.is_resettable(3000)
    assert not p.can_receive_resupply(3000)

    # t=6000 -> state 2 (resettable)
    assert p.get_state_at(6000) == 2
    assert p.is_down(6000)
    assert p.is_resettable(6000)

    # t=10000 -> state 0 (up again)
    assert p.get_state_at(10000) == 0
    assert not p.is_down(10000)
    p.update_downtime(10000)
    assert p.hp == p.max_hp


def test_configurable_boost_grace_period() -> None:
    from lfdata.model import PlayerStateHistory

    history = [
        PlayerStateHistory(game_id='g1', time=0, entity_id='#1', state=0),
        PlayerStateHistory(game_id='g1', time=1000, entity_id='#1', state=3),
    ]

    p = LFReplayPlayerState(
        entity_id='#1',
        role=LFRole.COMMANDER,
        team_index=0,
        state_history=history,
    )

    # At t=1650 (elapsed = 650ms):
    # Default (700ms grace period): 650ms <= 700ms -> True
    assert p.can_receive_resupply(1650)
    assert p.can_receive_resupply(1650, grace_period_ms=700)

    # Custom 500ms grace period: 650ms > 500ms -> False
    assert not p.can_receive_resupply(1650, grace_period_ms=500)

    # Custom 1000ms grace period: at t=1900 (elapsed = 900ms): 900ms <= 1000ms -> True
    assert p.can_receive_resupply(1900, grace_period_ms=1000)
    assert not p.can_receive_resupply(1900, grace_period_ms=700)
