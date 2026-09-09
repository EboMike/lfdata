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
    ConfigurationSuggestion,
    SoundDefinition,
    TestCaseEvaluationResult,
    main,
)


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


def test_analyze_threshold_too_high() -> None:
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
            threshold=0.999,
            test_cases=[
                AudioTestCase(
                    video_path=target_file,
                    expected_timestamp_ms=1500,
                    tolerance_ms=100,
                )
            ],
        )

        runner = AudioBenchmarkRunner()
        analysis = runner.analyze(sound_def)

        assert analysis.passed_cases == 0
        assert analysis.total_cases == 1
        tc_an = analysis.case_analyses[0]
        assert tc_an.evaluation.passed is False
        assert tc_an.root_cause == 'THRESHOLD_TOO_HIGH'
        assert tc_an.diagnostic is not None
        assert tc_an.diagnostic.expected_peak_confidence is not None
        assert tc_an.diagnostic.expected_peak_confidence > 0.4
        assert analysis.reconciling_threshold is not None
        assert analysis.reconciling_threshold < 0.999


def test_analyze_diagnoses_vocal_penalty_and_false_positive() -> None:
    from lfdata.video.audio_matcher import AudioMatchDiagnostic

    runner = AudioBenchmarkRunner()
    sound_def = SoundDefinition(
        name='siren',
        reference_sound_path='ref.wav',
        threshold=0.5,
    )

    # 1. Vocal penalty suppression
    tc1 = AudioTestCase(video_path='v1.mp4', expected_timestamp_ms=1000)
    diag1 = AudioMatchDiagnostic(
        expected_timestamp_ms=1000,
        tolerance_ms=100,
        expected_peak_timestamp_ms=1000,
        expected_peak_confidence=0.35,
        expected_peak_raw_correlation=0.75,
        expected_peak_vocal_penalty=0.4,
        top_false_positive_timestamp_ms=500,
        top_false_positive_confidence=0.1,
        margin=0.25,
    )
    eval1 = TestCaseEvaluationResult(
        test_case=tc1,
        passed=False,
        detected_timestamp_ms=None,
        error_ms=None,
        confidence=None,
        top_false_positive_confidence=0.1,
        message='No match above threshold 0.5',
        diagnostic=diag1,
    )
    with patch.object(runner, 'evaluate_test_case', return_value=eval1):
        sound_def.test_cases = [tc1]
        analysis = runner.analyze(sound_def)
        assert analysis.case_analyses[0].root_cause == (
            'VOCAL_PENALTY_SUPPRESSION'
        )

    # 2. False positive dominance
    tc2 = AudioTestCase(
        video_path='v2.mp4', expected_timestamp_ms=1000, tolerance_ms=100
    )
    diag2 = AudioMatchDiagnostic(
        expected_timestamp_ms=1000,
        tolerance_ms=100,
        expected_peak_timestamp_ms=1000,
        expected_peak_confidence=0.6,
        expected_peak_raw_correlation=0.6,
        expected_peak_vocal_penalty=1.0,
        top_false_positive_timestamp_ms=5000,
        top_false_positive_confidence=0.8,
        margin=-0.2,
    )
    eval2 = TestCaseEvaluationResult(
        test_case=tc2,
        passed=False,
        detected_timestamp_ms=5000,
        error_ms=4000,
        confidence=0.8,
        top_false_positive_confidence=0.8,
        message='Error 4000ms exceeds tolerance 100ms',
        diagnostic=diag2,
    )
    with patch.object(runner, 'evaluate_test_case', return_value=eval2):
        sound_def.test_cases = [tc2]
        analysis = runner.analyze(sound_def)
        assert analysis.case_analyses[0].root_cause == (
            'FALSE_POSITIVE_DOMINANCE'
        )

    # 3. No signal
    tc3 = AudioTestCase(video_path='v3.mp4', expected_timestamp_ms=1000)
    diag3 = AudioMatchDiagnostic(
        expected_timestamp_ms=1000,
        tolerance_ms=100,
        expected_peak_timestamp_ms=None,
        expected_peak_confidence=None,
    )
    eval3 = TestCaseEvaluationResult(
        test_case=tc3,
        passed=False,
        detected_timestamp_ms=None,
        error_ms=None,
        confidence=None,
        top_false_positive_confidence=None,
        message='No match',
        diagnostic=diag3,
    )
    with patch.object(runner, 'evaluate_test_case', return_value=eval3):
        sound_def.test_cases = [tc3]
        analysis = runner.analyze(sound_def)
        assert analysis.case_analyses[0].root_cause == 'NO_SIGNAL'


