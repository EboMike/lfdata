import pytest
from datetime import datetime
from lfdata.model import LFGame
from lfdata.video import VideoGenerator


def test_video_generator_generate(tmp_path) -> None:
    game = LFGame(
        game_id="video_test_game",
        timestamp=datetime.now(),
        game_type="Test Game",
    )

    generator = VideoGenerator(game)
    output_file = tmp_path / "output.mp4"

    generated_path = generator.generate(output_file)
    assert generated_path.exists()
    assert generated_path == output_file


def test_video_generator_custom_config(tmp_path) -> None:
    import yaml
    from datetime import datetime
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    game = LFGame(
        game_id="custom_config_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=1000,
    )
    t1 = GameTeam(
        game_id="custom_config_game",
        team_index=0,
        desc="Red Team",
        color_enum=1,
        color_desc="Red",
        color_rgb="#FF0000",
    )
    game.teams = [t1]
    cmd = GameEntity(
        game_id="custom_config_game",
        entity_id="C1",
        type="player",
        desc="Player1",
        team_index=0,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    game.entities = [cmd]
    game.events = [
        GameEvent(
            game_id="custom_config_game",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        )
    ]

    # Write custom configuration YAML
    config_data = {
        "fps": 10,
        "extra_footage_ms": 1000,
        "resolution": [800, 600],
        "background_color": "#112233ff",
        "font": "Arial",
        "elements": {
            "game_type": {"enabled": False},
            "time": {
                "x": 0.8,
                "y": 0.1,
                "align": "right",
                "style": {
                    "size": 25,
                    "color": "#00ff00ff",
                    "background_color": "#00000080",
                },
            },
        },
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)

    generator = VideoGenerator(game)
    output_file = tmp_path / "custom_output.mp4"

    generated_path = generator.generate(output_file, config_path=config_file)
    assert generated_path.exists()
    assert generated_path == output_file


def test_video_generator_font_fallback(tmp_path) -> None:
    import yaml
    from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent

    # Test rendering with fallback font
    game = LFGame(
        game_id="font_fallback_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=1000,
    )
    t1 = GameTeam(
        game_id="font_fallback_game",
        team_index=0,
        desc="Red Team",
        color_enum=1,
        color_desc="Red",
        color_rgb="#FF0000",
    )
    game.teams = [t1]
    cmd = GameEntity(
        game_id="font_fallback_game",
        entity_id="C1",
        type="player",
        desc="Player1",
        team_index=0,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    game.entities = [cmd]
    game.events = [
        GameEvent(
            game_id="font_fallback_game",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        )
    ]

    # Non-existent font should trigger fallback to default font with custom size
    config_data = {
        "fps": 5,
        "extra_footage_ms": 500,
        "resolution": [800, 600],
        "font": "ThisFontDoesNotExistAtAllSomeRandomName",
        "elements": {
            "player_name": {
                "style": {
                    "size": 30,
                }
            }
        },
    }
    config_file = tmp_path / "font_fallback_config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f)

    generator = VideoGenerator(game)
    output_file = tmp_path / "font_fallback_output.mp4"
    generated_path = generator.generate(output_file, config_path=config_file)
    assert generated_path.exists()


def test_new_hud_features_rendering() -> None:
    from PIL import Image
    from lfdata.video.element import (
        LFEventLogEntry,
        UIElement,
        UIElementStyle,
    )
    from lfdata.model import LFGame

    game = LFGame(
        game_id="test_render_hud",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    vg = VideoGenerator(game)

    # 1. Test _get_icon_path
    assert vg._get_icon_path("lives") is not None
    assert vg._get_icon_path("shots") is not None
    assert vg._get_icon_path("nonexistent_icon") is None

    # 2. Test _split_by_player_names
    player_colors = {"PlayerOne": "#FF0000", "PlayerTwo": "#00FF00"}
    segments = vg._split_by_player_names(
        "PlayerOne zaps PlayerTwo",
        player_colors,
    )
    assert segments == [
        ("PlayerOne", "#FF0000"),
        (" zaps ", None),
        ("PlayerTwo", "#00FF00"),
    ]

    # 3. Test _draw_counter rendering (Red, Yellow, Green thresholds)
    for value, max_val in [(1, 10), (4, 10), (8, 10)]:
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        el = UIElement(
            element_type="counter",
            x=0.1,
            y=0.1,
            extents=[0.5, 0.5],
            current_value=value,
            max_value=max_val,
            icon="lives",
            style=UIElementStyle(size=12),
        )
        vg._draw_counter(img, el, {})

    # 4. Test _draw_event_scroller rendering
    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    el = UIElement(
        element_type="event_scroller",
        x=0.1,
        y=0.1,
        extents=[0.8, 0.8],
        events_data=[
            LFEventLogEntry(
                time=100,
                desc="PlayerOne zaps PlayerTwo",
                is_important=False,
            ),
            LFEventLogEntry(
                time=200,
                desc="PlayerTwo missiles PlayerOne",
                is_important=False,
            ),
        ],
        player_to_color=player_colors,
        style=UIElementStyle(size=14),
    )
    vg._draw_event_scroller(img, el, 300, {"animation": "linear"})


def test_sm5_event_generation() -> None:
    from lfdata.model import GameTeam, GameEntity, GameEvent
    from lfdata.video.generator import VisualElementGenerator

    game = LFGame(
        game_id="test_sm5_events",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=10000,
    )
    game.teams = [
        GameTeam(
            game_id="test_sm5_events",
            team_index=0,
            desc="Fire Team",
            color_enum=11,
            color_desc="Fire",
            color_rgb="#FF5000",
        ),
        GameTeam(
            game_id="test_sm5_events",
            team_index=1,
            desc="Earth Team",
            color_enum=12,
            color_desc="Earth",
            color_rgb="#00FF00",
        ),
    ]
    game.entities = [
        GameEntity(
            game_id="test_sm5_events",
            entity_id="P1",
            type="player",
            desc="PlayerOne",
            team_index=0,
            category=1,  # Commander
        ),
        GameEntity(
            game_id="test_sm5_events",
            entity_id="P2",
            type="player",
            desc="PlayerTwo",
            team_index=0,
            category=5,  # Medic
        ),
        GameEntity(
            game_id="test_sm5_events",
            entity_id="P3",
            type="player",
            desc="PlayerThree",
            team_index=1,
            category=3,  # Scout
        ),
    ]
    game.events = [
        GameEvent(
            game_id="test_sm5_events",
            time=0,
            event_type="0100",
            action="start",
        ),
        # Zaps and Missiles
        GameEvent(
            game_id="test_sm5_events",
            time=1000,
            event_type="0205",  # Damage opponent
            actor_entity_id="P1",
            target_entity_id="P3",
        ),
        GameEvent(
            game_id="test_sm5_events",
            time=2000,
            event_type="0207",  # Damage teammate
            actor_entity_id="P1",
            target_entity_id="P2",
        ),
        GameEvent(
            game_id="test_sm5_events",
            time=3000,
            event_type="0306",  # Missile down opponent
            actor_entity_id="P1",
            target_entity_id="P3",
        ),
        # Resupplies & double resupply
        GameEvent(
            game_id="test_sm5_events",
            time=4000,
            event_type="0500",  # Ammo resupply
            actor_entity_id="P1",
            target_entity_id="P2",
        ),
        GameEvent(
            game_id="test_sm5_events",
            time=4500,
            event_type="0502",  # Medic resupply
            actor_entity_id="P2",
            target_entity_id="P1",
        ),
        # Boosts
        GameEvent(
            game_id="test_sm5_events",
            time=6000,
            event_type="0512",  # Life boost
            actor_entity_id="P2",
        ),
        GameEvent(
            game_id="test_sm5_events",
            time=10000,
            event_type="0101",
            action="end",
        ),
    ]

    hud_gen = VisualElementGenerator(game, "PlayerOne")

    # Verify that the nuke intervals were precomputed (empty since no nuke in events)
    assert hasattr(hud_gen, "nuke_intervals")

    # Verify that player_event_log contains the player events
    p_evs = [ev.desc for ev in hud_gen.player_event_log]
    assert len(p_evs) > 0
    assert any("Zapped PlayerThree" in msg for msg in p_evs)
    assert any("FRIENDLY zap PlayerTwo" in msg for msg in p_evs)


def test_hud_giver_resupply_and_boost_events() -> None:
    from datetime import datetime
    from lfdata.model import GameTeam, GameEntity, GameEvent, LFGame
    from lfdata.video.generator import VisualElementGenerator

    game = LFGame(
        game_id="test_giver_events",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=15000,
    )
    game.teams = [
        GameTeam(
            game_id="test_giver_events",
            team_index=0,
            desc="Fire Team",
            color_enum=11,
            color_desc="Fire",
            color_rgb="#FF5000",
        ),
    ]
    game.entities = [
        GameEntity(
            game_id="test_giver_events",
            entity_id="P1",
            type="player",
            desc="PlayerOne",
            team_index=0,
            category=2,  # Heavy
        ),
        GameEntity(
            game_id="test_giver_events",
            entity_id="P2",
            type="player",
            desc="PlayerTwo",
            team_index=0,
            category=5,  # Medic
        ),
    ]
    game.events = [
        GameEvent(
            game_id="test_giver_events",
            time=0,
            event_type="0100",
            action="start",
        ),
        # 1. PlayerOne (focused player) resupplies PlayerTwo with ammo (shots)
        GameEvent(
            game_id="test_giver_events",
            time=1000,
            event_type="0500",  # Ammo resupply
            actor_entity_id="P1",
            target_entity_id="P2",
        ),
        # 2. PlayerOne resupplies PlayerTwo with lives (too late for a double)
        GameEvent(
            game_id="test_giver_events",
            time=3000,
            event_type="0502",  # Medic resupply
            actor_entity_id="P1",
            target_entity_id="P2",
        ),
        # 3. PlayerOne resupplies PlayerTwo with shots (start of double)
        GameEvent(
            game_id="test_giver_events",
            time=5000,
            event_type="0500",  # Ammo resupply
            actor_entity_id="P1",
            target_entity_id="P2",
        ),
        # 4. PlayerOne resupplies PlayerTwo with lives 500ms later (double!)
        GameEvent(
            game_id="test_giver_events",
            time=5500,
            event_type="0502",  # Medic resupply
            actor_entity_id="P1",
            target_entity_id="P2",
        ),
        # 5. PlayerOne performs Ammo Boost
        GameEvent(
            game_id="test_giver_events",
            time=7000,
            event_type="0510",  # Ammo boost
            actor_entity_id="P1",
        ),
        # 6. PlayerOne performs Life Boost
        GameEvent(
            game_id="test_giver_events",
            time=8000,
            event_type="0512",  # Life boost
            actor_entity_id="P1",
        ),
        # 7. PlayerOne fires missile and misses (event 0304)
        GameEvent(
            game_id="test_giver_events",
            time=9000,
            event_type="0304",  # Missile miss
            actor_entity_id="P1",
        ),
        GameEvent(
            game_id="test_giver_events",
            time=15000,
            event_type="0101",
            action="end",
        ),
    ]

    hud_gen = VisualElementGenerator(game, "PlayerOne")

    p_evs = [ev.desc for ev in hud_gen.player_event_log]
    assert "Resupplied shots for PlayerTwo" in p_evs
    assert "Resupplied lives for PlayerTwo" in p_evs
    assert "Ammo-boosted team" in p_evs
    assert "Life-boosted team" in p_evs
    assert "Missile MISSES" in p_evs

    # Verify that double resupply was tracked and set on the previous event
    double_event = None
    for ev in hud_gen.player_event_log:
        if ev.time == 5000:
            double_event = ev
            break
    assert double_event is not None
    assert double_event.double_resup_desc == "Double-resupplied PlayerTwo"
    assert double_event.double_resup_time == 5500


def test_font_resolution_and_defaults() -> None:
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator
    from lfdata.video.element import (
        LFScoreboardData,
        LFScoreboardTeamData,
        LFScoreboardTeamTotals,
        UIElement,
        UIElementStyle,
    )
    from unittest.mock import patch
    from PIL import Image

    game = LFGame(game_id="test_font_resolution", game_type="SM5")
    vg = VideoGenerator(game)

    import os

    # 1. Test _resolve_font_path for fonts in the fonts/ directory
    from pathlib import Path

    existing_paths = {
        Path("fonts/GoogleSans-Bold.ttf"),
        Path("fonts/D Day Stencil.ttf"),
        Path("fonts/advanced_pixel_lcd-7.ttf"),
    }

    def mock_exists(self: Path) -> bool:
        normalized_self = Path(os.path.normpath(self))
        for p in existing_paths:
            if Path(os.path.normpath(p)) == normalized_self:
                return True
        return False

    with patch("pathlib.Path.exists", autospec=True, side_effect=mock_exists):
        assert os.path.normpath(vg._resolve_font_path("Anton")) == os.path.normpath(
            "fonts/GoogleSans-Bold.ttf"
        )
        assert os.path.normpath(
            vg._resolve_font_path("D Day Stencil")
        ) == os.path.normpath("fonts/D Day Stencil.ttf")
        assert os.path.normpath(
            vg._resolve_font_path("advanced_pixel_lcd-7")
        ) == os.path.normpath("fonts/advanced_pixel_lcd-7.ttf")

    # When no fonts are present on disk
    with patch("pathlib.Path.exists", autospec=True, return_value=False):
        assert vg._resolve_font_path("Anton") == "Anton"
        assert vg._resolve_font_path("D Day Stencil") == "D Day Stencil"
        assert vg._resolve_font_path("advanced_pixel_lcd-7") == "advanced_pixel_lcd-7"
        assert vg._resolve_font_path("NonexistentFont") == "NonexistentFont"

    # 2. Test scoreboard header font default logic
    el = UIElement(
        element_type="scoreboard",
        style=UIElementStyle(font="GoogleSans-Bold"),
        scoreboard_data=LFScoreboardData(
            teams=[
                LFScoreboardTeamData(
                    team_index=0,
                    team_name="Test",
                    team_score=100,
                    color_rgb="#ffffff",
                    players=[],
                    visual_rank=1.0,
                    totals=LFScoreboardTeamTotals(0, 0, 0, 0, 0, 0),
                )
            ]
        ),
    )
    img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    with patch.object(
        vg, "_load_scoreboard_fonts", return_value=(None, None)
    ) as mock_load:
        try:
            vg._draw_scoreboard(img, el, {})
        except Exception:
            pass
        any_dday = any(
            args[0] == "D Day Stencil" for args, _ in mock_load.call_args_list
        )
        assert any_dday


def test_compile_video_extensions() -> None:
    from pathlib import Path
    from unittest.mock import patch
    from lfdata.video.renderer import VideoGenerator
    from lfdata.model import LFGame

    game: LFGame = LFGame(game_id="test_compile", game_type="SM5")
    vg: VideoGenerator = VideoGenerator(game)

    with (
        patch("subprocess.run") as mock_run,
        patch("builtins.print") as mock_print,
        patch(
            "lfdata.video.renderer._get_best_h264_encoder",
            return_value="libx264",
        ),
    ):
        # 1. Test .mp4 (default H.264 / yuv420p)
        vg._compile_video(
            frames_dir=Path("temp"),
            fps=30,
            output_path=Path("out.mp4"),
        )
        assert mock_run.call_count == 1
        args, _ = mock_run.call_args
        cmd: list[str] = args[0]
        assert "-c:v" in cmd
        idx_codec: int = cmd.index("-c:v")
        assert cmd[idx_codec + 1] == "libx264"
        assert "-pix_fmt" in cmd
        idx_pix: int = cmd.index("-pix_fmt")
        assert cmd[idx_pix + 1] == "yuv420p"
        mock_print.assert_any_call("Encoding video to out.mp4...")

        mock_run.reset_mock()
        mock_print.reset_mock()

        # 2. Test .webm (libvpx-vp9 / yuva420p)
        vg._compile_video(
            frames_dir=Path("temp"),
            fps=30,
            output_path=Path("out.webm"),
        )
        assert mock_run.call_count == 1
        args, _ = mock_run.call_args
        cmd = args[0]
        assert "-c:v" in cmd
        idx_codec = cmd.index("-c:v")
        assert cmd[idx_codec + 1] == "libvpx-vp9"
        assert "-pix_fmt" in cmd
        idx_pix = cmd.index("-pix_fmt")
        assert cmd[idx_pix + 1] == "yuva420p"
        mock_print.assert_any_call("Encoding video to out.webm...")

        mock_run.reset_mock()
        mock_print.reset_mock()

        # 3. Test .mov (prores_ks / yuva444p10le / profile 4)
        vg._compile_video(
            frames_dir=Path("temp"),
            fps=30,
            output_path=Path("out.mov"),
        )
        assert mock_run.call_count == 1
        args, _ = mock_run.call_args
        cmd = args[0]
        assert "-c:v" in cmd
        idx_codec = cmd.index("-c:v")
        assert cmd[idx_codec + 1] == "prores_ks"
        assert "-profile:v" in cmd
        idx_prof: int = cmd.index("-profile:v")
        assert cmd[idx_prof + 1] == "4"
        assert "-pix_fmt" in cmd
        idx_pix = cmd.index("-pix_fmt")
        assert cmd[idx_pix + 1] == "yuva444p10le"
        mock_print.assert_any_call("Encoding video to out.mov...")


def test_generate_frames_progress() -> None:
    from pathlib import Path
    from unittest.mock import patch, MagicMock
    from lfdata.video.renderer import VideoGenerator
    from lfdata.model import LFGame
    from lfdata.video.generator import VisualElementGenerator

    game: LFGame = LFGame(game_id="test_progress", game_type="SM5")
    vg: VideoGenerator = VideoGenerator(game)

    from concurrent.futures import ThreadPoolExecutor

    with (
        patch("concurrent.futures.ProcessPoolExecutor", ThreadPoolExecutor),
        patch.object(vg, "_render_and_save_frame") as mock_render,
        patch("os.cpu_count", return_value=1),
        patch("time.time") as mock_time,
        patch("builtins.print") as mock_print,
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
            temp_path=Path("temp"),
            start_ms=0,
            end_ms=400,
            fps=10,
            config={},
            hud_gen=hud_gen,
        )

        any_status: bool = any(
            "Rendered" in args[0] for args, _ in mock_print.call_args_list
        )
        assert any_status
        assert mock_render.call_count == 5


def test_duration_formatting_and_progress_logging() -> None:
    from pathlib import Path
    from unittest.mock import patch, MagicMock
    from lfdata.video.renderer import VideoGenerator
    from lfdata.model import LFGame

    game = LFGame(game_id="test_progress_new", game_type="SM5")
    vg = VideoGenerator(game)

    # Test _format_duration directly
    assert vg._format_duration(45.5) == "45s"
    assert vg._format_duration(125.0) == "2m 5s"
    assert vg._format_duration(3665.0) == "1h 1m 5s"

    # Test progress logging
    from concurrent.futures import ThreadPoolExecutor

    with (
        patch("concurrent.futures.ProcessPoolExecutor", ThreadPoolExecutor),
        patch.object(vg, "_render_and_save_frame"),
        patch("os.cpu_count", return_value=1),
        patch("time.time") as mock_time,
        patch("builtins.print") as mock_print,
    ):
        t = 100.0

        def tick():
            nonlocal t
            t += 10.0
            return t

        mock_time.side_effect = tick

        hud_gen = MagicMock()
        vg._generate_frames(
            temp_path=Path("temp"),
            start_ms=0,
            end_ms=400,
            fps=10,
            config={},
            hud_gen=hud_gen,
        )

        # Check output messages
        printed_msgs = [args[0] for args, _ in mock_print.call_args_list]

        # There should be a message with elapsed and remaining
        assert any("elapsed" in msg for msg in printed_msgs)
        assert any("remaining" in msg for msg in printed_msgs)


def test_new_renderer_rules() -> None:
    from unittest.mock import MagicMock, patch
    from PIL import Image
    from lfdata.video.element import (
        LFScoreboardData,
        LFScoreboardPlayerData,
        LFScoreboardTeamData,
        LFScoreboardTeamTotals,
        UIElement,
        UIElementStyle,
    )
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_rules_render", game_type="SM5")
    vg = VideoGenerator(game)

    # 1. Test text outline parameters passed to draw.text
    img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    el = UIElement(
        element_type="text",
        x=0.5,
        y=0.5,
        text="Hello world",
        style=UIElementStyle(size=20, color="#ffffffff"),
    )

    mock_draw = MagicMock()
    mock_draw.textbbox.return_value = (0, 0, 100, 20)
    with patch("PIL.ImageDraw.Draw", return_value=mock_draw):
        vg._draw_text_elements(img, [el], {})

        # Verify draw.text was called with stroke_width and stroke_fill
        mock_draw.text.assert_called_once()
        args, kwargs = mock_draw.text.call_args
        assert kwargs.get("stroke_width") is not None
        assert kwargs.get("stroke_width") > 0
        assert kwargs.get("stroke_fill") == (0, 0, 0, 255)

    # 2. Test scoreboard optional borders/background (disabled by default)
    el_sb = UIElement(
        element_type="scoreboard",
        x=0.1,
        y=0.4,
        style=UIElementStyle(size=15),
        scoreboard_data=LFScoreboardData(
            teams=[
                LFScoreboardTeamData(
                    team_index=0,
                    team_name="Fire Team",
                    team_score=100,
                    color_rgb="#FF5000",
                    visual_rank=1.0,
                    players=[
                        LFScoreboardPlayerData(
                            codename="Cmdr",
                            role_name="Commander",
                            score=100,
                            lives=15,
                            shots=30,
                            missiles=5,
                            special_points=0,
                            hp=3,
                            max_hp=3,
                            is_down=False,
                            is_eliminated=False,
                            penalties=0,
                        ),
                        LFScoreboardPlayerData(
                            codename="Sct",
                            role_name="Scout",
                            score=50,
                            lives=15,
                            shots=30,
                            missiles=0,
                            special_points=0,
                            hp=1,
                            max_hp=1,
                            is_down=False,
                            is_eliminated=False,
                            penalties=0,
                        ),
                    ],
                    totals=LFScoreboardTeamTotals(
                        score=150,
                        lives=30,
                        shots=60,
                        missiles=5,
                        special_points=0,
                        hp=3,
                    ),
                )
            ]
        ),
    )

    mock_draw_sb = MagicMock()
    with (
        patch("PIL.ImageDraw.Draw", return_value=mock_draw_sb),
        patch.object(vg, "_load_scoreboard_fonts", return_value=(None, None)),
    ):
        # Default config: draw_background=False, draw_borders=False
        vg._draw_scoreboard(img, el_sb, {})
        # Should not call draw.rectangle or draw.line
        assert mock_draw_sb.rectangle.call_count == 0
        assert mock_draw_sb.line.call_count == 0

        # When enabled in config: draw_background=True, draw_borders=True
        mock_draw_sb.reset_mock()
        cfg = {
            "elements": {
                "scoreboard": {
                    "draw_background": True,
                    "draw_borders": True,
                }
            }
        }
        vg._draw_scoreboard(img, el_sb, cfg)
        # Should draw rectangle and separator lines
        assert mock_draw_sb.rectangle.call_count > 0
        assert mock_draw_sb.line.call_count > 0

        # Verify rectangle coordinates scale with font size
        rect_call_args = mock_draw_sb.rectangle.call_args[0][0]
        width_size_15 = rect_call_args[2] - rect_call_args[0]

        # Double the font size and draw again
        el_sb.style.size = 30
        mock_draw_sb.reset_mock()
        vg._draw_scoreboard(img, el_sb, cfg)
        rect_call_args_double = mock_draw_sb.rectangle.call_args[0][0]
        width_size_30 = rect_call_args_double[2] - rect_call_args_double[0]

        assert width_size_30 > width_size_15
        assert width_size_30 == pytest.approx(2 * width_size_15, abs=2)

    # 3. Test HP column is removed entirely
    mock_draw_p = MagicMock()
    with (
        patch("PIL.ImageDraw.Draw", return_value=mock_draw_p),
        patch.object(vg, "_load_scoreboard_fonts", return_value=(None, None)),
    ):
        vg._draw_scoreboard(img, el_sb, {})
        # Get all text elements drawn
        text_calls = [
            args[1] if len(args) > 1 else kwargs.get("text", "")
            for args, kwargs in mock_draw_p.text.call_args_list
        ]
        # HP column should be removed: no HP header, and no player HP values
        assert "HP" not in text_calls
        assert "3" not in text_calls
        assert "1" not in text_calls

        # Verify all scoreboard text calls use the 'lm' anchor
        for args, kwargs in mock_draw_p.text.call_args_list:
            assert kwargs.get("anchor") == "lm"


def test_downtime_bar_cropping() -> None:
    from unittest.mock import MagicMock, patch
    from PIL import Image
    from lfdata.video.element import UIElement
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_downtime_bar", game_type="SM5")
    vg = VideoGenerator(game)

    img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    el = UIElement(
        element_type="downtime_bar",
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
    mock_combined = MagicMock()

    mock_img_full.convert.return_value = mock_img_full
    mock_img_empty.convert.return_value = mock_img_empty
    mock_img_full.resize.return_value = mock_resized_full
    mock_img_empty.resize.return_value = mock_resized_empty
    mock_resized_empty.crop.return_value = mock_crop_left
    mock_resized_full.crop.return_value = mock_crop_right

    def open_side_effect(path):
        if "downtime-full" in str(path):
            return mock_img_full
        if "downtime-empty" in str(path):
            return mock_img_empty
        raise FileNotFoundError(path)

    with (
        patch("PIL.Image.open", side_effect=open_side_effect),
        patch("PIL.Image.new", return_value=mock_combined),
        patch.object(img, "alpha_composite") as mock_alpha,
    ):
        vg._draw_downtime_bar(img, el)

        # Verify alpha_composite was called with mock_combined
        mock_alpha.assert_called_once_with(mock_combined, dest=(240, 120))

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


def test_event_scroller_fade() -> None:
    from PIL import Image
    from lfdata.video.element import (
        LFEventLogEntry,
        UIElement,
        UIElementStyle,
    )
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_scroller_fade", game_type="SM5")
    vg = VideoGenerator(game)

    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    events = [
        LFEventLogEntry(
            time=i * 10,
            desc=f"PlayerOne zaps PlayerTwo {i}",
            is_important=False,
        )
        for i in range(20)
    ]
    el = UIElement(
        element_type="event_scroller",
        x=0.1,
        y=0.1,
        extents=[0.8, 0.8],
        events_data=events,
        style=UIElementStyle(size=14, color="#ffffffff"),
    )

    config = {
        "animation": "linear",
        "elements": {"all_game_events": {"tilt": 0.0}},
    }
    vg._draw_event_scroller(img, el, 300, config)

    # Let's inspect the alpha channel of pixels in the scroller area.
    # W = 320, H = 320.
    # Area: x from 40 to 360, y from 40 to 360.
    # The top 25% (fade region) is y from 40 to 120.
    # The bottom region is y from 120 to 360.
    top_alphas = []
    for y in range(40, 56):
        for x in range(40, 360):
            top_alphas.append(img.getpixel((x, y))[3])

    bottom_alphas = []
    for y in range(200, 360):
        for x in range(40, 360):
            bottom_alphas.append(img.getpixel((x, y))[3])

    max_top_alpha = max(top_alphas)
    max_bottom_alpha = max(bottom_alphas)

    # There should be text drawn in both regions
    assert max_bottom_alpha == 255
    # The top region should be heavily faded
    assert max_top_alpha < 100


def test_text_cache_and_local_composition() -> None:
    from PIL import Image
    from lfdata.model import LFGame
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_cache_game", game_type="SM5")
    vg = VideoGenerator(game)

    assert len(vg._text_cache) == 0

    img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    el1 = UIElement(
        element_type="text",
        x=0.5,
        y=0.5,
        text="Cache Test String",
        style=UIElementStyle(size=20, color="#ffffffff"),
        alpha=1.0,
    )
    el2 = UIElement(
        element_type="text",
        x=0.5,
        y=0.5,
        text="Cache Test String",
        style=UIElementStyle(size=20, color="#ffffffff"),
        alpha=1.0,
    )

    vg._draw_text_elements(img, [el1], {"resolution": [800, 600]})

    assert len(vg._text_cache) == 1
    cache_key = list(vg._text_cache.keys())[0]
    assert cache_key[0] == "Cache Test String"

    img2 = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    vg._draw_text_elements(img2, [el2], {"resolution": [800, 600]})

    assert len(vg._text_cache) == 1


def test_video_generator_pickling_and_multiprocessing() -> None:
    import pickle
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="pickle_test_game", game_type="SM5")
    vg = VideoGenerator(game)
    vg._text_cache[("test_key",)] = None

    # Try serializing the VideoGenerator
    dumped = pickle.dumps(vg)
    loaded = pickle.loads(dumped)

    assert loaded.game.game_id == "pickle_test_game"
    # Lock should be re-initialized and cache cleared in the loaded state
    assert hasattr(loaded, "_text_cache_lock")
    assert loaded._text_cache_lock is not None
    assert len(loaded._text_cache) == 0


def test_video_generator_generate_piped(tmp_path) -> None:
    from datetime import datetime
    from lfdata.model import LFGame

    game = LFGame(
        game_id="video_test_game_piped",
        timestamp=datetime.now(),
        game_type="Test Game",
    )

    generator = VideoGenerator(game)
    output_file = tmp_path / "output_piped.mp4"

    generated_path = generator.generate(output_file, use_pipe=True)
    assert generated_path.exists()
    assert generated_path == output_file


def test_video_generator_generate_no_pipe(tmp_path) -> None:
    from datetime import datetime
    from lfdata.model import LFGame

    game = LFGame(
        game_id="video_test_game_no_pipe",
        timestamp=datetime.now(),
        game_type="Test Game",
    )

    generator = VideoGenerator(game)
    output_file = tmp_path / "output_no_pipe.mp4"

    generated_path = generator.generate(output_file, use_pipe=False)
    assert generated_path.exists()
    assert generated_path == output_file


def test_icon_cache_and_pickling() -> None:
    """Verifies that role/counter icons are cached and picklable."""
    from pathlib import Path
    import pickle
    from unittest.mock import MagicMock, patch
    from PIL import Image
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_icon_game", game_type="SM5")
    vg = VideoGenerator(game)

    # Test cache starts empty
    assert len(vg._icon_cache) == 0

    icon_path = Path("tests/assets/fake_icon.png")
    mock_img = MagicMock(spec=Image.Image)
    mock_resized = MagicMock(spec=Image.Image)
    mock_img.__enter__.return_value = mock_img
    mock_img.convert.return_value = mock_img
    mock_img.resize.return_value = mock_resized

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("PIL.Image.open", return_value=mock_img),
    ):
        res1 = vg._get_cached_icon(icon_path, 24)
        assert res1 is mock_resized
        assert len(vg._icon_cache) == 1

        # Second request should hit the cache and not call Image.open again
        with patch("PIL.Image.open") as mock_open:
            res2 = vg._get_cached_icon(icon_path, 24)
            assert res2 is mock_resized
            mock_open.assert_not_called()

    # Serialization test
    dumped = pickle.dumps(vg)
    loaded = pickle.loads(dumped)
    assert len(loaded._icon_cache) == 0
    assert hasattr(loaded, "_icon_cache_lock")


def test_text_cache_eviction() -> None:
    """Verifies that text cache evicts and closes oldest images at limit."""
    from unittest.mock import MagicMock
    from PIL import Image
    from lfdata.model import LFGame
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_evict_game", game_type="SM5")
    vg = VideoGenerator(game)

    oldest_mock = MagicMock(spec=Image.Image)
    oldest_key = (
        "text_0",
        "Arial",
        "normal",
        12,
        "#ffffff",
        "#000000",
        1080,
        1.0,
    )
    vg._text_cache[oldest_key] = (oldest_mock, 0, 0)

    for i in range(1, 1000):
        mock_img = MagicMock(spec=Image.Image)
        key = (
            f"text_{i}",
            "Arial",
            "normal",
            12,
            "#ffffff",
            "#000000",
            1080,
            1.0,
        )
        vg._text_cache[key] = (mock_img, 0, 0)

    assert len(vg._text_cache) == 1000

    # Draw one more text element to trigger eviction
    img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    el = UIElement(
        element_type="text",
        x=0.5,
        y=0.5,
        text="New String",
        style=UIElementStyle(size=20, color="#ffffffff"),
        alpha=1.0,
    )
    vg._draw_text_elements(img, [el], {"resolution": [800, 600]})

    assert len(vg._text_cache) == 1000
    assert oldest_key not in vg._text_cache
    oldest_mock.close.assert_called_once()


def test_nuke_flash_rendering() -> None:
    """Verifies that nuke detonations trigger a white flash overlay."""
    from unittest.mock import MagicMock
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_flash_game", game_type="SM5")
    vg = VideoGenerator(game)

    hud_gen = MagicMock()
    hud_gen.nuke_flashes = [1000]

    # Test before flash
    res_before = vg._render_frame([], 500, {"resolution": [100, 100]}, hud_gen)
    # Background remains unchanged (transparent)
    assert res_before.getpixel((50, 50)) == (0, 0, 0, 0)
    res_before.close()

    # Test at exact flash start
    res_start = vg._render_frame([], 1000, {"resolution": [100, 100]}, hud_gen)
    # Overlay is fully white (alpha 255)
    assert res_start.getpixel((50, 50)) == (255, 255, 255, 255)
    res_start.close()

    # Test in the middle of the flash (125 ms elapsed, alpha should be 127)
    res_mid = vg._render_frame([], 1125, {"resolution": [100, 100]}, hud_gen)
    color = res_mid.getpixel((50, 50))
    assert color == (255, 255, 255, 127)
    res_mid.close()

    # Test after flash duration (250 ms elapsed)
    res_after = vg._render_frame([], 1250, {"resolution": [100, 100]}, hud_gen)
    assert res_after.getpixel((50, 50)) == (0, 0, 0, 0)
    res_after.close()


def test_get_best_h264_encoder() -> None:
    """Verifies that _get_best_h264_encoder returns a valid encoder."""
    from unittest.mock import patch
    import subprocess
    from lfdata.video.renderer import _get_best_h264_encoder

    # Test when a hardware encoder succeeds
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None  # succeeds
        encoder = _get_best_h264_encoder()
        assert encoder == "h264_nvenc"
        assert mock_run.call_count == 1

    # Test fallback to libx264 when all hardware encoders fail
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("Failed")
        encoder = _get_best_h264_encoder()
        assert encoder == "libx264"
        # Tries nvenc, amf, qsv, videotoolbox
        assert mock_run.call_count == 4


def test_get_encoder_details() -> None:
    """Verifies that _get_encoder_details describes encoders correctly."""
    from lfdata.video.renderer import _get_encoder_details

    # Test mapped GPU encoders
    assert "NVIDIA NVENC" in _get_encoder_details("h264_nvenc")
    assert "Apple VideoToolbox" in _get_encoder_details("h264_videotoolbox")

    # Test unmapped GPU encoders with known suffixes
    assert _get_encoder_details("custom_nvenc") == "GPU-assisted"
    assert _get_encoder_details("custom_amf") == "GPU-assisted"

    # Test CPU encoders
    assert _get_encoder_details("libx264") == "CPU-only"
    assert _get_encoder_details("libvpx-vp9") == "CPU-only"


def test_generate_video_piped_alpha(tmp_path) -> None:
    """Verifies generating video with separate alpha video file."""
    from unittest.mock import patch, MagicMock
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_alpha_video", game_type="SM5", duration=1000)
    vg = VideoGenerator(game)
    out_file = tmp_path / "main.mp4"
    alpha_file = tmp_path / "alpha.mp4"

    # Mock subprocess.Popen and communications
    with patch("subprocess.Popen") as mock_popen:
        mock_proc_main = MagicMock()
        mock_proc_main.poll.return_value = None
        mock_proc_main.communicate.return_value = (b"", b"")
        mock_proc_main.returncode = 0

        mock_proc_alpha = MagicMock()
        mock_proc_alpha.poll.return_value = None
        mock_proc_alpha.communicate.return_value = (b"", b"")
        mock_proc_alpha.returncode = 0

        # We return main first, then alpha
        mock_popen.side_effect = [mock_proc_main, mock_proc_alpha]

        mock_stdin_main = mock_proc_main.stdin
        mock_stdin_alpha = mock_proc_alpha.stdin

        # Mock the best H.264 encoder to avoid actual hardware checks in tests
        with patch(
            "lfdata.video.renderer._get_best_h264_encoder",
            return_value="libx264",
        ):
            vg.generate(
                output_path=out_file,
                alpha_output_path=alpha_file,
                video_start_ms=0,
                video_end_ms=100,  # Just 7 frames at 60fps
                fps=60,
                use_pipe=True,
            )

        assert mock_popen.call_count == 2
        # Check that both processes had frames written to stdin
        assert mock_stdin_main.write.call_count > 0
        assert mock_stdin_alpha.write.call_count > 0


def test_counter_indicator_rendering() -> None:
    """Verifies that counter arc is rendered in segments to leave gaps."""
    from unittest.mock import MagicMock, patch
    from PIL import Image
    from lfdata.model import LFGame
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_indicator_render", game_type="SM5")
    vg = VideoGenerator(game)

    img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    el = UIElement(
        element_type="counter",
        x=0.1,
        y=0.1,
        extents=[0.05, 0.05],
        current_value=50,
        max_value=100,
        indicator_interval=20,
        style=UIElementStyle(size=18),
    )

    mock_draw = MagicMock()
    with patch("PIL.ImageDraw.Draw", return_value=mock_draw):
        vg._draw_counter(img, el, {})

        # Verify draw.arc calls
        # There should be 3 arc segments because of gaps at 20 and 40
        assert mock_draw.arc.call_count == 3

        call_args_list = mock_draw.arc.call_args_list
        # Segment 1: [141.0, 201.0]
        args1, kwargs1 = call_args_list[0]
        assert abs(kwargs1["start"] - 141.0) < 1e-7
        assert abs(kwargs1["end"] - 201.0) < 1e-7

        # Segment 2: [213.0, 273.0]
        args2, kwargs2 = call_args_list[1]
        assert abs(kwargs2["start"] - 213.0) < 1e-7
        assert abs(kwargs2["end"] - 273.0) < 1e-7

        # Segment 3: [285.0, 315.0]
        args3, kwargs3 = call_args_list[2]
        assert abs(kwargs3["start"] - 285.0) < 1e-7
        assert abs(kwargs3["end"] - 315.0) < 1e-7


def test_missile_flash_rendering() -> None:
    """Verifies that player missiled events trigger a white flash overlay."""
    from unittest.mock import MagicMock
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_missile_flash_game", game_type="SM5")
    vg = VideoGenerator(game)

    hud_gen = MagicMock()
    hud_gen.nuke_flashes = []
    hud_gen.missile_flashes_ms = [1000]

    # Test before flash
    res_before = vg._render_frame([], 500, {"resolution": [100, 100]}, hud_gen)
    assert res_before.getpixel((50, 50)) == (0, 0, 0, 0)
    res_before.close()

    # Test at exact flash start
    res_start = vg._render_frame([], 1000, {"resolution": [100, 100]}, hud_gen)
    assert res_start.getpixel((50, 50)) == (255, 255, 255, 255)
    res_start.close()

    # Test in the middle of the flash (65 ms elapsed, alpha should be 127)
    res_mid = vg._render_frame([], 1065, {"resolution": [100, 100]}, hud_gen)
    color = res_mid.getpixel((50, 50))
    assert color == (255, 255, 255, 127)
    res_mid.close()

    # Test after flash duration (130 ms elapsed)
    res_after = vg._render_frame([], 1130, {"resolution": [100, 100]}, hud_gen)
    assert res_after.getpixel((50, 50)) == (0, 0, 0, 0)
    res_after.close()


def test_dimmed_color_half_saturation_and_darker() -> None:
    """Verifies that dimmed colors have half saturation and slightly darker
    lightness value.
    """
    from lfdata.model import LFGame
    from lfdata.video.element import (
        LFScoreboardTeamData,
        LFScoreboardTeamTotals,
    )
    from lfdata.video.renderer import VideoGenerator
    import colorsys

    game = LFGame(game_id="test_color_game", game_type="SM5")
    vg = VideoGenerator(game)

    # Test with #FF5000 (saturated red-orange)
    team = LFScoreboardTeamData(
        team_index=0,
        team_name="Test Team",
        team_score=0,
        color_rgb="#FF5000",
        players=[],
        visual_rank=1.0,
        totals=LFScoreboardTeamTotals(
            score=0,
            lives=0,
            shots=0,
            missiles=0,
            special_points=0,
            hp=0,
        ),
    )
    _, _, dimmed_color, _ = vg._calculate_team_colors(team)

    h, lightness, s = colorsys.rgb_to_hls(255.0 / 255.0, 80.0 / 255.0, 0.0 / 255.0)

    r_dim, g_dim, b_dim = colorsys.hls_to_rgb(h, lightness * 0.8, s * 0.5)
    expected_dimmed = (
        int(r_dim * 255),
        int(g_dim * 255),
        int(b_dim * 255),
        255,
    )

    assert dimmed_color == expected_dimmed


def test_scoreboard_penalties_rendering() -> None:
    """Verifies that penalty cards are correctly drawn in player rows."""
    from unittest.mock import MagicMock
    from PIL import Image
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id="test_penalties_render", game_type="SM5")
    vg = VideoGenerator(game)

    # 1. Test column offsets shifted by max_player_w
    columns, offsets = vg._resolve_scoreboard_columns(
        x_start=100, table_width=650, max_player_w=300
    )
    # Default Player col starts at 20, default width is 160 units
    # Since max_player_w is 300, excess_w = 300 - 160 = 140 pixels.
    # Non-player columns should be shifted by 140 pixels.
    default_offsets = [100 + int(x) for x in [20, 180, 230, 330, 410, 490, 580]]
    assert offsets[0] == default_offsets[0]
    for i in range(1, len(offsets)):
        assert offsets[i] == default_offsets[i] + 140

    # 2. Test rendering penalty cards in _draw_player_rows
    from lfdata.video.element import LFScoreboardPlayerData

    players = [
        LFScoreboardPlayerData(
            codename="Player1",
            role_name="Medic",
            score=100,
            lives=15,
            shots=30,
            missiles=0,
            special_points=5,
            hp=15,
            max_hp=15,
            is_down=False,
            is_eliminated=False,
            penalties=2,
        ),
        LFScoreboardPlayerData(
            codename="Player2",
            role_name="Medic",
            score=100,
            lives=15,
            shots=30,
            missiles=0,
            special_points=5,
            hp=15,
            max_hp=15,
            is_down=False,
            is_eliminated=False,
            penalties=5,
        ),
    ]

    mock_draw = MagicMock()
    mock_overlay = MagicMock()

    # Stub _get_cached_penalty_card to return a mock card image
    mock_card = MagicMock(spec=Image.Image)
    mock_card.width = 20
    mock_card.height = 20
    vg._get_cached_penalty_card = MagicMock(return_value=mock_card)

    vg._draw_player_rows(
        draw=mock_draw,
        players=players,
        columns=columns,
        offsets=offsets,
        font=None,
        text_color=(255, 255, 255, 255),
        gray_color=(128, 128, 128, 255),
        dimmed_color=(100, 100, 100, 255),
        y_row=100,
        row_h=30,
        height=600,
        overlay=mock_overlay,
        stroke_width=1,
    )

    # 2 penalties for Player 1 -> 2 paste calls
    # 5 penalties for Player 2 -> 3 paste calls (max 3 cards)
    # 2 Medic role icons -> 2 paste calls
    # Total paste calls on overlay = 7
    assert mock_overlay.paste.call_count == 7

    # Player 2 has 5 penalties, so it should draw 'x5' text using draw.text
    x5_calls = [call for call in mock_draw.text.call_args_list if "x5" in call[0][1]]
    assert len(x5_calls) == 1


def test_embedded_images_rendering(tmp_path) -> None:
    """Tests that images embedded via [img:...] tag are rendered correctly."""
    from pathlib import Path
    from PIL import Image
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.video.renderer import VideoGenerator
    from unittest.mock import patch

    # Create a dummy image in assets folder
    asset_dir = Path("assets")
    asset_dir.mkdir(exist_ok=True)
    dummy_asset = asset_dir / "test_logo.png"
    img_logo = Image.new("RGBA", (20, 10), "#FF0000")
    img_logo.save(dummy_asset)

    try:
        game = LFGame(game_id="test_embedded_img", game_type="SM5")
        vg = VideoGenerator(game)

        img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
        # Text element containing an embedded image tag
        el = UIElement(
            element_type="text",
            x=0.5,
            y=0.5,
            text="Score: [img:test_logo.png] 100",
            style=UIElementStyle(size=20, color="#ffffffff"),
        )

        resize_calls = []
        original_resize = Image.Image.resize

        def mock_resize(self, size, *args, **kwargs):
            resize_calls.append(size)
            return original_resize(self, size, *args, **kwargs)

        # Draw the text element and capture resize parameters
        with patch.object(Image.Image, "resize", mock_resize):
            vg._draw_text_elements(img, [el], {})

        assert len(resize_calls) > 0
        target_w, target_h = resize_calls[0]
        # For font size 20 on 600px height, the pixel size is 15
        assert target_h >= 15
        # Aspect ratio of the dummy image is 20 / 10 = 2.0
        # So width should be 2.0 * height
        assert target_w == target_h * 2

        # Test fallback for missing image
        el_fallback = UIElement(
            element_type="text",
            x=0.5,
            y=0.6,
            text="Missing: [img:missing_logo.png]",
            style=UIElementStyle(size=20, color="#ffffffff"),
        )
        vg._draw_text_elements(img, [el_fallback], {})

    finally:
        # Cleanup dummy asset
        if dummy_asset.exists():
            dummy_asset.unlink()


def test_embedded_images_rendering_transparency_cropping(tmp_path) -> None:
    """Tests that transparent padding in embedded images is cropped out."""
    from pathlib import Path
    from PIL import Image, ImageDraw
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.video.renderer import VideoGenerator
    from unittest.mock import patch

    # Create dummy asset dir and a dummy image with transparent borders
    asset_dir = Path("assets")
    asset_dir.mkdir(exist_ok=True)
    dummy_asset = asset_dir / "test_padded.png"

    # 30x20 image, entirely transparent
    img_padded = Image.new("RGBA", (30, 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img_padded)
    # Draw a 10x10 solid red square (non-transparent area)
    draw.rectangle([10, 5, 20, 15], fill="#FF0000")
    img_padded.save(dummy_asset)

    try:
        game = LFGame(game_id="test_padded_img", game_type="SM5")
        vg = VideoGenerator(game)

        img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
        el = UIElement(
            element_type="text",
            x=0.5,
            y=0.5,
            text="Padded: [img:test_padded.png]",
            style=UIElementStyle(size=20, color="#ffffffff"),
        )

        resize_calls = []
        original_resize = Image.Image.resize

        def mock_resize(self, size, *args, **kwargs):
            resize_calls.append(size)
            return original_resize(self, size, *args, **kwargs)

        with patch.object(Image.Image, "resize", mock_resize):
            vg._draw_text_elements(img, [el], {})

        assert len(resize_calls) > 0
        target_w, target_h = resize_calls[0]
        # Aspect ratio of the non-transparent bbox is 1.0 (10x10 square)
        # So width should equal height, confirming transparent margins were cropped
        assert target_w == target_h
    finally:
        if dummy_asset.exists():
            dummy_asset.unlink()


def test_renderer_player_events_in_color() -> None:
    """Verifies renderer colors player name segments inside text elements."""
    from PIL import Image
    from lfdata.video.element import UIElement, UIElementStyle
    from lfdata.video.renderer import VideoGenerator
    from lfdata.model import LFGame

    game = LFGame(game_id="test_render_color_events", game_type="SM5")
    vg = VideoGenerator(game)

    img = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    el = UIElement(
        element_type="text",
        x=0.5,
        y=0.5,
        text="Zapped Player2",
        style=UIElementStyle(size=20, color="#ffffffff"),
        player_to_color={"Player1": "#ff0000", "Player2": "#00ff00"},
    )

    from unittest.mock import patch
    from PIL import ImageDraw

    draw_text_calls = []
    original_text = ImageDraw.ImageDraw.text

    def mock_text(self, xy, text, fill, *args, **kwargs):
        draw_text_calls.append((text, fill))
        return original_text(self, xy, text, fill, *args, **kwargs)

    with patch.object(ImageDraw.ImageDraw, "text", mock_text):
        vg._draw_text_elements(img, [el], {})

    # Since player_to_color has 'Player2': '#00ff00',
    # "Zapped Player2" should be split into:
    # Segment 1: "Zapped " (color #ffffffff)
    # Segment 2: "Player2" (color #00ff00)
    assert len(draw_text_calls) >= 2
    assert draw_text_calls[0][0] == "Zapped "
    assert draw_text_calls[0][1] == (255, 255, 255, 255)
    assert draw_text_calls[1][0] == "Player2"
    assert draw_text_calls[1][1] == (0, 255, 0, 255)


def test_renderer_font_fallback() -> None:
    from PIL import Image, ImageFont, ImageDraw
    from lfdata.model import LFGame
    from lfdata.video.renderer import VideoGenerator

    game = LFGame(game_id='test_font_fallback', game_type='SM5')
    vg = VideoGenerator(game)

    # Load default font
    font = ImageFont.truetype('fonts/GoogleSans-Bold.ttf', 20)

    # 1. Test _is_char_supported
    assert vg._is_char_supported(font, 'A') is True
    assert vg._is_char_supported(font, '☺') is False

    # 2. Test _get_fallback_fonts
    fb = vg._get_fallback_fonts(20)
    assert isinstance(fb, list)

    # 3. Test _get_text_runs
    runs = vg._get_text_runs('Apmkb☺Muwj', font)
    assert len(runs) >= 3
    assert runs[0][0] == 'Apmkb'
    assert runs[1][0] == '☺'
    assert runs[2][0] == 'Muwj'

    # 4. Test _measure_text_width_with_fallback and bbox
    img = Image.new('RGBA', (800, 600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w = vg._measure_text_width_with_fallback(draw, 'Apmkb☺Muwj', font)
    assert w > 0

    bbox = vg._measure_text_bbox_with_fallback(draw, 'Apmkb☺Muwj', font)
    assert len(bbox) == 4
    assert bbox[2] == w

    # 5. Test _draw_text_with_fallback
    vg._draw_text_with_fallback(
        draw, (10, 10), 'Apmkb☺Muwj', fill=(255, 255, 255, 255), font=font
    )
