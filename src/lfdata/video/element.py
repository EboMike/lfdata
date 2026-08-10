"""UI elements and styling for LF game video generation.

This module defines dataclasses representing visual UI elements, styling definitions,
scoreboard structures, timeline slots, event log entries, and camera shake parameters
rendered on video frames.

Usage example:
    from lfdata.video.element import UIElement, UIElementStyle

    style = UIElementStyle(font='GoogleSans-Bold', size=24, color='#FFFFFFFF')
    element = UIElement(element_type='text', text='Game Start', style=style, x=100, y=50)
"""

from dataclasses import dataclass, field


@dataclass
class LFEventLogEntry:
    """Event log record formatted for video overlay display.

    Holds event time offset in milliseconds, text description, importance flag, and actor/target IDs.
    """

    time: int
    desc: str
    is_important: bool
    actor_id: str | None = None
    target_id: str | None = None


@dataclass
class LFPlayerEventUpdate:
    """Represents a bundled zap update within a player event entry."""

    time: int
    desc: str
    target_color_override: dict[str, str] | None = None


@dataclass
class LFPlayerEventLogEntry:
    """Represents a logged player-specific event with updates and durations."""

    time: int
    desc: str
    actor_id: str | None = None
    target_id: str | None = None
    event_type: str | None = None
    target_color_override: dict[str, str] | None = None
    base_desc: str | None = None
    zap_count: int = 1
    updates: list[LFPlayerEventUpdate] = field(default_factory=list)
    duration: int | None = None
    follow_up_desc: str | None = None
    follow_up_time: int | None = None
    double_resup_desc: str | None = None
    double_resup_time: int | None = None


@dataclass
class LFCameraShake:
    """Represents a camera shake action configuration."""

    start_ms: int
    duration_ms: int
    strength: float


@dataclass
class LFHitBorderInstance:
    """Represents a single fullscreen hit border flash instance."""

    start_ms: int
    duration_ms: int
    tint_hex: str
    max_scale: float


@dataclass
class LFScoreboardPlayerData:
    """Represents a player's scoreboard statistics."""

    codename: str
    role_name: str
    score: int
    lives: int
    shots: int
    missiles: int
    special_points: int
    hp: int
    max_hp: int
    is_down: bool
    is_eliminated: bool
    penalties: int


@dataclass
class LFScoreboardTeamTotals:
    """Represents scoreboard totals for a team."""

    score: int
    lives: int
    shots: int
    missiles: int
    special_points: int
    hp: int


@dataclass
class LFScoreboardTeamData:
    """Represents scoreboard details for a team."""

    team_index: int
    team_name: str
    team_score: int
    color_rgb: str
    players: list[LFScoreboardPlayerData]
    visual_rank: float
    totals: LFScoreboardTeamTotals
    y_pos: float | None = None


@dataclass
class LFScoreboardData:
    """Wrapper for scoreboard team data list."""

    teams: list[LFScoreboardTeamData]


@dataclass
class LFMultilineSlot:
    """Represents an active timeline slot for event text display."""

    text: str
    start: int
    end: int
    is_nuke_act: bool
    duration: int
    target_color_override: dict[str, str] | None = None


@dataclass
class UIElementStyle:
    """Represents text styling attributes for visual elements."""

    font: str = 'GoogleSans-Bold'
    style: str = 'normal'
    size: float | int = 20
    color: str = '#ffffffff'
    background_color: str = '#00000000'


@dataclass
class UIElement:
    """Represents a single UI element on a video frame."""

    element_type: str
    position: str = ''
    text: str | None = None
    style: UIElementStyle = field(default_factory=UIElementStyle)
    x: float | None = None
    y: float | None = None
    align: str | None = None
    safe_ms: int = 0
    resettable_ms: int = 0
    scoreboard_data: LFScoreboardData | None = None
    alpha: float = 1.0
    extents: list[float] | None = None
    icon: str | None = None
    current_value: int | None = None
    max_value: int | None = None
    indicator_interval: int | None = None
    events_data: list[LFEventLogEntry] | None = None
    player_to_color: dict[str, str] | None = None
    visible_start_ms: int = 0
    visible_end_ms: int = 0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    formatted_text: str | None = None
