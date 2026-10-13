from lfdata.model import GameEntity, GameEvent, LFGame
from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_AMMO_BOOST,
    SM5_EVENT_BASE_AWARDED,
    SM5_EVENT_CLAIM_BEACON,
    SM5_EVENT_DAMAGED_OPPONENT,
    SM5_EVENT_DEACTIVATE_RAPID_FIRE,
    SM5_EVENT_DETONATE_NUKE,
    SM5_EVENT_DOWNED_OPPONENT,
    SM5_EVENT_DOWNED_TEAM,
    SM5_EVENT_LIFE_BOOST,
    SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
    SM5_EVENT_MISSILE_DAMAGE_TEAM,
    SM5_EVENT_MISSILE_DOWN_OPPONENT,
    SM5_EVENT_MISSION_END,
    SM5_EVENT_MISSION_START,
    SM5_EVENT_NUKE_CANCEL,
    SM5_EVENT_PENALTY,
    SM5_EVENT_SHOT_EMPTY,
    SM5_EVENT_WARBOT_ZAP,
)
from lfdata.replay.diagnostics import PlayerDiscrepancy
from lfdata.replay.unhandled_events import (
    HANDLED_EVENT_TYPES,
    LFUnhandledEventsAnalyzer,
    UnhandledEventInfo,
    format_timestamp_ms,
)


def test_handled_event_types_contents() -> None:
    assert SM5_EVENT_MISSION_START in HANDLED_EVENT_TYPES
    assert SM5_EVENT_MISSION_END in HANDLED_EVENT_TYPES
    assert SM5_EVENT_DAMAGED_OPPONENT in HANDLED_EVENT_TYPES
    assert SM5_EVENT_DOWNED_OPPONENT in HANDLED_EVENT_TYPES
    assert SM5_EVENT_DOWNED_TEAM in HANDLED_EVENT_TYPES
    assert SM5_EVENT_WARBOT_ZAP in HANDLED_EVENT_TYPES
    assert SM5_EVENT_MISSILE_DOWN_OPPONENT in HANDLED_EVENT_TYPES
    assert SM5_EVENT_DETONATE_NUKE in HANDLED_EVENT_TYPES
    assert SM5_EVENT_AMMO_BOOST in HANDLED_EVENT_TYPES
    assert SM5_EVENT_LIFE_BOOST in HANDLED_EVENT_TYPES
    assert SM5_EVENT_PENALTY in HANDLED_EVENT_TYPES
    assert SM5_EVENT_CLAIM_BEACON in HANDLED_EVENT_TYPES
    assert SM5_EVENT_BASE_AWARDED in HANDLED_EVENT_TYPES
    assert SM5_EVENT_NUKE_CANCEL in HANDLED_EVENT_TYPES

    # Unhandled / ignored event types
    assert SM5_EVENT_SHOT_EMPTY not in HANDLED_EVENT_TYPES
    assert SM5_EVENT_MISSILE_DAMAGE_OPPONENT not in HANDLED_EVENT_TYPES
    assert SM5_EVENT_MISSILE_DAMAGE_TEAM not in HANDLED_EVENT_TYPES
    assert SM5_EVENT_DEACTIVATE_RAPID_FIRE not in HANDLED_EVENT_TYPES
    assert '9999' not in HANDLED_EVENT_TYPES


def test_format_timestamp_ms() -> None:
    assert format_timestamp_ms(0) == '00:00.000'
    assert format_timestamp_ms(61500) == '01:01.500'
    assert format_timestamp_ms(-10) == '00:00.000'


def test_unhandled_event_info_dataclass() -> None:
    info = UnhandledEventInfo(
        time_ms=5000,
        event_type=SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
        action='missile damage opponent',
        actor_entity_id='p1',
        target_entity_id='p2',
        actor_name='Player1',
        target_name='Player2',
        pertains_to_mismatched_player=True,
        mismatched_player_ids=['p1'],
        discrepancy_summaries=['lives: diff -1'],
    )
    assert info.time_ms == 5000
    assert info.event_type == SM5_EVENT_MISSILE_DAMAGE_OPPONENT
    assert info.pertains_to_mismatched_player is True
    assert info.mismatched_player_ids == ['p1']
    assert info.discrepancy_summaries == ['lives: diff -1']


