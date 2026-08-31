import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np
import pytest
from scipy.io import wavfile

from lfdata.video.audio_benchmark import (
    AudioBenchmarkRunner,
    AudioTestCase,
    BenchmarkSummary,
    SoundDefinition,
    TestCaseEvaluationResult,
    TuningResult,
    main,
)
from lfdata.video.audio_matcher import AudioMatchResult, AudioMatcher


def _create_synthetic_chirp(
    file_path: str,
    sample_rate: int = 22050,
    duration_s: float = 0.3,
    start_freq_hz: float = 1200.0,
    end_freq_hz: float = 2200.0,
) -> None:
    t = np.linspace(0, duration_s, int(duration_s * sample_rate))
    freq_slope = (end_freq_hz - start_freq_hz) / duration_s
    phase = 2 * np.pi * (start_freq_hz * t + 0.5 * freq_slope * (t**2))
    audio = np.sin(phase)
    wavfile.write(file_path, sample_rate, np.int16(audio * 32767))


def _create_synthetic_target(
    file_path: str,
    ref_path: str,
    insert_timestamps_ms: list[int],
    total_duration_s: float = 4.0,
    sample_rate: int = 22050,
    noise_level: float = 0.05,
) -> None:
    _, ref_data = wavfile.read(ref_path)
    ref_float = ref_data.astype(np.float32) / 32768.0

    target = np.random.normal(
        0, noise_level, int(total_duration_s * sample_rate)
    ).astype(np.float32)

    for ts_ms in insert_timestamps_ms:
        idx = int((ts_ms / 1000.0) * sample_rate)
        if idx + len(ref_float) <= len(target):
            target[idx : idx + len(ref_float)] += ref_float

    clamped = np.clip(target, -1.0, 1.0)
    wavfile.write(file_path, sample_rate, np.int16(clamped * 32767))


def test_audio_test_case_dataclass() -> None:
    tc = AudioTestCase(
        video_path='video.mp4',
        expected_timestamp_ms=1500,
        tolerance_ms=300,
        search_start_ms=1000,
        search_end_ms=2000,
        description='Test case 1',
    )
    assert tc.video_path == 'video.mp4'
    assert tc.expected_timestamp_ms == 1500
    assert tc.tolerance_ms == 300
    assert tc.search_start_ms == 1000
    assert tc.search_end_ms == 2000
    assert tc.description == 'Test case 1'


def test_sound_definition_yaml_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / 'test_config.yaml'
        sound_def = SoundDefinition(
            name='game_start',
            reference_sound_path='buzzer.wav',
            freq_min_hz=1400.0,
            freq_max_hz=2400.0,
            threshold=0.25,
            description='Game start siren',
            test_cases=[
                AudioTestCase(
                    video_path='v1.mp4',
                    expected_timestamp_ms=20000,
                    tolerance_ms=400,
                    description='POV 1',
                )
            ],
        )

        runner = AudioBenchmarkRunner()
        runner.save_to_yaml(sound_def, config_path)

        loaded = runner.load_from_yaml(config_path)
        assert loaded.name == 'game_start'
        assert loaded.freq_min_hz == 1400.0
        assert loaded.freq_max_hz == 2400.0
        assert loaded.threshold == 0.25
        assert len(loaded.test_cases) == 1
        assert loaded.test_cases[0].expected_timestamp_ms == 20000
        assert loaded.test_cases[0].tolerance_ms == 400


def test_yaml_load_missing_file_raises() -> None:
    runner = AudioBenchmarkRunner()
    with pytest.raises(FileNotFoundError):
        runner.load_from_yaml('non_existent_path.yaml')


def test_yaml_load_missing_fields_raises() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_yaml = Path(tmpdir) / 'bad.yaml'
        bad_yaml.write_text('description: incomplete\n', encoding='utf-8')

        runner = AudioBenchmarkRunner()
        with pytest.raises(ValueError, match="Missing required field 'name'"):
            runner.load_from_yaml(bad_yaml)


def test_evaluate_single_test_case_success() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target_file = os.path.join(tmpdir, 'target.wav')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(
            target_file, ref_file, insert_timestamps_ms=[1500]
        )

        sound_def = SoundDefinition(
            name='siren',
            reference_sound_path=ref_file,
            freq_min_hz=1000.0,
            freq_max_hz=2400.0,
            threshold=0.2,
        )
        test_case = AudioTestCase(
            video_path=target_file,
            expected_timestamp_ms=1500,
            tolerance_ms=100,
        )

        runner = AudioBenchmarkRunner()
        result = runner.evaluate_test_case(sound_def, test_case)

        assert result.passed is True
        assert result.detected_timestamp_ms is not None
        assert abs(result.detected_timestamp_ms - 1500) <= 50
        assert result.error_ms is not None
        assert abs(result.error_ms) <= 50
        assert result.confidence is not None
        assert result.confidence > 0.5


