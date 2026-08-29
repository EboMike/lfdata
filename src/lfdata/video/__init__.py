"""Video generation and visualization for LF games.

Provides HUD rendering, element layouts, YouTube chapter generation, audio
matching, and image/video synthesis.

Usage example:
    from lfdata.video import VideoGenerator

    generator = VideoGenerator(game=game)
    generator.render_video(output_path='game.mp4')
"""

from typing import TYPE_CHECKING, Any

from lfdata.video.element import UIElement, UIElementStyle
from lfdata.video.generator import VisualElementGenerator
from lfdata.video.renderer import VideoGenerator
from lfdata.video.chapter import LFChapter, LFChapterGenerator

if TYPE_CHECKING:
    from lfdata.video.audio_matcher import AudioMatcher, AudioMatchResult

__all__ = [
    'VideoGenerator',
    'UIElement',
    'UIElementStyle',
    'VisualElementGenerator',
    'LFChapter',
    'LFChapterGenerator',
    'AudioMatcher',
    'AudioMatchResult',
]


def __getattr__(name: str) -> Any:
    """Lazy imports audio matcher classes on first access.

    Args:
        name: Name of the attribute being requested.

    Returns:
        Any: Imported class or attribute.

    Raises:
        AttributeError: If attribute is not recognized.
    """
    if name == 'AudioMatcher':
        from lfdata.video.audio_matcher import AudioMatcher

        return AudioMatcher
    if name == 'AudioMatchResult':
        from lfdata.video.audio_matcher import AudioMatchResult

        return AudioMatchResult
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
