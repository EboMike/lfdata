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

    Attributes:
        time: Millisecond timestamp offset from start of game.
        desc: Description text string for the event.
        is_important: True if event is highlighted as high priority.
        actor_id: Optional entity ID string of event actor.
        target_id: Optional entity ID string of event target.
    """

    time: int
    desc: str
    is_important: bool
    actor_id: str | None = None
    target_id: str | None = None


@dataclass
class LFPlayerEventUpdate:
    """Represents a bundled zap update within a player event entry.

    Attributes:
        time: Millisecond timestamp offset.
        desc: Description string of update.
        target_color_override: Optional mapping of target entity ID to hex color.
    """

    time: int
    desc: str
    target_color_override: dict[str, str] | None = None


@dataclass
class LFPlayerEventLogEntry:
    """Represents a logged player-specific event with updates and durations.

    Attributes:
        time: Millisecond timestamp offset.
        desc: Description string.
        actor_id: Optional actor entity ID string.
        target_id: Optional target entity ID string.
        event_type: Optional TDF event type code string.
        target_color_override: Optional color mapping override dict.
        base_desc: Optional base event description string.
        zap_count: Count of consecutive zaps bundled.
        updates: List of LFPlayerEventUpdate records.
        duration: Optional duration in milliseconds.
        follow_up_desc: Optional follow-up description string.
        follow_up_time: Optional follow-up timestamp in milliseconds.
        double_resup_desc: Optional double resupply description string.
        double_resup_time: Optional double resupply timestamp in milliseconds.
    """

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
    """Represents a camera shake action configuration.

    Attributes:
        start_ms: Timestamp in milliseconds when camera shake starts.
        duration_ms: Duration in milliseconds of camera shake.
        strength: Shake intensity multiplier float.
    """

    start_ms: int
    duration_ms: int
    strength: float


@dataclass
class LFHitBorderInstance:
    """Represents a single fullscreen hit border flash instance.

    Attributes:
        start_ms: Timestamp in milliseconds when border flash starts.
        duration_ms: Duration in milliseconds of border flash.
        tint_hex: CSS hex color string for tinting.
        max_scale: Maximum scaling factor float.
    """

    start_ms: int
    duration_ms: int
    tint_hex: str
    max_scale: float


@dataclass
class LFScoreboardPlayerData:
    """Represents a player's scoreboard statistics.

    Attributes:
        codename: Player codename string.
        role_name: Player role name string.
        score: Current score integer.
        lives: Current lives integer.
        shots: Current shots integer.
        missiles: Current missiles integer.
        special_points: Current special points integer.
        hp: Current hit points integer.
        max_hp: Maximum hit points integer.
        is_down: True if player is down.
        is_eliminated: True if player is eliminated.
        penalties: Penalty count integer.
    """

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
    """Represents scoreboard totals for a team.

    Attributes:
        score: Total team score integer.
        lives: Total team lives integer.
        shots: Total team shots integer.
        missiles: Total team missiles integer.
        special_points: Total team special points integer.
        hp: Total team hit points integer.
    """

    score: int
    lives: int
    shots: int
    missiles: int
    special_points: int
    hp: int


@dataclass
class LFScoreboardTeamData:
    """Represents scoreboard details for a team.

    Attributes:
        team_index: Team index integer.
        team_name: Printable team name string.
        team_score: Total team score integer.
        color_rgb: CSS RGB hex color string.
        players: List of LFScoreboardPlayerData entries.
        visual_rank: Visual animated rank position float.
        totals: Team total statistics object.
        y_pos: Optional vertical y-position coordinate float.
    """

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
    """Wrapper for scoreboard team data list.

    Attributes:
        teams: List of LFScoreboardTeamData objects.
    """

    teams: list[LFScoreboardTeamData]


@dataclass
class LFMultilineSlot:
    """Represents an active timeline slot for event text display.

    Attributes:
        text: Event display text string.
        start: Start timestamp in milliseconds.
        end: End timestamp in milliseconds.
        is_nuke_act: True if slot displays a nuke activation.
        duration: Slot display duration in milliseconds.
        target_color_override: Optional target color mapping dict.
    """

    text: str
    start: int
    end: int
    is_nuke_act: bool
    duration: int
    target_color_override: dict[str, str] | None = None


@dataclass
class UIElementStyle:
    """Represents text styling attributes for visual elements.

    Attributes:
        font: Font family name string.
        style: Font style string ('normal', 'bold').
        size: Font size in pixels.
        color: CSS RGBA hex color string.
        background_color: CSS RGBA hex background color string.
    """

    font: str = 'GoogleSans-Bold'
    style: str = 'normal'
    size: float | int = 20
    color: str = '#ffffffff'
    background_color: str = '#00000000'


@dataclass
class UIElement:
    """Represents a single UI element on a video frame.

    Attributes:
        element_type: Type identifier string ('text', 'scoreboard', etc.).
        position: Layout anchor position string ('top-left', 'center', etc.).
        text: Optional text content string.
        style: UIElementStyle object.
        x: Optional horizontal coordinate float.
        y: Optional vertical coordinate float.
        align: Optional alignment string ('left', 'center', 'right').
        safe_ms: Safe time duration in milliseconds.
        resettable_ms: Resettable status duration in milliseconds.
        scoreboard_data: Optional LFScoreboardData object.
        alpha: Opacity alpha value float (0.0 to 1.0).
        extents: Optional list of bounding box extents [w, h].
        icon: Optional icon path string.
        current_value: Optional numeric current value.
        max_value: Optional numeric maximum value.
        indicator_interval: Optional indicator animation interval.
        events_data: Optional list of LFEventLogEntry objects.
        player_to_color: Optional player entity ID to color mapping.
        visible_start_ms: Visibility start timestamp in milliseconds.
        visible_end_ms: Visibility end timestamp in milliseconds.
        fade_in_ms: Fade-in animation duration in milliseconds.
        fade_out_ms: Fade-out animation duration in milliseconds.
        formatted_text: Optional preformatted text content string.
    """

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
