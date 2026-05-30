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
    assert p.lives == 13

    # Shots resupply
    p.shots = 20
    p.resupply_shots_from_ammo()
    assert p.shots == 30

    # Eliminated player cannot resupply
    p.lives = 0
    p.resupply_lives_from_medic()
    assert p.lives == 0