def test_evaluate_missing_video_fails_gracefully() -> None:
    sound_def = SoundDefinition(
        name='siren',
        reference_sound_path='dummy_ref.wav',
    )
    test_case = AudioTestCase(
        video_path='missing_video.mp4',
        expected_timestamp_ms=5000,
    )
    runner = AudioBenchmarkRunner()
    result = runner.evaluate_test_case(sound_def, test_case)

    assert result.passed is False
    assert result.detected_timestamp_ms is None
    assert 'not found' in result.message.lower()


def test_evaluate_multiple_test_cases_summary() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target1 = os.path.join(tmpdir, 'target1.wav')
        target2 = os.path.join(tmpdir, 'target2.wav')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(
            target1, ref_file, insert_timestamps_ms=[1000]
        )
        _create_synthetic_target(
            target2, ref_file, insert_timestamps_ms=[2500]
        )

        sound_def = SoundDefinition(
            name='chirp',
            reference_sound_path=ref_file,
            freq_min_hz=1000.0,
            freq_max_hz=2400.0,
            threshold=0.2,
            test_cases=[
                AudioTestCase(
                    video_path=target1,
                    expected_timestamp_ms=1000,
                    tolerance_ms=100,
                ),
                AudioTestCase(
                    video_path=target2,
                    expected_timestamp_ms=2500,
                    tolerance_ms=100,
                ),
            ],
        )

        runner = AudioBenchmarkRunner()
        summary = runner.evaluate(sound_def)

        assert summary.total_cases == 2
        assert summary.passed_cases == 2
        assert summary.accuracy == 1.0
        assert summary.mean_error_ms is not None
        assert summary.mean_error_ms < 50.0


def test_tune_parameter_sweep() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target = os.path.join(tmpdir, 'target.wav')

        # Chirp from 1400 to 2200 Hz
        _create_synthetic_chirp(
            ref_file, start_freq_hz=1400.0, end_freq_hz=2200.0
        )
        _create_synthetic_target(target, ref_file, insert_timestamps_ms=[1200])

        sound_def = SoundDefinition(
            name='tuned_sound',
            reference_sound_path=ref_file,
            test_cases=[
                AudioTestCase(
                    video_path=target,
                    expected_timestamp_ms=1200,
                    tolerance_ms=100,
                )
            ],
        )

        runner = AudioBenchmarkRunner()
        tuning = runner.tune(
            sound_def=sound_def,
            min_freq_candidates=[1000.0, 1400.0],
            max_freq_candidates=[2200.0, 2600.0],
            threshold_candidates=[0.2],
        )

        assert tuning.best_accuracy == 1.0
        assert tuning.best_mean_error_ms is not None
        assert tuning.best_mean_error_ms < 50.0
        assert tuning.best_freq_min_hz is not None


def test_cli_evaluate_and_tune(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target = os.path.join(tmpdir, 'target.wav')
        config_path = os.path.join(tmpdir, 'config.yaml')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(target, ref_file, insert_timestamps_ms=[1000])

        sound_def = SoundDefinition(
            name='cli_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1000.0,
            freq_max_hz=2400.0,
            threshold=0.2,
            test_cases=[
                AudioTestCase(
                    video_path=target,
                    expected_timestamp_ms=1000,
                    tolerance_ms=100,
                )
            ],
        )
        runner = AudioBenchmarkRunner()
        runner.save_to_yaml(sound_def, config_path)

        # Test CLI evaluate
        with patch('sys.argv', ['audio_benchmark.py', 'evaluate', config_path]):
            main()

        out_eval = capsys.readouterr().out
        assert 'Passed: 1/1 (100.0%)' in out_eval
        assert '[PASS]' in out_eval

        # Test CLI evaluate with --json
        with patch(
            'sys.argv',
            ['audio_benchmark.py', 'evaluate', config_path, '--json'],
        ):
            main()

        out_json = capsys.readouterr().out
        assert '"passed_cases": 1' in out_json

        # Test CLI tune
        with patch('sys.argv', ['audio_benchmark.py', 'tune', config_path]):
            main()

        out_tune = capsys.readouterr().out
        assert 'Best freq_min:' in out_tune
        assert 'Accuracy: 100.0%' in out_tune
