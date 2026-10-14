import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from lfdata.video import (
    AudioMatchConfig,
    AudioMatchDiagnostic,
    AudioMatcher,
    AudioMatchResult,
    load_sound_config,
)


def _create_synthetic_wav(
    file_path: str,
    duration_sec: float,
    sample_rate: int = 22050,
    chirp_start_ms: int | None = None,
    chirp_duration_ms: int = 400,
    chirp_f0: float = 1200.0,
    chirp_f1: float = 2400.0,
) -> None:
    total_samples = int(duration_sec * sample_rate)
    # Background noise
    rng = np.random.default_rng(seed=42)
    audio = rng.normal(0, 0.05, total_samples)

    if chirp_start_ms is not None:
        start_sample = int((chirp_start_ms / 1000.0) * sample_rate)
        chirp_samples = int((chirp_duration_ms / 1000.0) * sample_rate)
        t_chirp = np.linspace(0, chirp_duration_ms / 1000.0, chirp_samples)
        # Linear frequency chirp
        chirp_dur_sec = chirp_duration_ms / 1000.0
        phase = (
            2
            * np.pi
            * (
                chirp_f0 * t_chirp
                + (chirp_f1 - chirp_f0) * (t_chirp**2) / (2 * chirp_dur_sec)
            )
        )
        chirp = np.sin(phase)
        end_sample = min(total_samples, start_sample + chirp_samples)
        actual_len = end_sample - start_sample
        audio[start_sample:end_sample] += chirp[:actual_len] * 0.8

    # Normalize to 16-bit PCM
    scaled = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    wavfile.write(file_path, sample_rate, scaled)


def test_audio_match_result_properties() -> None:
    result = AudioMatchResult(timestamp_ms=2500, confidence=0.88)
    assert result.timestamp_ms == 2500
    assert result.confidence == 0.88
    assert result.timestamp_sec == 2.5


def test_synthetic_audio_single_match() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target.wav')
        ref_wav = os.path.join(tmpdir, 'ref.wav')

        # Clean reference chirp: 400 ms without background noise
        sample_rate = 22050
        duration = 0.4
        t = np.linspace(0, duration, int(duration * sample_rate))
        phase = 2 * np.pi * (1000.0 * t + 1500.0 * (t**2) / (2 * duration))
        ref_audio = np.sin(phase)
        wavfile.write(ref_wav, sample_rate, np.int16(ref_audio * 32767))

        # Target: 4.0s with background noise and chirp at 1500 ms
        t_target = np.linspace(0, 4.0, int(4.0 * sample_rate))
        target_audio = np.random.normal(0, 0.08, len(t_target))
        insert_idx = int(1.5 * sample_rate)
        end_idx = insert_idx + len(ref_audio)
        target_audio[insert_idx:end_idx] += ref_audio * 1.5
        wavfile.write(
            target_wav,
            sample_rate,
            np.int16(np.clip(target_audio, -1.0, 1.0) * 32767),
        )

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)
        results = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.5,
        )

        assert len(results) >= 1
        best_match = results[0]
        # Detected time within 30ms of ground truth (1500 ms)
        assert abs(best_match.timestamp_ms - 1500) < 30
        assert best_match.confidence > 0.55


def test_synthetic_audio_multiple_matches() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_multi.wav')
        ref_wav = os.path.join(tmpdir, 'ref.wav')

        sample_rate = 22050
        duration = 0.3
        t = np.linspace(0, duration, int(duration * sample_rate))
        phase = 2 * np.pi * (1000.0 * t + 2000.0 * (t**2) / (2 * duration))
        ref_audio = np.sin(phase)
        wavfile.write(ref_wav, sample_rate, np.int16(ref_audio * 32767))

        # Target with chirps at 1000 ms and 3000 ms
        target_audio = np.random.normal(0, 0.05, int(5.0 * sample_rate))
        s1 = int(1.0 * sample_rate)
        s2 = int(3.0 * sample_rate)
        target_audio[s1 : s1 + len(ref_audio)] += ref_audio * 1.2
        target_audio[s2 : s2 + len(ref_audio)] += ref_audio * 1.0

        wavfile.write(
            target_wav,
            sample_rate,
            np.int16(np.clip(target_audio, -1.0, 1.0) * 32767),
        )

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)
        results = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.5,
            min_interval_ms=500,
        )

        assert len(results) >= 2
        detected_times = [r.timestamp_ms for r in results[:2]]
        assert any(abs(t - 1000) < 30 for t in detected_times)
        assert any(abs(t - 3000) < 30 for t in detected_times)
        # Results must be sorted descending by confidence
        assert results[0].confidence >= results[1].confidence


