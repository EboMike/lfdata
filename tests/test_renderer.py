from datetime import datetime
from lfdata.model import LFGame
from lfdata.video import VideoGenerator


def test_video_generator_generate(tmp_path) -> None:
    game = LFGame(
        game_id='video_test_game',
        timestamp=datetime.now(),
        game_type='Test Game',
    )

    generator = VideoGenerator(game)
    output_file = tmp_path / 'output.mp4'

    generated_path = generator.generate(output_file)
    assert generated_path.exists()
    assert generated_path == output_file


def test_video_generator_custom_config(tmp_path) -> None:
    import yaml
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id='custom_config_game',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=1000,
    )
    t1 = GameTeam(
        game_id='custom_config_game',
        team_index=0,
        desc='Red Team',
        color_enum=1,
        color_desc='Red',
        color_rgb='#FF0000',
    )
    game.teams = [t1]
    cmd = GameEntity(
        game_id='custom_config_game',
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
            game_id='custom_config_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    # Write custom configuration YAML
    config_data = {
        'fps': 10,
        'extra_footage_ms': 1000,
        'resolution': [800, 600],
        'background_color': '#112233ff',
        'font': 'Arial',
        'elements': {
            'game_type': {'enabled': False},
            'time': {
                'x': 0.8,
                'y': 0.1,
                'align': 'right',
                'style': {
                    'size': 25,
                    'color': '#00ff00ff',
                    'background_color': '#00000080',
                },
            },
        },
    }
    config_file = tmp_path / 'config.yaml'
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config_data, f)

    generator = VideoGenerator(game)
    output_file = tmp_path / 'custom_output.mp4'

    generated_path = generator.generate(output_file, config_path=config_file)
    assert generated_path.exists()
    assert generated_path == output_file


def test_video_generator_font_fallback(tmp_path) -> None:
    import yaml
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    # Test rendering with fallback font
    game = LFGame(
        game_id='font_fallback_game',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=1000,
    )
    t1 = GameTeam(
        game_id='font_fallback_game',
        team_index=0,
        desc='Red Team',
        color_enum=1,
        color_desc='Red',
        color_rgb='#FF0000',
    )
    game.teams = [t1]
    cmd = GameEntity(
        game_id='font_fallback_game',
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
            game_id='font_fallback_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    # Non-existent font should trigger fallback to default font with custom size
    config_data = {
        'fps': 5,
        'extra_footage_ms': 500,
        'resolution': [800, 600],
        'font': 'ThisFontDoesNotExistAtAllSomeRandomName',
        'elements': {
            'player_name': {
                'style': {
                    'size': 30,
                }
            }
        },
    }
    config_file = tmp_path / 'font_fallback_config.yaml'
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config_data, f)

    generator = VideoGenerator(game)
    output_file = tmp_path / 'font_fallback_output.mp4'
    generated_path = generator.generate(output_file, config_path=config_file)
    assert generated_path.exists()


def test_new_hud_features_rendering() -> None:
    from PIL import Image
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.model import LFGame

    game = LFGame(
        game_id='test_render_hud',
        timestamp=datetime.now(),
        game_type='SM5',
    )
    vg = VideoGenerator(game)

    # 1. Test _get_icon_path
    assert vg._get_icon_path('lives') is not None
    assert vg._get_icon_path('shots') is not None
    assert vg._get_icon_path('nonexistent_icon') is None

    # 2. Test _split_by_player_names
    player_colors = {'PlayerOne': '#FF0000', 'PlayerTwo': '#00FF00'}
    segments = vg._split_by_player_names(
        'PlayerOne zaps PlayerTwo',
        player_colors,
    )
    assert segments == [
        ('PlayerOne', '#FF0000'),
        (' zaps ', None),
        ('PlayerTwo', '#00FF00'),
    ]

    # 3. Test _draw_counter rendering (Red, Yellow, Green thresholds)
    for value, max_val in [(1, 10), (4, 10), (8, 10)]:
        img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        el = UIElement(
            element_type='counter',
            x=0.1,
            y=0.1,
            extents=[0.5, 0.5],
            current_value=value,
            max_value=max_val,
            icon='lives',
            style=UIElementStyle(size=12),
        )
        vg._draw_counter(img, el, {})

    # 4. Test _draw_event_scroller rendering
    img = Image.new('RGBA', (400, 400), (0, 0, 0, 0))
    el = UIElement(
        element_type='event_scroller',
        x=0.1,
        y=0.1,
        extents=[0.8, 0.8],
        events_data=[
            {'time': 100, 'desc': 'PlayerOne zaps PlayerTwo'},
            {'time': 200, 'desc': 'PlayerTwo missiles PlayerOne'},
        ],
        player_to_color=player_colors,
        style=UIElementStyle(size=14),
    )
    vg._draw_event_scroller(img, el, 300, {'animation': 'linear'})


