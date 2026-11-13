from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from lfdata.model import (
    Base,
    Competition,
    CompetitionDataset,
    ScheduledGame,
)


def test_competition_dataset_init_default() -> None:
    dataset = CompetitionDataset()
    assert dataset.fixtures_dir == Path('tests/fixtures/test_competitions')
    comps = dataset.get_competitions()
    assert len(comps) == 2


def test_competition_dataset_init_custom_str_path() -> None:
    dataset = CompetitionDataset('tests/fixtures/test_competitions')
    assert dataset.fixtures_dir == Path('tests/fixtures/test_competitions')
    assert len(dataset.get_competitions()) == 2


def test_competition_dataset_missing_fixtures_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match='Competitions fixture file'):
        CompetitionDataset(tmp_path)


def test_competition_dataset_missing_schedule_fixture_raises(
    tmp_path: Path,
) -> None:
    comp_file = tmp_path / 'competitions.json'
    comp_file.write_text(
        '{"data": [{"slug": "missing_slug", "name": "Missing Comp"}]}',
        encoding='utf-8',
    )
    with pytest.raises(FileNotFoundError, match='Schedule fixture not found'):
        CompetitionDataset(tmp_path)


def test_competition_dataset_internationals_2026() -> None:
    dataset = CompetitionDataset()
    comp = dataset.get_internationals_2026()

    assert comp.name == 'Internationals 2026'
    assert comp.slug == 'internationals_2026'
    assert len(comp.schedule) == 5

    g1 = comp.schedule[0]
    assert g1.game_name == 'R1 M1 G1'
    assert g1.team_names == ['Hidden Valley Sanch', 'Utah Heatseekers']
    assert g1.team_scores == [44452, 28130]
    assert g1.score_differential == 16322
    assert g1.actual_start_time is not None
    assert g1.is_complete is True

    g2 = comp.schedule[1]
    assert g2.game_name == 'R1 M2 G1'
    assert g2.team_names == ['No Lives From Jackal', 'Sweets And Savory']
    assert g2.team_scores == [33192, 36072]
    assert g2.score_differential == 2880
    assert g2.actual_start_time is not None
    assert g2.is_complete is True

    g3 = comp.schedule[2]
    assert g3.game_name == 'R1 M3 G1'
    assert g3.team_names == ['HYBRIS', 'Armagedd You']
    assert g3.team_scores == [37052, 17970]
    assert g3.score_differential == 19082
    assert g3.actual_start_time is not None
    assert g3.is_complete is True

    g4 = comp.schedule[3]
    assert g4.game_name == 'R1 M4 G1'
    assert g4.team_names == ['The Expendables', 'Team Olympus']
    assert g4.team_scores is None
    assert g4.score_differential is None
    assert g4.actual_start_time is None
    assert g4.is_complete is False

    g5 = comp.schedule[4]
    assert g5.game_name == 'R1 M1 G2'
    assert g5.team_names == ['Hidden Valley Sanch', 'Utah Heatseekers']
    assert g5.team_scores is None
    assert g5.score_differential is None
    assert g5.actual_start_time is None
    assert g5.is_complete is False


def test_competition_dataset_syracuse_trios_2026() -> None:
    dataset = CompetitionDataset()
    comp = dataset.get_syracuse_trios_2026()

    assert comp.name == 'Syracuse Trios 2026'
    assert comp.slug == 'syracuse_trios_2026'
    assert len(comp.schedule) == 5

    expected_names = [
        'R1 M1 G1',
        'R1 M2 G1',
        'R1 M1 G2',
        'R1 M2 G2',
        'R1 M3 G1',
    ]
    expected_scores = [
        [41172, 11229],
        [47032, 28712],
        [38092, 13189],
        [44732, 26051],
        [37192, 21910],
    ]
    expected_diffs = [29943, 18320, 24903, 18681, 15282]

    for i, game in enumerate(comp.schedule):
        assert game.game_name == expected_names[i]
        assert game.team_scores == expected_scores[i]
        assert game.score_differential == expected_diffs[i]
        assert game.actual_start_time is not None
        assert game.is_complete is True


def test_competition_dataset_lookups_and_aliases() -> None:
    dataset = CompetitionDataset()

    tournaments = dataset.get_tournaments()
    assert len(tournaments) == 2

    comp1 = dataset.get_competition('internationals_2026')
    assert comp1 is not None
    assert comp1.slug == 'internationals_2026'

    tourney2 = dataset.get_tournament('syracuse_trios_2026')
    assert tourney2 is not None
    assert tourney2.slug == 'syracuse_trios_2026'

    assert dataset.get_competition('non_existent') is None
    assert dataset.get_tournament('non_existent') is None


def test_competition_dataset_populate_database() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    dataset = CompetitionDataset()

    with Session(engine) as session:
        persisted = dataset.populate_database(session=session)
        assert len(persisted) == 2

        comps = session.scalars(select(Competition)).all()
        assert len(comps) == 2

        games = session.scalars(select(ScheduledGame)).all()
        assert len(games) == 10

