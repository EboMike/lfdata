"""Tests for ColorAveragesBar and compute_frame_color_column."""

from pathlib import Path
from typing import Any
from unittest.mock import patch
import cv2
import numpy as np
import pytest


class DummyCanvas:
    """Mock Canvas widget for headless testing of ColorAveragesBar."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._options: dict[str, Any] = dict(kwargs)
        self.items: list[dict[str, Any]] = []

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, *args: Any, **kwargs: Any) -> None:
        pass

    def winfo_width(self) -> int:
        return 30

    def winfo_height(self) -> int:
        return 20

    def delete(self, *args: Any, **kwargs: Any) -> None:
        self.items.clear()

    def create_rectangle(self, *args: Any, **kwargs: Any) -> int:
        self.items.append({'type': 'rectangle', 'args': args, 'kwargs': kwargs})
        return len(self.items)

    def create_image(self, *args: Any, **kwargs: Any) -> int:
        self.items.append({'type': 'image', 'args': args, 'kwargs': kwargs})
        return len(self.items)

    def after(self, ms: int, func: Any = None, *args: Any) -> Any:
        if func is not None:
            return func(*args)
        return None


with patch('tkinter.Canvas', DummyCanvas):
    import sys

    sys.modules.pop('lfdata.color_correction.color_averages_bar', None)
    from lfdata.color_correction.color_averages_bar import (
        ColorAveragesBar,
        compute_frame_color_column,
    )


@pytest.fixture(autouse=True)
def patch_tkinter_canvas() -> Any:
    with patch('tkinter.Canvas', DummyCanvas):
        yield


@pytest.fixture
def synthetic_color_video(tmp_path: Path) -> Path:
    video_file = tmp_path / 'color_test_video.mp4'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(video_file), fourcc, 30.0, (16, 12))
    for _ in range(3):
        frame = np.zeros((12, 16, 3), dtype=np.uint8)
        frame[:6, :, 2] = 200  # Red channel in BGR
        frame[6:, :, 1] = 200  # Green channel in BGR
        writer.write(frame)
    writer.release()
    return video_file


def test_compute_frame_color_column_math() -> None:
    frame = np.zeros((100, 50, 3), dtype=np.uint8)
    frame[:50, :, :] = [255, 0, 0]  # Red top half
    frame[50:, :, :] = [0, 255, 0]  # Green bottom half

    target_height = 20
    col = compute_frame_color_column(frame=frame, height=target_height)

    assert col.shape == (20, 3)
    assert col.dtype == np.uint8
    assert col[0, 0] > 200
    assert col[0, 1] < 50
    assert col[19, 1] > 200
    assert col[19, 0] < 50


def test_compute_frame_color_column_invalid_height() -> None:
    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match='Target height must be >= 1'):
        compute_frame_color_column(frame=frame, height=0)


def test_compute_frame_color_column_invalid_frame() -> None:
    with pytest.raises(ValueError, match='Frame must be a non-empty'):
        compute_frame_color_column(frame=np.array([]), height=10)

    with pytest.raises(ValueError, match='Frame must be a non-empty'):
        compute_frame_color_column(frame=np.zeros((10, 10)), height=10)


def test_color_averages_bar_initial_state() -> None:
    bar = ColorAveragesBar(
        parent=DummyCanvas(),
        duration_ms=30000,
        update_interval_ms=1000,
    )
    assert bar.duration_ms == 30000
    assert bar.update_interval_ms == 1000
    assert bar.is_computing is False
    assert bar.computed_columns == 0


def test_color_averages_bar_redraw() -> None:
    bar = ColorAveragesBar(parent=DummyCanvas(), duration_ms=10000)
    bar.redraw()
    assert len(bar.items) >= 1


def test_color_averages_bar_computation_lifecycle(
    synthetic_color_video: Path,
) -> None:
    bar = ColorAveragesBar(
        parent=DummyCanvas(),
        duration_ms=500,
        update_interval_ms=50,
    )
    bar.start_computation(
        video_path=synthetic_color_video,
        duration_ms=500,
        fps=30.0,
        total_frames=3,
    )
    assert bar.is_computing is True

    if bar._worker_thread is not None:
        bar._worker_thread.join(timeout=0.5)

    assert bar.is_computing is False
    assert bar.computed_columns == bar.total_columns
    assert bar._buffer is not None


def test_color_averages_bar_cancel(
    synthetic_color_video: Path,
) -> None:
    bar = ColorAveragesBar(
        parent=DummyCanvas(),
        duration_ms=5000,
        update_interval_ms=50,
    )
    bar.start_computation(
        video_path=synthetic_color_video,
        duration_ms=5000,
    )
    assert bar.is_computing is True
    bar.cancel()
    assert bar.is_computing is False
    assert bar._cancel_event.is_set()


def test_color_averages_bar_progress_notification() -> None:
    bar = ColorAveragesBar(parent=DummyCanvas(), duration_ms=1000)
    test_snapshot = np.zeros((20, 10, 3), dtype=np.uint8)
    bar._notify_progress(snapshot=test_snapshot, computed=5, total=10)
    assert bar.computed_columns == 5
    assert bar.total_columns == 10
    assert bar._buffer is test_snapshot


def test_color_averages_bar_complete_notification() -> None:
    bar = ColorAveragesBar(parent=DummyCanvas(), duration_ms=1000)
    bar.is_computing = True
    test_snapshot = np.zeros((20, 10, 3), dtype=np.uint8)
    bar._notify_complete(snapshot=test_snapshot)
    assert bar.is_computing is False
    assert bar._buffer is test_snapshot