def test_synthetic_audio_no_match() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'noise.wav')
        ref_wav = os.path.join(tmpdir, 'ref.wav')

        _create_synthetic_wav(
            ref_wav,
            duration_sec=0.4,
            chirp_start_ms=0,
            chirp_duration_ms=400,
            chirp_f0=3000.0,
            chirp_f1=4000.0,
        )
        # Pure noise target, no chirp
        _create_synthetic_wav(target_wav, duration_sec=2.0)

        matcher = AudioMatcher()
        results = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.85,
        )
        assert len(results) == 0


def test_file_not_found_errors() -> None:
    matcher = AudioMatcher()
    with pytest.raises(FileNotFoundError):
        matcher.match('nonexistent_video.mp4', 'ref.wav')

    with (
        tempfile.NamedTemporaryFile(suffix='.wav') as tmp,
        pytest.raises(FileNotFoundError),
    ):
        matcher.match(tmp.name, 'nonexistent_ref.wav')


def test_target_shorter_than_reference_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        short_wav = os.path.join(tmpdir, 'short.wav')
        long_wav = os.path.join(tmpdir, 'long.wav')

        _create_synthetic_wav(short_wav, duration_sec=0.5)
        _create_synthetic_wav(long_wav, duration_sec=2.0)

        matcher = AudioMatcher()
        with pytest.raises(ValueError):
            matcher.match(short_wav, long_wav)


def test_max_matches_limit() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target.wav')
        ref_wav = os.path.join(tmpdir, 'ref.wav')

        _create_synthetic_wav(
            ref_wav,
            duration_sec=0.3,
            chirp_start_ms=0,
            chirp_duration_ms=300,
        )
        _create_synthetic_wav(
            target_wav,
            duration_sec=3.0,
            chirp_start_ms=1000,
            chirp_duration_ms=300,
        )

        matcher = AudioMatcher()
        results = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.2,
            max_matches=1,
        )
        assert len(results) <= 1


def test_search_window_start_and_end_ms() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_window.wav')
        ref_wav = os.path.join(tmpdir, 'ref.wav')

        _create_synthetic_wav(
            ref_wav,
            duration_sec=0.3,
            chirp_start_ms=0,
            chirp_duration_ms=300,
        )
        # Chirp at 2000 ms
        _create_synthetic_wav(
            target_wav,
            duration_sec=5.0,
            chirp_start_ms=2000,
            chirp_duration_ms=300,
        )

        matcher = AudioMatcher()
        # Search only within 1000ms to 3500ms
        results = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.5,
            start_ms=1000,
            end_ms=3500,
        )
        assert len(results) >= 1
        best_match = results[0]
        # Should be offset to absolute timestamp ~2000ms
        assert abs(best_match.timestamp_ms - 2000) < 30


def test_gopro_reference_match_if_available() -> None:
    gopro_path = Path(r'E:\Videos\Laserforce\070526\GX011044.MP4')
    ref_path = (
        Path(r'C:\Users\ebomi\dev\Python\laserforce_ranking\assets\sm5')
        / 'audio'
        / 'Effect'
        / 'General Quarters.wav'
    )
    if not gopro_path.exists() or not ref_path.exists():
        pytest.skip(
            'GoPro video or reference sound not present on this machine.'
        )

    matcher = AudioMatcher()
    # Scan first 60 seconds of GoPro video with frequency bounds
    matches = matcher.match(
        video_or_audio_path=gopro_path,
        reference_sound_path=ref_path,
        start_ms=0,
        end_ms=60000,
        freq_min_hz=1400,
        freq_max_hz=2400,
    )

    assert len(matches) > 0
    top_match = matches[0]
    # Sound starts at ~20.2s (within 20s mark, no later than 21s)
    assert 20000 <= top_match.timestamp_ms <= 21000
    assert top_match.confidence > 0.25

    # Verify that the false-positive voice at ~43.6s is rejected
    match_timestamps = [m.timestamp_ms for m in matches]
    assert not any(43000 <= ts <= 44500 for ts in match_timestamps)


