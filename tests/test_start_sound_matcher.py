from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from scipy.io import wavfile

from lfdata.video.audio_matcher import (
    AudioMatchConfig,
    AudioMatcher,
    AudioMatchResult,
    load_sound_config,
)
from lfdata.video.start_sound_matcher import (
    GameStartDetector,
    StartSoundMatcher,
)


def _load_wav_mono(path: Path, target_sr: int = 22050) -> np.ndarray:
    sr, data = wavfile.read(str(path))
    if data.dtype == np.int16:
        samples = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        samples = data.astype(np.float32) / 2147483648.0
    else:
        samples = data.astype(np.float32)
    if samples.ndim > 1:
        samples = np.mean(samples, axis=1)
    if sr != target_sr:
        num_out = int(round(len(samples) * target_sr / sr))
        x_old = np.linspace(0.0, 1.0, len(samples), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num_out, endpoint=False)
        samples = np.interp(x_new, x_old, samples).astype(np.float32)
    return samples


def test_list_sample_files_real_assets() -> None:
    matcher = StartSoundMatcher()
    files = matcher.list_sample_files(
        start_sounds_dir=Path('assets/sm5/start_sounds')
    )
    names = [f.name for f in files]
    assert 'aliens_day_in_the_corps.wav' in names
    assert 'aliens_express_elevator_to_hell.wav' in names
    assert 'aliens_tough_hombres.wav' in names
    assert 'ready_arming_now.wav' in names


def test_list_sample_files_missing_dir() -> None:
    matcher = StartSoundMatcher()
    with pytest.raises(FileNotFoundError):
        matcher.list_sample_files(
            start_sounds_dir=Path('assets/sm5/does_not_exist')
        )


def test_match_samples_full_sample_end_time() -> None:
    sample_path = Path('assets/sm5/start_sounds/ready_arming_now.wav')
    sample_audio = _load_wav_mono(path=sample_path)
    sr = 22050

    rng = np.random.default_rng(42)
    target = rng.normal(0.0, 0.01, size=sr * 6).astype(np.float32)
    onset_sample = sr * 2
    target[onset_sample : onset_sample + len(sample_audio)] += sample_audio

    expected_game_start_ms = int(
        round((onset_sample + len(sample_audio)) / sr * 1000)
    )

    audio_matcher = AudioMatcher(sample_rate=sr)
    with patch.object(
        audio_matcher,
        'load_audio',
        side_effect=lambda file_path, start_ms=None, end_ms=None: (
            _load_wav_mono(path=file_path, target_sr=sr)
        ),
    ):
        matcher = StartSoundMatcher(audio_matcher=audio_matcher)
        results = matcher.match_samples(
            target_audio=target,
            sample_paths=[sample_path],
            threshold=0.2,
        )

    assert len(results) == 1
    assert results[0].method == 'start_sounds/ready_arming_now.wav'
    assert 0.2 <= results[0].confidence <= 1.0
    assert abs(results[0].timestamp_ms - expected_game_start_ms) <= 150


def test_match_samples_partial_late_recording() -> None:
    sample_path = Path('assets/sm5/start_sounds/aliens_tough_hombres.wav')
    sample_audio = _load_wav_mono(path=sample_path)
    sr = 22050

    # Simulate GoPro starting 3.5s into the 7.0s sample
    keep_samples = int(sr * 3.5)
    tail_audio = sample_audio[-keep_samples:]

    rng = np.random.default_rng(7)
    target = rng.normal(0.0, 0.01, size=sr * 6).astype(np.float32)
    target[:keep_samples] += tail_audio
    expected_game_start_ms = int(round(keep_samples / sr * 1000))

    audio_matcher = AudioMatcher(sample_rate=sr)
    with patch.object(
        audio_matcher,
        'load_audio',
        side_effect=lambda file_path, start_ms=None, end_ms=None: (
            _load_wav_mono(path=file_path, target_sr=sr)
        ),
    ):
        matcher = StartSoundMatcher(audio_matcher=audio_matcher)
        results = matcher.match_samples(
            target_audio=target,
            sample_paths=[sample_path],
            threshold=0.2,
        )

    assert len(results) == 1
    assert results[0].method == 'start_sounds/aliens_tough_hombres.wav'
    assert abs(results[0].timestamp_ms - expected_game_start_ms) <= 200
    assert results[0].confidence >= 0.4