def test_sm5_event_generation() -> None:
    from lfdata.model import GameTeam, GameEntity, GameEvent
    from lfdata.video.generator import VisualElementGenerator

    game = LFGame(
        game_id='test_sm5_events',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=10000,
    )
    game.teams = [
        GameTeam(
            game_id='test_sm5_events',
            team_index=0,
            desc='Fire Team',
            color_enum=11,
            color_desc='Fire',
            color_rgb='#FF5000',
        ),
        GameTeam(
            game_id='test_sm5_events',
            team_index=1,
            desc='Earth Team',
            color_enum=12,
            color_desc='Earth',
            color_rgb='#00FF00',
        ),
    ]
    game.entities = [
        GameEntity(
            game_id='test_sm5_events',
            entity_id='P1',
            type='player',
            desc='PlayerOne',
            team_index=0,
            category=1,  # Commander
        ),
        GameEntity(
            game_id='test_sm5_events',
            entity_id='P2',
            type='player',
            desc='PlayerTwo',
            team_index=0,
            category=5,  # Medic
        ),
        GameEntity(
            game_id='test_sm5_events',
            entity_id='P3',
            type='player',
            desc='PlayerThree',
            team_index=1,
            category=3,  # Scout
        ),
    ]
    game.events = [
        GameEvent(
            game_id='test_sm5_events',
            time=0,
            event_type='0100',
            action='start',
        ),
        # Zaps and Missiles
        GameEvent(
            game_id='test_sm5_events',
            time=1000,
            event_type='0205',  # Damage opponent
            actor_entity_id='P1',
            target_entity_id='P3',
        ),
        GameEvent(
            game_id='test_sm5_events',
            time=2000,
            event_type='0207',  # Damage teammate
            actor_entity_id='P1',
            target_entity_id='P2',
        ),
        GameEvent(
            game_id='test_sm5_events',
            time=3000,
            event_type='0306',  # Missile down opponent
            actor_entity_id='P1',
            target_entity_id='P3',
        ),
        # Resupplies & double resupply
        GameEvent(
            game_id='test_sm5_events',
            time=4000,
            event_type='0500',  # Ammo resupply
            actor_entity_id='P1',
            target_entity_id='P2',
        ),
        GameEvent(
            game_id='test_sm5_events',
            time=4500,
            event_type='0502',  # Medic resupply
            actor_entity_id='P2',
            target_entity_id='P1',
        ),
        # Boosts
        GameEvent(
            game_id='test_sm5_events',
            time=6000,
            event_type='0512',  # Life boost
            actor_entity_id='P2',
        ),
        GameEvent(
            game_id='test_sm5_events',
            time=10000,
            event_type='0101',
            action='end',
        ),
    ]

    hud_gen = VisualElementGenerator(game, 'PlayerOne')

    # Verify that the nuke intervals were precomputed (empty since no nuke in events)
    assert hasattr(hud_gen, 'nuke_intervals')

    # Verify that player_event_log contains the player events
    p_evs = [ev['desc'] for ev in hud_gen.player_event_log]
    assert len(p_evs) > 0
    assert any('Zapped PlayerThree' in msg for msg in p_evs)
    assert any('FRIENDLY zap PlayerTwo' in msg for msg in p_evs)


