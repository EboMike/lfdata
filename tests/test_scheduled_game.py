from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import (
    Base,
    ScheduledGame,
    StageType,
    format_game_name,
    parse_game_name,
)


def test_format_game_name() -> None:
    assert (
        format_game_name(
            round_number=1,
            match_number=3,
            game_number=2,
            stage_indicator='G',
        )
        == 'R1 M3 G2'
    )
    assert (
        format_game_name(
            round_number=2,
            match_number=3,
            game_number=1,
            stage_indicator='H',
        )
        == 'R2 M3 H1'
    )
    assert (
        format_game_name(
            round_number=2,
            match_number=3,
            game_number=1,
            stage_indicator='OT',
        )
        == 'R2 M3 OT1'
    )
    assert format_game_name(round_number=1, game_number=4) == 'R1 G4'
    assert format_game_name(match_number=5, game_number=1) == 'M5 G1'
    assert format_game_name(game_number=3) == 'G3'
    assert format_game_name() == ''


def test_parse_game_name() -> None:
    assert parse_game_name('R1 M3 G2') == (1, 3, 2, 'G')
    assert parse_game_name('R2 M3 H1') == (2, 3, 1, 'H')
    assert parse_game_name('R2 M3 OT1') == (2, 3, 1, 'OT')
    assert parse_game_name('R1 G4') == (1, None, 4, 'G')
    assert parse_game_name('M5 G1') == (None, 5, 1, 'G')
    assert parse_game_name('G3') == (None, None, 3, 'G')
    assert parse_game_name('Grand Final') == (None, None, None, 'G')


def test_scheduled_game_initialization() -> None:
    start = datetime(2026, 7, 10, 14, 0)
    end = datetime(2026, 7, 10, 14, 20)

    game = ScheduledGame(
        game_name='R1 M3 G2',
        start_time=start,
        end_time=end,
        team_names=['Tigers', 'Lions'],
        team_logos=[
            'https://example.com/tigers.png',
            'https://example.com/lions.png',
        ],
        round_number=1,
        match_number=3,
        game_number=2,
    )

    assert game.game_name == 'R1 M3 G2'
    assert game.start_time == start
    assert game.end_time == end
    assert game.scheduled_start == start
    assert game.scheduled_end == end
    assert game.team_names == ['Tigers', 'Lions']
    assert game.names == ['Tigers', 'Lions']
    assert game.team_logos == [
        'https://example.com/tigers.png',
        'https://example.com/lions.png',
    ]
    assert game.logos == [
        'https://example.com/tigers.png',
        'https://example.com/lions.png',
    ]
    assert game.round_number == 1
    assert game.match_number == 3
    assert game.game_number == 2
    assert game.stage_indicator == 'G'
    assert game.is_complete is False
    assert game.score_differential is None
    assert repr(game) == (
        "ScheduledGame(id=None, game_name='R1 M3 G2', "
        "teams=['Tigers', 'Lions'])"
    )


def test_scheduled_game_auto_name_and_stage_enum() -> None:
    start = datetime(2026, 7, 10, 15, 0)
    end = datetime(2026, 7, 10, 15, 20)

    game = ScheduledGame(
        scheduled_start=start,
        scheduled_end=end,
        round_number=2,
        match_number=4,
        game_number=1,
        stage_indicator=StageType.HALF,
        names=['Firebirds', 'Icebergs'],
        logos=['https://example.com/f.png', 'https://example.com/i.png'],
    )

    assert game.game_name == 'R2 M4 H1'
    assert game.stage_indicator == 'H'
    assert game.team_names == ['Firebirds', 'Icebergs']


def test_scheduled_game_scores_and_differential() -> None:
    start = datetime(2026, 7, 10, 16, 0)
    end = datetime(2026, 7, 10, 16, 20)

    game = ScheduledGame(
        start_time=start,
        end_time=end,
        game_name='R1 M1 G1',
        team_names=['Team A', 'Team B'],
        team_scores=[15200, 12800],
    )

    assert game.is_complete is True
    assert game.scores == [15200, 12800]
    assert game.score_differential == 2400

    # Test differential when scores are equal
    game.scores = [10000, 10000]
    assert game.score_differential == 0

    # Test explicit override
    game.score_differential = 500
    assert game.score_differential == 500


def test_scheduled_game_property_setters() -> None:
    start = datetime(2026, 7, 10, 10, 0)
    end = datetime(2026, 7, 10, 10, 30)

    game = ScheduledGame(start_time=start, end_time=end, game_name='Match 1')

    new_start = datetime(2026, 7, 10, 11, 0)
    new_end = datetime(2026, 7, 10, 11, 30)
    game.scheduled_start = new_start
    game.scheduled_end = new_end
    game.names = ['Side A', 'Side B']
    game.logos = ['https://example.com/a.png', 'https://example.com/b.png']

    assert game.start_time == new_start
    assert game.end_time == new_end
    assert game.team_names == ['Side A', 'Side B']
    assert game.team_logos == [
        'https://example.com/a.png',
        'https://example.com/b.png',
    ]


def test_scheduled_game_missing_times_raises() -> None:
    with pytest.raises(
        ValueError, match='start_time and end_time must be provided.'
    ):
        ScheduledGame(game_name='Incomplete')


def test_scheduled_game_database_persistence() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    start = datetime(2026, 7, 10, 17, 0)
    end = datetime(2026, 7, 10, 17, 20)

    with Session(engine) as session:
        game = ScheduledGame(
            game_name='R3 M1 G1',
            round_number=3,
            match_number=1,
            game_number=1,
            start_time=start,
            end_time=end,
            team_names=['Cobras', 'Pythons'],
            team_logos=[
                'https://example.com/c.png',
                'https://example.com/p.png',
            ],
            team_scores=[21000, 18500],
        )
        session.add(game)
        session.commit()

        retrieved = (
            session.query(ScheduledGame)
            .filter_by(game_name='R3 M1 G1')
            .first()
        )
        assert retrieved is not None
        assert retrieved.round_number == 3
        assert retrieved.match_number == 1
        assert retrieved.game_number == 1
        assert retrieved.team_names == ['Cobras', 'Pythons']
        assert retrieved.team_scores == [21000, 18500]
        assert retrieved.score_differential == 2500
        assert retrieved.is_complete is True


def test_scheduled_game_actual_time() -> None:
    start = datetime(2026, 7, 10, 10, 0)
    end = datetime(2026, 7, 10, 10, 20)
    actual = datetime(2026, 7, 10, 10, 5)

    game = ScheduledGame(
        start_time=start,
        end_time=end,
        actual_start_time=actual,
        game_name='R1 M1 G1',
    )
    assert game.actual_start_time == actual
    assert game.actual_time == actual

    new_actual = datetime(2026, 7, 10, 10, 7)
    game.actual_time = new_actual
    assert game.actual_start_time == new_actual
    assert game.actual_time == new_actual