def test_cli_main(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'cli_target.wav')
        ref_wav = os.path.join(tmpdir, 'cli_ref.wav')

        # 400ms chirp at 1000ms
        sample_rate = 22050
        duration = 0.4
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * (1000.0 * t + 1000.0 * (t**2)))
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(3.0 * sample_rate), dtype=np.float32)
        target[int(1.0 * sample_rate) : int(1.0 * sample_rate) + len(chirp)] = (
            chirp
        )
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        from unittest.mock import patch

        from lfdata.video.audio_matcher import main

        test_args = ['audio_matcher.py', target_wav, ref_wav, '--json']
        with patch('sys.argv', test_args):
            main()

        captured = capsys.readouterr()
        assert 'timestamp_ms' in captured.out
        assert '1000' in captured.out or '998' in captured.out


def test_load_sound_config_valid() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'sound.yaml')
        ref_wav = os.path.join(tmpdir, 'ref.wav')
        with open(ref_wav, 'w') as f:
            f.write('')

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(
                f'name: test_sound\n'
                f'reference_sound_path: {ref_wav}\n'
                f'freq_min_hz: 1200.0\n'
                f'freq_max_hz: 2400.0\n'
                f'threshold: 0.35\n'
            )

        cfg = load_sound_config(config_file)
        assert cfg.reference_sound_path == str(Path(ref_wav).resolve())
        assert cfg.freq_min_hz == 1200.0
        assert cfg.freq_max_hz == 2400.0
        assert cfg.threshold == 0.35


def test_load_sound_config_relative_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sounds_dir = Path(tmpdir) / 'sounds'
        sounds_dir.mkdir(parents=True, exist_ok=True)
        (sounds_dir / 'alert.wav').touch()
        config_file = os.path.join(tmpdir, 'sound.yaml')
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(
                'name: test_sound\nreference_sound_path: sounds/alert.wav\n'
            )

        cfg = load_sound_config(config_file)
        expected_ref = str((Path(tmpdir) / 'sounds' / 'alert.wav').resolve())
        assert cfg.reference_sound_path == expected_ref
        assert cfg.threshold == 0.2
        assert cfg.freq_min_hz is None
        assert cfg.freq_max_hz is None


def test_load_sound_config_errors() -> None:
    with pytest.raises(FileNotFoundError):
        load_sound_config('non_existent_config.yaml')

    with tempfile.TemporaryDirectory() as tmpdir:
        invalid_yaml = os.path.join(tmpdir, 'invalid.yaml')
        with open(invalid_yaml, 'w', encoding='utf-8') as f:
            f.write('- just\n- a\n- list\n')
        with pytest.raises(ValueError, match='Invalid YAML configuration'):
            load_sound_config(invalid_yaml)

        missing_ref = os.path.join(tmpdir, 'missing_ref.yaml')
        with open(missing_ref, 'w', encoding='utf-8') as f:
            f.write('name: alert\nfreq_min_hz: 1000\n')
        with pytest.raises(ValueError, match='Missing required field'):
            load_sound_config(missing_ref)

        missing_sound_file = os.path.join(tmpdir, 'missing_sound.yaml')
        with open(missing_sound_file, 'w', encoding='utf-8') as f:
            f.write(
                'name: alert\nreference_sound_path: non_existent_sound.wav\n'
            )
        with pytest.raises(
            FileNotFoundError, match='Reference sound file not found'
        ):
            load_sound_config(missing_sound_file)


