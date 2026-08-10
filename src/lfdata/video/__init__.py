"""Video generation and visualization for LF games.

Provides HUD rendering, element layouts, YouTube chapter generation, and image/video synthesis.

Usage example:
    from lfdata.video import VideoGenerator

    generator = VideoGenerator(game=game)
    generator.render_video(output_path='game.mp4')
"""

from lfdata.video.element import UIElement, UIElementStyle
from lfdata.video.generator import VisualElementGenerator
from lfdata.video.renderer import VideoGenerator
from lfdata.video.chapter import LFChapter, LFChapterGenerator

__all__ = [
    'VideoGenerator',
    'UIElement',
    'UIElementStyle',
    'VisualElementGenerator',
    'LFChapter',
    'LFChapterGenerator',
]
