from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from lfdata.__main__ import main


def test_main_no_args() -> None:
    with patch.object(sys, 'argv', ['lfdata']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_print_replay(capsys) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch.object(
        sys,
        'argv',
        ['lfdata', '--input_tdf', str(real_path), '--print_replay'],
    ):
        main()
        captured = capsys.readouterr()
        assert '* Mission Start *' in captured.out
        assert 'completes an achievement!' in captured.out


def test_main_state_at(capsys) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch.object(
        sys,
        'argv',
        ['lfdata', '--input_tdf', str(real_path), '--state_at', '5000'],
    ):
        main()
        captured = capsys.readouterr()
        assert 'Game State at 5000 ms:' in captured.out
        assert 'Teams:' in captured.out
        assert 'Players:' in captured.out


def test_main_video_state_at(capsys) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch.object(
        sys,
        'argv',
        ['lfdata', '--input_tdf', str(real_path), '--video_state_at', '5000'],
    ):
        main()
        captured = capsys.readouterr()
        assert 'HUD Elements at 5000 ms:' in captured.out
        assert 'Game Type: Space Marines 5 Tournament Edition' in captured.out
        assert 'Spec' in captured.out
        assert 'HP' not in captured.out
        assert '-' * 79 in captured.out


def test_main_image_at(tmp_path: Path) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch.object(
        sys,
        'argv',
        [
            'lfdata',
            '--input_tdf',
            str(real_path),
            '--image-outdir',
            str(tmp_path),
            '--image-at',
            '5000',
        ],
    ):
        main()
        expected_file = tmp_path / 'image_at_5000.png'
        assert expected_file.exists()


def test_main_video_frame_generation_range() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch(
        'lfdata.video.VideoGenerator._generate_frames'
    ) as mock_gen_frames:
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--video_player',
                'Cyborg',
                '--video_start_ms',
                '1000',
                '--video_end_ms',
                '2000',
            ],
        ):
            main()
            mock_gen_frames.assert_called_once()
            _, kwargs = mock_gen_frames.call_args
            assert kwargs['start_ms'] == 1000
            assert kwargs['end_ms'] == 2000


def test_main_video_out() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator.generate') as mock_generate:
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--video_player',
                'Cyborg',
                '--video_start_ms',
                '1000',
                '--video_end_ms',
                '2000',
                '--video_out',
                'output.mp4',
            ],
        ):
            main()
            mock_generate.assert_called_once_with(
                output_path='output.mp4',
                config_path=None,
                video_start_ms=1000,
                video_end_ms=2000,
                video_player='Cyborg',
                fps=None,
                use_pipe=True,
                alpha_output_path=None,
                pregame_delay_ms=None,
            )


def test_main_video_out_fps() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator.generate') as mock_generate:
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--video_player',
                'Cyborg',
                '--video_start_ms',
                '1000',
                '--video_end_ms',
                '2000',
                '--video_out',
                'output.mp4',
                '--fps',
                '30',
            ],
        ):
            main()
            mock_generate.assert_called_once_with(
                output_path='output.mp4',
                config_path=None,
                video_start_ms=1000,
                video_end_ms=2000,
                video_player='Cyborg',
                fps=30,
                use_pipe=True,
                alpha_output_path=None,
                pregame_delay_ms=None,
            )


def test_main_video_out_no_pipe() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator.generate') as mock_generate:
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--video_player',
                'Cyborg',
                '--video_start_ms',
                '1000',
                '--video_end_ms',
                '2000',
                '--video_out',
                'output.mp4',
                '--no_pipe',
            ],
        ):
            main()
            mock_generate.assert_called_once_with(
                output_path='output.mp4',
                config_path=None,
                video_start_ms=1000,
                video_end_ms=2000,
                video_player='Cyborg',
                fps=None,
                use_pipe=False,
                alpha_output_path=None,
                pregame_delay_ms=None,
            )


def test_main_alpha_video_out_validation() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch.object(
        sys,
        'argv',
        [
            'lfdata',
            '--input_tdf',
            str(real_path),
            '--alpha_video_out',
            'alpha.mp4',
        ],
    ):
        with pytest.raises(SystemExit):
            main()