def test_match_with_config() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target.wav')
        ref_wav = os.path.join(tmpdir, 'ref.wav')
        config_file = os.path.join(tmpdir, 'sound.yaml')

        sample_rate = 22050
        duration = 0.4
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * (1200.0 * t + 800.0 * (t**2)))
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(2.5 * sample_rate), dtype=np.float32)
        target[int(0.8 * sample_rate) : int(0.8 * sample_rate) + len(chirp)] = (
            chirp
        )
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(
                f'name: test_chirp\n'
                f'reference_sound_path: {ref_wav}\n'
                f'freq_min_hz: 1000.0\n'
                f'freq_max_hz: 2500.0\n'
                f'threshold: 0.3\n'
            )

        matcher = AudioMatcher()
        # Test passing path string
        results_from_path = matcher.match_with_config(target_wav, config_file)
        assert len(results_from_path) >= 1
        assert abs(results_from_path[0].timestamp_ms - 800) < 30

        # Test passing AudioMatchConfig instance with override
        cfg_obj = AudioMatchConfig(
            reference_sound_path=ref_wav,
            freq_min_hz=1000.0,
            freq_max_hz=2500.0,
            threshold=0.2,
        )
        results_from_obj = matcher.match_with_config(
            target_wav, cfg_obj, threshold=0.4
        )
        assert len(results_from_obj) >= 1
        assert abs(results_from_obj[0].timestamp_ms - 800) < 30


def test_cli_main_with_config(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'cli_target.wav')
        ref_wav = os.path.join(tmpdir, 'cli_ref.wav')
        config_file = os.path.join(tmpdir, 'sound.yaml')

        sample_rate = 22050
        duration = 0.4
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * (1000.0 * t + 1000.0 * (t**2)))
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(3.0 * sample_rate), dtype=np.float32)
        target[int(1.0 * sample_rate) : int(1.0 * sample_rate) + len(chirp)] = (
            chirp
        )
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(
                f'name: test_sound\n'
                f'reference_sound_path: {ref_wav}\n'
                f'freq_min_hz: 800.0\n'
                f'freq_max_hz: 2500.0\n'
                f'threshold: 0.3\n'
            )

        from unittest.mock import patch

        from lfdata.video.audio_matcher import main

        # Invoke CLI with --config instead of reference WAV positional argument
        test_args = [
            'audio_matcher.py',
            target_wav,
            '--config',
            config_file,
            '--json',
        ]
        with patch('sys.argv', test_args):
            main()

        captured = capsys.readouterr()
        assert 'timestamp_ms' in captured.out
        assert '1000' in captured.out or '998' in captured.out


def test_cli_main_error_without_ref_or_config() -> None:
    from unittest.mock import patch

    from lfdata.video.audio_matcher import main

    test_args = ['audio_matcher.py', 'video.mp4']
    with patch('sys.argv', test_args), pytest.raises(SystemExit):
        main()


def test_cli_main_error_video_not_found(tmp_path: Path) -> None:
    from unittest.mock import patch

    from lfdata.video.audio_matcher import main

    ref_file = tmp_path / 'ref.wav'
    ref_file.touch()
    test_args = [
        'audio_matcher.py',
        str(tmp_path / 'missing_video.mp4'),
        str(ref_file),
    ]
    with (
        patch('sys.argv', test_args),
        pytest.raises(FileNotFoundError, match='Video file not found'),
    ):
        main()


def test_cli_main_error_ref_not_found(tmp_path: Path) -> None:
    from unittest.mock import patch

    from lfdata.video.audio_matcher import main

    video_file = tmp_path / 'video.mp4'
    video_file.touch()
    test_args = [
        'audio_matcher.py',
        str(video_file),
        str(tmp_path / 'missing_ref.wav'),
    ]
    with (
        patch('sys.argv', test_args),
        pytest.raises(FileNotFoundError, match='Reference sound not found'),
    ):
        main()


def test_audio_match_diagnostic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_diag.wav')
        ref_wav = os.path.join(tmpdir, 'ref_diag.wav')

        sample_rate = 22050
        duration = 0.3
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * (1200.0 * t + 800.0 * (t**2)))
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(3.0 * sample_rate), dtype=np.float32)
        chirp_start = int(1.2 * sample_rate)
        target[chirp_start : chirp_start + len(chirp)] = chirp
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)
        matches, diag = matcher.match_diagnostic(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            expected_timestamp_ms=1200,
            tolerance_ms=100,
            threshold=0.3,
        )

        assert isinstance(diag, AudioMatchDiagnostic)
        assert len(matches) >= 1
        assert abs(matches[0].timestamp_ms - 1200) < 30
        assert diag.expected_peak_raw_correlation is not None
        assert diag.expected_peak_confidence is not None
        assert diag.expected_peak_confidence > 0.5
        if diag.top_false_positive_confidence is not None:
            assert (
                diag.top_false_positive_confidence
                < diag.expected_peak_confidence
            )


