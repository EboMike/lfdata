from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, GameEntity, LFGame, Player, Sm5Stats


def test_create_entity() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        game = LFGame(
            game_id='test_game_123',
            timestamp=datetime.now(),
            game_type='SM5',
        )
        player = Player(codename='Sqnfdcp', real_name='John Doe')
        session.add_all([game, player])
        session.commit()

        entity = GameEntity(
            game_id='test_game_123',
            entity_id='#dJevxws',
            type='player',
            desc='Sqnfdcp',
            team_index=1,
            level=0,
            category=2,
            battlesuit='Maverick',
            end_score=1500,
            player_id=player.id,
        )
        session.add(entity)
        session.commit()

        retrieved = (
            session.query(GameEntity)
            .filter_by(game_id='test_game_123', entity_id='#dJevxws')
            .first()
        )
        assert retrieved is not None
        assert retrieved.type == 'player'
        assert retrieved.desc == 'Sqnfdcp'
        assert retrieved.team_index == 1
        assert retrieved.level == 0
        assert retrieved.category == 2
        assert retrieved.battlesuit == 'Maverick'
        assert retrieved.end_score == 1500
        assert retrieved.player is not None
        assert retrieved.player.codename == 'Sqnfdcp'
        assert retrieved.game.game_id == 'test_game_123'
        assert repr(retrieved) == (
            "GameEntity(id=1, entity_id='#dJevxws', type='player', desc='Sqnfdcp')"
        )


def test_entity_hit_diff() -> None:
    # Entity without game or stats
    standalone_entity = GameEntity(
        game_id='g1',
        entity_id='#1',
        type='player',
        desc='Alpha',
        team_index=0,
    )
    assert standalone_entity.hit_diff is None

    # Base entity (not player)
    base_entity = GameEntity(
        game_id='g1',
        entity_id='@base1',
        type='base',
        desc='Red Base',
        team_index=0,
    )
    assert base_entity.hit_diff is None

    # Player entity linked to a game with SM5 stats
    game = LFGame(
        game_id='g1',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    player_ent = GameEntity(
        game_id='g1',
        entity_id='#P1',
        type='player',
        desc='Bravo',
        team_index=1,
    )
    player_ent.game = game

    stat_p1 = Sm5Stats(
        game_id='g1',
        entity_id='#P1',
        shot_opponent=30,
        shot_team=2,
        times_zapped=15,
    )
    game.sm5_stats = [stat_p1]

    # 30 / 15 = 2.0 (shot_team is excluded)
    assert player_ent.hit_diff == 2.0

    # Never zapped
    stat_p1.times_zapped = 0
    assert player_ent.hit_diff is None

