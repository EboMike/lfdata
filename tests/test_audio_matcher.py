import os
from pathlib import Path
import tempfile
import numpy as np
import pytest
from scipy.io import wavfile

from lfdata.video import AudioMatcher, AudioMatchResult


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
        phase = 2 * np.pi * (
            chirp_f0 * t_chirp
            + (chirp_f1 - chirp_f0) * (t_chirp**2) / (2 * chirp_dur_sec)
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
        wavfile.write(
            ref_wav, sample_rate, np.int16(ref_audio * 32767)
        )

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
        wavfile.write(
            ref_wav, sample_rate, np.int16(ref_audio * 32767)
        )

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

    with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
        with pytest.raises(FileNotFoundError):
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