def test_template_duration_ms_cropping() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_crop.wav')
        ref_wav = os.path.join(tmpdir, 'ref_crop.wav')

        sample_rate = 22050
        # Reference is 1.0s: first 400ms is chirp, remaining 600ms is silence
        t_ref = np.linspace(0, 1.0, int(1.0 * sample_rate))
        chirp = np.sin(2 * np.pi * 1500.0 * t_ref[: int(0.4 * sample_rate)])
        ref_data = np.zeros_like(t_ref)
        ref_data[: len(chirp)] = chirp
        wavfile.write(ref_wav, sample_rate, np.int16(ref_data * 32767))

        # Target only contains the 400ms chirp at 1000ms
        target = np.zeros(int(3.0 * sample_rate), dtype=np.float32)
        target[sample_rate : sample_rate + len(chirp)] = chirp
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)
        # Without crop, full 1.0s template includes silence, lowering match
        # With crop to 400ms, only the chirp is matched
        matches = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.5,
            template_duration_ms=400,
        )

        assert len(matches) >= 1
        assert abs(matches[0].timestamp_ms - 1000) < 30
        assert matches[0].confidence > 0.7


def test_min_energy_ratio_gating() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_gate.wav')
        ref_wav = os.path.join(tmpdir, 'ref_gate.wav')

        sample_rate = 22050
        dur = 0.3
        t = np.linspace(0, dur, int(dur * sample_rate))
        chirp = np.sin(2 * np.pi * 1800.0 * t)
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        # High energy chirp at 1500ms, low energy quiet noise at 500ms
        target = np.zeros(int(3.0 * sample_rate), dtype=np.float32)
        # Tiny chirp amplitude 0.005 at 500ms
        tiny_start = int(0.5 * sample_rate)
        target[tiny_start : tiny_start + len(chirp)] = chirp * 0.005
        # Full chirp at 1500ms
        full_start = int(1.5 * sample_rate)
        target[full_start : full_start + len(chirp)] = chirp * 1.0
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)
        # Without energy ratio, tiny chirp may yield high normalized corr
        # With min_energy_ratio=0.1, the tiny chirp is heavily scaled down
        matches_gated = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.3,
            min_energy_ratio=0.1,
        )

        assert len(matches_gated) == 1
        assert abs(matches_gated[0].timestamp_ms - 1500) < 30


def test_match_config_yaml_with_template_duration_and_energy_ratio() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_cfg.wav')
        ref_wav = os.path.join(tmpdir, 'ref_cfg.wav')
        cfg_file = os.path.join(tmpdir, 'sound.yaml')

        sample_rate = 22050
        dur = 0.4
        t = np.linspace(0, dur, int(dur * sample_rate))
        chirp = np.sin(2 * np.pi * 1600.0 * t)
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(2.0 * sample_rate), dtype=np.float32)
        target[sample_rate : sample_rate + len(chirp)] = chirp
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        with open(cfg_file, 'w', encoding='utf-8') as f:
            f.write(
                f"reference_sound_path: '{ref_wav}'\n"
                f'threshold: 0.3\n'
                f'template_duration_ms: 400\n'
                f'min_energy_ratio: 0.05\n'
            )

        cfg = load_sound_config(cfg_file)
        assert cfg.template_duration_ms == 400
        assert cfg.min_energy_ratio == 0.05

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)
        matches = matcher.match_with_config(
            video_or_audio_path=target_wav,
            config=cfg,
        )
        assert len(matches) >= 1
        assert abs(matches[0].timestamp_ms - 1000) < 30


