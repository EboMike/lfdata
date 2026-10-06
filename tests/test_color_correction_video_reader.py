"""Tests for VideoReader class."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import pytest

from lfdata.color_correction.video_reader import VideoReader


@pytest.fixture
def sample_video_path(tmp_path: Path) -> Path:
    video_file = tmp_path / 'sample_test_video.mp4'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(video_file), fourcc, 30.0, (160, 120))
    for i in range(30):
        frame = np.full((120, 160, 3), fill_value=i * 5, dtype=np.uint8)
        out.write(frame)
    out.release()
    return video_file


def test_video_reader_initial_state() -> None:
    reader = VideoReader()
    assert reader.video_path is None
    assert reader.duration_ms == 0
    assert reader.fps == 0.0
    assert reader.frame_count == 0


def test_video_reader_load_missing_file() -> None:
    reader = VideoReader()
    with pytest.raises(FileNotFoundError, match='Video file not found'):
        reader.load('nonexistent_video_path.mp4')


def test_video_reader_load_invalid_open(tmp_path: Path) -> None:
    dummy_file = tmp_path / 'dummy.mp4'
    dummy_file.write_text('not a real video')
    reader = VideoReader()
    with pytest.raises(ValueError):
        reader.load(dummy_file)


def test_video_reader_load_invalid_fps_or_frames(tmp_path: Path) -> None:
    dummy_file = tmp_path / 'fake.mp4'
    dummy_file.write_text('test')

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.side_effect = lambda prop: 0.0

    with patch('cv2.VideoCapture', return_value=mock_cap):
        reader = VideoReader()
        with pytest.raises(ValueError, match='Invalid video properties'):
            reader.load(dummy_file)


def test_video_reader_load_and_extract_frame(sample_video_path: Path) -> None:
    reader = VideoReader()
    dur_ms = reader.load(sample_video_path)
    assert dur_ms > 0
    assert reader.duration_ms == dur_ms
    assert reader.fps == 30.0
    assert reader.frame_count == 30
    assert reader.width == 160
    assert reader.height == 120

    img = reader.get_frame_at(timestamp_ms=500)
    assert img.size == (160, 120)

    reader.close()
    assert reader.video_path is None
    assert reader.duration_ms == 0


def test_video_reader_get_frame_before_load() -> None:
    reader = VideoReader()
    with pytest.raises(RuntimeError, match='No video file currently loaded'):
        reader.get_frame_at(timestamp_ms=100)


def test_video_reader_frame_read_failure(sample_video_path: Path) -> None:
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.side_effect = lambda prop: (
        30.0 if prop == cv2.CAP_PROP_FPS else 30
    )
    mock_cap.read.return_value = (False, None)

    with patch('cv2.VideoCapture', return_value=mock_cap):
        reader = VideoReader()
        reader.load(sample_video_path)
        with pytest.raises(RuntimeError, match='Failed to extract video frame'):
            reader.get_frame_at(timestamp_ms=200)
