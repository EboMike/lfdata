"""Tests for video helpers."""

from lfdata.video.helpers import (
    LFTeamTransition,
    _merge_configs,
    apply_animation,
    get_fade_alpha,
    get_visual_rank,
    hex_to_rgb,
    parse_color_with_alpha,
    resolve_animated_value,
    resolve_config_dict,
)


def test_merge_configs() -> None:
    base = {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 5}
    loaded = {'b': {'d': 4, 'f': 7}, 'e': 6, 'g': 8}
    merged = _merge_configs(base, loaded)
    assert merged == {
        'a': 1,
        'b': {'c': 2, 'd': 4, 'f': 7},
        'e': 6,
        'g': 8,
    }


def test_hex_to_rgb() -> None:
    assert hex_to_rgb('#ff5000') == (255, 80, 0)
    assert hex_to_rgb('ff5000') == (255, 80, 0)
    assert hex_to_rgb('invalid') == (255, 255, 255)


def test_parse_color_with_alpha() -> None:
    assert parse_color_with_alpha('#ff5000ff', 1.0) == (255, 80, 0, 255)
    assert parse_color_with_alpha('ff500080', 0.5) == (255, 80, 0, 64)
    assert parse_color_with_alpha('#ff5000', 1.0) == (255, 80, 0, 255)
    assert parse_color_with_alpha('invalid', 1.0) == (255, 255, 255, 255)


def test_apply_animation() -> None:
    assert apply_animation(0.5, 'linear') == 0.5
    assert apply_animation(0.5, 'ease-in') == 0.25
    assert apply_animation(0.5, 'ease-out') == 0.75
    assert apply_animation(0.5, 'ease-in-out') == 0.5
    assert apply_animation(0.5, 'unknown') == 0.5


def test_get_fade_alpha() -> None:
    assert get_fade_alpha(500, 1000, 'linear') == 0.5
    assert get_fade_alpha(500, 0, 'linear') == 0.0
    # Test delayed fade duration behavior
    assert get_fade_alpha(
        500, 2000, 'linear', fade_duration_ms=1000
    ) == 1.0
    assert get_fade_alpha(
        1500, 2000, 'linear', fade_duration_ms=1000
    ) == 0.5
    assert get_fade_alpha(
        2000, 2000, 'linear', fade_duration_ms=1000
    ) == 0.0
    # Test delayed fade duration where fade_duration_ms > total_ms
    assert get_fade_alpha(
        200, 400, 'linear', fade_duration_ms=1000
    ) == 0.5


def test_get_visual_rank() -> None:
    transitions = [
        LFTeamTransition(event_time_ms=1000, visual_rank=1.0, ranking=2),
        LFTeamTransition(event_time_ms=3000, visual_rank=2.0, ranking=1),
    ]
    assert get_visual_rank(0, 500, transitions, 1, 'linear') == 1.0
    assert get_visual_rank(0, 1500, transitions, 1, 'linear') == 1.5
    assert get_visual_rank(0, 2500, transitions, 1, 'linear') == 2.0
    assert get_visual_rank(0, 500, [], 3, 'linear') == 3.0


def test_resolve_animated_value_constant() -> None:
    # Test with normal constant values (no keyframes)
    assert resolve_animated_value(42, 1000) == 42
    assert resolve_animated_value('hello', 1000) == 'hello'
    assert resolve_animated_value([1, 2], 1000) == [1, 2]


def test_resolve_animated_value_keyframes() -> None:
    config_val = {
        'keyframes': [
            {
                'time': 1000,
                'reference': 'start_of_video',
                'value': 10.0,
                'interpolator': 'linear',
            },
            {
                'time': 2000,
                'reference': 'start_of_video',
                'value': 20.0,
                'interpolator': 'linear',
            },
        ]
    }
    # Before first keyframe
    assert resolve_animated_value(config_val, 500) == 10.0
    # At first keyframe
    assert resolve_animated_value(config_val, 1000) == 10.0
    # In between keyframes
    assert resolve_animated_value(config_val, 1500) == 15.0
    # At second keyframe
    assert resolve_animated_value(config_val, 2000) == 20.0
    # After last keyframe
    assert resolve_animated_value(config_val, 2500) == 20.0


def test_resolve_animated_value_time_references() -> None:
    config_val = {
        'keyframes': [
            {
                'time': 1000,
                'reference': 'start_of_game',
                'value': 10.0,
                'interpolator': 'linear',
            },
            {
                'time': -1000,
                'reference': 'end_of_game',
                'value': 20.0,
                'interpolator': 'linear',
            },
        ]
    }
    # Pregame delay: 2000 ms, Game duration: 60000 ms
    # Keyframe 1 absolute time: 2000 + 1000 = 3000 ms
    # Keyframe 2 absolute time: 2000 + 60000 - 1000 = 61000 ms
    # Before Keyframe 1
    assert (
        resolve_animated_value(
            config_val, 2000, pregame_delay_ms=2000, game_duration_ms=60000
        )
        == 10.0
    )
    # At Keyframe 1
    assert (
        resolve_animated_value(
            config_val, 3000, pregame_delay_ms=2000, game_duration_ms=60000
        )
        == 10.0
    )
    # Between Keyframe 1 and 2 (at time 32000 ms)
    # Linear interpolation: progress = (32000 - 3000) / (61000 - 3000) = 0.5
    # Value should be 10.0 + 0.5 * (20.0 - 10.0) = 15.0
    assert (
        resolve_animated_value(
            config_val, 32000, pregame_delay_ms=2000, game_duration_ms=60000
        )
        == 15.0
    )
    # At Keyframe 2
    assert (
        resolve_animated_value(
            config_val, 61000, pregame_delay_ms=2000, game_duration_ms=60000
        )
        == 20.0
    )


def test_resolve_animated_value_coordinate_pair() -> None:
    import pytest

    config_val = {
        'keyframes': [
            {
                'time': 0,
                'value': [0.1, 0.2],
            },
            {
                'time': 1000,
                'value': [0.5, 0.8],
            },
        ]
    }
    # In between (0.5 progress)
    # x: 0.1 + 0.5 * 0.4 = 0.3
    # y: 0.2 + 0.5 * 0.6 = 0.5
    res = resolve_animated_value(config_val, 500)
    assert res == pytest.approx([0.3, 0.5])


def test_resolve_config_dict() -> None:
    import pytest

    config_dict = {
        'fps': 60,
        'size': {
            'keyframes': [
                {'time': 0, 'value': 20},
                {'time': 1000, 'value': 40},
            ]
        },
        'elements': {
            'time': {
                'x': {
                    'keyframes': [
                        {'time': 0, 'value': 0.1},
                        {'time': 1000, 'value': 0.9},
                    ]
                },
                'y': 0.5,
                'extents': {
                    'keyframes': [
                        {'time': 0, 'value': [0.05, 0.05]},
                        {'time': 1000, 'value': [0.15, 0.25]},
                    ]
                },
            }
        },
        'simple_list': [
            1,
            {
                'keyframes': [
                    {'time': 0, 'value': 10},
                    {'time': 1000, 'value': 20},
                ]
            },
        ],
    }

    resolved = resolve_config_dict(config_dict, 500)
    assert resolved['fps'] == 60
    assert resolved['size'] == 30
    assert resolved['elements']['time']['x'] == pytest.approx(0.5)
    assert resolved['elements']['time']['y'] == pytest.approx(0.5)
    assert resolved['elements']['time']['extents'] == pytest.approx([0.1, 0.15])
    assert resolved['simple_list'] == pytest.approx([1, 15])