def test_cluster_sequence_matches_empty_and_single() -> None:
    matcher = AudioMatcher()
    assert matcher.cluster_sequence_matches(matches=[]) == []

    single = [AudioMatchResult(timestamp_ms=5000, confidence=0.75)]
    clustered = matcher.cluster_sequence_matches(matches=single)
    assert len(clustered) == 1
    assert clustered[0].timestamp_ms == 5000
    assert clustered[0].confidence == 0.75


def test_cluster_sequence_matches_consecutive_blasts() -> None:
    matcher = AudioMatcher()
    # 3 blasts at ~950ms spacing, blast 3 has highest confidence
    matches = [
        AudioMatchResult(timestamp_ms=125345, confidence=0.643),
        AudioMatchResult(timestamp_ms=124410, confidence=0.510),
        AudioMatchResult(timestamp_ms=123464, confidence=0.286),
    ]
    clustered = matcher.cluster_sequence_matches(matches=matches)
    assert len(clustered) == 1
    # Earliest blast timestamp is selected with peak confidence
    assert clustered[0].timestamp_ms == 123464
    assert clustered[0].confidence == 0.643


def test_cluster_sequence_matches_missed_intermediate_blast() -> None:
    matcher = AudioMatcher()
    # Blast 2 missed: gap between Blast 1 and Blast 3 is 1900ms (1600-2300ms)
    matches = [
        AudioMatchResult(timestamp_ms=2900, confidence=0.82),
        AudioMatchResult(timestamp_ms=1000, confidence=0.35),
    ]
    clustered = matcher.cluster_sequence_matches(matches=matches)
    assert len(clustered) == 1
    assert clustered[0].timestamp_ms == 1000
    assert clustered[0].confidence == 0.82


def test_cluster_sequence_matches_multiple_clusters_and_sorting() -> None:
    matcher = AudioMatcher()
    matches = [
        # Cluster A at ~1000ms, peak confidence 0.6
        AudioMatchResult(timestamp_ms=1000, confidence=0.4),
        AudioMatchResult(timestamp_ms=1950, confidence=0.6),
        # Cluster B at ~50000ms, peak confidence 0.9
        AudioMatchResult(timestamp_ms=50000, confidence=0.5),
        AudioMatchResult(timestamp_ms=50950, confidence=0.9),
    ]
    clustered = matcher.cluster_sequence_matches(matches=matches)
    assert len(clustered) == 2
    # Sorted by peak confidence descending: Cluster B (0.9) before Cluster A (0.6)
    assert clustered[0].timestamp_ms == 50000
    assert clustered[0].confidence == 0.9
    assert clustered[1].timestamp_ms == 1000
    assert clustered[1].confidence == 0.6


def test_cluster_sequence_matches_span_limit_and_custom_bounds() -> None:
    matcher = AudioMatcher()
    matches = [
        AudioMatchResult(timestamp_ms=1000, confidence=0.5),
        AudioMatchResult(timestamp_ms=1800, confidence=0.6),
        AudioMatchResult(timestamp_ms=2600, confidence=0.7),
        AudioMatchResult(timestamp_ms=3400, confidence=0.8),
    ]
    # With max_cluster_span_ms=2000, 2600ms is span 1600 (ok), 3400ms is span 2400 (> 2000)
    clustered = matcher.cluster_sequence_matches(
        matches=matches,
        min_step_ms=700,
        max_step_ms=900,
        max_gap_missed_ms=1900,
        max_cluster_span_ms=2000,
    )
    assert len(clustered) == 2
    # First cluster: 1000..2600 with peak 0.7
    assert clustered[0].timestamp_ms == 3400
    assert clustered[0].confidence == 0.8
    assert clustered[1].timestamp_ms == 1000
    assert clustered[1].confidence == 0.7


