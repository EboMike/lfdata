from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, CompetitionTeam, Player


def test_competition_team_initialization() -> None:
    player1 = Player(codename='Striker', real_name='Alice')
    player2 = Player(codename='Sniper', real_name='Bob')

    team = CompetitionTeam(
        slug='tigers',
        name='Thunder Tigers',
        short_name='TIG',
        logo_url='https://example.com/tigers.png',
        players=[player1, player2],
    )

    assert team.slug == 'tigers'
    assert team.name == 'Thunder Tigers'
    assert team.short_name == 'TIG'
    assert team.logo_url == 'https://example.com/tigers.png'
    assert team.logo == 'https://example.com/tigers.png'
    assert len(team.players) == 2
    assert team.player_codenames == ['Striker', 'Sniper']
    assert repr(team) == (
        "CompetitionTeam(slug='tigers', name='Thunder Tigers', "
        "short_name='TIG')"
    )


def test_competition_team_logo_setter() -> None:
    team = CompetitionTeam(
        slug='panthers',
        name='Panthers',
        short_name='PAN',
    )
    assert team.logo is None
    assert team.logo_url is None

    team.logo = 'https://example.com/panthers.png'
    assert team.logo == 'https://example.com/panthers.png'
    assert team.logo_url == 'https://example.com/panthers.png'


def test_competition_team_string_players() -> None:
    team = CompetitionTeam(
        slug='wolves',
        name='Dire Wolves',
        short_name='WLV',
        logo='https://example.com/wolves.png',
        players=['Shadow', 'Ghost'],
    )
    assert len(team.players) == 2
    assert team.player_codenames == ['Shadow', 'Ghost']
    assert team.players[0].codename == 'Shadow'
    assert team.players[1].codename == 'Ghost'


def test_competition_team_database_persistence() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        player1 = Player(codename='Viper', real_name='Victor')
        player2 = Player(codename='Cobra', real_name='Chris')
        session.add_all([player1, player2])
        session.commit()

        team = CompetitionTeam(
            slug='snakes',
            name='Solid Snakes',
            short_name='SNK',
            logo_url='https://example.com/snk.png',
            players=[player1, player2],
        )
        session.add(team)
        session.commit()

        retrieved = (
            session.query(CompetitionTeam).filter_by(slug='snakes').first()
        )
        assert retrieved is not None
        assert retrieved.name == 'Solid Snakes'
        assert retrieved.short_name == 'SNK'
        assert retrieved.logo == 'https://example.com/snk.png'
        assert len(retrieved.players) == 2
        assert retrieved.player_codenames == ['Viper', 'Cobra']
