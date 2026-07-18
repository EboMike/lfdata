"""Tests for the game chapter generator."""

from datetime import datetime
from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent
from lfdata.video.chapter import LFChapter, LFChapterGenerator


def test_chapter_dataclass() -> None:
    chapter = LFChapter(time_ms=5000, message='Test Event', importance=3)
    assert chapter.time_ms == 5000
    assert chapter.message == 'Test Event'
    assert chapter.importance == 3


def _create_test_game() -> LFGame:
    game = LFGame(
        game_id='test_chapter_game',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    t1 = GameTeam(
        game_id='test_chapter_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_chapter_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    # Med1 on Team 0 (Medic starts with 20 lives)
    med1 = GameEntity(
        game_id='test_chapter_game',
        entity_id='M1',
        type='player',
        desc='Med1',
        team_index=0,
        level=1,
        category=5,  # Medic
        battlesuit='Medic1',
    )
    # Cmd1 on Team 0 (Commander starts with 15 lives)
    cmd1 = GameEntity(
        game_id='test_chapter_game',
        entity_id='C1',
        type='player',
        desc='Cmd1',
        team_index=0,
        level=1,
        category=1,  # Commander
        battlesuit='Cmdr1',
    )
    # Sct2 on Team 1 (Scout starts with 15 lives)
    sct2 = GameEntity(
        game_id='test_chapter_game',
        entity_id='S2',
        type='player',
        desc='Sct2',
        team_index=1,
        level=1,
        category=3,  # Scout
        battlesuit='Scout2',
    )
    game.entities = [med1, cmd1, sct2]
    return game


def test_collect_candidates_medic_down_to_10_lives() -> None:
    game = _create_test_game()

    # We need to get Medic Med1 down to 10 lives.
    # Medic starts with 20 lives.
    # Scout2 zaps Medic 10 times to take 10 lives.
    events = [
        GameEvent(
            game_id='test_chapter_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    # Medic HP is 1, so each DOWNED_OPPONENT (0206) or DAMAGED_OPPONENT (0205)
    # takes lives.
    # Note that zapped player goes down for 8 seconds (8000ms).
    # So we zap every 9000ms.
    for i in range(10):
        t = 1000 + i * 9000
        events.append(
            GameEvent(
                game_id='test_chapter_game',
                time=t,
                event_type='0206',
                actor_entity_id='S2',
                target_entity_id='M1',
                action='zaps',
                raw_message='',
            )
        )

    game.events = events

    generator = LFChapterGenerator(game)
    candidates = generator._collect_candidates()

    # Find the chapter about Medic down to 10 lives
    medic_chapters = [
        c
        for c in candidates
        if 'Medic Med1' in c.message and '10 lives left' in c.message
    ]
    assert len(medic_chapters) == 1
    assert medic_chapters[0].importance == 1
    # 10th zap is at t = 1000 + 9 * 9000 = 82000
    assert medic_chapters[0].time_ms == 82000


def test_collect_candidates_eliminations() -> None:
    game = _create_test_game()

    # We want to eliminate Scout2 (15 lives), Cmd1 (15 lives), and Med1 (20 lives).
    # To do this quickly, we can have detonate nuke events or zaps.
    # Let's eliminate them directly with zaps or by simply simulating a single zap
    # when they have 1 life left.
    # Wait, they start with start_lives. To simulate them being eliminated:
    # Let's just run zaps every 9000ms.
    # To eliminate Scout2 (starts with 15 lives): Cmd1 zaps Scout2.
    events = [
        GameEvent(
            game_id='test_chapter_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    # Cmd1 zaps Scout2 15 times
    for i in range(15):
        t = 1000 + i * 9000
        events.append(
            GameEvent(
                game_id='test_chapter_game',
                time=t,
                event_type='0206',
                actor_entity_id='C1',
                target_entity_id='S2',
                action='zaps',
                raw_message='',
            )
        )

    game.events = events

    generator = LFChapterGenerator(game)
    candidates = generator._collect_candidates()

    elim_chapters = [c for c in candidates if 'Sct2 eliminated' in c.message]
    assert len(elim_chapters) == 1
    assert (
        elim_chapters[0].importance == 2
    )  # Scout (other role) is importance 2
    assert elim_chapters[0].time_ms == 1000 + 14 * 9000


def test_collect_candidates_nuke_detonate_and_cancel() -> None:
    game = _create_test_game()

    events = [
        GameEvent(
            game_id='test_chapter_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Cmd1 activates nuke (0404) at 5000
        GameEvent(
            game_id='test_chapter_game',
            time=5000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Cmd1 detonates nuke (0405) at 10000
        GameEvent(
            game_id='test_chapter_game',
            time=10000,
            event_type='0405',
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
        # Cmd1 activates nuke (0404) at 20000
        GameEvent(
            game_id='test_chapter_game',
            time=20000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Scout2 zaps/downs Cmd1 at 22000, canceling nuke
        GameEvent(
            game_id='test_chapter_game',
            time=22000,
            event_type='0206',
            actor_entity_id='S2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
    ]

    game.events = events

    generator = LFChapterGenerator(game)
    candidates = generator._collect_candidates()

    detonate_ch = [c for c in candidates if 'detonates nuke' in c.message]
    cancel_ch = [c for c in candidates if 'nuke canceled' in c.message]

    assert len(detonate_ch) == 1
    assert detonate_ch[0].time_ms == 10000
    assert detonate_ch[0].importance == 3

    assert len(cancel_ch) == 1
    assert cancel_ch[0].time_ms == 22000
    assert cancel_ch[0].importance == 3


def test_filter_and_consolidate() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now())
    )

    # Setup chapters:
    # 1. Cmd1 nuke canceled at 5000, importance 3
    # 2. Med1 eliminated at 8000, importance 5 (within 10s of 1)
    # Since 5 > 3, chapter 1 should be discarded, keeping 2.
    ch1 = LFChapter(time_ms=5000, message='Nuke Canceled', importance=3)
    ch2 = LFChapter(time_ms=8000, message='Med1 eliminated', importance=5)

    res = generator._filter_and_consolidate([ch1, ch2])
    assert len(res) == 1
    assert res[0].message == 'Med1 eliminated'

    # Same importance:
    # 3. Sct2 eliminated at 20000, importance 2
    # 4. Heavy eliminated at 25000, importance 2
    # Within 10s, same importance -> combine messages and keep earlier time (20000)
    ch3 = LFChapter(time_ms=20000, message='Sct2 eliminated', importance=2)
    ch4 = LFChapter(time_ms=25000, message='Heavy eliminated', importance=2)

    res = generator._filter_and_consolidate([ch3, ch4])
    assert len(res) == 1
    assert res[0].time_ms == 20000
    assert res[0].message == 'Sct2 eliminated, Heavy eliminated'
    assert res[0].importance == 2


def test_limit_chapters() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now())
    )

    # Build 22 chapters of varying importance
    # 10 of importance 1, 10 of importance 2, 2 of importance 5
    chapters = []
    for i in range(10):
        chapters.append(
            LFChapter(time_ms=1000 * i, message=f'Low {i}', importance=1)
        )
    for i in range(10):
        chapters.append(
            LFChapter(
                time_ms=10000 + 1000 * i, message=f'Mid {i}', importance=2
            )
        )
    chapters.append(LFChapter(time_ms=30000, message='High 1', importance=5))
    chapters.append(LFChapter(time_ms=31000, message='High 2', importance=5))

    # Limit to 20
    limited = generator._limit_chapters(chapters, max_chapters=20)
    assert len(limited) == 20

    # The 2 eliminated should be the lowest importance (1), and within importance 1,
    # the latest ones (Low 9 and Low 8).
    messages = [c.message for c in limited]
    assert 'Low 9' not in messages
    assert 'Low 8' not in messages
    assert 'Low 7' in messages


def test_format_youtube_chapters() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now())
    )

    ch = [
        LFChapter(time_ms=15000, message='Nuke Detonated', importance=3),
        LFChapter(time_ms=75000, message='Med1 eliminated', importance=5),
    ]

    # Without pregame delay (starts with Start at 00:00)
    out1 = generator.format_youtube_chapters(ch, pregame_delay_ms=0)
    expected1 = '00:00 Start\n00:15 Nuke Detonated\n01:15 Med1 eliminated'
    assert out1 == expected1

    # With pregame delay of 10000ms (starts with Warmup at 00:00)
    out2 = generator.format_youtube_chapters(ch, pregame_delay_ms=10000)
    expected2 = '00:00 Warmup\n00:25 Nuke Detonated\n01:25 Med1 eliminated'
    assert out2 == expected2