def test_match_with_cluster_sequence_synthetic_audio() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_cluster.wav')
        ref_wav = os.path.join(tmpdir, 'ref_blast.wav')

        sample_rate = 22050
        duration = 0.3
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * 1500.0 * t)
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        rng = np.random.default_rng(seed=42)
        target = rng.normal(0, 0.15, int(5.0 * sample_rate)).astype(np.float32)
        # Blast 1 at 1000ms (weaker, amplitude 0.25)
        s1 = int(1.0 * sample_rate)
        target[s1 : s1 + len(chirp)] += chirp * 0.25
        # Blast 2 at 1950ms (amplitude 0.6)
        s2 = int(1.95 * sample_rate)
        target[s2 : s2 + len(chirp)] += chirp * 0.6
        # Blast 3 at 2900ms (stronger, amplitude 1.8)
        s3 = int(2.9 * sample_rate)
        target[s3 : s3 + len(chirp)] += chirp * 1.8

        wavfile.write(
            target_wav,
            sample_rate,
            np.int16(np.clip(target, -1.0, 1.0) * 32767),
        )

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)

        # Without cluster_sequence, max_matches=1 picks the strongest blast (Blast 3 ~2900ms)
        unclustered = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.3,
            min_interval_ms=500,
            max_matches=1,
            cluster_sequence=False,
        )
        assert len(unclustered) == 1
        assert abs(unclustered[0].timestamp_ms - 2900) < 30

        # With cluster_sequence, max_matches=1 groups them and picks Blast 1 (~1000ms)
        clustered = matcher.match(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.3,
            min_interval_ms=500,
            max_matches=1,
            cluster_sequence=True,
        )
        assert len(clustered) == 1
        assert abs(clustered[0].timestamp_ms - 1000) < 30
        assert clustered[0].confidence > 0.5


def test_cli_main_cluster_sequence(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'cli_cluster.wav')
        ref_wav = os.path.join(tmpdir, 'cli_ref.wav')

        sample_rate = 22050
        duration = 0.3
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * 1400.0 * t)
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(4.5 * sample_rate), dtype=np.float32)
        # Blast 1 at 1000ms (amplitude 0.5)
        s1 = int(1.0 * sample_rate)
        target[s1 : s1 + len(chirp)] = chirp * 0.5
        # Blast 2 at 1950ms (amplitude 1.0)
        s2 = int(1.95 * sample_rate)
        target[s2 : s2 + len(chirp)] = chirp * 1.0
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        from unittest.mock import patch

        from lfdata.video.audio_matcher import main

        test_args = [
            'audio_matcher.py',
            target_wav,
            ref_wav,
            '--cluster-sequence',
            '--max-matches',
            '1',
            '--json',
        ]
        with patch('sys.argv', test_args):
            main()

        import json

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 1
        # Earliest blast ~1000ms selected
        assert abs(data[0]['timestamp_ms'] - 1000) < 30


def test_cli_main_template_duration_override(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'cli_target.wav')
        ref_wav = os.path.join(tmpdir, 'cli_ref.wav')
        cfg_file = os.path.join(tmpdir, 'sound.yaml')

        sample_rate = 22050
        duration = 0.4
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * 1500.0 * t)
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(3.0 * sample_rate), dtype=np.float32)
        target[sample_rate : sample_rate + len(chirp)] = chirp
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        with open(cfg_file, 'w', encoding='utf-8') as f:
            f.write(
                f"reference_sound_path: '{ref_wav}'\n"
                f'threshold: 0.3\n'
                f'template_duration_ms: 200\n'
            )

        from unittest.mock import patch

        from lfdata.video.audio_matcher import main

        # Test overriding template_duration_ms with 0 (disabling crop)
        test_args = [
            'audio_matcher.py',
            target_wav,
            '--config',
            cfg_file,
            '--template-duration-ms',
            '0',
            '--json',
        ]
        with patch('sys.argv', test_args):
            main()

        captured = capsys.readouterr()
        assert 'timestamp_ms' in captured.out


