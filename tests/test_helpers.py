"""Tests for video helpers."""

from lfdata.video.helpers import (
    _merge_configs,
    apply_animation,
    get_fade_alpha,
    get_visual_rank,
    hex_to_rgb,
    parse_color_with_alpha,
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


def test_get_visual_rank() -> None:
    transitions = [(1000, 1.0, 2), (3000, 2.0, 1)]
    assert get_visual_rank(0, 500, transitions, 1, 'linear') == 1.0
    assert get_visual_rank(0, 1500, transitions, 1, 'linear') == 1.5
    assert get_visual_rank(0, 2500, transitions, 1, 'linear') == 2.0
    assert get_visual_rank(0, 500, [], 3, 'linear') == 3.0
