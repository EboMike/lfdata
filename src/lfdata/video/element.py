"""UI elements and styling for LF game video generation."""

from dataclasses import dataclass, field


@dataclass
class UIElementStyle:
    """Represents text styling attributes for visual elements."""

    font: str = "GoogleSans-Bold"
    style: str = "normal"
    size: int = 20
    color: str = "#ffffffff"
    background_color: str = "#00000000"


@dataclass
class UIElement:
    """Represents a single UI element on a video frame."""

    element_type: str
    position: str = ""
    text: str | None = None
    style: UIElementStyle = field(default_factory=UIElementStyle)
    x: float | None = None
    y: float | None = None
    align: str | None = None
    safe_ms: int = 0
    resettable_ms: int = 0
    scoreboard_data: dict[str, any] | None = None
    alpha: float = 1.0
    extents: list[float] | None = None
    icon: str | None = None
    current_value: int | None = None
    max_value: int | None = None
    indicator_interval: int | None = None
    events_data: list[dict[str, any]] | None = None
    player_to_color: dict[str, str] | None = None
    visible_start_ms: int = 0
    visible_end_ms: int = 0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    formatted_text: str | None = None
