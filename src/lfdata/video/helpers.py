"""Visual helpers and default configurations for LF video generation."""

import dataclasses
from typing import Any


@dataclasses.dataclass
class LFTeamTransition:
    """Represents a team rank transition at a specific timestamp.

    Attributes:
        event_time_ms: The millisecond timestamp of the transition.
        visual_rank: The animated visual rank position of the team.
        ranking: The actual scoreboard ranking of the team.
    """

    event_time_ms: int
    visual_rank: float
    ranking: int


DEFAULT_CONFIG: dict[str, Any] = {
    "font": "GoogleSans-Bold",
    "style": "normal",
    "size": 20,
    "color": "#ffffffff",
    "background_color": "#00000000",
    "fps": 60,
    "extra_footage_ms": 10000,
    "pregame_delay_ms": 0,
    "player_name": None,
    "resolution": [1920, 1080],
    "animation": "ease-in-out",
    'fade_duration': 1.0,
    "elements": {
        "game_type": {
            "enabled": True,
            "x": 0.98,
            "y": 0.96,
            "align": "right",
            "style": {"size": 14},
        },
        "normalized_game_type": {
            "enabled": False,
            "x": 0.98,
            "y": 0.96,
            "align": "right",
            "style": {"size": 14},
        },
        "time": {
            "enabled": True,
            "x": 0.98,
            "y": 0.22,
            "align": "right",
            "style": {
                "size": 40,
                "font": "advanced_pixel_lcd-7",
            },
        },
        "player_name": {
            "enabled": True,
            "x": 0.5,
            "y": 0.05,
            "align": "center",
            "style": {"size": 24},
        },
        "player_role": {
            "enabled": True,
            "x": 0.5,
            "y": 0.09,
            "align": "center",
            "style": {"size": 16},
        },
        "player_lives": {
            "enabled": True,
            "x": 0.25,
            "y": 0.92,
            "extents": [0.05, 0.05],
            "align": "left",
            "icon": "lives",
            "style": {"size": 18},
        },
        "player_shots": {
            "enabled": True,
            "x": 0.35,
            "y": 0.92,
            "extents": [0.05, 0.05],
            "align": "left",
            "icon": "shots",
            "style": {"size": 18},
        },
        "player_missiles": {
            "enabled": True,
            "x": 0.45,
            "y": 0.92,
            "extents": [0.05, 0.05],
            "align": "left",
            "icon": "missiles",
            "style": {"size": 18},
        },
        "player_hitpoints": {
            "enabled": True,
            "x": 0.55,
            "y": 0.92,
            "extents": [0.05, 0.05],
            "align": "left",
            "icon": "shields",
            "style": {"size": 18},
        },
        "player_special_points": {
            "enabled": True,
            "x": 0.65,
            "y": 0.92,
            "extents": [0.05, 0.05],
            "align": "left",
            "icon": "sp",
            "style": {"size": 18},
        },
        "player_score": {
            "enabled": True,
            "x": 0.98,
            "y": 0.05,
            "align": "right",
            "style": {"size": 36},
        },
        "scoreboard": {
            "enabled": True,
            "x": 0.02,
            "y": 0.4,
            "extents": [0.4, 0.4],
            "align": "left",
            "draw_background": False,
            "draw_borders": False,
            "style": {"size": 15},
        },
        "downtime": {
            "enabled": True,
            "x": 0.3,
            "y": 0.14,
            "extents": [0.4, 0.03],
        },
        "player_events": {
            "enabled": True,
            "x": 0.5,
            "y": 0.18,
            "align": "center",
            "style": {"size": 18},
            'max_lines': 4,
        },
        "game_events": {
            "enabled": True,
            "x": 0.5,
            "y": 0.3,
            "align": "center",
            "style": {"size": 20},
        },
        "all_game_events": {
            "enabled": True,
            "x": 0.75,
            "y": 0.6,
            "extents": [0.25, 0.25],
            "align": "left",
            "tilt": 10.0,
            "style": {"size": 16},
        },
        "date_of_game": {
            "enabled": True,
            "x": 0.98,
            "y": 0.92,
            "align": "right",
            "style": {"size": 18},
            "format": None,
        },
        "user_defined_text_1": {
            "enabled": False,
            "x": 0.1,
            "y": 0.6,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_2": {
            "enabled": False,
            "x": 0.1,
            "y": 0.7,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_3": {
            "enabled": False,
            "x": 0.1,
            "y": 0.8,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_4": {
            "enabled": False,
            "x": 0.1,
            "y": 0.9,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_5": {
            "enabled": False,
            "x": 0.1,
            "y": 0.1,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_6": {
            "enabled": False,
            "x": 0.1,
            "y": 0.2,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_7": {
            "enabled": False,
            "x": 0.1,
            "y": 0.3,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_8": {
            "enabled": False,
            "x": 0.1,
            "y": 0.4,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_9": {
            "enabled": False,
            "x": 0.1,
            "y": 0.5,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_10": {
            "enabled": False,
            "x": 0.1,
            "y": 0.6,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_11": {
            "enabled": False,
            "x": 0.1,
            "y": 0.7,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "user_defined_text_12": {
            "enabled": False,
            "x": 0.1,
            "y": 0.8,
            "align": "left",
            "style": {"size": 20},
            "text": "",
        },
        "centre_name": {
            "enabled": False,
            "x": 0.1,
            "y": 0.8,
            "align": "left",
            "style": {"size": 20},
        },
    },
}


def _merge_configs(base: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
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
    if hex_str.startswith("#"):
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
    if color_hex.startswith("#"):
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
    if name == "linear":
        return p
    if name == "ease-in":
        return p * p
    if name == "ease-out":
        return p * (2.0 - p)
    if name == "ease-in-out":
        return p * p * (3.0 - 2.0 * p)
    return p


def get_fade_alpha(
    elapsed_ms: int,
    total_ms: int,
    function_name: str,
    fade_duration_ms: int | None = None,
) -> float:
    """Calculates fade-out alpha (1.0 to 0.0) based on elapsed duration.

    Supports optional delayed fade where the element stays fully visible
    until the final fade duration is reached, then animating down.

    Args:
        elapsed_ms: Milliseconds elapsed since the fade started.
        total_ms: Total duration of the fade in milliseconds.
        function_name: Name of the animation function.
        fade_duration_ms: Optional duration of the fadeout period in ms.

    Returns:
        float: The calculated alpha opacity value.
    """
    if total_ms <= 0:
        return 0.0

    if fade_duration_ms is not None:
        fade_duration_ms = min(fade_duration_ms, total_ms)
        if elapsed_ms < total_ms - fade_duration_ms:
            return 1.0
        elapsed_ms = elapsed_ms - (total_ms - fade_duration_ms)
        total_ms = fade_duration_ms

    if total_ms <= 0:
        return 0.0
    p = elapsed_ms / total_ms
    p = max(0.0, min(1.0, p))
    return 1.0 - apply_animation(p, function_name)


def get_visual_rank(
    team_idx: int,
    t_ms: int,
    transitions: list[LFTeamTransition],
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
        if trans.event_time_ms <= t_ms:
            last_trans = trans
        else:
            break

    if last_trans is None:
        if transitions:
            return transitions[0].visual_rank
        return float(final_rank)

    elapsed_ms = t_ms - last_trans.event_time_ms
    if elapsed_ms < 1000:
        p = elapsed_ms / 1000.0
        p_anim = apply_animation(p, animation_func)
        return (
            last_trans.visual_rank
            + (last_trans.ranking - last_trans.visual_rank) * p_anim
        )
    return float(last_trans.ranking)


def _interpolate_values(val_start: Any, val_end: Any, p_anim: float) -> Any:
    """Interpolates between two values or value pairs.

    Uses the animated progress fraction to calculate the intermediate value.
    If the values are coordinate lists or tuples, interpolates both components.

    Args:
        val_start: The starting value (number or coordinate pair).
        val_end: The ending value (number or coordinate pair).
        p_anim: The animated progress fraction (0.0 to 1.0).

    Returns:
        Any: The interpolated value or value pair.
    """
    if isinstance(val_start, (list, tuple)) and isinstance(val_end, (list, tuple)):
        if len(val_start) >= 2 and len(val_end) >= 2:
            x_start, y_start = val_start[0], val_start[1]
            x_end, y_end = val_end[0], val_end[1]
            return [
                x_start + (x_end - x_start) * p_anim,
                y_start + (y_end - y_start) * p_anim,
            ]

    try:
        return val_start + (val_end - val_start) * p_anim
    except (TypeError, ValueError):
        return val_start


def resolve_animated_value(
    config_val: Any,
    time_ms: int,
    pregame_delay_ms: int = 0,
    game_duration_ms: int = 0,
) -> Any:
    """Resolves a configured value at a specific timestamp.

    If the value defines keyframes, interpolates the value based on the current
    timestamp and the keyframes' references and values.

    Args:
        config_val: The configuration value (direct value or keyframe dict).
        time_ms: The current time in milliseconds since the start of the video.
        pregame_delay_ms: Pregame delay in milliseconds.
        game_duration_ms: The duration of the game in milliseconds.

    Returns:
        Any: The resolved value or value pair at the specified timestamp.
    """
    if not isinstance(config_val, dict) or "keyframes" not in config_val:
        return config_val

    keyframes = config_val["keyframes"]
    if not keyframes:
        return None

    # Resolve each keyframe's time to absolute video time in ms
    resolved_keyframes = []
    for kf in keyframes:
        if not isinstance(kf, dict):
            continue
        kf_time_raw = kf.get("time", 0)
        try:
            kf_time_ms = float(kf_time_raw)
        except (TypeError, ValueError):
            kf_time_ms = 0.0

        ref = kf.get("reference", kf.get("time_reference", "start_of_video"))
        if not isinstance(ref, str):
            ref = "start_of_video"
        ref_clean = ref.strip().lower().replace(" ", "_")

        if ref_clean in ("start_of_game", "game_start"):
            abs_time_ms = pregame_delay_ms + kf_time_ms
        elif ref_clean in ("end_of_game", "game_end"):
            abs_time_ms = pregame_delay_ms + game_duration_ms + kf_time_ms
        else:
            abs_time_ms = kf_time_ms

        resolved_keyframes.append(
            {
                "abs_time_ms": abs_time_ms,
                "value": kf.get("value"),
                "interpolator": kf.get("interpolator", "linear"),
            }
        )

    # Sort keyframes by absolute video time
    resolved_keyframes.sort(key=lambda k: k["abs_time_ms"])

    if not resolved_keyframes:
        return None

    # Return boundary values if time is outside keyframe range
    if time_ms <= resolved_keyframes[0]["abs_time_ms"]:
        return resolved_keyframes[0]["value"]
    if time_ms >= resolved_keyframes[-1]["abs_time_ms"]:
        return resolved_keyframes[-1]["value"]

    # Interpolate between matching keyframes
    for i in range(len(resolved_keyframes) - 1):
        kf_start = resolved_keyframes[i]
        kf_end = resolved_keyframes[i + 1]
        t_start_ms = kf_start["abs_time_ms"]
        t_end_ms = kf_end["abs_time_ms"]

        if t_start_ms <= time_ms <= t_end_ms:
            if t_end_ms == t_start_ms:
                return kf_end["value"]

            p = (time_ms - t_start_ms) / (t_end_ms - t_start_ms)
            p_anim = apply_animation(p, kf_start["interpolator"])
            return _interpolate_values(kf_start["value"], kf_end["value"], p_anim)

    return None


def resolve_config_dict(
    config_dict: dict[str, Any],
    time_ms: int,
    pregame_delay_ms: int = 0,
    game_duration_ms: int = 0,
) -> dict[str, Any]:
    """Recursively resolves all values in a config dictionary at a timestamp.

    Iterates through the dictionary structure and resolves any animated values
    defined by keyframes.

    Args:
        config_dict: The configuration dictionary to resolve.
        time_ms: The current time in milliseconds since the start of the video.
        pregame_delay_ms: Pregame delay in milliseconds.
        game_duration_ms: The duration of the game in milliseconds.

    Returns:
        dict[str, Any]: A new dictionary with resolved values.
    """
    resolved: dict[str, Any] = {}
    for k, v in config_dict.items():
        if isinstance(v, dict):
            if "keyframes" in v:
                resolved[k] = resolve_animated_value(
                    v,
                    time_ms,
                    pregame_delay_ms=pregame_delay_ms,
                    game_duration_ms=game_duration_ms,
                )
            else:
                resolved[k] = resolve_config_dict(
                    v,
                    time_ms,
                    pregame_delay_ms=pregame_delay_ms,
                    game_duration_ms=game_duration_ms,
                )
        elif isinstance(v, list):
            resolved_list = []
            for item in v:
                if isinstance(item, dict):
                    if "keyframes" in item:
                        resolved_list.append(
                            resolve_animated_value(
                                item,
                                time_ms,
                                pregame_delay_ms=pregame_delay_ms,
                                game_duration_ms=game_duration_ms,
                            )
                        )
                    else:
                        resolved_list.append(
                            resolve_config_dict(
                                item,
                                time_ms,
                                pregame_delay_ms=pregame_delay_ms,
                                game_duration_ms=game_duration_ms,
                            )
                        )
                else:
                    resolved_list.append(item)
            resolved[k] = resolved_list
        else:
            resolved[k] = v
    return resolved
