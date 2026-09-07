"""Audio template matching for identifying reference sound effects in video.

This module provides tools to locate occurrences of a reference sound effect
(such as an arena horn, chime, or buzzer) inside video or audio files using 2D
normalized cross-correlation on audio spectrograms.

Usage example:
    from lfdata.video.audio_matcher import AudioMatcher

    matcher = AudioMatcher()
    results = matcher.match(
        video_or_audio_path='video.mp4',
        reference_sound_path='buzzer.wav',
        threshold=0.6,
    )
    for match in results:
        print(f'{match.timestamp_ms}ms: {match.confidence:.2f}')
"""

import argparse
import dataclasses
import json
import os
from pathlib import Path
import subprocess
import tempfile

try:
    import cv2
    import numpy as np
    from scipy.io import wavfile
    from scipy.signal import spectrogram
    import yaml
except ImportError as err:
    raise ImportError(
        'Audio matching requires numpy, scipy, opencv-python, and PyYAML. '
        'Install them using `pip install lfdata[video]`.'
    ) from err


@dataclasses.dataclass(frozen=True)
class AudioMatchConfig:
    """Configuration parameters loaded from a sound definition YAML file.

    Attributes:
        reference_sound_path: Path to the reference sound effect audio file.
        freq_min_hz: Optional lower frequency cutoff in Hz.
        freq_max_hz: Optional upper frequency cutoff in Hz.
        threshold: Minimum confidence score threshold (default: 0.2).
    """

    reference_sound_path: str
    freq_min_hz: float | None = None
    freq_max_hz: float | None = None
    threshold: float = 0.2


def load_sound_config(config_path: str | Path) -> AudioMatchConfig:
    """Loads sound configuration parameters from a YAML file.

    Resolves relative reference sound paths against the directory containing
    the configuration file.

    Args:
        config_path: Path to the YAML sound configuration file.

    Returns:
        AudioMatchConfig: Parsed configuration parameters.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If required fields are missing or the file is invalid YAML.
    """
    path = Path(config_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f'Config file not found: {path}')

    with open(path, 'r', encoding='utf-8') as file_obj:
        raw_data = yaml.safe_load(file_obj)

    if not isinstance(raw_data, dict):
        raise ValueError(f'Invalid YAML configuration in {path}')

    ref_path = raw_data.get('reference_sound_path')
    if not ref_path:
        raise ValueError(
            "Missing required field 'reference_sound_path' in config."
        )

    ref_path_obj = Path(ref_path)
    if not ref_path_obj.is_absolute():
        resolved_ref_path = str((path.parent / ref_path_obj).resolve())
    else:
        resolved_ref_path = str(ref_path_obj)

    raw_freq_min = raw_data.get('freq_min_hz')
    freq_min = float(raw_freq_min) if raw_freq_min is not None else None

    raw_freq_max = raw_data.get('freq_max_hz')
    freq_max = float(raw_freq_max) if raw_freq_max is not None else None

    threshold = float(raw_data.get('threshold', 0.2))

    return AudioMatchConfig(
        reference_sound_path=resolved_ref_path,
        freq_min_hz=freq_min,
        freq_max_hz=freq_max,
        threshold=threshold,
    )


@dataclasses.dataclass(frozen=True)
class AudioMatchResult:
    """Represents a candidate timestamp match with its confidence score.

    Attributes:
        timestamp_ms: Millisecond offset into the video where the sound starts.
        confidence: Confidence score from 0.0 to 1.0 (normalized correlation).
    """

    timestamp_ms: int
    confidence: float

    @property
    def timestamp_sec(self) -> float:
        """Returns the timestamp in seconds.

        Returns:
            float: Offset in seconds.
        """
        return self.timestamp_ms / 1000.0