def test_tune_adaptive_reconciliation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target1 = os.path.join(tmpdir, 'target1.wav')
        target2 = os.path.join(tmpdir, 'target2.wav')

        _create_synthetic_chirp(
            ref_file, start_freq_hz=1400.0, end_freq_hz=2200.0
        )
        _create_synthetic_target(
            target1, ref_file, insert_timestamps_ms=[1000], noise_level=0.02
        )
        _create_synthetic_target(
            target2, ref_file, insert_timestamps_ms=[2000], noise_level=0.02
        )

        sound_def = SoundDefinition(
            name='adaptive_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1400.0,
            freq_max_hz=2200.0,
            threshold=0.999,
            test_cases=[
                AudioTestCase(
                    video_path=target1,
                    expected_timestamp_ms=1000,
                    tolerance_ms=100,
                ),
                AudioTestCase(
                    video_path=target2,
                    expected_timestamp_ms=2000,
                    tolerance_ms=100,
                ),
            ],
        )

        runner = AudioBenchmarkRunner()
        # Candidate threshold is intentionally higher than chirp correlation
        # (~0.995). Adaptive reconciliation discovers reconciling threshold
        # (< 0.99) and successfully passes both cases.
        tuning = runner.tune(
            sound_def=sound_def,
            min_freq_candidates=[1400.0],
            max_freq_candidates=[2200.0],
            threshold_candidates=[0.999],
        )

        assert tuning.best_accuracy == 1.0
        assert tuning.best_threshold < 0.99
        assert tuning.best_mean_error_ms is not None
        assert tuning.best_mean_error_ms < 50.0


def test_cli_analyze_human_and_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target = os.path.join(tmpdir, 'target.wav')
        config_path = os.path.join(tmpdir, 'config.yaml')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(
            target, ref_file, insert_timestamps_ms=[1000]
        )

        sound_def = SoundDefinition(
            name='cli_analyze_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1000.0,
            freq_max_hz=2400.0,
            threshold=0.999,
            test_cases=[
                AudioTestCase(
                    video_path=target,
                    expected_timestamp_ms=1000,
                    tolerance_ms=100,
                    description='POV Test',
                )
            ],
        )
        runner = AudioBenchmarkRunner()
        runner.save_to_yaml(sound_def, config_path)

        # Test CLI analyze
        with patch('sys.argv', ['audio_benchmark.py', 'analyze', config_path]):
            main()

        out_text = capsys.readouterr().out
        assert 'Root Cause:' in out_text
        assert 'THRESHOLD_TOO_HIGH' in out_text
        assert 'Reconciling Threshold:' in out_text

        # Test CLI analyze --json
        with patch(
            'sys.argv',
            ['audio_benchmark.py', 'analyze', config_path, '--json'],
        ):
            main()

        out_json = capsys.readouterr().out
        assert '"passed_cases": 0' in out_json
        assert '"THRESHOLD_TOO_HIGH"' in out_json


def test_analyze_suggestions_generated() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target = os.path.join(tmpdir, 'target.wav')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(
            target, ref_file, insert_timestamps_ms=[1000]
        )

        sound_def = SoundDefinition(
            name='sug_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1000.0,
            freq_max_hz=2400.0,
            threshold=0.999,
            test_cases=[
                AudioTestCase(
                    video_path=target,
                    expected_timestamp_ms=1000,
                    tolerance_ms=100,
                )
            ],
        )
        runner = AudioBenchmarkRunner()
        analysis = runner.analyze(sound_def)

        assert len(analysis.suggestions) >= 1
        sug = analysis.suggestions[0]
        assert sug.name == 'Reconciling Threshold'
        assert sug.threshold is not None
        assert sug.threshold < 0.999
        assert 'Discovered threshold' in sug.rationale


def test_analyze_iterate_mode() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target1 = os.path.join(tmpdir, 'target1.wav')
        target2 = os.path.join(tmpdir, 'target2.wav')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(
            target1, ref_file, insert_timestamps_ms=[1000]
        )
        _create_synthetic_target(
            target2, ref_file, insert_timestamps_ms=[2000]
        )

        sound_def = SoundDefinition(
            name='iter_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1000.0,
            freq_max_hz=2400.0,
            threshold=0.999,
            test_cases=[
                AudioTestCase(
                    video_path=target1,
                    expected_timestamp_ms=1000,
                    tolerance_ms=100,
                ),
                AudioTestCase(
                    video_path=target2,
                    expected_timestamp_ms=2000,
                    tolerance_ms=100,
                ),
            ],
        )
        runner = AudioBenchmarkRunner()
        analysis = runner.analyze(sound_def, iterate=True)

        assert analysis.iteration_results is not None
        assert len(analysis.iteration_results) >= 2
        assert analysis.best_iteration is not None
        assert analysis.best_iteration.summary.accuracy == 1.0
        assert analysis.best_iteration.suggestion.threshold is not None
        assert analysis.best_iteration.suggestion.threshold < 0.999


