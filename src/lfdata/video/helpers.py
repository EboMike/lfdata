"""Visual helpers and default configurations for LF video generation."""

from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    'font': 'GoogleSans-Bold',
    'style': 'normal',
    'size': 20,
    'color': '#ffffffff',
    'background_color': '#00000000',
    'fade_out_time': 2.0,
    'fps': 60,
    'extra_footage_ms': 10000,
    'player_name': None,
    'resolution': [1920, 1080],
    'animation': 'ease-in-out',
    'elements': {
        'game_type': {
            'enabled': True,
            'x': 0.95,
            'y': 0.9,
            'align': 'right',
            'style': {'size': 14},
        },
        'time': {
            'enabled': True,
            'x': 0.95,
            'y': 0.22,
            'align': 'right',
            'style': {
                'size': 40,
                'font': 'advanced_pixel_lcd-7',
            },
        },
        'player_name': {
            'enabled': True,
            'x': 0.5,
            'y': 0.05,
            'align': 'center',
            'style': {'size': 24},
        },
        'player_role': {
            'enabled': True,
            'x': 0.5,
            'y': 0.09,
            'align': 'center',
            'style': {'size': 16},
        },
        'player_lives': {
            'enabled': True,
            'x': 0.2,
            'y': 0.9,
            'extents': [0.05, 0.05],
            'align': 'left',
            'icon': 'lives',
            'style': {'size': 18},
        },
        'player_shots': {
            'enabled': True,
            'x': 0.3,
            'y': 0.9,
            'extents': [0.05, 0.05],
            'align': 'left',
            'icon': 'shots',
            'style': {'size': 18},
        },
        'player_missiles': {
            'enabled': True,
            'x': 0.4,
            'y': 0.9,
            'extents': [0.05, 0.05],
            'align': 'left',
            'icon': 'missiles',
            'style': {'size': 18},
        },
        'player_hitpoints': {
            'enabled': True,
            'x': 0.5,
            'y': 0.9,
            'extents': [0.05, 0.05],
            'align': 'left',
            'icon': 'shields',
            'style': {'size': 18},
        },
        'player_special_points': {
            'enabled': True,
            'x': 0.6,
            'y': 0.9,
            'extents': [0.05, 0.05],
            'align': 'left',
            'icon': 'sp',
            'style': {'size': 18},
        },
        'player_score': {
            'enabled': True,
            'x': 0.95,
            'y': 0.05,
            'align': 'right',
            'style': {'size': 24},
        },
        'scoreboard': {
            'enabled': True,
            'x': 0.05,
            'y': 0.4,
            'extents': [0.4, 0.4],
            'align': 'left',
            'draw_background': False,
            'draw_borders': False,
            'style': {'size': 15},
        },
        'downtime': {
            'enabled': True,
            'x': 0.3,
            'y': 0.14,
            'extents': [0.4, 0.03],
        },
        'player_events': {
            'enabled': True,
            'x': 0.5,
            'y': 0.2,
            'align': 'center',
            'style': {'size': 18},
        },
        'game_events': {
            'enabled': True,
            'x': 0.5,
            'y': 0.25,
            'align': 'center',
            'style': {'size': 20},
        },
        'all_game_events': {
            'enabled': True,
            'x': 0.75,
            'y': 0.6,
            'extents': [0.25, 0.25],
            'align': 'left',
            'tilt': 10.0,
            'style': {'size': 16},
        },
    },
}


def _merge_configs(
    base: dict[str, Any], loaded: dict[str, Any]
) -> dict[str, Any]:
    """Recursively merges a loaded configuration dict into base defaults.

    Args:
        base: The default configuration dictionary.
        loaded: The user-supplied configuration dictionary.

    Returns:
        dict[str, Any]: The recursively merged configuration dictionary.
    """
    result: dict[str, Any] = {}
    for k, v in base.items():
        if k in loaded:
            if isinstance(v, dict) and isinstance(loaded[k], dict):
                result[k] = _merge_configs(v, loaded[k])
            else:
                result[k] = loaded[k]
        else:
            if isinstance(v, dict):
                result[k] = _merge_configs(v, {})
            else:
                result[k] = v
    for k, v in loaded.items():
        if k not in result:
            result[k] = v
    return result


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Converts a hex color string to an RGB tuple.

    Args:
        hex_str: The color hex string (e.g. '#FF5000' or 'FF5000').

    Returns:
        tuple[int, int, int]: The RGB integer values (0-255).
    """
    hex_str = hex_str.strip()
    if hex_str.startswith('#'):
        hex_str = hex_str[1:]
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return r, g, b
    except Exception:
        return 255, 255, 255


def parse_color_with_alpha(
    color_hex: str, element_alpha: float = 1.0
) -> tuple[int, int, int, int]:
    """Parses a hex color and merges it with the element alpha component.

    Args:
        color_hex: The color hex string (e.g. '#ffffffff' or 'ffffffff').
        element_alpha: The element-specific opacity fraction (0.0 to 1.0).

    Returns:
        tuple[int, int, int, int]: The combined RGBA color values (0-255).
    """
    color_hex = color_hex.strip()
    if color_hex.startswith('#'):
        color_hex = color_hex[1:]
    try:
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        if len(color_hex) >= 8:
            a = int(color_hex[6:8], 16)
        else:
            a = 255
    except Exception:
        r, g, b, a = 255, 255, 255, 255

    final_a = int(a * element_alpha)
    return r, g, b, final_a


def apply_animation(p: float, name: str) -> float:
    """Applies the specified animation function to progress value p.

    Args:
        p: Linear progress value from 0.0 to 1.0.
        name: Name of the animation function.

    Returns:
        float: The interpolated progress value.
    """
    p = max(0.0, min(1.0, p))
    if name == 'linear':
        return p
    if name == 'ease-in':
        return p * p
    if name == 'ease-out':
        return p * (2.0 - p)
    if name == 'ease-in-out':
        return p * p * (3.0 - 2.0 * p)
    return p


def get_fade_alpha(elapsed_ms: int, total_ms: int, function_name: str) -> float:
    """Calculates fade-out alpha (1.0 to 0.0) based on elapsed duration.

    Args:
        elapsed_ms: Milliseconds elapsed since the fade started.
        total_ms: Total duration of the fade in milliseconds.
        function_name: Name of the animation function.

    Returns:
        float: The calculated alpha opacity value.
    """
    if total_ms <= 0:
        return 0.0
    p = elapsed_ms / total_ms
    p = max(0.0, min(1.0, p))
    return 1.0 - apply_animation(p, function_name)


def get_visual_rank(
    team_idx: int,
    t_ms: int,
    transitions: list[tuple[int, float, int]],
    final_rank: int,
    animation_func: str,
) -> float:
    """Calculates the animated visual rank of a team at time t_ms.

    Args:
        team_idx: The team index.
        t_ms: The current millisecond timestamp.
        transitions: The precomputed rank swap transitions.
        final_rank: The final target rank of the team.
        animation_func: The animation function to apply.

    Returns:
        float: The animated visual rank position.
    """
    last_trans = None
    for trans in transitions:
        if trans[0] <= t_ms:
            last_trans = trans
        else:
            break

    if last_trans is None:
        if transitions:
            return transitions[0][1]
        return float(final_rank)

    t_start_ms, v_start, target_rank = last_trans
    elapsed_ms = t_ms - t_start_ms
    if elapsed_ms < 1000:
        p = elapsed_ms / 1000.0
        p_anim = apply_animation(p, animation_func)
        return v_start + (target_rank - v_start) * p_anim
    return float(target_rank)