def test_main_alpha_video_out_generation() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator.generate') as mock_generate:
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--video_out',
                'output.mp4',
                '--alpha_video_out',
                'alpha.mp4',
            ],
        ):
            main()
            mock_generate.assert_called_once_with(
                output_path='output.mp4',
                config_path=None,
                video_start_ms=0,
                video_end_ms=None,
                video_player=None,
                fps=None,
                use_pipe=True,
                alpha_output_path='alpha.mp4',
                pregame_delay_ms=None,
            )


def test_main_state_interval(capsys) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch.object(
        sys,
        'argv',
        [
            'lfdata',
            '--input_tdf',
            str(real_path),
            '--state_start_ms',
            '800000',
            '--state_interval_ms',
            '20000',
        ],
    ):
        main()
        captured = capsys.readouterr()
        assert 'Game State at 800000 ms:' in captured.out
        assert 'Game State at 820000 ms:' in captured.out
        assert 'Game State at 840000 ms:' in captured.out
        assert 'Game State at 860000 ms:' in captured.out
        assert 'Game State at 880000 ms:' in captured.out
        assert 'Game State at 900000 ms:' in captured.out
        assert 'Game State at 920000 ms:' not in captured.out


def test_main_state_interval_with_end(capsys) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch.object(
        sys,
        'argv',
        [
            'lfdata',
            '--input_tdf',
            str(real_path),
            '--state_start_ms',
            '1000',
            '--state_end_ms',
            '3000',
            '--state_interval_ms',
            '1000',
        ],
    ):
        main()
        captured = capsys.readouterr()
        assert 'Game State at 1000 ms:' in captured.out
        assert 'Game State at 2000 ms:' in captured.out
        assert 'Game State at 3000 ms:' in captured.out
        assert 'Game State at 4000 ms:' not in captured.out


def test_main_config_video_out() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator.generate') as mock_generate:
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--config',
                'test_config.yaml',
                '--video_out',
                'output.mp4',
            ],
        ):
            main()
            mock_generate.assert_called_once_with(
                output_path='output.mp4',
                config_path='test_config.yaml',
                video_start_ms=0,
                video_end_ms=None,
                video_player=None,
                fps=None,
                use_pipe=True,
                alpha_output_path=None,
                pregame_delay_ms=None,
            )


def test_main_config_image_at(tmp_path: Path) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator._load_config') as mock_load_config:
        mock_load_config.return_value = {
            'resolution': [1920, 1080],
            'fps': 60,
        }
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--config',
                'test_config.yaml',
                '--image-outdir',
                str(tmp_path),
                '--image-at',
                '5000',
            ],
        ):
            main()
            mock_load_config.assert_called_with('test_config.yaml')


def test_main_config_video_state_at() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator._load_config') as mock_load_config:
        mock_load_config.return_value = {}
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--config',
                'test_config.yaml',
                '--video_state_at',
                '5000',
            ],
        ):
            main()
            mock_load_config.assert_called_with('test_config.yaml')


def test_main_pregame_delay() -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    with patch('lfdata.video.VideoGenerator.generate') as mock_generate:
        with patch.object(
            sys,
            'argv',
            [
                'lfdata',
                '--input_tdf',
                str(real_path),
                '--video_out',
                'output.mp4',
                '--pregame_delay_ms',
                '5000',
            ],
        ):
            main()
            mock_generate.assert_called_once_with(
                output_path='output.mp4',
                config_path=None,
                video_start_ms=0,
                video_end_ms=None,
                video_player=None,
                fps=None,
                use_pipe=True,
                alpha_output_path=None,
                pregame_delay_ms=5000,
            )


def test_main_chapters_out(tmp_path: Path) -> None:
    real_path = Path(__file__).parent.parent / 'assets' / 'sm5_sanitized.tdf'
    out_file = tmp_path / 'chapters.txt'
    with patch.object(
        sys,
        'argv',
        [
            'lfdata',
            '--input_tdf',
            str(real_path),
            '--chapters_out',
            str(out_file),
            '--pregame_delay_ms',
            '5000',
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        assert out_file.exists()
        content = out_file.read_text(encoding='utf-8')
        assert '00:00 Warmup' in content
