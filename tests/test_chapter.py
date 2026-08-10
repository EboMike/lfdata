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
    # Within 10s, both are player eliminations -> combine with 'and'
    ch3 = LFChapter(time_ms=20000, message='Sct2 eliminated', importance=2)
    ch4 = LFChapter(time_ms=25000, message='Heavy eliminated', importance=2)

    res = generator._filter_and_consolidate([ch3, ch4])
    assert len(res) == 1
    assert res[0].time_ms == 20000
    assert res[0].message == 'Sct2 and Heavy eliminated'
    assert res[0].importance == 2


def test_filter_and_consolidate_three_player_eliminations() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now())
    )

    ch1 = LFChapter(time_ms=10000, message='David eliminated', importance=2)
    ch2 = LFChapter(time_ms=12000, message='John eliminated', importance=2)
    ch3 = LFChapter(time_ms=15000, message='Alex eliminated', importance=2)

    res = generator._filter_and_consolidate([ch1, ch2, ch3])
    assert len(res) == 1
    assert res[0].message == 'David, John, and Alex eliminated'


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

    # Without pregame delay (starts with Game Starts at 00:00)
    out1 = generator.format_youtube_chapters(ch, pregame_delay_ms=0)
    expected1 = '00:00 Game Starts\n00:15 Nuke Detonated\n01:15 Med1 eliminated'
    assert out1 == expected1

    # With pregame delay of 10000ms <= 20s (starts with Game Starts at 00:00)
    out2 = generator.format_youtube_chapters(ch, pregame_delay_ms=10000)
    expected2 = '00:00 Game Starts\n00:25 Nuke Detonated\n01:25 Med1 eliminated'
    assert out2 == expected2


def test_format_youtube_chapters_preroll_over_20s() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now())
    )

    ch = [
        LFChapter(time_ms=15000, message='Nuke Detonated', importance=3),
        LFChapter(time_ms=75000, message='Med1 eliminated', importance=5),
    ]

    # With pregame delay of 25000ms (>20s): Getting Ready at 00:00, Game Start at 00:25
    out = generator.format_youtube_chapters(ch, pregame_delay_ms=25000)
    expected = (
        '00:00 Getting Ready\n'
        '00:25 Game Start\n'
        '00:40 Nuke Detonated\n'
        '01:40 Med1 eliminated'
    )
    assert out == expected


def test_format_youtube_chapters_preroll_exactly_20s() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now())
    )

    ch = [
        LFChapter(time_ms=15000, message='Nuke Detonated', importance=3),
    ]

    # Exactly 20000ms is not > 20s, so Game Starts at 00:00
    out = generator.format_youtube_chapters(ch, pregame_delay_ms=20000)
    expected = '00:00 Game Starts\n00:35 Nuke Detonated'
    assert out == expected


def test_format_youtube_chapters_over_20s_delay_truncation() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now())
    )

    ch = [
        LFChapter(time_ms=1000 * i, message=f'Event {i}', importance=1)
        for i in range(25)
    ]

    out = generator.format_youtube_chapters(ch, pregame_delay_ms=25000)
    lines = out.split('\n')
    assert len(lines) == 20
    assert lines[0] == '00:00 Getting Ready'
    assert lines[1] == '00:25 Game Start'


def test_collect_candidates_multi_nuke_detonations() -> None:
    game = _create_test_game()
    events = [
        GameEvent(
            game_id='test_chapter_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # Nuke 1
        GameEvent(
            game_id='test_chapter_game',
            time=5000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        GameEvent(
            game_id='test_chapter_game',
            time=10000,
            event_type='0405',
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
        # Nuke 2 (detonated at 24000ms, which is 14000ms after Nuke 1)
        GameEvent(
            game_id='test_chapter_game',
            time=20000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        GameEvent(
            game_id='test_chapter_game',
            time=24000,
            event_type='0405',
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
        # Nuke 3 (detonated at 50000ms, which is 26000ms after Nuke 2)
        GameEvent(
            game_id='test_chapter_game',
            time=45000,
            event_type='0404',
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        GameEvent(
            game_id='test_chapter_game',
            time=50000,
            event_type='0405',
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
    ]
    game.events = events

    generator = LFChapterGenerator(game)
    candidates = generator._collect_candidates()

    # We expect:
    # 1. A double-nukes chapter at 10000ms: 'Commander Cmd1 double-nukes'
    # 2. A single nuke detonate chapter at 50000ms: 'Cmd1 detonates nuke'
    double_nukes = [c for c in candidates if 'double-nukes' in c.message]
    assert len(double_nukes) == 1
    assert double_nukes[0].time_ms == 10000
    assert double_nukes[0].importance == 3

    single_nukes = [c for c in candidates if 'detonates nuke' in c.message]
    assert len(single_nukes) == 1
    assert single_nukes[0].time_ms == 50000
    assert single_nukes[0].importance == 3


def test_generate_limits_chapters() -> None:
    game = _create_test_game()

    class MockChapterGenerator(LFChapterGenerator):
        def _collect_candidates(self) -> list[LFChapter]:
            return [
                LFChapter(
                    time_ms=20000 * i,
                    message=f'Event {i}',
                    importance=2,
                )
                for i in range(25)
            ]

    generator = MockChapterGenerator(game)
    chapters = generator.generate()
    assert len(chapters) == 20


def test_collect_candidates_team_elimination_on_player_elim() -> None:
    game = _create_test_game()

    # Give Sct2 only 1 life initially by simulating 14 zaps beforehand
    # Or simply zap Sct2 15 times so Sct2 is eliminated.
    # Sct2 is the only player on Earth team in _create_test_game().
    events = [
        GameEvent(
            game_id='test_chapter_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]
    for i in range(15):
        events.append(
            GameEvent(
                game_id='test_chapter_game',
                time=1000 + i * 9000,
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

    elim_chapters = [
        c for c in candidates if 'Earth team eliminated' in c.message
    ]
    assert len(elim_chapters) == 1
    assert 'Sct2 eliminated, Earth team eliminated' in elim_chapters[0].message


def test_collect_candidates_team_elimination_on_nuke_detonation() -> None:
    game = _create_test_game()

    # Reduce Sct2 (Earth team) lives to 3 by zaps, then detonate nuke which loses 3 lives
    events = [
        GameEvent(
            game_id='test_chapter_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        # 12 zaps to get Sct2 down to 3 lives
    ]
    for i in range(12):
        events.append(
            GameEvent(
                game_id='test_chapter_game',
                time=1000 + i * 9000,
                event_type='0206',
                actor_entity_id='C1',
                target_entity_id='S2',
                action='zaps',
                raw_message='',
            )
        )

    # Now Cmd1 activates and detonates nuke.
    # Nuke detonate (0405) takes 3 lives from opposing players (Sct2 has 3 lives, so goes to 0).
    events.extend(
        [
            GameEvent(
                game_id='test_chapter_game',
                time=120000,
                event_type='0404',
                actor_entity_id='C1',
                action='activates nuke',
                raw_message='',
            ),
            GameEvent(
                game_id='test_chapter_game',
                time=125000,
                event_type='0405',
                actor_entity_id='C1',
                action='detonates nuke',
                raw_message='',
            ),
        ]
    )

    game.events = events
    generator = LFChapterGenerator(game)
    candidates = generator._collect_candidates()

    nuke_team_elim = [
        c for c in candidates if 'Earth team eliminated' in c.message
    ]
    assert len(nuke_team_elim) >= 1
    # Check that the nuke event or elimination message has team eliminated
    assert any('Earth team eliminated' in c.message for c in candidates)
