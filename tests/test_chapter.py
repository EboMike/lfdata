"""Tests for the game chapter generator."""

from datetime import datetime, timezone

from lfdata.model import GameEntity, GameEvent, GameTeam, LFGame
from lfdata.model.gametypes.laserball_events import (
    LASERBALL_EVENT_GOAL,
)
from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_ACTIVATE_NUKE,
    SM5_EVENT_DETONATE_NUKE,
    SM5_EVENT_DOWNED_OPPONENT,
    SM5_EVENT_MISSION_START,
)
from lfdata.video.chapter import LFChapter, LFChapterGenerator


def test_chapter_dataclass() -> None:
    chapter = LFChapter(time_ms=5000, message='Test Event', importance=3)
    assert chapter.time_ms == 5000
    assert chapter.message == 'Test Event'
    assert chapter.importance == 3


def _create_test_game() -> LFGame:
    game = LFGame(
        game_id='test_chapter_game',
        timestamp=datetime.now(timezone.utc),
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
            event_type=SM5_EVENT_MISSION_START,
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
                event_type=SM5_EVENT_DOWNED_OPPONENT,
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
            event_type=SM5_EVENT_MISSION_START,
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
                event_type=SM5_EVENT_DOWNED_OPPONENT,
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
            event_type=SM5_EVENT_MISSION_START,
            action='start',
            raw_message='',
        ),
        # Cmd1 activates nuke (0404) at 5000
        GameEvent(
            game_id='test_chapter_game',
            time=5000,
            event_type=SM5_EVENT_ACTIVATE_NUKE,
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Cmd1 detonates nuke (0405) at 10000
        GameEvent(
            game_id='test_chapter_game',
            time=10000,
            event_type=SM5_EVENT_DETONATE_NUKE,
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
        # Cmd1 activates nuke (0404) at 20000
        GameEvent(
            game_id='test_chapter_game',
            time=20000,
            event_type=SM5_EVENT_ACTIVATE_NUKE,
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        # Scout2 zaps/downs Cmd1 at 22000, canceling nuke
        GameEvent(
            game_id='test_chapter_game',
            time=22000,
            event_type=SM5_EVENT_DOWNED_OPPONENT,
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
        LFGame(game_id='dummy', timestamp=datetime.now(timezone.utc))
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
        LFGame(game_id='dummy', timestamp=datetime.now(timezone.utc))
    )

    ch1 = LFChapter(time_ms=10000, message='David eliminated', importance=2)
    ch2 = LFChapter(time_ms=12000, message='John eliminated', importance=2)
    ch3 = LFChapter(time_ms=15000, message='Alex eliminated', importance=2)

    res = generator._filter_and_consolidate([ch1, ch2, ch3])
    assert len(res) == 1
    assert res[0].message == 'David, John, and Alex eliminated'


def test_limit_chapters() -> None:
    generator = LFChapterGenerator(
        LFGame(game_id='dummy', timestamp=datetime.now(timezone.utc))
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
        LFGame(game_id='dummy', timestamp=datetime.now(timezone.utc))
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
        LFGame(game_id='dummy', timestamp=datetime.now(timezone.utc))
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
        LFGame(game_id='dummy', timestamp=datetime.now(timezone.utc))
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
        LFGame(game_id='dummy', timestamp=datetime.now(timezone.utc))
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
            event_type=SM5_EVENT_MISSION_START,
            action='start',
            raw_message='',
        ),
        # Nuke 1
        GameEvent(
            game_id='test_chapter_game',
            time=5000,
            event_type=SM5_EVENT_ACTIVATE_NUKE,
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        GameEvent(
            game_id='test_chapter_game',
            time=10000,
            event_type=SM5_EVENT_DETONATE_NUKE,
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
        # Nuke 2 (detonated at 24000ms, which is 14000ms after Nuke 1)
        GameEvent(
            game_id='test_chapter_game',
            time=20000,
            event_type=SM5_EVENT_ACTIVATE_NUKE,
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        GameEvent(
            game_id='test_chapter_game',
            time=24000,
            event_type=SM5_EVENT_DETONATE_NUKE,
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
        # Nuke 3 (detonated at 50000ms, which is 26000ms after Nuke 2)
        GameEvent(
            game_id='test_chapter_game',
            time=45000,
            event_type=SM5_EVENT_ACTIVATE_NUKE,
            actor_entity_id='C1',
            action='activates nuke',
            raw_message='',
        ),
        GameEvent(
            game_id='test_chapter_game',
            time=50000,
            event_type=SM5_EVENT_DETONATE_NUKE,
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
            event_type=SM5_EVENT_MISSION_START,
            action='start',
            raw_message='',
        )
    ]
    for i in range(15):
        events.append(
            GameEvent(
                game_id='test_chapter_game',
                time=1000 + i * 9000,
                event_type=SM5_EVENT_DOWNED_OPPONENT,
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
            event_type=SM5_EVENT_MISSION_START,
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
                event_type=SM5_EVENT_DOWNED_OPPONENT,
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
                event_type=SM5_EVENT_ACTIVATE_NUKE,
                actor_entity_id='C1',
                action='activates nuke',
                raw_message='',
            ),
            GameEvent(
                game_id='test_chapter_game',
                time=125000,
                event_type=SM5_EVENT_DETONATE_NUKE,
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


def _create_laserball_test_game() -> LFGame:
    """Creates a basic Laserball game model for testing.

    Sets up a two-team Laserball game with two players for chapter
    candidate evaluation tests.

    Returns:
        LFGame: The initialized Laserball game instance.
    """
    game = LFGame(
        game_id='test_lb_chapter_game',
        timestamp=datetime.now(timezone.utc),
        game_type='Laserball',
    )
    t1 = GameTeam(
        game_id='test_lb_chapter_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    t2 = GameTeam(
        game_id='test_lb_chapter_game',
        team_index=1,
        desc='Earth Team',
        color_enum=13,
        color_desc='Earth',
        color_rgb='#00FF00',
    )
    game.teams = [t1, t2]

    p1 = GameEntity(
        game_id='test_lb_chapter_game',
        entity_id='P1',
        type='player',
        desc='Player1',
        team_index=0,
        level=1,
        battlesuit='Suit1',
    )
    p2 = GameEntity(
        game_id='test_lb_chapter_game',
        entity_id='P2',
        type='player',
        desc='Player2',
        team_index=1,
        level=1,
        battlesuit='Suit2',
    )
    game.entities = [p1, p2]
    return game


def test_classify_laserball_goal() -> None:
    game = _create_laserball_test_game()
    gen = LFChapterGenerator(game)

    # 1. Multiple of 5 (Importance 4)
    msg, imp = gen._classify_laserball_goal(
        actor_name='Player1',
        team_name='Fire Team',
        score_before=4,
        score_after=5,
        max_other_before=2,
        max_other_after=2,
    )
    assert msg == 'Fire Team reaches 5 goals'
    assert imp == 4

    # Multiple of 5 at 10 goals
    msg, imp = gen._classify_laserball_goal(
        actor_name='Player1',
        team_name='Fire Team',
        score_before=9,
        score_after=10,
        max_other_before=11,
        max_other_after=11,
    )
    assert msg == 'Fire Team reaches 10 goals'
    assert imp == 4

    # 2. Lead change (Importance 3)
    # Tied (2-2) -> lead (3-2)
    msg, imp = gen._classify_laserball_goal(
        actor_name='Player1',
        team_name='Fire Team',
        score_before=2,
        score_after=3,
        max_other_before=2,
        max_other_after=2,
    )
    assert msg == 'Player1 scores, putting Fire Team in the lead'
    assert imp == 3

    # Trailing (1-2) -> lead (3-2)
    msg, imp = gen._classify_laserball_goal(
        actor_name='Player1',
        team_name='Fire Team',
        score_before=1,
        score_after=3,
        max_other_before=2,
        max_other_after=2,
    )
    assert msg == 'Player1 scores, putting Fire Team in the lead'
    assert imp == 3

    # 3. Tie game (Importance 2)
    # Trailing (1-2) -> tied (2-2)
    msg, imp = gen._classify_laserball_goal(
        actor_name='Player2',
        team_name='Earth Team',
        score_before=1,
        score_after=2,
        max_other_before=2,
        max_other_after=2,
    )
    assert msg == 'Player2 scores, tying the game'
    assert imp == 2

    # 4. Regular goal (Importance 1)
    # Already leading (3-1 -> 4-1)
    msg, imp = gen._classify_laserball_goal(
        actor_name='Player1',
        team_name='Fire Team',
        score_before=3,
        score_after=4,
        max_other_before=1,
        max_other_after=1,
    )
    assert msg == 'Player1 scores a goal'
    assert imp == 1

    # Still trailing (0-3 -> 1-3)
    msg, imp = gen._classify_laserball_goal(
        actor_name='Player2',
        team_name='Earth Team',
        score_before=0,
        score_after=1,
        max_other_before=3,
        max_other_after=3,
    )
    assert msg == 'Player2 scores a goal'
    assert imp == 1


def test_collect_candidates_laserball_all_rules() -> None:
    game = _create_laserball_test_game()

    events = [
        # Game start at 0
        GameEvent(
            game_id='test_lb_chapter_game',
            time=0,
            event_type=SM5_EVENT_MISSION_START,
            action='start',
            raw_message='',
        ),
        # 1. P1 scores at 20000ms: 1-0 -> Fire Team takes lead (imp 3)
        GameEvent(
            game_id='test_lb_chapter_game',
            time=20000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P1',
            action='scores a goal',
            raw_message='',
        ),
        # 2. P2 scores at 40000ms: 1-1 -> ties game (imp 2)
        GameEvent(
            game_id='test_lb_chapter_game',
            time=40000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P2',
            action='scores a goal',
            raw_message='',
        ),
        # 3. P2 scores at 60000ms: 1-2 -> Earth Team takes lead (imp 3)
        GameEvent(
            game_id='test_lb_chapter_game',
            time=60000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P2',
            action='scores a goal',
            raw_message='',
        ),
        # 4. P2 scores at 80000ms: 1-3 -> regular goal (imp 1)
        GameEvent(
            game_id='test_lb_chapter_game',
            time=80000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P2',
            action='scores a goal',
            raw_message='',
        ),
        # 5. P2 scores at 100000ms: 1-4 -> regular goal (imp 1)
        GameEvent(
            game_id='test_lb_chapter_game',
            time=100000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P2',
            action='scores a goal',
            raw_message='',
        ),
        # 6. P2 scores at 120000ms: 1-5 -> multiple of 5 (imp 4)
        GameEvent(
            game_id='test_lb_chapter_game',
            time=120000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P2',
            action='scores a goal',
            raw_message='',
        ),
    ]
    game.events = events

    gen = LFChapterGenerator(game)
    candidates = gen._collect_candidates()

    assert len(candidates) == 6

    # 1. Lead change: Fire Team leads
    assert candidates[0].time_ms == 20000
    assert candidates[0].message == (
        'Player1 scores, putting Fire Team in the lead'
    )
    assert candidates[0].importance == 3

    # 2. Tie game
    assert candidates[1].time_ms == 40000
    assert candidates[1].message == 'Player2 scores, tying the game'
    assert candidates[1].importance == 2

    # 3. Lead change: Earth Team leads
    assert candidates[2].time_ms == 60000
    assert candidates[2].message == (
        'Player2 scores, putting Earth Team in the lead'
    )
    assert candidates[2].importance == 3

    # 4. Regular goal
    assert candidates[3].time_ms == 80000
    assert candidates[3].message == 'Player2 scores a goal'
    assert candidates[3].importance == 1

    # 5. Regular goal
    assert candidates[4].time_ms == 100000
    assert candidates[4].message == 'Player2 scores a goal'
    assert candidates[4].importance == 1

    # 6. Multiple of 5
    assert candidates[5].time_ms == 120000
    assert candidates[5].message == 'Earth Team reaches 5 goals'
    assert candidates[5].importance == 4


def test_laserball_differentiates_game_types() -> None:
    # 1. Laserball game should collect goal events, not SM5 events
    lb_game = _create_laserball_test_game()
    lb_game.events = [
        GameEvent(
            game_id='test_lb_chapter_game',
            time=10000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P1',
            action='scores a goal',
            raw_message='',
        ),
        # SM5 nuke event placed in a Laserball game should be ignored
        GameEvent(
            game_id='test_lb_chapter_game',
            time=25000,
            event_type=SM5_EVENT_DETONATE_NUKE,
            actor_entity_id='P1',
            action='detonates nuke',
            raw_message='',
        ),
    ]
    lb_gen = LFChapterGenerator(lb_game)
    lb_candidates = lb_gen._collect_candidates()
    assert len(lb_candidates) == 1
    assert lb_candidates[0].time_ms == 10000
    assert 'scores' in lb_candidates[0].message

    # 2. SM5 game should collect SM5 events, not Laserball events
    sm5_game = _create_test_game()
    sm5_game.events = [
        # Laserball goal in SM5 game should be ignored
        GameEvent(
            game_id='test_chapter_game',
            time=10000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='C1',
            action='scores a goal',
            raw_message='',
        ),
        # SM5 nuke in SM5 game
        GameEvent(
            game_id='test_chapter_game',
            time=25000,
            event_type=SM5_EVENT_DETONATE_NUKE,
            actor_entity_id='C1',
            action='detonates nuke',
            raw_message='',
        ),
    ]
    sm5_gen = LFChapterGenerator(sm5_game)
    sm5_candidates = sm5_gen._collect_candidates()
    assert len(sm5_candidates) == 1
    assert sm5_candidates[0].time_ms == 25000
    assert 'detonates nuke' in sm5_candidates[0].message


def test_laserball_filter_and_consolidate() -> None:
    game = _create_laserball_test_game()
    # Goal 1 at 10000ms: P1 scores (1-0, lead, imp 3)
    # Goal 2 at 15000ms (within 10s): P1 scores (2-0, regular, imp 1)
    # The 15000ms goal should be suppressed because it is lower importance
    game.events = [
        GameEvent(
            game_id='test_lb_chapter_game',
            time=10000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P1',
            action='scores a goal',
            raw_message='',
        ),
        GameEvent(
            game_id='test_lb_chapter_game',
            time=15000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P1',
            action='scores a goal',
            raw_message='',
        ),
    ]
    gen = LFChapterGenerator(game)
    chapters = gen.generate()

    assert len(chapters) == 1
    assert chapters[0].time_ms == 10000
    assert chapters[0].importance == 3
    assert 'lead' in chapters[0].message


def test_laserball_generate_and_format_youtube_chapters() -> None:
    game = _create_laserball_test_game()
    game.events = [
        GameEvent(
            game_id='test_lb_chapter_game',
            time=30000,
            event_type=LASERBALL_EVENT_GOAL,
            actor_entity_id='P1',
            action='scores a goal',
            raw_message='',
        ),
    ]
    gen = LFChapterGenerator(game)
    chapters = gen.generate()
    formatted = gen.format_youtube_chapters(chapters, pregame_delay_ms=0)
    assert '00:00 Game Starts' in formatted
    assert '00:30 Player1 scores, putting Fire Team in the lead' in formatted