def test_analyzer_no_events() -> None:
    game = LFGame(game_id='g1', game_type='SM5')
    analyzer = LFUnhandledEventsAnalyzer(game=game)
    assert analyzer.find_unhandled_events() == []


def test_analyzer_all_handled_events() -> None:
    game = LFGame(game_id='g1', game_type='SM5')
    game.events = [
        GameEvent(
            game_id='g1',
            time=0,
            event_type=SM5_EVENT_MISSION_START,
            action='start',
            raw_message='',
        ),
        GameEvent(
            game_id='g1',
            time=1000,
            event_type=SM5_EVENT_DAMAGED_OPPONENT,
            action='zaps',
            raw_message='',
        ),
        GameEvent(
            game_id='g1',
            time=60000,
            event_type=SM5_EVENT_MISSION_END,
            action='end',
            raw_message='',
        ),
    ]
    analyzer = LFUnhandledEventsAnalyzer(game=game)
    assert analyzer.find_unhandled_events() == []


def test_analyzer_finds_unhandled_events_without_discrepancies() -> None:
    game = LFGame(game_id='g1', game_type='SM5')
    e1 = GameEntity(
        game_id='g1',
        entity_id='p1',
        type='player',
        desc='Alpha',
        team_index=0,
    )
    e2 = GameEntity(
        game_id='g1',
        entity_id='p2',
        type='player',
        desc='Bravo',
        team_index=1,
    )
    game.entities = [e1, e2]
    game.events = [
        GameEvent(
            game_id='g1',
            time=5000,
            event_type=SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
            action='missile damage opponent',
            actor_entity_id='p1',
            target_entity_id='p2',
            raw_message='',
        ),
        GameEvent(
            game_id='g1',
            time=10000,
            event_type=SM5_EVENT_DEACTIVATE_RAPID_FIRE,
            action='deactivate rapid fire',
            actor_entity_id='p1',
            raw_message='',
        ),
    ]

    analyzer = LFUnhandledEventsAnalyzer(game=game)
    unhandled = analyzer.find_unhandled_events()
    assert len(unhandled) == 2

    assert unhandled[0].time_ms == 5000
    assert unhandled[0].event_type == SM5_EVENT_MISSILE_DAMAGE_OPPONENT
    assert unhandled[0].actor_name == 'Alpha'
    assert unhandled[0].target_name == 'Bravo'
    assert unhandled[0].pertains_to_mismatched_player is False

    assert unhandled[1].time_ms == 10000
    assert unhandled[1].event_type == SM5_EVENT_DEACTIVATE_RAPID_FIRE
    assert unhandled[1].actor_name == 'Alpha'
    assert unhandled[1].target_name is None
    assert unhandled[1].pertains_to_mismatched_player is False