@dataclasses.dataclass(frozen=True)
class AudioMatchDiagnostic:
    """Detailed diagnostic information about detection around expected time.

    Attributes:
        expected_timestamp_ms: Target timestamp being verified in ms.
        tolerance_ms: Tolerance window around target in ms.
        expected_peak_timestamp_ms: Peak time in tolerance, or None.
        expected_peak_confidence: Peak score in tolerance, or None.
        expected_peak_raw_correlation: Raw correlation before vocal penalty.
        expected_peak_vocal_penalty: Vocal penalty factor (0.0 to 1.0) applied.
        top_false_positive_timestamp_ms: Time of top out-of-tolerance peak.
        top_false_positive_confidence: Score of top out-of-tolerance peak.
        margin: Difference (expected_peak_confidence - top_fp_confidence).
    """

    expected_timestamp_ms: int
    tolerance_ms: int
    expected_peak_timestamp_ms: int | None = None
    expected_peak_confidence: float | None = None
    expected_peak_raw_correlation: float | None = None
    expected_peak_vocal_penalty: float | None = None
    top_false_positive_timestamp_ms: int | None = None
    top_false_positive_confidence: float | None = None
    margin: float | None = None


class AudioMatcher:
    """Matches reference sound effects within video or audio recordings.

    Extracts audio from video containers using ffmpeg (or loads audio directly),
    computes log-power spectrograms, and locates occurrences using 2D normalized
    cross-correlation.

    Attributes:
        sample_rate: Target audio sampling rate in Hz (default 22050).
        hop_length: FFT hop length in samples (default 256).
        n_fft: FFT window size in samples (default 1024).
    """

    def __init__(
        self,
        sample_rate: int = 22050,
        hop_length: int = 256,
        n_fft: int = 1024,
    ) -> None:
        """Initializes the AudioMatcher with processing parameters.

        Args:
            sample_rate: Common sampling rate in Hz.
            hop_length: Step size between FFT frames in samples.
            n_fft: Window length for FFT analysis in samples.
        """
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.n_fft = n_fft

    def match(
        self,
        video_or_audio_path: str | Path,
        reference_sound_path: str | Path,
        threshold: float = 0.2,
        min_interval_ms: int | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        max_matches: int | None = None,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
    ) -> list[AudioMatchResult]:
        """Finds timestamps where the reference sound effect occurs.

        Extracts audio, performs 2D cross-correlation on cropped magnitude
        spectrograms, penalizes out-of-band vocal energy, suppresses nearby
        duplicates, and returns matches sorted by confidence.

        Args:
            video_or_audio_path: Path to the target video or audio file.
            reference_sound_path: Path to the reference sound effect WAV/audio.
            threshold: Minimum correlation score threshold (0.0 to 1.0).
            min_interval_ms: Minimum millisecond distance between detections.
                Defaults to the duration of the reference sound.
            start_ms: Optional start offset in milliseconds to restrict search.
            end_ms: Optional end offset in milliseconds to restrict search.
            max_matches: Optional limit on the number of returned matches.
            freq_min_hz: Optional lower frequency bound in Hz for filtering.
            freq_max_hz: Optional upper frequency bound in Hz for filtering.

        Returns:
            list[AudioMatchResult]: Candidate matches sorted by highest
                confidence first.

        Raises:
            FileNotFoundError: If the video or reference sound file is missing.
            ValueError: If audio duration is shorter than the reference sound.
        """
        scores, _, _, ms_per_frame, offset_ms, ref_dur_ms = (
            self._compute_correlation_scores(
                video_or_audio_path=video_or_audio_path,
                reference_sound_path=reference_sound_path,
                start_ms=start_ms,
                end_ms=end_ms,
                freq_min_hz=freq_min_hz,
                freq_max_hz=freq_max_hz,
            )
        )

        eff_interval_ms = (
            min_interval_ms if min_interval_ms is not None else int(ref_dur_ms)
        )
        min_dist_frames = max(1, int(eff_interval_ms / ms_per_frame))

        raw_peaks = self._find_peaks_nms(
            correlation_series=scores,
            threshold=threshold,
            min_dist_frames=min_dist_frames,
        )

        results: list[AudioMatchResult] = []
        for frame_idx, conf in raw_peaks:
            match_time_ms = int(round(offset_ms + frame_idx * ms_per_frame))
            results.append(
                AudioMatchResult(
                    timestamp_ms=match_time_ms,
                    confidence=float(conf),
                )
            )

        if max_matches is not None and max_matches > 0:
            results = results[:max_matches]

        return results

    def match_diagnostic(
        self,
        video_or_audio_path: str | Path,
        reference_sound_path: str | Path,
        expected_timestamp_ms: int,
        tolerance_ms: int = 500,
        threshold: float = 0.2,
        min_interval_ms: int | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        max_matches: int | None = None,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
    ) -> tuple[list[AudioMatchResult], AudioMatchDiagnostic]:
        """Matches a reference sound and extracts detailed diagnostics.

        Extracts audio, computes spectrograms, runs cross-correlation, and
        analyzes detection performance at and around the expected timestamp.

        Args:
            video_or_audio_path: Path to the target video or audio file.
            reference_sound_path: Path to reference sound effect WAV/audio.
            expected_timestamp_ms: Expected ground-truth timestamp in ms.
            tolerance_ms: Acceptable error window in ms around expected time.
            threshold: Minimum correlation score threshold (0.0 to 1.0).
            min_interval_ms: Minimum ms between detections.
            start_ms: Optional start offset in ms to restrict search.
            end_ms: Optional end offset in ms to restrict search.
            max_matches: Optional limit on returned matches.
            freq_min_hz: Optional lower frequency bound in Hz.
            freq_max_hz: Optional upper frequency bound in Hz.

        Returns:
            tuple[list[AudioMatchResult], AudioMatchDiagnostic]: Matches and
                diagnostic analysis around the target timestamp.

        Raises:
            FileNotFoundError: If media file or reference sound is missing.
            ValueError: If audio duration is shorter than reference sound.
        """
        scores, raw_corr, penalty, ms_per_frame, offset_ms, ref_dur_ms = (
            self._compute_correlation_scores(
                video_or_audio_path=video_or_audio_path,
                reference_sound_path=reference_sound_path,
                start_ms=start_ms,
                end_ms=end_ms,
                freq_min_hz=freq_min_hz,
                freq_max_hz=freq_max_hz,
            )
        )

        eff_interval_ms = (
            min_interval_ms if min_interval_ms is not None else int(ref_dur_ms)
        )
        min_dist_frames = max(1, int(eff_interval_ms / ms_per_frame))

        raw_peaks = self._find_peaks_nms(
            correlation_series=scores,
            threshold=threshold,
            min_dist_frames=min_dist_frames,
        )

        results: list[AudioMatchResult] = []
        for frame_idx, conf in raw_peaks:
            match_time_ms = int(round(offset_ms + frame_idx * ms_per_frame))
            results.append(
                AudioMatchResult(
                    timestamp_ms=match_time_ms,
                    confidence=float(conf),
                )
            )

        if max_matches is not None and max_matches > 0:
            results = results[:max_matches]

        # Extract diagnostic metrics
        num_scores = len(scores)
        frame_indices = np.arange(num_scores)
        frame_times_ms = offset_ms + frame_indices * ms_per_frame

        tol_start = expected_timestamp_ms - tolerance_ms
        tol_end = expected_timestamp_ms + tolerance_ms

        in_tol_mask = (
            (frame_times_ms >= tol_start) & (frame_times_ms <= tol_end)
        )
        in_tol_indices = np.where(in_tol_mask)[0]
        out_tol_indices = np.where(~in_tol_mask)[0]

        exp_peak_time: int | None = None
        exp_peak_conf: float | None = None
        exp_peak_raw: float | None = None
        exp_peak_vocal: float | None = None

        if len(in_tol_indices) > 0:
            best_in = in_tol_indices[np.argmax(scores[in_tol_indices])]
            exp_peak_time = int(round(frame_times_ms[best_in]))
            exp_peak_conf = float(scores[best_in])
            exp_peak_raw = float(raw_corr[best_in])
            exp_peak_vocal = float(penalty[best_in])

        top_fp_time: int | None = None
        top_fp_conf: float | None = None

        if len(out_tol_indices) > 0:
            best_out = out_tol_indices[np.argmax(scores[out_tol_indices])]
            top_fp_time = int(round(frame_times_ms[best_out]))
            top_fp_conf = float(scores[best_out])

        margin = (
            (exp_peak_conf - top_fp_conf)
            if (exp_peak_conf is not None and top_fp_conf is not None)
            else None
        )

        diagnostic = AudioMatchDiagnostic(
            expected_timestamp_ms=expected_timestamp_ms,
            tolerance_ms=tolerance_ms,
            expected_peak_timestamp_ms=exp_peak_time,
            expected_peak_confidence=exp_peak_conf,
            expected_peak_raw_correlation=exp_peak_raw,
            expected_peak_vocal_penalty=exp_peak_vocal,
            top_false_positive_timestamp_ms=top_fp_time,
            top_false_positive_confidence=top_fp_conf,
            margin=margin,
        )

        return results, diagnostic

    def _compute_correlation_scores(
        self,
        video_or_audio_path: str | Path,
        reference_sound_path: str | Path,
        start_ms: int | None = None,
        end_ms: int | None = None,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, int, float]:
        """Extracts audio and calculates correlation series and vocal penalty.

        Args:
            video_or_audio_path: Path to target media file.
            reference_sound_path: Path to reference audio WAV file.
            start_ms: Optional start offset in milliseconds.
            end_ms: Optional end offset in milliseconds.
            freq_min_hz: Optional lower frequency bound in Hz.
            freq_max_hz: Optional upper frequency bound in Hz.

        Returns:
            tuple: (final_scores, raw_correlation_series, vocal_penalty,
                ms_per_frame, offset_ms, ref_duration_ms).

        Raises:
            FileNotFoundError: If target or reference media is missing.
            ValueError: If target audio is shorter than reference audio.
        """
        target_path = Path(video_or_audio_path)
        ref_path = Path(reference_sound_path)

        if not target_path.exists():
            raise FileNotFoundError(f'File not found: {target_path}')
        if not ref_path.exists():
            raise FileNotFoundError(f'Reference sound not found: {ref_path}')

        target_audio = self._load_audio(
            target_path, start_ms=start_ms, end_ms=end_ms
        )
        ref_audio = self._load_audio(ref_path)

        if len(target_audio) < len(ref_audio):
            raise ValueError(
                'Target audio is shorter than the reference sound.'
            )

        freqs, s_target = self._compute_spectrogram(target_audio)
        _, s_ref = self._compute_spectrogram(ref_audio)

        f_min, f_max = self._determine_frequency_bounds(
            freqs, s_ref, freq_min_hz, freq_max_hz
        )
        band_mask = (freqs >= f_min) & (freqs <= f_max)

        mag_target = np.sqrt(s_target[band_mask, :]).astype(np.float32)
        mag_ref = np.sqrt(s_ref[band_mask, :]).astype(np.float32)

        correlation_matrix = cv2.matchTemplate(
            mag_target, mag_ref, cv2.TM_CCOEFF_NORMED
        )
        correlation_series = correlation_matrix[0]

        penalty = self._compute_vocal_penalty(
            freqs, s_target, s_ref, band_mask, mag_ref.shape[1]
        )
        final_scores = np.maximum(0.0, correlation_series) * penalty

        ms_per_frame = (self.hop_length / self.sample_rate) * 1000.0
        ref_duration_ms = (len(ref_audio) / self.sample_rate) * 1000.0
        offset_ms = start_ms if start_ms is not None else 0

        return (
            final_scores,
            correlation_series,
            penalty,
            ms_per_frame,
            offset_ms,
            ref_duration_ms,
        )

    def match_with_config(
        self,
        video_or_audio_path: str | Path,
        config: AudioMatchConfig | str | Path,
        threshold: float | None = None,
        min_interval_ms: int | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        max_matches: int | None = None,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
    ) -> list[AudioMatchResult]:
        """Matches a reference sound using a configuration object or file.

        Loads reference sound path and frequency settings from the
        configuration, allowing explicit arguments to override configuration
        defaults.

        Args:
            video_or_audio_path: Path to the target video or audio file.
            config: AudioMatchConfig instance or path to a YAML config file.
            threshold: Optional threshold override. Defaults to config value.
            min_interval_ms: Optional minimum interval between detections in ms.
            start_ms: Optional start offset in milliseconds.
            end_ms: Optional end offset in milliseconds.
            max_matches: Optional limit on the number of returned matches.
            freq_min_hz: Optional lower frequency bound override in Hz.
            freq_max_hz: Optional upper frequency bound override in Hz.

        Returns:
            list[AudioMatchResult]: Candidate matches sorted by confidence.

        Raises:
            FileNotFoundError: If the media file, config, or sound is missing.
            ValueError: If audio duration is shorter than the reference sound.
        """
        match_cfg = (
            config
            if isinstance(config, AudioMatchConfig)
            else load_sound_config(config)
        )

        eff_threshold = (
            threshold if threshold is not None else match_cfg.threshold
        )
        eff_freq_min = (
            freq_min_hz if freq_min_hz is not None else match_cfg.freq_min_hz
        )
        eff_freq_max = (
            freq_max_hz if freq_max_hz is not None else match_cfg.freq_max_hz
        )

        return self.match(
            video_or_audio_path=video_or_audio_path,
            reference_sound_path=match_cfg.reference_sound_path,
            threshold=eff_threshold,
            min_interval_ms=min_interval_ms,
            start_ms=start_ms,
            end_ms=end_ms,
            max_matches=max_matches,
            freq_min_hz=eff_freq_min,
            freq_max_hz=eff_freq_max,
        )

    def _load_audio(
        self,
        file_path: Path,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> np.ndarray:
        """Loads and converts an audio or video file into mono float32 samples.

        Uses ffmpeg to extract or decode into the target sampling rate.

        Args:
            file_path: Path to the media file.
            start_ms: Optional start offset in milliseconds.
            end_ms: Optional end offset in milliseconds.

        Returns:
            np.ndarray: 1D array of normalized float32 audio samples.

        Raises:
            RuntimeError: If ffmpeg fails to decode the audio stream.
        """
        with tempfile.NamedTemporaryFile(
            suffix='.wav', delete=False
        ) as tmp_file:
            temp_wav_path = tmp_file.name

        try:
            cmd = ['ffmpeg', '-y']
            if start_ms is not None and start_ms > 0:
                cmd.extend(['-ss', f'{start_ms / 1000.0:.3f}'])
            if end_ms is not None:
                duration_sec = (
                    (end_ms - (start_ms or 0)) / 1000.0
                )
                if duration_sec > 0:
                    cmd.extend(['-t', f'{duration_sec:.3f}'])

            cmd.extend([
                '-i',
                str(file_path),
                '-vn',
                '-ac',
                '1',
                '-ar',
                str(self.sample_rate),
                temp_wav_path,
            ])

            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0:
                err_msg = result.stderr.decode('utf-8', errors='replace')
                raise RuntimeError(
                    f'ffmpeg audio extraction failed: {err_msg[:200]}'
                )

            _, data = wavfile.read(temp_wav_path)
            if data.dtype == np.int16:
                samples = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                samples = data.astype(np.float32) / 2147483648.0
            elif data.dtype == np.uint8:
                samples = (data.astype(np.float32) - 128.0) / 128.0
            else:
                samples = data.astype(np.float32)

            return samples
        finally:
            if os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)

    def _compute_spectrogram(
        self, audio: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Computes frequency bin centers and power spectrogram of audio.

        Args:
            audio: 1D normalized float32 audio sample array.

        Returns:
            tuple[np.ndarray, np.ndarray]: 1D frequency bins array in Hz, and 2D
                power spectrogram matrix.
        """
        noverlap = self.n_fft - self.hop_length
        freqs, _, sxx = spectrogram(
            audio,
            fs=self.sample_rate,
            nperseg=self.n_fft,
            noverlap=noverlap,
        )
        return freqs, sxx.astype(np.float32)

    def _determine_frequency_bounds(
        self,
        freqs: np.ndarray,
        s_ref: np.ndarray,
        freq_min_hz: float | None,
        freq_max_hz: float | None,
    ) -> tuple[float, float]:
        """Determines effective lower and upper frequency bounds for matching.

        Args:
            freqs: 1D array of frequency bin centers in Hz.
            s_ref: 2D power spectrogram of the reference sound.
            freq_min_hz: User-specified lower frequency bound, if any.
            freq_max_hz: User-specified upper frequency bound, if any.

        Returns:
            tuple[float, float]: (freq_min, freq_max) in Hz.
        """
        if freq_min_hz is not None and freq_max_hz is not None:
            return freq_min_hz, freq_max_hz

        mean_power = np.mean(s_ref, axis=1)
        peak_power = np.max(mean_power)
        active_bins = np.where(mean_power >= peak_power * 0.01)[0]

        if len(active_bins) == 0:
            auto_min = 20.0
            auto_max = float(self.sample_rate / 2.0)
        else:
            auto_min = float(freqs[max(0, active_bins[0] - 1)])
            auto_max = float(freqs[min(len(freqs) - 1, active_bins[-1] + 1)])

        final_min = freq_min_hz if freq_min_hz is not None else auto_min
        final_max = freq_max_hz if freq_max_hz is not None else auto_max
        return final_min, final_max

    def _compute_vocal_penalty(
        self,
        freqs: np.ndarray,
        s_target: np.ndarray,
        s_ref: np.ndarray,
        band_mask: np.ndarray,
        kernel_len: int,
    ) -> np.ndarray:
        """Computes a penalty factor (0.0 to 1.0) to reject speech fundamentals.

        Penalizes windows where energy below the target band dominates, which is
        characteristic of human vocal fundamentals and shouting.

        Args:
            freqs: 1D array of frequency bin centers in Hz.
            s_target: 2D power spectrogram of the target audio.
            s_ref: 2D power spectrogram of the reference audio.
            band_mask: Boolean mask for frequency bins in the active band.
            kernel_len: Number of time frames in the reference sound template.

        Returns:
            np.ndarray: 1D array of penalty multipliers (0.0 to 1.0).
        """
        f_min = freqs[band_mask][0] if np.any(band_mask) else 0.0
        low_mask = (freqs >= 150.0) & (freqs < f_min)
        num_frames = s_target.shape[1] - kernel_len + 1
        if not np.any(low_mask) or num_frames <= 0:
            return np.ones(max(1, num_frames), dtype=np.float32)

        band_p = np.convolve(
            np.sum(s_target[band_mask, :], axis=0),
            np.ones(kernel_len) / kernel_len,
            mode='valid',
        )
        low_p = np.convolve(
            np.sum(s_target[low_mask, :], axis=0),
            np.ones(kernel_len) / kernel_len,
            mode='valid',
        )
        target_ratio = band_p / (band_p + low_p + 1e-8)

        ref_band_p = np.sum(s_ref[band_mask, :])
        ref_low_p = np.sum(s_ref[low_mask, :])
        ref_ratio = ref_band_p / (ref_band_p + ref_low_p + 1e-8)

        # Apply penalty when target window has much lower in-band concentration
        # than the reference sound effect.
        penalty = np.clip(target_ratio / (ref_ratio * 0.4), 0.0, 1.0)
        return penalty.astype(np.float32)

    def _find_peaks_nms(
        self,
        correlation_series: np.ndarray,
        threshold: float,
        min_dist_frames: int,
    ) -> list[tuple[int, float]]:
        """Applies Non-Maximum Suppression to extract peaks above a threshold.

        Args:
            correlation_series: 1D array of normalized correlation scores.
            threshold: Minimum score threshold.
            min_dist_frames: Minimum frame distance between adjacent peaks.

        Returns:
            list[tuple[int, float]]: List of (frame_index, score) pairs
                sorted by highest score first.
        """
        indices = np.where(correlation_series >= threshold)[0]
        if len(indices) == 0:
            return []

        # Sort indices by score descending
        sorted_indices = indices[np.argsort(correlation_series[indices])[::-1]]

        selected: list[tuple[int, float]] = []
        suppressed = np.zeros(len(correlation_series), dtype=bool)

        for idx in sorted_indices:
            if suppressed[idx]:
                continue
            selected.append((int(idx), float(correlation_series[idx])))
            start_frame = max(0, idx - min_dist_frames)
            end_frame = min(
                len(correlation_series), idx + min_dist_frames + 1
            )
            suppressed[start_frame:end_frame] = True

        return selected


def main() -> None:
    """Command-line entry point for matching reference sounds in media files.

    Parses command-line arguments, runs AudioMatcher, and outputs formatted
    matches or JSON.
    """
    parser = argparse.ArgumentParser(
        description='Match reference sound effects in video or audio files.'
    )
    parser.add_argument(
        'video',
        type=str,
        help='Path to target video or audio file.',
    )
    parser.add_argument(
        'reference',
        type=str,
        nargs='?',
        default=None,
        help='Path to reference sound WAV (optional if --config is provided).',
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to sound definition YAML file (e.g. sm5_game_start.yaml).',
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=None,
        help='Minimum confidence threshold (overrides config or defaults 0.2).',
    )
    parser.add_argument(
        '--min-interval-ms',
        type=int,
        default=None,
        help='Minimum millisecond interval between detections.',
    )
    parser.add_argument(
        '--start-ms',
        type=int,
        default=None,
        help='Start offset in milliseconds to restrict search.',
    )
    parser.add_argument(
        '--end-ms',
        type=int,
        default=None,
        help='End offset in milliseconds to restrict search.',
    )
    parser.add_argument(
        '--freq-min',
        type=float,
        default=None,
        help='Lower frequency bound in Hz for bandpass filtering.',
    )
    parser.add_argument(
        '--freq-max',
        type=float,
        default=None,
        help='Upper frequency bound in Hz for bandpass filtering.',
    )
    parser.add_argument(
        '--max-matches',
        type=int,
        default=None,
        help='Maximum number of matches to return.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as a JSON array.',
    )

    args = parser.parse_args()

    if not args.reference and not args.config:
        parser.error(
            'Either a reference sound WAV path or --config must be provided.'
        )

    ref_path = args.reference
    eff_threshold = args.threshold
    eff_freq_min = args.freq_min
    eff_freq_max = args.freq_max

    if args.config:
        cfg = load_sound_config(args.config)
        if not ref_path:
            ref_path = cfg.reference_sound_path
        if eff_threshold is None:
            eff_threshold = cfg.threshold
        if eff_freq_min is None:
            eff_freq_min = cfg.freq_min_hz
        if eff_freq_max is None:
            eff_freq_max = cfg.freq_max_hz

    if eff_threshold is None:
        eff_threshold = 0.2

    matcher = AudioMatcher()
    results = matcher.match(
        video_or_audio_path=args.video,
        reference_sound_path=ref_path,
        threshold=eff_threshold,
        min_interval_ms=args.min_interval_ms,
        start_ms=args.start_ms,
        end_ms=args.end_ms,
        max_matches=args.max_matches,
        freq_min_hz=eff_freq_min,
        freq_max_hz=eff_freq_max,
    )

    if args.json:
        data = [
            {
                'timestamp_ms': r.timestamp_ms,
                'timestamp_sec': r.timestamp_sec,
                'confidence': round(r.confidence, 4),
            }
            for r in results
        ]
        print(json.dumps(data, indent=2))
        return

    if not results:
        print('No matches found.')
        return

    print(f'Found {len(results)} match(es):')
    for i, r in enumerate(results, 1):
        minutes = int(r.timestamp_sec // 60)
        seconds = r.timestamp_sec % 60
        time_str = f'{minutes:02d}:{seconds:06.3f}'
        print(
            f'  {i}. {r.timestamp_ms} ms ({time_str}) - '
            f'confidence: {r.confidence:.4f}'
        )


if __name__ == '__main__':
    main()
