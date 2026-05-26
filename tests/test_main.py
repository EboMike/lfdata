from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from lfdata.__main__ import main


def test_main_no_args() -> None:
    with patch.object(sys, "argv", ["lfdata"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_print_replay(capsys) -> None:
    real_path = Path(__file__).parent.parent / "assets" / "sm5_sanitized.tdf"
    with patch.object(
        sys,
        "argv",
        ["lfdata", "--input_tdf", str(real_path), "--print_replay"],
    ):
        main()
        captured = capsys.readouterr()
        assert "* Mission Start *" in captured.out
        assert "completes an achievement!" in captured.out


def test_main_state_at(capsys) -> None:
    real_path = Path(__file__).parent.parent / "assets" / "sm5_sanitized.tdf"
    with patch.object(
        sys,
        "argv",
        ["lfdata", "--input_tdf", str(real_path), "--state_at", "5000"],
    ):
        main()
        captured = capsys.readouterr()
        assert "Game State at 5000 ms:" in captured.out
        assert "Teams:" in captured.out
        assert "Players:" in captured.out


def test_main_video_state_at(capsys) -> None:
    real_path = Path(__file__).parent.parent / "assets" / "sm5_sanitized.tdf"
    with patch.object(
        sys,
        "argv",
        ["lfdata", "--input_tdf", str(real_path), "--video_state_at", "5000"],
    ):
        main()
        captured = capsys.readouterr()
        assert "HUD Elements at 5000 ms:" in captured.out
        assert "Game Type: Space Marines 5 Tournament Edition" in captured.out


def test_main_image_at(tmp_path: Path) -> None:
    real_path = Path(__file__).parent.parent / "assets" / "sm5_sanitized.tdf"
    with patch.object(
        sys,
        "argv",
        [
            "lfdata",
            "--input_tdf",
            str(real_path),
            "--image-outdir",
            str(tmp_path),
            "--image-at",
            "5000",
        ],
    ):
        main()
        expected_file = tmp_path / "image_at_5000.png"
        assert expected_file.exists()