def test_font_resolution_and_defaults() -> None:
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator
    from lfdata.video.element import UIElement, UIElementStyle
    from unittest.mock import patch
    from PIL import Image

    game = LFGame(game_id='test_font_resolution', game_type='SM5')
    vg = VideoGenerator(game)

    import os

    # 1. Test _resolve_font_path for fonts in the fonts/ directory
    assert os.path.normpath(vg._resolve_font_path('Anton')) == os.path.normpath(
        'fonts/GoogleSans-Bold.ttf'
    )
    assert os.path.normpath(
        vg._resolve_font_path('D Day Stencil')
    ) == os.path.normpath('fonts/D Day Stencil.ttf')
    assert os.path.normpath(
        vg._resolve_font_path('advanced_pixel_lcd-7')
    ) == os.path.normpath('fonts/advanced_pixel_lcd-7.ttf')
    assert vg._resolve_font_path('NonexistentFont') == 'NonexistentFont'

    # 2. Test scoreboard header font default logic
    el = UIElement(
        element_type='scoreboard',
        style=UIElementStyle(font='GoogleSans-Bold'),
        scoreboard_data={
            'teams': [
                {
                    'team_index': 0,
                    'team_name': 'Test',
                    'team_score': 100,
                    'visual_rank': 1.0,
                    'players': [],
                }
            ]
        },
    )
    img = Image.new('RGBA', (800, 600), (0, 0, 0, 0))
    with patch.object(
        vg, '_load_scoreboard_fonts', return_value=(None, None)
    ) as mock_load:
        try:
            vg._draw_scoreboard(img, el, {})
        except Exception:
            pass
        any_dday = any(
            args[0] == 'D Day Stencil' for args, _ in mock_load.call_args_list
        )
        assert any_dday


def test_compile_video_extensions() -> None:
    from pathlib import Path
    from unittest.mock import patch
    from lfdata.video.renderer import VideoGenerator
    from lfdata.model import LFGame

    game: LFGame = LFGame(game_id='test_compile', game_type='SM5')
    vg: VideoGenerator = VideoGenerator(game)

    with (
        patch('subprocess.run') as mock_run,
        patch('builtins.print') as mock_print,
    ):
        # 1. Test .mp4 (default H.264 / yuv420p)
        vg._compile_video(
            frames_dir=Path('temp'),
            fps=30,
            output_path=Path('out.mp4'),
        )
        assert mock_run.call_count == 1
        args, _ = mock_run.call_args
        cmd: list[str] = args[0]
        assert '-c:v' in cmd
        idx_codec: int = cmd.index('-c:v')
        assert cmd[idx_codec + 1] == 'libx264'
        assert '-pix_fmt' in cmd
        idx_pix: int = cmd.index('-pix_fmt')
        assert cmd[idx_pix + 1] == 'yuv420p'
        mock_print.assert_any_call('Encoding video to out.mp4...')

        mock_run.reset_mock()
        mock_print.reset_mock()

        # 2. Test .webm (libvpx-vp9 / yuva420p)
        vg._compile_video(
            frames_dir=Path('temp'),
            fps=30,
            output_path=Path('out.webm'),
        )
        assert mock_run.call_count == 1
        args, _ = mock_run.call_args
        cmd = args[0]
        assert '-c:v' in cmd
        idx_codec = cmd.index('-c:v')
        assert cmd[idx_codec + 1] == 'libvpx-vp9'
        assert '-pix_fmt' in cmd
        idx_pix = cmd.index('-pix_fmt')
        assert cmd[idx_pix + 1] == 'yuva420p'
        mock_print.assert_any_call('Encoding video to out.webm...')

        mock_run.reset_mock()
        mock_print.reset_mock()

        # 3. Test .mov (prores_ks / yuva444p10le / profile 4)
        vg._compile_video(
            frames_dir=Path('temp'),
            fps=30,
            output_path=Path('out.mov'),
        )
        assert mock_run.call_count == 1
        args, _ = mock_run.call_args
        cmd = args[0]
        assert '-c:v' in cmd
        idx_codec = cmd.index('-c:v')
        assert cmd[idx_codec + 1] == 'prores_ks'
        assert '-profile:v' in cmd
        idx_prof: int = cmd.index('-profile:v')
        assert cmd[idx_prof + 1] == '4'
        assert '-pix_fmt' in cmd
        idx_pix = cmd.index('-pix_fmt')
        assert cmd[idx_pix + 1] == 'yuva444p10le'
        mock_print.assert_any_call('Encoding video to out.mov...')