def test_analyzer_highlights_mismatched_players() -> None:
    game = LFGame(game_id='g1', game_type='SM5')
    e1 = GameEntity(
        game_id='g1',
        entity_id='p1',
        type='player',
        desc='Alpha',
        team_index=0,
    )
    e2 = GameEntity(
        game_id='g1',
        entity_id='p2',
        type='player',
        desc='Bravo',
        team_index=1,
    )
    e3 = GameEntity(
        game_id='g1',
        entity_id='p3',
        type='player',
        desc='Charlie',
        team_index=1,
    )
    game.entities = [e1, e2, e3]
    game.events = [
        # Involves p1 (mismatched) as actor
        GameEvent(
            game_id='g1',
            time=5000,
            event_type=SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
            action='missile damage opponent',
            actor_entity_id='p1',
            target_entity_id='p2',
            raw_message='',
        ),
        # Involves p2 (not mismatched) as actor, p3 as target
        GameEvent(
            game_id='g1',
            time=8000,
            event_type=SM5_EVENT_SHOT_EMPTY,
            action='empty zap',
            actor_entity_id='p2',
            target_entity_id='p3',
            raw_message='',
        ),
        # Involves p1 (mismatched) as target
        GameEvent(
            game_id='g1',
            time=12000,
            event_type=SM5_EVENT_MISSILE_DAMAGE_TEAM,
            action='missile damage team',
            actor_entity_id='p2',
            target_entity_id='p1',
            raw_message='',
        ),
    ]

    discrepancies = {
        'p1': [
            PlayerDiscrepancy(field='lives', computed=14, expected=15),
            PlayerDiscrepancy(field='shots', computed=25, expected=30),
        ]
    }

    analyzer = LFUnhandledEventsAnalyzer(game=game, discrepancies=discrepancies)
    unhandled = analyzer.find_unhandled_events()
    assert len(unhandled) == 3

    assert unhandled[0].pertains_to_mismatched_player is True
    assert unhandled[0].mismatched_player_ids == ['p1']
    assert len(unhandled[0].discrepancy_summaries) == 1
    assert 'Player Alpha (p1)' in unhandled[0].discrepancy_summaries[0]
    assert 'lives: computed=14' in unhandled[0].discrepancy_summaries[0]

    assert unhandled[1].pertains_to_mismatched_player is False
    assert unhandled[1].mismatched_player_ids == []

    assert unhandled[2].pertains_to_mismatched_player is True
    assert unhandled[2].mismatched_player_ids == ['p1']


def test_get_events_for_player() -> None:
    game = LFGame(game_id='g1', game_type='SM5')
    game.events = [
        GameEvent(
            game_id='g1',
            time=5000,
            event_type=SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
            action='missile damage opponent',
            actor_entity_id='p1',
            target_entity_id='p2',
            raw_message='',
        ),
        GameEvent(
            game_id='g1',
            time=8000,
            event_type=SM5_EVENT_SHOT_EMPTY,
            action='empty zap',
            actor_entity_id='p3',
            target_entity_id='p4',
            raw_message='',
        ),
        GameEvent(
            game_id='g1',
            time=12000,
            event_type=SM5_EVENT_MISSILE_DAMAGE_TEAM,
            action='missile damage team',
            actor_entity_id='p5',
            target_entity_id='p1',
            raw_message='',
        ),
    ]

    analyzer = LFUnhandledEventsAnalyzer(game=game)
    p1_events = analyzer.get_events_for_player(entity_id='p1')
    assert len(p1_events) == 2
    assert p1_events[0].time_ms == 5000
    assert p1_events[1].time_ms == 12000

    p3_events = analyzer.get_events_for_player(entity_id='p3')
    assert len(p3_events) == 1
    assert p3_events[0].time_ms == 8000

    p99_events = analyzer.get_events_for_player(entity_id='p99')
    assert len(p99_events) == 0


def test_dump_unhandled_events(capsys: object) -> None:
    game = LFGame(game_id='g1', game_type='SM5')
    analyzer = LFUnhandledEventsAnalyzer(game=game)

    # Empty does not print
    analyzer.dump_unhandled_events()
    captured = capsys.readouterr()
    assert captured.out == ''

    # With unhandled events
    game.entities = [
        GameEntity(
            game_id='g1',
            entity_id='p1',
            type='player',
            desc='Commander',
            team_index=0,
        )
    ]
    game.events = [
        GameEvent(
            game_id='g1',
            time=5000,
            event_type=SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
            action='missile damage opponent',
            actor_entity_id='p1',
            raw_message='',
        )
    ]
    discrepancies = {
        'p1': [PlayerDiscrepancy(field='lives', computed=10, expected=12)]
    }
    analyzer = LFUnhandledEventsAnalyzer(game=game, discrepancies=discrepancies)
    analyzer.dump_unhandled_events()
    captured = capsys.readouterr()

    assert 'UNHANDLED & IGNORED EVENT ANALYSIS' in captured.out
    assert (
        'Found 1 event(s) with types ignored/unhandled by lfdata:'
        in captured.out
    )
    assert 'Type 0305' in captured.out
    assert (
        '*** HIGHLIGHT: PERTAINS TO PLAYER WITH DISCREPANCY ***' in captured.out
    )
    assert 'Player Commander (p1)' in captured.out
