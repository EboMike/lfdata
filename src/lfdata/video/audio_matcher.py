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
except ImportError as err:
    raise ImportError(
        'Audio matching requires numpy, scipy, and opencv-python. '
        'Install them using `pip install lfdata[video]`.'
    ) from err


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

        # 2D Normalized cross-correlation on cropped magnitude band
        correlation_matrix = cv2.matchTemplate(
            mag_target, mag_ref, cv2.TM_CCOEFF_NORMED
        )
        correlation_series = correlation_matrix[0]

        # Penalize human vocal/speech fundamentals outside the target band
        penalty = self._compute_vocal_penalty(
            freqs, s_target, s_ref, band_mask, mag_ref.shape[1]
        )
        final_scores = np.maximum(0.0, correlation_series) * penalty

        ms_per_frame = (self.hop_length / self.sample_rate) * 1000.0
        ref_duration_ms = (len(ref_audio) / self.sample_rate) * 1000.0

        effective_min_interval_ms = (
            min_interval_ms
            if min_interval_ms is not None
            else int(ref_duration_ms)
        )
        min_dist_frames = max(
            1, int(effective_min_interval_ms / ms_per_frame)
        )

        offset_ms = start_ms if start_ms is not None else 0
        raw_peaks = self._find_peaks_nms(
            correlation_series=final_scores,
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
        help='Path to reference sound effect WAV file.',
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.2,
        help='Minimum confidence threshold (default: 0.2).',
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
    matcher = AudioMatcher()
    results = matcher.match(
        video_or_audio_path=args.video,
        reference_sound_path=args.reference,
        threshold=args.threshold,
        min_interval_ms=args.min_interval_ms,
        start_ms=args.start_ms,
        end_ms=args.end_ms,
        max_matches=args.max_matches,
        freq_min_hz=args.freq_min,
        freq_max_hz=args.freq_max,
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