def test_cli_analyze_iterate_and_save(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target = os.path.join(tmpdir, 'target.wav')
        config_path = os.path.join(tmpdir, 'config.yaml')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(
            target, ref_file, insert_timestamps_ms=[1000]
        )

        sound_def = SoundDefinition(
            name='cli_iter_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1000.0,
            freq_max_hz=2400.0,
            threshold=0.999,
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

        # 1. Test CLI analyze --iterate
        with patch(
            'sys.argv',
            ['audio_benchmark.py', 'analyze', config_path, '--iterate'],
        ):
            main()

        out_text = capsys.readouterr().out
        assert 'Suggested Configuration Changes:' in out_text
        assert 'Iteration Mode Results:' in out_text
        assert 'Recommended Best Configuration:' in out_text

        # 2. Test CLI analyze --iterate --save
        with patch(
            'sys.argv',
            [
                'audio_benchmark.py',
                'analyze',
                config_path,
                '--iterate',
                '--save',
            ],
        ):
            main()

        out_save = capsys.readouterr().out
        assert 'Updated config saved to' in out_save

        # Verify file was updated on disk
        updated_def = runner.load_from_yaml(config_path)
        assert updated_def.threshold < 0.999


def test_sound_definition_yaml_persistence_with_new_fields() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        config_path = os.path.join(tmpdir, 'config.yaml')
        _create_synthetic_chirp(ref_file)

        sound_def = SoundDefinition(
            name='new_fields_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1400.0,
            freq_max_hz=2400.0,
            threshold=0.25,
            template_duration_ms=800,
            min_energy_ratio=0.1,
            description='Test description',
        )
        runner = AudioBenchmarkRunner()
        runner.save_to_yaml(sound_def, config_path)

        loaded_def = runner.load_from_yaml(config_path)
        assert loaded_def.name == 'new_fields_sound'
        assert loaded_def.template_duration_ms == 800
        assert loaded_def.min_energy_ratio == 0.1
        assert loaded_def.threshold == 0.25


def test_configuration_suggestion_with_new_fields() -> None:
    sug = ConfigurationSuggestion(
        name='Crop and Gate',
        rationale='Testing new fields',
        template_duration_ms=800,
        min_energy_ratio=0.15,
    )
    assert sug.name == 'Crop and Gate'
    assert sug.template_duration_ms == 800
    assert sug.min_energy_ratio == 0.15


def test_benchmark_analyze_suggests_template_crop_for_long_reference() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'long_ref.wav')
        target = os.path.join(tmpdir, 'target.wav')

        # Create a 2.0s long reference audio (duration > 1.5s)
        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(duration * sample_rate))
        audio = np.sin(2 * np.pi * 1500.0 * t)
        wavfile.write(ref_file, sample_rate, np.int16(audio * 32767))

        _create_synthetic_target(
            target, ref_file, insert_timestamps_ms=[1000]
        )

        sound_def = SoundDefinition(
            name='long_sound',
            reference_sound_path=ref_file,
            freq_min_hz=1200.0,
            freq_max_hz=2000.0,
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
        analysis = runner.analyze(sound_def)

        # Verify Crop Template to 800ms suggestion is produced
        crop_sug = [
            s
            for s in analysis.suggestions
            if 'Crop Template to 800ms' in s.name
        ]
        assert len(crop_sug) >= 1
        assert crop_sug[0].template_duration_ms == 800


def test_cli_evaluate_and_analyze_with_duration_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, 'ref.wav')
        target = os.path.join(tmpdir, 'target.wav')
        config_path = os.path.join(tmpdir, 'config.yaml')

        _create_synthetic_chirp(ref_file)
        _create_synthetic_target(
            target, ref_file, insert_timestamps_ms=[1000]
        )

        sound_def = SoundDefinition(
            name='flag_test_sound',
            reference_sound_path=ref_file,
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

        with patch(
            'sys.argv',
            [
                'audio_benchmark.py',
                'evaluate',
                config_path,
                '--template-duration',
                '300',
                '--min-energy-ratio',
                '0.05',
            ],
        ):
            main()

        out = capsys.readouterr().out
        assert 'Passed: 1/1' in out




