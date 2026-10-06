"""Video file loading and frame extraction utility.

This module provides the `VideoReader` class to open video files, extract their
total duration in milliseconds, and decode still images at specific timestamps.

Usage example:
    from lfdata.color_correction.video_reader import VideoReader

    reader = VideoReader()
    duration_ms = reader.load('reference.mp4')
    frame = reader.get_frame_at(timestamp_ms=1000)
    reader.close()
"""

from pathlib import Path
import cv2
from PIL import Image

from lfdata.model.constants.time import MS_PER_SECOND


class VideoReader:
    """Reads video metadata and extracts still frames at millisecond offsets.

    Attributes:
        video_path: Path of the loaded video file, or None if no video loaded.
        duration_ms: Total length of the video in milliseconds.
        fps: Frames per second of the loaded video.
        frame_count: Total number of frames in the video file.
        width: Pixel width of the video frames.
        height: Pixel height of the video frames.
    """

    video_path: Path | None = None
    duration_ms: int = 0
    fps: float = 0.0
    frame_count: int = 0
    width: int = 0
    height: int = 0

    def __init__(self) -> None:
        """Initializes an empty VideoReader with default state."""
        self.video_path: Path | None = None
        self.duration_ms: int = 0
        self.fps: float = 0.0
        self.frame_count: int = 0
        self.width: int = 0
        self.height: int = 0
        self._capture: cv2.VideoCapture | None = None

    def load(self, video_path: str | Path) -> int:
        """Opens a video file and calculates its duration in milliseconds.

        Inspects the video file, extracts frame rate and frame count, and
        stores dimensions and duration.

        Args:
            video_path: File system path to the target video file.

        Returns:
            int: The duration of the video in milliseconds.

        Raises:
            FileNotFoundError: If the specified video file does not exist.
            ValueError: If the file cannot be decoded as a valid video.

        Usage example:
            duration_ms = reader.load(video_path='clip.mp4')
        """
        path_obj = Path(video_path)
        if not path_obj.exists():
            raise FileNotFoundError(f'Video file not found: {video_path}')

        self.close()

        cap = cv2.VideoCapture(str(path_obj))
        if not cap.isOpened():
            cap.release()
            raise ValueError(f'Could not open video file: {video_path}')

        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps <= 0.0 or frame_count <= 0:
            cap.release()
            raise ValueError(
                f'Invalid video properties: fps={fps}, frames={frame_count}'
            )

        duration_ms = int((frame_count / fps) * MS_PER_SECOND)
        if duration_ms <= 0:
            cap.release()
            raise ValueError('Video duration must be greater than zero')

        self._capture = cap
        self.video_path = path_obj
        self.fps = fps
        self.frame_count = frame_count
        self.width = width
        self.height = height
        self.duration_ms = duration_ms

        return self.duration_ms

    def get_frame_at(self, timestamp_ms: int) -> Image.Image:
        """Extracts a still video frame as a PIL Image at the given timestamp.

        Seeks to the specified millisecond offset in the video and decodes
        the corresponding frame as an RGB PIL Image.

        Args:
            timestamp_ms: Time offset in milliseconds to seek and capture.

        Returns:
            Image.Image: Decoded RGB still image of the video frame.

        Raises:
            RuntimeError: If no video is loaded or frame decoding fails.

        Usage example:
            image = reader.get_frame_at(timestamp_ms=500)
        """
        if self._capture is None or not self._capture.isOpened():
            raise RuntimeError('No video file currently loaded.')

        clamped_ms = max(0, min(self.duration_ms, timestamp_ms))

        self._capture.set(cv2.CAP_PROP_POS_MSEC, float(clamped_ms))
        success, frame = self._capture.read()

        if not success or frame is None:
            # Fallback to seeking by frame index
            target_frame_idx = int((clamped_ms / MS_PER_SECOND) * self.fps)
            target_frame_idx = max(
                0, min(self.frame_count - 1, target_frame_idx)
            )
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
            success, frame = self._capture.read()

        if not success or frame is None:
            raise RuntimeError(
                f'Failed to extract video frame at {timestamp_ms} ms'
            )

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_frame)

    def close(self) -> None:
        """Releases the underlying video capture resources if open.

        Usage example:
            reader.close()
        """
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self.video_path = None
        self.duration_ms = 0
        self.fps = 0.0
        self.frame_count = 0
        self.width = 0
        self.height = 0
