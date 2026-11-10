from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import (
    Base,
    Competition,
    CompetitionTeam,
    Player,
    ScheduledGame,
)


def test_competition_initialization() -> None:
    start = datetime(2026, 7, 10, 9, 0)
    end = datetime(2026, 7, 17, 18, 0)

    comp = Competition(
        name='Laserforce World Championships 2026',
        slug='world-champs-2026',
        site='Brisbane Arena',
        start_time=start,
        end_time=end,
    )

    assert comp.name == 'Laserforce World Championships 2026'
    assert comp.slug == 'world-champs-2026'
    assert comp.site == 'Brisbane Arena'
    assert comp.start_time == start
    assert comp.end_time == end
    assert len(comp.teams) == 0
    assert len(comp.schedule) == 0
    assert (
        repr(comp)
        == "Competition(id=None, name='Laserforce World Championships 2026', "
        "site='Brisbane Arena')"
    )


def test_competition_team_management() -> None:
    comp = Competition(name='Summer Invitational', site='Sydney')
    team1 = CompetitionTeam(slug='tigers', name='Tigers', short_name='TIG')
    team2 = CompetitionTeam(slug='lions', name='Lions', short_name='LIO')

    comp.add_team(team1)
    comp.add_team(team2)

    assert len(comp.teams) == 2
    assert comp.get_team(slug='tigers') == team1
    assert comp.get_team(slug='lions') == team2
    assert comp.get_team(slug='bears') is None
    assert team1.competition == comp


def test_competition_schedule_management() -> None:
    comp = Competition(name='National League', site='Melbourne')
    start = datetime(2026, 8, 1, 10, 0)
    end = datetime(2026, 8, 1, 10, 20)

    game1 = ScheduledGame(
        game_name='R1 M1 G1',
        start_time=start,
        end_time=end,
        team_names=['Team A', 'Team B'],
    )
    game2 = ScheduledGame(
        game_name='R1 M1 G2',
        start_time=start,
        end_time=end,
        team_names=['Team C', 'Team D'],
    )

    comp.add_scheduled_game(game1)
    comp.add_scheduled_game(game2)

    assert len(comp.schedule) == 2
    assert comp.get_scheduled_game(game_name='R1 M1 G1') == game1
    assert comp.get_scheduled_game(game_name='R1 M1 G2') == game2
    assert comp.get_scheduled_game(game_name='R1 M1 G3') is None
    assert game1.competition == comp


def test_competition_database_persistence() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    comp_start = datetime(2026, 9, 1, 8, 0)
    comp_end = datetime(2026, 9, 5, 20, 0)
    game_start = datetime(2026, 9, 1, 9, 0)
    game_end = datetime(2026, 9, 1, 9, 20)

    with Session(engine) as session:
        player = Player(codename='Ace', real_name='Ashley')
        session.add(player)
        session.commit()

        team = CompetitionTeam(
            slug='falcons',
            name='Flying Falcons',
            short_name='FLC',
            logo_url='https://example.com/falcons.png',
            players=[player],
        )

        game = ScheduledGame(
            game_name='R1 M1 G1',
            round_number=1,
            match_number=1,
            game_number=1,
            start_time=game_start,
            end_time=game_end,
            team_names=['Flying Falcons', 'Eagles'],
            team_logos=[
                'https://example.com/falcons.png',
                'https://example.com/eagles.png',
            ],
            team_scores=[16000, 14000],
        )

        comp = Competition(
            name='Autumn Cup',
            slug='autumn-cup-2026',
            site='Adelaide',
            start_time=comp_start,
            end_time=comp_end,
            teams=[team],
            schedule=[game],
        )

        session.add(comp)
        session.commit()

        retrieved = (
            session.query(Competition)
            .filter_by(slug='autumn-cup-2026')
            .first()
        )
        assert retrieved is not None
        assert retrieved.name == 'Autumn Cup'
        assert retrieved.site == 'Adelaide'
        assert len(retrieved.teams) == 1
        assert retrieved.teams[0].slug == 'falcons'
        assert retrieved.teams[0].player_codenames == ['Ace']
        assert len(retrieved.schedule) == 1
        assert retrieved.schedule[0].game_name == 'R1 M1 G1'
        assert retrieved.schedule[0].score_differential == 2000

        # Test cascade delete
        session.delete(retrieved)
        session.commit()

        assert session.query(Competition).count() == 0
        assert session.query(CompetitionTeam).count() == 0
        assert session.query(ScheduledGame).count() == 0
        # Player should still exist (not deleted by cascade)
        assert session.query(Player).count() == 1
