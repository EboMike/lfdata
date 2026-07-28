from datetime import datetime
from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent
from lfdata.video import VideoGenerator, VisualElementGenerator
from lfdata.video.element import UIElement
from lfdata.video.helpers import DEFAULT_CONFIG


def test_pregame_delay_default_config() -> None:
    assert 'pregame_delay_ms' in DEFAULT_CONFIG
    assert DEFAULT_CONFIG['pregame_delay_ms'] == 0


def test_ui_element_defaults() -> None:
    el = UIElement(element_type='text')
    assert el.visible_start_ms == 0
    assert el.visible_end_ms == 0
    assert el.fade_in_ms == 0
    assert el.fade_out_ms == 0


def test_determine_video_end_ms_with_pregame_delay() -> None:
    game = LFGame(
        game_id='test_end_ms',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=100000,
    )
    game.events = [
        GameEvent(
            game_id='test_end_ms',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]
    generator = VideoGenerator(game)
    config = {
        'pregame_delay_ms': 5000,
        'extra_footage_ms': 10000,
    }
    hud_gen = VisualElementGenerator(game, config=config)
    end_ms = generator._determine_video_end_ms(
        hud_gen, config, video_end_ms=None
    )
    # 100000 duration + 10000 extra + 5000 pregame delay = 115000 ms
    assert end_ms == 115000


def test_ui_element_visibility_and_fading() -> None:
    game = LFGame(
        game_id='test_fading',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=20000,
    )
    game.events = [
        GameEvent(
            game_id='test_fading',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]
    # Set up config with pregame_delay_ms = 5000
    config = {
        'pregame_delay_ms': 5000,
        'elements': {
            'game_type': {
                'enabled': True,
                'end_time_offset': 'beginning of video',
                'visible_start_ms': 5000,
                'visible_end_ms': 15000,
                'fade_in_ms': 1000,
                'fade_out_ms': 2000,
            }
        },
    }
    hud_gen = VisualElementGenerator(game, config=config)

    # 1. Before visible_start_ms (time = 4000)
    elements = hud_gen.generate_at(4000)
    el = next((e for e in elements if e.element_type == 'text'), None)
    assert el is not None
    assert el.alpha == 0.0

    # 2. During fade in (time = 5500, progress = (5500-5000)/1000 = 0.5)
    elements = hud_gen.generate_at(5500)
    el = next(
        (
            e
            for e in elements
            if e.element_type == 'text' and 'Game Type' in e.text
        ),
        None,
    )
    assert el is not None
    assert abs(el.alpha - 0.5) < 1e-7

    # 3. Fully visible (time = 8000)
    elements = hud_gen.generate_at(8000)
    el = next(
        (
            e
            for e in elements
            if e.element_type == 'text' and 'Game Type' in e.text
        ),
        None,
    )
    assert el is not None
    assert el.alpha == 1.0

    # 4. During fade out (time = 14000, progress = (15000-14000)/2000 = 0.5)
    elements = hud_gen.generate_at(14000)
    el = next(
        (
            e
            for e in elements
            if e.element_type == 'text' and 'Game Type' in e.text
        ),
        None,
    )
    assert el is not None
    assert abs(el.alpha - 0.5) < 1e-7

    # 5. After visible_end_ms (time = 16000)
    elements = hud_gen.generate_at(16000)
    el = next((e for e in elements if e.element_type == 'text'), None)
    assert el is not None
    assert el.alpha == 0.0


def test_game_time_shifting_with_pregame_delay() -> None:
    game = LFGame(
        game_id='test_shifting',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=20000,
    )
    t1 = GameTeam(
        game_id='test_shifting',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    game.teams = [t1]
    cmd = GameEntity(
        game_id='test_shifting',
        entity_id='C1',
        type='player',
        desc='Player1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    game.entities = [cmd]
    game.events = [
        GameEvent(
            game_id='test_shifting',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    # Config with pregame delay of 5000 ms
    config = {
        'pregame_delay_ms': 5000,
    }
    hud_gen = VisualElementGenerator(game, 'Player1', config=config)

    # At video time 6000 ms, the game time should be 1000 ms.
    # Check timer text: it should display 00:01 (1 second).
    elements = hud_gen.generate_at(6000)
    texts = [el.text for el in elements if el.text]
    assert '00:01' in texts

    # At video time 4000 ms, the game time should be 0 ms.
    # Check timer text: it should display 00:00 (0 seconds).
    elements = hud_gen.generate_at(4000)
    texts = [el.text for el in elements if el.text]
    assert '00:00' in texts


def test_user_defined_text_elements() -> None:
    game = LFGame(
        game_id='test_user_texts',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=10000,
    )
    game.events = [
        GameEvent(
            game_id='test_shifting',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]
    # Check default behavior: elements 1 to 12 should not be created if disabled
    hud_gen = VisualElementGenerator(game, None)
    elements = hud_gen.generate_at(1000)
    for i in range(1, 13):
        el = next((e for e in elements if e.text == f'Custom {i}'), None)
        assert el is None

    # Check that they can be enabled and set
    config = {
        'elements': {
            f'user_defined_text_{i}': {
                'enabled': True,
                'text': f'Custom {i}',
            }
            for i in range(1, 13)
        }
    }
    hud_gen_enabled = VisualElementGenerator(game, None, config=config)
    elements_enabled = hud_gen_enabled.generate_at(1000)
    for i in range(1, 13):
        el = next(
            (e for e in elements_enabled if e.text == f'Custom {i}'),
            None,
        )
        assert el is not None
        assert el.visible_start_ms == 0
        assert el.fade_in_ms == 0
