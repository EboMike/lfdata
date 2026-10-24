from lfdata.model import (
    LFRole,
    PlayerAmmoHistory,
    PlayerLivesHistory,
    PlayerMissilesHistory,
)
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
    assert p.downtime_ends_at_ms == 0
    assert p.resettable_starts_at_ms == 0

    # t=1500 -> state 3 (down non-resettable), went down at t=1000 (elapsed 500ms <= 750ms)
    assert p.get_state_at(1500) == 3
    assert p.is_down(1500)
    assert not p.is_resettable(1500)
    assert p.can_receive_resupply(1500)
    p.update_downtime(1500)
    assert p.hp == 0
    assert p.resettable_starts_at_ms == 5000
    assert p.downtime_ends_at_ms == 9000

    # t=3000 -> state 3, went down at t=1000 (elapsed 2000ms > 750ms)
    assert p.get_state_at(3000) == 3
    assert p.is_down(3000)
    assert not p.is_resettable(3000)
    assert not p.can_receive_resupply(3000)

    # t=6000 -> state 2 (resettable)
    assert p.get_state_at(6000) == 2
    assert p.is_down(6000)
    assert p.is_resettable(6000)
    p.update_downtime(6000)
    assert p.resettable_starts_at_ms == 5000
    assert p.downtime_ends_at_ms == 9000

    # t=10000 -> state 0 (up again)
    assert p.get_state_at(10000) == 0
    assert not p.is_down(10000)
    p.update_downtime(10000)
    assert p.hp == p.max_hp
    assert p.downtime_ends_at_ms == 0
    assert p.resettable_starts_at_ms == 0


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

    # Custom 1000ms grace period: at t=1900 (elapsed = 900ms):
    # 900ms <= 1000ms -> True
    assert p.can_receive_resupply(1900, grace_period_ms=1000)
    assert not p.can_receive_resupply(1900, grace_period_ms=700)


def test_replay_player_state_hit_diff() -> None:
    p = LFReplayPlayerState(entity_id='#1', role=LFRole.SCOUT, team_index=0)
    assert p.times_zapped == 0
    assert p.times_zapped_opponents == 0
    assert p.hit_diff == 1.0

    p.times_zapped_opponents = 15
    p.times_zapped = 5
    assert p.hit_diff == 3.0


def test_player_authoritative_lives() -> None:

    history = [
        PlayerLivesHistory(game_id='g1', time=5000, entity_id='#1', lives=14),
        PlayerLivesHistory(game_id='g1', time=15000, entity_id='#1', lives=10),
    ]

    p = LFReplayPlayerState(
        entity_id='#1',
        role=LFRole.SCOUT,
        team_index=0,
        lives_history=history,
    )
    assert p.has_authoritative_lives is True
    assert p.lives == 15  # Starting lives before first record

    assert p.get_lives_at(0) == 15
    assert p.get_lives_at(4999) == 15
    assert p.get_lives_at(5000) == 14
    assert p.get_lives_at(10000) == 14
    assert p.get_lives_at(15000) == 10
    assert p.get_lives_at(20000) == 10

    p.update_lives(5000)
    assert p.lives == 14

    p.update_lives(15000)
    assert p.lives == 10

    # Resupply from medic should not compute or alter authoritative lives
    p.resupply_lives_from_medic()
    assert p.lives == 10

    # Player with has_authoritative_lives flag but no records for this player
    p2 = LFReplayPlayerState(
        entity_id='#2',
        role=LFRole.MEDIC,
        team_index=0,
        has_authoritative_lives=True,
    )
    assert p2.has_authoritative_lives is True
    assert p2.lives == 20
    assert p2.get_lives_at(10000) == 20
    p2.update_lives(10000)
    assert p2.lives == 20
    p2.resupply_lives_from_medic()
    assert p2.lives == 20


def test_player_authoritative_ammo() -> None:
    history = [
        PlayerAmmoHistory(game_id='g1', time=5000, entity_id='#1', shots=25),
        PlayerAmmoHistory(game_id='g1', time=15000, entity_id='#1', shots=15),
    ]

    p = LFReplayPlayerState(
        entity_id='#1',
        role=LFRole.SCOUT,
        team_index=0,
        ammo_history=history,
    )
    assert p.has_authoritative_ammo is True
    assert p.has_authoritative_shots is True
    assert p.shots == 30  # Starting shots before first record

    assert p.get_shots_at(0) == 30
    assert p.get_shots_at(4999) == 30
    assert p.get_shots_at(5000) == 25
    assert p.get_shots_at(10000) == 25
    assert p.get_shots_at(15000) == 15
    assert p.get_shots_at(20000) == 15

    assert p.get_ammo_at(5000) == 25
    assert p.get_ammo_at(15000) == 15

    p.update_shots(5000)
    assert p.shots == 25

    p.update_ammo(15000)
    assert p.shots == 15

    # Resupply from ammo carrier should not compute or alter authoritative shots
    p.resupply_shots_from_ammo()
    assert p.shots == 15

    # Player with has_authoritative_ammo flag but no records for this player
    p2 = LFReplayPlayerState(
        entity_id='#2',
        role=LFRole.COMMANDER,
        team_index=0,
        has_authoritative_ammo=True,
    )
    assert p2.has_authoritative_ammo is True
    assert p2.has_authoritative_shots is True
    assert p2.shots == 30
    assert p2.get_shots_at(10000) == 30
    p2.update_shots(10000)
    assert p2.shots == 30
    p2.resupply_shots_from_ammo()
    assert p2.shots == 30


def test_player_authoritative_missiles() -> None:
    history = [
        PlayerMissilesHistory(
            game_id='g1', time=5000, entity_id='#1', missiles=4
        ),
        PlayerMissilesHistory(
            game_id='g1', time=15000, entity_id='#1', missiles=2
        ),
    ]

    p = LFReplayPlayerState(
        entity_id='#1',
        role=LFRole.COMMANDER,
        team_index=0,
        missiles_history=history,
    )
    assert p.has_authoritative_missiles is True
    assert p.missiles == 5  # Starting missiles before first record

    assert p.get_missiles_at(0) == 5
    assert p.get_missiles_at(4999) == 5
    assert p.get_missiles_at(5000) == 4
    assert p.get_missiles_at(10000) == 4
    assert p.get_missiles_at(15000) == 2
    assert p.get_missiles_at(20000) == 2

    p.update_missiles(5000)
    assert p.missiles == 4

    p.update_missiles(15000)
    assert p.missiles == 2

    # Player with has_authoritative_missiles flag but no records for this player
    p2 = LFReplayPlayerState(
        entity_id='#2',
        role=LFRole.COMMANDER,
        team_index=0,
        has_authoritative_missiles=True,
    )
    assert p2.has_authoritative_missiles is True
    assert p2.missiles == 5
    assert p2.get_missiles_at(10000) == 5
    p2.update_missiles(10000)
    assert p2.missiles == 5