def test_match_samples_with_overlapping_speech_noise() -> None:
    sample_path = Path('assets/sm5/start_sounds/aliens_tough_hombres.wav')
    sample_audio = _load_wav_mono(path=sample_path)
    sr = 22050

    rng = np.random.default_rng(99)
    target = rng.normal(0.0, 0.01, size=sr * 10).astype(np.float32)
    onset_sample = sr * 1
    target[onset_sample : onset_sample + len(sample_audio)] += sample_audio

    # Overlay loud speech-like shout burst over a 1.2s window inside the sample
    shout_start = onset_sample + int(sr * 2.0)
    shout_len = int(sr * 1.2)
    t = np.arange(shout_len) / sr
    shout = 0.6 * np.sin(2.0 * np.pi * 320.0 * t) + 0.3 * rng.normal(
        0.0, 1.0, size=shout_len
    )
    target[shout_start : shout_start + shout_len] += shout.astype(np.float32)

    expected_game_start_ms = int(
        round((onset_sample + len(sample_audio)) / sr * 1000)
    )

    audio_matcher = AudioMatcher(sample_rate=sr)
    with patch.object(
        audio_matcher,
        'load_audio',
        side_effect=lambda file_path, start_ms=None, end_ms=None: (
            _load_wav_mono(path=file_path, target_sr=sr)
        ),
    ):
        matcher = StartSoundMatcher(audio_matcher=audio_matcher)
        results = matcher.match_samples(
            target_audio=target,
            sample_paths=[sample_path],
            threshold=0.2,
        )

    assert len(results) == 1
    assert abs(results[0].timestamp_ms - expected_game_start_ms) <= 200


def test_match_samples_no_match_on_silence() -> None:
    sample_path = Path('assets/sm5/start_sounds/ready_arming_now.wav')
    sr = 22050
    silence = np.zeros(sr * 4, dtype=np.float32)

    audio_matcher = AudioMatcher(sample_rate=sr)
    with patch.object(
        audio_matcher,
        'load_audio',
        side_effect=lambda file_path, start_ms=None, end_ms=None: (
            _load_wav_mono(path=file_path, target_sr=sr)
        ),
    ):
        matcher = StartSoundMatcher(audio_matcher=audio_matcher)
        results = matcher.match_samples(
            target_audio=silence,
            sample_paths=[sample_path],
            threshold=0.2,
        )

    assert results == []


def test_resolve_best_match_corroborated_boosts_confidence() -> None:
    detector = GameStartDetector(agreement_tolerance_ms=500)
    sample_res = AudioMatchResult(
        timestamp_ms=10200,
        confidence=0.72,
        method='start_sounds/aliens_tough_hombres.wav',
    )
    siren_res = AudioMatchResult(
        timestamp_ms=10350,
        confidence=0.65,
        method='siren',
    )
    best = detector.resolve_best_match(
        sample_matches=[sample_res],
        siren_matches=[siren_res],
    )
    assert best is not None
    assert best.timestamp_ms == 10200
    assert best.method == 'start_sounds/aliens_tough_hombres.wav'
    assert best.confidence > 0.72
    assert best.confidence <= 1.0


def test_resolve_best_match_siren_fallback() -> None:
    detector = GameStartDetector()
    siren_res = AudioMatchResult(
        timestamp_ms=15000,
        confidence=0.61,
        method='siren',
    )
    best = detector.resolve_best_match(
        sample_matches=[],
        siren_matches=[siren_res],
    )
    assert best == siren_res


