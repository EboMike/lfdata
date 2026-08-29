from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lfdata.model import Base, LFGame, Sm5Stats


def test_create_sm5_stats() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        game = LFGame(
            game_id='test_game_123',
            timestamp=datetime.now(),
            game_type='SM5',
        )
        session.add(game)
        session.commit()

        stats = Sm5Stats(
            game_id='test_game_123',
            entity_id='#fwqiZ',
            shots_hit=58,
            shots_fired=62,
            times_zapped=11,
            times_missiled=0,
            missile_hits=0,
            nukes_detonated=0,
            nukes_activated=0,
            nuke_cancels=0,
            medic_hits=0,
            own_medic_hits=0,
            medic_nukes=0,
            scout_rapid=0,
            life_boost=1,
            ammo_boost=0,
            lives_left=0,
            shots_left=30,
            penalties=0,
            shot3_hit=0,
            own_nuke_cancels=0,
            shot_opponent=4,
            shot_team=0,
            missiled_opponent=0,
            missiled_team=0,
        )
        session.add(stats)
        session.commit()

        retrieved = (
            session.query(Sm5Stats)
            .filter_by(game_id='test_game_123', entity_id='#fwqiZ')
            .first()
        )
        assert retrieved is not None
        assert retrieved.shots_hit == 58
        assert retrieved.shots_fired == 62
        assert retrieved.times_zapped == 11
        assert retrieved.life_boost == 1
        assert retrieved.shots_left == 30
        assert retrieved.shot_opponent == 4
        assert retrieved.hit_diff == 4 / 11
        assert retrieved.game.game_id == 'test_game_123'
        assert repr(retrieved) == (
            "Sm5Stats(id=1, game_id='test_game_123', entity_id='#fwqiZ')"
        )


def test_sm5_stats_hit_diff() -> None:
    stats_never_zapped = Sm5Stats(
        game_id='game_1',
        entity_id='#P1',
        shot_opponent=25,
        shot_team=5,
        times_zapped=0,
        times_missiled=4,
        missile_hits=6,
        nukes_detonated=1,
    )
    assert stats_never_zapped.hit_diff == 1.0

    # shot_opponent=40, shot_team=5 (friendly fire excluded),
    # shots_hit=55 (bases excluded), times_zapped=20 -> 40 / 20 = 2.0
    stats_zapped = Sm5Stats(
        game_id='game_1',
        entity_id='#P2',
        shots_hit=55,
        shot_opponent=40,
        shot_team=5,
        times_zapped=20,
        times_missiled=10,
        missile_hits=5,
        nukes_detonated=3,
    )
    assert stats_zapped.hit_diff == 2.0