def test_combine_two_stage_matches() -> None:
    matcher = AudioMatcher()
    # Case 1: Stage 1 and Stage 2 align within 1500ms
    s1 = [AudioMatchResult(timestamp_ms=1010, confidence=0.35)]
    s2 = [AudioMatchResult(timestamp_ms=1000, confidence=0.88)]
    combined = matcher._combine_two_stage_matches(
        stage1_matches=s1,
        stage2_matches=s2,
        alignment_tolerance_ms=1500,
    )
    assert len(combined) == 1
    # Exact anchor of Stage 1 (1010) with peak confidence (0.88)
    assert combined[0].timestamp_ms == 1010
    assert combined[0].confidence == 0.88

    # Case 2: Stage 1 has no match -> returns Stage 2
    combined_no_s1 = matcher._combine_two_stage_matches(
        stage1_matches=[],
        stage2_matches=s2,
    )
    assert len(combined_no_s1) == 1
    assert combined_no_s1[0].timestamp_ms == 1000
    assert combined_no_s1[0].confidence == 0.88

    # Case 3: Stage 2 has no match -> returns Stage 1
    combined_no_s2 = matcher._combine_two_stage_matches(
        stage1_matches=s1,
        stage2_matches=[],
    )
    assert len(combined_no_s2) == 1
    assert combined_no_s2[0].timestamp_ms == 1010
    assert combined_no_s2[0].confidence == 0.35

    # Case 4: Not aligned (> 1500ms) -> stronger match is first
    s1_far = [AudioMatchResult(timestamp_ms=50000, confidence=0.4)]
    s2_far = [AudioMatchResult(timestamp_ms=1000, confidence=0.9)]
    combined_far = matcher._combine_two_stage_matches(
        stage1_matches=s1_far,
        stage2_matches=s2_far,
        alignment_tolerance_ms=1500,
    )
    assert len(combined_far) == 2
    assert combined_far[0].timestamp_ms == 1000
    assert combined_far[0].confidence == 0.9
    assert combined_far[1].timestamp_ms == 50000
    assert combined_far[1].confidence == 0.4


def test_match_two_stage_synthetic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'target_twostage.wav')
        ref_wav = os.path.join(tmpdir, 'ref_twostage.wav')

        sample_rate = 22050
        # Reference has 2 chirps at 0ms and 950ms
        dur_ref = 1.3
        ref_audio = np.zeros(int(dur_ref * sample_rate), dtype=np.float32)
        chirp_dur = 0.3
        t_c = np.linspace(0, chirp_dur, int(chirp_dur * sample_rate))
        chirp = np.sin(2 * np.pi * 1600.0 * t_c)
        ref_audio[: len(chirp)] = chirp
        s2_ref = int(0.95 * sample_rate)
        ref_audio[s2_ref : s2_ref + len(chirp)] = chirp
        wavfile.write(
            ref_wav,
            sample_rate,
            np.int16(np.clip(ref_audio, -1.0, 1.0) * 32767),
        )

        # Target has the same 2 chirps starting at 1200ms
        target_audio = np.zeros(int(4.0 * sample_rate), dtype=np.float32)
        start_idx = int(1.2 * sample_rate)
        target_audio[start_idx : start_idx + len(ref_audio)] = ref_audio
        wavfile.write(
            target_wav,
            sample_rate,
            np.int16(np.clip(target_audio, -1.0, 1.0) * 32767),
        )

        matcher = AudioMatcher(sample_rate=22050, hop_length=256)
        results = matcher.match_two_stage(
            video_or_audio_path=target_wav,
            reference_sound_path=ref_wav,
            threshold=0.3,
            template_duration_ms=400,
            max_matches=1,
        )

        assert len(results) == 1
        assert abs(results[0].timestamp_ms - 1200) < 30
        assert results[0].confidence > 0.5


def test_cli_main_two_stage(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_wav = os.path.join(tmpdir, 'cli_ts_target.wav')
        ref_wav = os.path.join(tmpdir, 'cli_ts_ref.wav')

        sample_rate = 22050
        duration = 0.3
        t = np.linspace(0, duration, int(duration * sample_rate))
        chirp = np.sin(2 * np.pi * 1500.0 * t)
        wavfile.write(ref_wav, sample_rate, np.int16(chirp * 32767))

        target = np.zeros(int(3.0 * sample_rate), dtype=np.float32)
        target[sample_rate : sample_rate + len(chirp)] = chirp
        wavfile.write(target_wav, sample_rate, np.int16(target * 32767))

        from unittest.mock import patch

        from lfdata.video.audio_matcher import main

        test_args = [
            'audio_matcher.py',
            target_wav,
            ref_wav,
            '--two-stage',
            '--max-matches',
            '1',
            '--json',
        ]
        with patch('sys.argv', test_args):
            main()

        import json

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 1
        assert abs(data[0]['timestamp_ms'] - 1000) < 30