def test_generate_frames_progress() -> None:
    from pathlib import Path
    from unittest.mock import patch, MagicMock
    from lfdata.video.renderer import VideoGenerator
    from lfdata.model import LFGame
    from lfdata.video.generator import VisualElementGenerator

    game: LFGame = LFGame(game_id='test_progress', game_type='SM5')
    vg: VideoGenerator = VideoGenerator(game)

    with (
        patch.object(vg, '_render_and_save_frame') as mock_render,
        patch('os.cpu_count', return_value=1),
        patch('time.time') as mock_time,
        patch('builtins.print') as mock_print,
    ):
        # Let's set up time.time() to trigger the 10-second elapsed print
        mock_time.side_effect = [
            100.0,
            100.0,
            111.0,
            111.0,
            111.0,
            111.0,
            111.0,
            111.0,
        ]

        hud_gen: VisualElementGenerator = MagicMock(spec=VisualElementGenerator)
        vg._generate_frames(
            temp_path=Path('temp'),
            start_ms=0,
            end_ms=400,
            fps=10,
            config={},
            hud_gen=hud_gen,
        )

        any_status: bool = any(
            'Rendered' in args[0] for args, _ in mock_print.call_args_list
        )
        assert any_status
        assert mock_render.call_count == 5


def test_new_renderer_rules() -> None:
    from unittest.mock import MagicMock, patch
    from PIL import Image
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id='test_rules_render', game_type='SM5')
    vg = VideoGenerator(game)

    # 1. Test text outline parameters passed to draw.text
    img = Image.new('RGBA', (800, 600), (0, 0, 0, 0))
    el = UIElement(
        element_type='text',
        x=0.5,
        y=0.5,
        text='Hello world',
        style=UIElementStyle(size=20, color='#ffffffff'),
    )

    mock_draw = MagicMock()
    with patch('PIL.ImageDraw.Draw', return_value=mock_draw):
        vg._draw_text_elements(img, [el], {})

        # Verify draw.text was called with stroke_width and stroke_fill
        mock_draw.text.assert_called_once()
        args, kwargs = mock_draw.text.call_args
        assert kwargs.get('stroke_width') is not None
        assert kwargs.get('stroke_width') > 0
        assert kwargs.get('stroke_fill') == (0, 0, 0, 255)

    # 2. Test scoreboard optional borders/background (disabled by default)
    el_sb = UIElement(
        element_type='scoreboard',
        x=0.1,
        y=0.4,
        style=UIElementStyle(size=15),
        scoreboard_data={
            'teams': [
                {
                    'team_index': 0,
                    'team_name': 'Fire Team',
                    'team_score': 100,
                    'color_rgb': '#FF5000',
                    'visual_rank': 1.0,
                    'players': [
                        {
                            'codename': 'Cmdr',
                            'role_name': 'Commander',
                            'score': 100,
                            'lives': 15,
                            'shots': 30,
                            'missiles': 5,
                            'special_points': 0,
                            'hp': 3,
                            'max_hp': 3,
                        },
                        {
                            'codename': 'Sct',
                            'role_name': 'Scout',
                            'score': 50,
                            'lives': 15,
                            'shots': 30,
                            'missiles': 0,
                            'special_points': 0,
                            'hp': 1,
                            'max_hp': 1,
                        },
                    ],
                    'totals': {'score': 150, 'hp': 3},
                }
            ]
        },
    )

    mock_draw_sb = MagicMock()
    with (
        patch('PIL.ImageDraw.Draw', return_value=mock_draw_sb),
        patch.object(vg, '_load_scoreboard_fonts', return_value=(None, None)),
    ):
        # Default config: draw_background=False, draw_borders=False
        vg._draw_scoreboard(img, el_sb, {})
        # Should not call draw.rectangle or draw.line
        assert mock_draw_sb.rectangle.call_count == 0
        assert mock_draw_sb.line.call_count == 0

        # When enabled in config: draw_background=True, draw_borders=True
        mock_draw_sb.reset_mock()
        cfg = {
            'elements': {
                'scoreboard': {
                    'draw_background': True,
                    'draw_borders': True,
                }
            }
        }
        vg._draw_scoreboard(img, el_sb, cfg)
        # Should draw rectangle and separator lines
        assert mock_draw_sb.rectangle.call_count > 0
        assert mock_draw_sb.line.call_count > 0

    # 3. Test HP column is removed entirely
    mock_draw_p = MagicMock()
    with (
        patch('PIL.ImageDraw.Draw', return_value=mock_draw_p),
        patch.object(vg, '_load_scoreboard_fonts', return_value=(None, None)),
    ):
        vg._draw_scoreboard(img, el_sb, {})
        # Get all text elements drawn
        text_calls = [
            args[1] if len(args) > 1 else kwargs.get('text', '')
            for args, kwargs in mock_draw_p.text.call_args_list
        ]
        # HP column should be removed: no HP header, and no player HP values
        assert 'HP' not in text_calls
        assert '3' not in text_calls
        assert '1' not in text_calls