def test_resolve_best_match_conflict_applies_penalty() -> None:
    detector = GameStartDetector(agreement_tolerance_ms=500)
    sample_res = AudioMatchResult(
        timestamp_ms=10000,
        confidence=0.70,
        method='start_sounds/ready_arming_now.wav',
    )
    siren_res = AudioMatchResult(
        timestamp_ms=25000,
        confidence=0.65,
        method='siren',
    )
    best = detector.resolve_best_match(
        sample_matches=[sample_res],
        siren_matches=[siren_res],
    )
    assert best is not None
    assert best.timestamp_ms == 10000
    assert best.method == 'start_sounds/ready_arming_now.wav'
    assert best.confidence == pytest.approx(0.70 * 0.8)


def test_resolve_best_match_none_when_empty() -> None:
    detector = GameStartDetector()
    result = detector.resolve_best_match(sample_matches=[], siren_matches=[])
    assert result is None


def test_load_sound_config_with_start_sounds_dir(tmp_path: Path) -> None:
    ref_wav = tmp_path / 'siren.wav'
    ref_wav.write_bytes(b'RIFF')
    sounds_dir = tmp_path / 'start_sounds'
    sounds_dir.mkdir()
    cfg_file = tmp_path / 'sound.yaml'
    cfg_file.write_text(
        'reference_sound_path: siren.wav\n'
        'start_sounds_dir: start_sounds\n'
        'threshold: 0.3\n',
        encoding='utf-8',
    )
    cfg = load_sound_config(config_path=cfg_file)
    assert cfg.start_sounds_dir == str(sounds_dir.resolve())
    assert cfg.threshold == 0.3


def test_audio_matcher_detect_game_start_delegates(tmp_path: Path) -> None:
    media = tmp_path / 'game.wav'
    media.write_bytes(b'RIFF')
    ref = tmp_path / 'siren.wav'
    ref.write_bytes(b'RIFF')

    matcher = AudioMatcher()
    expected = AudioMatchResult(
        timestamp_ms=12345,
        confidence=0.88,
        method='siren',
    )
    with patch.object(
        matcher,
        'match',
        return_value=[expected],
    ):
        result = matcher.detect_game_start(
            video_or_audio_path=media,
            reference_sound_path=ref,
        )
    assert result == expected


def test_short_sample_finer_chunking_and_upper_band_resilience(
    tmp_path: Path,
) -> None:
    sample_rate = 22050
    dur_s = 1.2
    t = np.linspace(0, dur_s, int(dur_s * sample_rate), endpoint=False)
    # Wideband sample with energy in both 800 Hz and 3500-5500 Hz
    sample = (
        0.4 * np.sin(2 * np.pi * 800.0 * t)
        + 0.4 * np.sin(2 * np.pi * (3500.0 + 1500.0 * t) * t)
    ).astype(np.float32)

    start_dir = tmp_path / 'start_sounds'
    start_dir.mkdir()
    sample_path = start_dir / 'short_wide.wav'
    wavfile.write(sample_path, sample_rate, np.int16(sample * 32767))

    matcher = StartSoundMatcher(chunk_duration_ms=1500, chunk_step_ms=750)
    ms_per_frame = (
        matcher.audio_matcher.hop_length / matcher.audio_matcher.sample_rate
    ) * 1000.0
    spec = matcher._prepare_log_spectrogram(sample)
    chunks = matcher._build_sample_chunks(spec, ms_per_frame=ms_per_frame)
    # Short sample (1.2s < 1.5s) should still produce >= 3 overlapping chunks
    assert len(chunks) >= 3

    # Target recording: sample placed at 1000ms (game start = 2200ms),
    # with loud low-frequency interference (300-1100 Hz) over the entire
    # first half of the sample.
    target = np.zeros(int(4.0 * sample_rate), dtype=np.float32)
    s_idx = int(1.0 * sample_rate)
    target[s_idx : s_idx + len(sample)] += sample
    t_noise = np.linspace(0, 0.7, int(0.7 * sample_rate), endpoint=False)
    low_shout = 0.8 * np.sin(2 * np.pi * 500.0 * t_noise)
    target[s_idx : s_idx + len(low_shout)] += low_shout.astype(np.float32)

    results = matcher.match_samples(
        target_audio=target,
        sample_paths=[sample_path],
        threshold=0.25,
    )
    assert len(results) == 1
    assert abs(results[0].timestamp_ms - 2200) <= 150
