"""Reference video sequence composite model.

This module provides the `ReferenceVideo` class that combines a source video
reader with a sequence of timestamp ranges to create a single continuous
virtual reference video strung together from the selected ranges.

Usage example:
    from lfdata.color_correction.reference_video import ReferenceVideo
    from lfdata.color_correction.time_range import TimeRange
    from lfdata.color_correction.video_reader import VideoReader

    reader = VideoReader()
    reader.load('raw.mp4')
    ref_video = ReferenceVideo(
        video_reader=reader,
        ranges=[TimeRange(start_ms=1000, end_ms=4000)],
    )
    frame = ref_video.get_frame_at(ref_time_ms=500)
"""

from __future__ import annotations

from PIL import Image

from lfdata.color_correction.time_range import TimeRange
from lfdata.color_correction.video_reader import VideoReader


class ReferenceVideo:
    """Manages playback and frame extraction for composite reference ranges.

    Attributes:
        video_reader: Optional VideoReader instance decoding source frames.
        ranges: List of TimeRange intervals comprising the reference video.
    """

    def __init__(
        self,
        video_reader: VideoReader | None = None,
        ranges: list[TimeRange] | None = None,
    ) -> None:
        """Initializes a ReferenceVideo composite.

        Args:
            video_reader: The VideoReader decoding underlying video frames.
            ranges: The list of TimeRange clips included in the reference video.
        """
        self.video_reader: VideoReader | None = video_reader
        self.ranges: list[TimeRange] = (
            list(ranges) if ranges is not None else []
        )

    @property
    def is_valid(self) -> bool:
        """Returns True if a video reader is loaded and at least one range exists.

        Returns:
            bool: True if video can be previewed, False otherwise.
        """
        return (
            self.video_reader is not None
            and self.video_reader.duration_ms > 0
            and len(self.ranges) > 0
            and self.total_duration_ms > 0
        )

    @property
    def total_duration_ms(self) -> int:
        """Calculates total playback length across all reference ranges.

        Returns:
            int: Total duration of the strung-together ranges in milliseconds.
        """
        return sum(max(0, r.duration_ms) for r in self.ranges)

    def map_reference_time_to_source_time(self, ref_time_ms: int) -> int:
        """Maps a continuous reference timeline offset to a source timestamp.

        Args:
            ref_time_ms: Offset in milliseconds into the composite reference.

        Returns:
            int: The corresponding timestamp in milliseconds in the source video.

        Usage example:
            src_ms = ref_video.map_reference_time_to_source_time(1500)
        """
        if not self.ranges:
            return ref_time_ms

        tot_ms = self.total_duration_ms
        if tot_ms <= 0:
            return self.ranges[0].start_ms

        clamped_ref_ms = max(0, ref_time_ms % tot_ms)
        accum_ms = 0

        for r in self.ranges:
            dur = max(0, r.duration_ms)
            if accum_ms <= clamped_ref_ms < accum_ms + dur:
                offset_into_range = clamped_ref_ms - accum_ms
                return r.start_ms + offset_into_range
            accum_ms += dur

        return self.ranges[-1].end_ms

    def get_source_timestamp_ms(self, composite_ms: int) -> int:
        """Maps composite reference timestamp to source video timestamp.

        Args:
            composite_ms: Millisecond offset into reference video.

        Returns:
            int: Source video timestamp in milliseconds.

        Usage example:
            src_ms = ref_video.get_source_timestamp_ms(composite_ms=1500)
        """
        return self.map_reference_time_to_source_time(ref_time_ms=composite_ms)

    def get_frame_at(self, ref_time_ms: int) -> Image.Image:
        """Extracts a still frame from the reference video at the given timestamp.

        Args:
            ref_time_ms: Millisecond offset into the composite reference video.

        Returns:
            Image.Image: Decoded still RGB image of the reference video frame.

        Raises:
            RuntimeError: If no valid video reader is configured or video is empty.

        Usage example:
            image = ref_video.get_frame_at(ref_time_ms=1000)
        """
        if self.video_reader is None or not self.ranges:
            raise RuntimeError('Reference video is not configured.')

        source_time_ms = self.map_reference_time_to_source_time(ref_time_ms)
        return self.video_reader.get_frame_at(timestamp_ms=source_time_ms)

    def get_frame(self, composite_ms: int) -> Image.Image | None:
        """Extracts a frame or returns None if video reader is not configured.

        Args:
            composite_ms: Millisecond offset into composite reference video.

        Returns:
            Image.Image | None: Decoded still frame or None if not configured.

        Usage example:
            frame = ref_video.get_frame(composite_ms=500)
        """
        if self.video_reader is None or not self.ranges:
            return None
        return self.get_frame_at(ref_time_ms=composite_ms)