def test_downtime_bar_cropping() -> None:
    from unittest.mock import MagicMock, patch
    from PIL import Image
    from lfdata.video.element import UIElement
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id='test_downtime_bar', game_type='SM5')
    vg = VideoGenerator(game)

    img = Image.new('RGBA', (800, 600), (0, 0, 0, 0))
    el = UIElement(
        element_type='downtime_bar',
        x=0.3,
        y=0.2,
        extents=[0.4, 0.05],
        safe_ms=2000,
        resettable_ms=4000,
    )

    mock_img_full = MagicMock()
    mock_img_empty = MagicMock()
    mock_resized_full = MagicMock()
    mock_resized_empty = MagicMock()
    mock_crop_left = MagicMock()
    mock_crop_right = MagicMock()
    mock_overlay = MagicMock()
    mock_combined = MagicMock()

    mock_img_full.convert.return_value = mock_img_full
    mock_img_empty.convert.return_value = mock_img_empty
    mock_img_full.resize.return_value = mock_resized_full
    mock_img_empty.resize.return_value = mock_resized_empty
    mock_resized_empty.crop.return_value = mock_crop_left
    mock_resized_full.crop.return_value = mock_crop_right

    def open_side_effect(path):
        if 'downtime-full' in str(path):
            return mock_img_full
        if 'downtime-empty' in str(path):
            return mock_img_empty
        raise FileNotFoundError(path)

    with (
        patch('PIL.Image.open', side_effect=open_side_effect),
        patch('PIL.Image.new') as mock_new,
        patch.object(img, 'alpha_composite') as mock_alpha,
    ):
        mock_new.side_effect = [mock_overlay, mock_combined]
        vg._draw_downtime_bar(img, el)

        # Verify alpha_composite was called with mock_overlay
        mock_alpha.assert_called_once_with(mock_overlay)

        # W = 560 - 240 = 320, H = 150 - 120 = 30.
        mock_img_full.resize.assert_called_once_with(
            (320, 30), Image.Resampling.LANCZOS
        )
        mock_img_empty.resize.assert_called_once_with(
            (320, 30), Image.Resampling.LANCZOS
        )

        # progress = (8000 - 6000) / 8000 = 0.25
        # split_x = 320 * 0.25 = 80.
        mock_resized_empty.crop.assert_called_once_with((0, 0, 80, 30))
        mock_resized_full.crop.assert_called_once_with((80, 0, 320, 30))

        # Paste parts on combined
        mock_combined.paste.assert_any_call(mock_crop_left, (0, 0))
        mock_combined.paste.assert_any_call(mock_crop_right, (80, 0))

        # Paste combined on overlay
        mock_overlay.paste.assert_called_once_with(
            mock_combined, (240, 120), mock_combined
        )
