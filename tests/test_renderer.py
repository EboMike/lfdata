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
