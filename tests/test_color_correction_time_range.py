"""Tests for TimeRange dataclass and formatting functions."""

import pytest

from lfdata.color_correction.time_range import TimeRange


def test_time_range_properties() -> None:
    time_range = TimeRange(start_ms=1250, end_ms=5750)
    assert time_range.start_ms == 1250
    assert time_range.end_ms == 5750
    assert time_range.duration_ms == 4500


def test_time_range_validation_negative_start() -> None:
    with pytest.raises(ValueError, match='start_ms must be non-negative'):
        TimeRange(start_ms=-10, end_ms=100)


def test_time_range_validation_end_before_start() -> None:
    with pytest.raises(ValueError, match='cannot be before start_ms'):
        TimeRange(start_ms=5000, end_ms=2000)


def test_format_timestamp_ms() -> None:
    assert TimeRange.format_timestamp_ms(0) == '00:00.000'
    assert TimeRange.format_timestamp_ms(1250) == '00:01.250'
    assert TimeRange.format_timestamp_ms(65432) == '01:05.432'
    assert TimeRange.format_timestamp_ms(3661005) == '61:01.005'


def test_display_str() -> None:
    time_range = TimeRange(start_ms=1250, end_ms=5750)
    expected = '00:01.250 - 00:05.750 (4.500s)'
    assert time_range.display_str() == expected
