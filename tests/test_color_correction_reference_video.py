"""Unit tests for composite ReferenceVideo model."""

from __future__ import annotations

from unittest.mock import MagicMock
from PIL import Image

from lfdata.color_correction.reference_video import ReferenceVideo
from lfdata.color_correction.time_range import TimeRange


def test_reference_video_duration_calculation() -> None:
    ranges = [
        TimeRange(start_ms=1000, end_ms=3000),  # 2000 ms
        TimeRange(start_ms=5000, end_ms=8000),  # 3000 ms
    ]
    ref = ReferenceVideo(video_reader=None, ranges=ranges)
    assert ref.total_duration_ms == 5000


def test_reference_video_duration_empty_ranges() -> None:
    ref = ReferenceVideo(video_reader=None, ranges=[])
    assert ref.total_duration_ms == 0


def test_reference_video_timestamp_mapping() -> None:
    ranges = [
        TimeRange(start_ms=1000, end_ms=3000),  # Range 0: duration 2000 ms
        TimeRange(start_ms=5000, end_ms=8000),  # Range 1: duration 3000 ms
    ]
    ref = ReferenceVideo(video_reader=None, ranges=ranges)

    # Within first range:
    assert ref.get_source_timestamp_ms(composite_ms=0) == 1000
    assert ref.get_source_timestamp_ms(composite_ms=1500) == 2500

    # Within second range:
    assert ref.get_source_timestamp_ms(composite_ms=2000) == 5000
    assert ref.get_source_timestamp_ms(composite_ms=3500) == 6500

    # Beyond total duration loops via modulo:
    assert ref.get_source_timestamp_ms(composite_ms=5500) == 1500


def test_reference_video_timestamp_mapping_empty() -> None:
    ref = ReferenceVideo(video_reader=None, ranges=[])
    assert ref.get_source_timestamp_ms(composite_ms=1000) == 1000


def test_reference_video_get_frame() -> None:
    mock_reader = MagicMock()
    fake_frame = Image.new('RGB', (100, 100), color=(10, 20, 30))
    mock_reader.get_frame_at.return_value = fake_frame

    ranges = [TimeRange(start_ms=2000, end_ms=4000)]
    ref = ReferenceVideo(video_reader=mock_reader, ranges=ranges)

    frame = ref.get_frame(composite_ms=500)
    assert frame is fake_frame
    mock_reader.get_frame_at.assert_called_once_with(timestamp_ms=2500)


def test_reference_video_get_frame_no_reader() -> None:
    ranges = [TimeRange(start_ms=2000, end_ms=4000)]
    ref = ReferenceVideo(video_reader=None, ranges=ranges)
    assert ref.get_frame(composite_ms=500) is None
