"""Pre-game start-sound sample matching and dual-method game-start detection.

This module complements single-sound siren matching by detecting pre-game
sound samples (stored in ``assets/sm5/start_sounds/``) played immediately
before a game begins. Because GoPro recordings may start mid-sample and
contain overlapping player speech, samples are matched using overlapping
end-anchored spectrogram chunks and consensus voting.

Usage example:
    from lfdata.video.audio_matcher import AudioMatcher
    from lfdata.video.start_sound_matcher import GameStartDetector

    detector = GameStartDetector(audio_matcher=AudioMatcher())
    result = detector.detect(
        video_or_audio_path='pov_video.mp4',
        reference_sound_path='siren.wav',
        start_sounds_dir='assets/sm5/start_sounds',
    )
    if result is not None:
        print(result.timestamp_ms, result.method, result.confidence)
"""

import dataclasses
from pathlib import Path

import cv2
import numpy as np

from lfdata.model.constants.time import MS_PER_SECOND
from lfdata.video.audio_matcher import (
    AudioMatchConfig,
    AudioMatchDiagnostic,
    AudioMatcher,
    AudioMatchResult,
    load_sound_config,
)
from lfdata.video.constants import (
    DEFAULT_AGREEMENT_TOLERANCE_MS,
    DEFAULT_AUDIO_THRESHOLD,
    DEFAULT_CHUNK_DURATION_MS,
    DEFAULT_CHUNK_STEP_MS,
    DEFAULT_CONSENSUS_TOLERANCE_MS,
    DEFAULT_SAMPLE_HIGH_PASS_HZ,
    DEFAULT_SAMPLE_MAX_FREQ_HZ,
    DEFAULT_START_SOUND_METHOD,
)

SUPPORTED_AUDIO_EXTENSIONS: tuple[str, ...] = ('.wav', '.mp3', '.flac', '.ogg')
LOG_MAG_SCALE: float = 100.0
MIN_CHUNK_RMS_RATIO: float = 0.05
MIN_HALF_CHUNK_MS: float = 500.0
CONFLICT_PENALTY_FACTOR: float = 0.8


@dataclasses.dataclass(frozen=True)
class SampleChunk:
    """Represents a spectrogram sub-window extracted from a reference sample.

    Attributes:
        start_frame: Frame index where this chunk begins in the sample.
        end_frame: Frame index where this chunk ends in the sample.
        start_offset_ms: Millisecond offset from sample start to this chunk.
        spec: Log-magnitude 2D spectrogram array for this chunk.
    """

    start_frame: int
    end_frame: int
    start_offset_ms: float
    spec: np.ndarray


@dataclasses.dataclass(frozen=True)
class ChunkHit:
    """Represents a single chunk match and its predicted game-start timestamp.

    Attributes:
        predicted_game_start_ms: Predicted game start timestamp in ms.
        score: Normalized cross-correlation score for this chunk hit.
        chunk_start_offset_ms: Sample start offset of the matched chunk in ms.
    """

    predicted_game_start_ms: int
    score: float
    chunk_start_offset_ms: int


@dataclasses.dataclass(frozen=True)
class SampleCandidate:
    """Internal candidate summary for one matched pre-game sample cluster.

    Attributes:
        method: Sample identifier (e.g., ``start_sounds/sample.wav``).
        timestamp_ms: Consensus game-start timestamp in milliseconds.
        confidence: Confidence score in [0.0, 1.0].
        consensus_ratio: Fraction of available chunks agreeing on timestamp.
    """

    method: str
    timestamp_ms: int
    confidence: float
    consensus_ratio: float


class StartSoundMatcher:
    """Matches pre-game start-sound samples using chunk consensus voting.

    Handles late-starting recordings (where the recording begins after the
    sample has already started) and overlapping foreground noise (such as
    players talking) by matching overlapping end-anchored spectrogram chunks
    and clustering predictions of the sample's end time.

    Attributes:
        audio_matcher: AudioMatcher instance used for audio loading and STFT.
        chunk_duration_ms: Duration of each sub-window chunk in milliseconds.
        chunk_step_ms: Step size between consecutive chunks in milliseconds.
        consensus_tolerance_ms: Max timing spread for chunk votes to cluster.
        min_freq_hz: Lower frequency cutoff in Hz to filter rumble.
        max_freq_hz: Upper frequency cutoff in Hz.
    """

    def __init__(
        self,
        audio_matcher: AudioMatcher | None = None,
        chunk_duration_ms: int = DEFAULT_CHUNK_DURATION_MS,
        chunk_step_ms: int = DEFAULT_CHUNK_STEP_MS,
        consensus_tolerance_ms: int = DEFAULT_CONSENSUS_TOLERANCE_MS,
        min_freq_hz: float = DEFAULT_SAMPLE_HIGH_PASS_HZ,
        max_freq_hz: float = DEFAULT_SAMPLE_MAX_FREQ_HZ,
    ) -> None:
        """Initializes StartSoundMatcher with chunking and frequency settings.

        Args:
            audio_matcher: Optional AudioMatcher instance to reuse.
            chunk_duration_ms: Duration of each sub-window chunk in ms.
            chunk_step_ms: Step size between chunks in ms.
            consensus_tolerance_ms: Timing tolerance for chunk voting in ms.
            min_freq_hz: Lower frequency cutoff in Hz.
            max_freq_hz: Upper frequency cutoff in Hz.
        """
        self.audio_matcher = (
            audio_matcher if audio_matcher is not None else AudioMatcher()
        )
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_step_ms = chunk_step_ms
        self.consensus_tolerance_ms = consensus_tolerance_ms
        self.min_freq_hz = min_freq_hz
        self.max_freq_hz = max_freq_hz

    def list_sample_files(self, start_sounds_dir: str | Path) -> list[Path]:
        """Lists supported audio sample files in the start-sounds directory.

        Args:
            start_sounds_dir: Path to directory containing start-sound files.

        Returns:
            list[Path]: Sorted list of audio sample file paths.

        Raises:
            FileNotFoundError: If ``start_sounds_dir`` does not exist.
        """
        dir_path = Path(start_sounds_dir)
        if not dir_path.exists():
            raise FileNotFoundError(
                f'Start sounds directory not found: {start_sounds_dir}'
            )

        files = [
            path
            for path in dir_path.iterdir()
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        ]
        return sorted(files, key=lambda p: p.name)

    def match_directory(
        self,
        video_or_audio_path: str | Path,
        start_sounds_dir: str | Path,
        threshold: float = DEFAULT_AUDIO_THRESHOLD,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[AudioMatchResult]:
        """Matches all pre-game start-sound samples against a media file.

        Args:
            video_or_audio_path: Path to the target video or audio file.
            start_sounds_dir: Directory containing candidate start-sound WAVs.
            threshold: Minimum confidence score threshold (0.0 to 1.0).
            start_ms: Optional search start offset in milliseconds.
            end_ms: Optional search end offset in milliseconds.

        Returns:
            list[AudioMatchResult]: Candidate game-start matches sorted by
                confidence descending.

        Raises:
            FileNotFoundError: If the media file or directory does not exist.
        """
        media_path = Path(video_or_audio_path)
        if not media_path.exists():
            raise FileNotFoundError(
                f'Target media file not found: {video_or_audio_path}'
            )

        sample_files = self.list_sample_files(
            start_sounds_dir=start_sounds_dir
        )
        if not sample_files:
            return []

        target_audio = self.audio_matcher.load_audio(
            file_path=media_path,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        offset_ms = start_ms if start_ms is not None and start_ms > 0 else 0
        return self.match_samples(
            target_audio=target_audio,
            sample_paths=sample_files,
            offset_ms=offset_ms,
            threshold=threshold,
        )

    def match_samples(
        self,
        target_audio: np.ndarray,
        sample_paths: list[Path],
        offset_ms: int = 0,
        threshold: float = DEFAULT_AUDIO_THRESHOLD,
    ) -> list[AudioMatchResult]:
        """Matches pre-loaded target audio against candidate sample files.

        Args:
            target_audio: 1D normalized mono float32 target audio samples.
            sample_paths: List of candidate start-sound file paths.
            offset_ms: Start offset of ``target_audio`` in milliseconds.
            threshold: Minimum confidence score threshold (0.0 to 1.0).

        Returns:
            list[AudioMatchResult]: Candidate game-start matches sorted by
                confidence descending.
        """
        if len(target_audio) == 0 or not sample_paths:
            return []

        target_spec = self._prepare_log_spectrogram(audio=target_audio)
        ms_per_frame = (
            self.audio_matcher.hop_length / self.audio_matcher.sample_rate
        ) * MS_PER_SECOND

        candidates: list[SampleCandidate] = []
        for sample_path in sample_paths:
            candidate = self._evaluate_sample(
                target_spec=target_spec,
                sample_path=sample_path,
                offset_ms=offset_ms,
                ms_per_frame=ms_per_frame,
                chunk_threshold=max(0.15, threshold * 0.8),
            )
            if candidate is not None:
                candidates.append(candidate)

        if not candidates:
            return []

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        second_best_conf = (
            candidates[1].confidence if len(candidates) > 1 else 0.0
        )

        results: list[AudioMatchResult] = []
        for idx, cand in enumerate(candidates):
            final_conf = cand.confidence
            if idx == 0 and len(candidates) > 1:
                margin = max(0.0, cand.confidence - second_best_conf)
                final_conf = min(1.0, cand.confidence + 0.15 * margin)
            if final_conf >= threshold:
                results.append(
                    AudioMatchResult(
                        timestamp_ms=cand.timestamp_ms,
                        confidence=float(np.clip(final_conf, 0.0, 1.0)),
                        method=cand.method,
                    )
                )

        return results

    def _prepare_log_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        """Computes a band-cropped log-magnitude spectrogram for matching.

        Args:
            audio: 1D normalized float32 audio sample array.

        Returns:
            np.ndarray: 2D log-magnitude spectrogram cropped to active band.
        """
        freqs, sxx = self.audio_matcher.compute_spectrogram(audio=audio)
        band_mask = (freqs >= self.min_freq_hz) & (freqs <= self.max_freq_hz)
        if not np.any(band_mask):
            band_mask = np.ones_like(freqs, dtype=bool)
        mag = np.sqrt(np.maximum(sxx[band_mask, :], 0.0))
        return np.log1p(mag * LOG_MAG_SCALE).astype(np.float32)

    def _build_sample_chunks(
        self,
        ref_spec: np.ndarray,
        ms_per_frame: float,
    ) -> list[SampleChunk]:
        """Splits a sample spectrogram into overlapping end-anchored chunks.

        Args:
            ref_spec: 2D log-magnitude spectrogram of the reference sample.
            ms_per_frame: Duration of one spectrogram frame in milliseconds.

        Returns:
            list[SampleChunk]: Non-silent sub-window chunks covering the sample.
        """
        total_frames = ref_spec.shape[1]
        if total_frames < 2:
            return []

        chunk_frames = max(
            2, int(round(self.chunk_duration_ms / ms_per_frame))
        )
        step_frames = max(1, int(round(self.chunk_step_ms / ms_per_frame)))

        ranges: list[tuple[int, int]] = []
        if total_frames <= chunk_frames:
            ranges.append((0, total_frames))
            half_frames = total_frames // 2
            if half_frames * ms_per_frame >= MIN_HALF_CHUNK_MS:
                ranges.append((half_frames, total_frames))
        else:
            starts = list(
                range(0, total_frames - chunk_frames + 1, step_frames)
            )
            last_start = total_frames - chunk_frames
            if starts[-1] != last_start:
                starts.append(last_start)
            ranges = [(s, s + chunk_frames) for s in starts]

        raw_chunks = [
            SampleChunk(
                start_frame=start_f,
                end_frame=end_f,
                start_offset_ms=start_f * ms_per_frame,
                spec=ref_spec[:, start_f:end_f],
            )
            for start_f, end_f in ranges
        ]

        rms_values = [
            float(np.sqrt(np.mean(np.square(c.spec)))) for c in raw_chunks
        ]
        peak_rms = max(rms_values, default=0.0)
        if peak_rms <= 0.0:
            return []

        return [
            chunk
            for chunk, rms in zip(raw_chunks, rms_values)
            if rms >= peak_rms * MIN_CHUNK_RMS_RATIO
        ]

    def _evaluate_sample(
        self,
        target_spec: np.ndarray,
        sample_path: Path,
        offset_ms: int,
        ms_per_frame: float,
        chunk_threshold: float,
    ) -> SampleCandidate | None:
        """Evaluates a single candidate start-sound sample against target audio.

        Args:
            target_spec: 2D log-magnitude spectrogram of target audio.
            sample_path: Path to the candidate start-sound audio file.
            offset_ms: Target audio start offset in milliseconds.
            ms_per_frame: Duration of one spectrogram frame in milliseconds.
            chunk_threshold: Minimum correlation score per chunk hit.

        Returns:
            SampleCandidate | None: Best consensus candidate for this sample,
                or None if no chunks matched.
        """
        ref_audio = self.audio_matcher.load_audio(file_path=sample_path)
        if len(ref_audio) == 0:
            return None

        ref_spec = self._prepare_log_spectrogram(audio=ref_audio)
        total_sample_ms = ref_spec.shape[1] * ms_per_frame
        chunks = self._build_sample_chunks(
            ref_spec=ref_spec,
            ms_per_frame=ms_per_frame,
        )
        if not chunks:
            return None

        hits = self._collect_chunk_hits(
            target_spec=target_spec,
            chunks=chunks,
            total_sample_ms=total_sample_ms,
            offset_ms=offset_ms,
            ms_per_frame=ms_per_frame,
            chunk_threshold=chunk_threshold,
        )
        if not hits:
            return None

        return self._select_best_cluster(
            hits=hits,
            chunks=chunks,
            total_sample_ms=total_sample_ms,
            offset_ms=offset_ms,
            method_name=f'start_sounds/{sample_path.name}',
        )

    def _collect_chunk_hits(
        self,
        target_spec: np.ndarray,
        chunks: list[SampleChunk],
        total_sample_ms: float,
        offset_ms: int,
        ms_per_frame: float,
        chunk_threshold: float,
    ) -> list[ChunkHit]:
        """Runs template correlation per chunk and collects game-start hits.

        Args:
            target_spec: 2D log-magnitude spectrogram of target audio.
            chunks: Sub-window chunks extracted from the reference sample.
            total_sample_ms: Total duration of the reference sample in ms.
            offset_ms: Target audio start offset in milliseconds.
            ms_per_frame: Duration of one spectrogram frame in milliseconds.
            chunk_threshold: Minimum correlation score per chunk hit.

        Returns:
            list[ChunkHit]: All chunk detections with predicted game-start ms.
        """
        hits: list[ChunkHit] = []
        target_frames = target_spec.shape[1]

        for chunk in chunks:
            chunk_frames = chunk.spec.shape[1]
            if target_frames < chunk_frames:
                continue

            corr_mat = cv2.matchTemplate(
                target_spec,
                chunk.spec,
                cv2.TM_CCOEFF_NORMED,
            )
            corr_series = np.clip(corr_mat[0], 0.0, 1.0)
            peaks = self.audio_matcher.find_peaks_nms(
                correlation_series=corr_series,
                threshold=chunk_threshold,
                min_dist_frames=max(1, chunk_frames // 2),
            )
            remaining_ms = total_sample_ms - chunk.start_offset_ms
            for frame_idx, score in peaks:
                hit_ms = offset_ms + frame_idx * ms_per_frame
                predicted_ms = int(round(hit_ms + remaining_ms))
                hits.append(
                    ChunkHit(
                        predicted_game_start_ms=predicted_ms,
                        score=float(score),
                        chunk_start_offset_ms=int(
                            round(chunk.start_offset_ms)
                        ),
                    )
                )

        return hits

    def match_sample_diagnostic(
        self,
        video_or_audio_path: str | Path,
        sample_path: str | Path,
        expected_timestamp_ms: int,
        tolerance_ms: int = 500,
        threshold: float = DEFAULT_AUDIO_THRESHOLD,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> tuple[list[AudioMatchResult], AudioMatchDiagnostic]:
        """Matches a single start-sound sample and returns diagnostics.

        Evaluates end-anchored chunk consensus for ``sample_path`` against the
        target recording and builds an ``AudioMatchDiagnostic`` around
        ``expected_timestamp_ms``.

        Args:
            video_or_audio_path: Path to the target video or audio file.
            sample_path: Path to the start-sound sample WAV/audio file.
            expected_timestamp_ms: Expected game-start timestamp in ms.
            tolerance_ms: Acceptable error window in ms around expected time.
            threshold: Minimum confidence score threshold (0.0 to 1.0).
            start_ms: Optional search start offset in milliseconds.
            end_ms: Optional search end offset in milliseconds.

        Returns:
            tuple[list[AudioMatchResult], AudioMatchDiagnostic]: Matches above
                threshold (sorted descending) and diagnostic breakdown.

        Raises:
            FileNotFoundError: If target media or sample file does not exist.
        """
        media_path = Path(video_or_audio_path)
        sample_file = Path(sample_path)
        if not media_path.exists():
            raise FileNotFoundError(
                f'Target media file not found: {video_or_audio_path}'
            )
        if not sample_file.exists():
            raise FileNotFoundError(
                f'Start-sound sample file not found: {sample_path}'
            )

        target_audio = self.audio_matcher.load_audio(
            file_path=media_path,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        ref_audio = self.audio_matcher.load_audio(file_path=sample_file)
        offset_ms = start_ms if start_ms is not None and start_ms > 0 else 0
        ms_per_frame = (
            self.audio_matcher.hop_length / self.audio_matcher.sample_rate
        ) * MS_PER_SECOND

        candidates: list[SampleCandidate] = []
        if len(target_audio) > 0 and len(ref_audio) > 0:
            target_spec = self._prepare_log_spectrogram(audio=target_audio)
            ref_spec = self._prepare_log_spectrogram(audio=ref_audio)
            total_sample_ms = ref_spec.shape[1] * ms_per_frame
            chunks = self._build_sample_chunks(
                ref_spec=ref_spec,
                ms_per_frame=ms_per_frame,
            )
            if chunks:
                diag_chunk_thresh = max(0.10, min(0.15, threshold * 0.8))
                hits = self._collect_chunk_hits(
                    target_spec=target_spec,
                    chunks=chunks,
                    total_sample_ms=total_sample_ms,
                    offset_ms=offset_ms,
                    ms_per_frame=ms_per_frame,
                    chunk_threshold=diag_chunk_thresh,
                )
                if hits:
                    candidates = self._score_clusters(
                        hits=hits,
                        chunks=chunks,
                        total_sample_ms=total_sample_ms,
                        offset_ms=offset_ms,
                        method_name=f'start_sounds/{sample_file.name}',
                    )

        results = [
            AudioMatchResult(
                timestamp_ms=c.timestamp_ms,
                confidence=c.confidence,
                method=c.method,
            )
            for c in candidates
            if c.confidence >= threshold
        ]

        in_tol = [
            c
            for c in candidates
            if abs(c.timestamp_ms - expected_timestamp_ms) <= tolerance_ms
        ]
        out_tol = [
            c
            for c in candidates
            if abs(c.timestamp_ms - expected_timestamp_ms) > tolerance_ms
        ]

        exp_peak = in_tol[0] if in_tol else None
        top_fp = out_tol[0] if out_tol else None
        margin = (
            (exp_peak.confidence - top_fp.confidence)
            if (exp_peak is not None and top_fp is not None)
            else None
        )

        diagnostic = AudioMatchDiagnostic(
            expected_timestamp_ms=expected_timestamp_ms,
            tolerance_ms=tolerance_ms,
            expected_peak_timestamp_ms=(
                exp_peak.timestamp_ms if exp_peak is not None else None
            ),
            expected_peak_confidence=(
                exp_peak.confidence if exp_peak is not None else None
            ),
            top_false_positive_timestamp_ms=(
                top_fp.timestamp_ms if top_fp is not None else None
            ),
            top_false_positive_confidence=(
                top_fp.confidence if top_fp is not None else None
            ),
            margin=margin,
        )
        return results, diagnostic

    def _select_best_cluster(
        self,
        hits: list[ChunkHit],
        chunks: list[SampleChunk],
        total_sample_ms: float,
        offset_ms: int,
        method_name: str,
    ) -> SampleCandidate | None:
        """Clusters chunk hits by predicted timestamp and scores the best one.

        Args:
            hits: All chunk hits collected for the sample.
            chunks: All chunks belonging to the sample.
            total_sample_ms: Total duration of the sample in milliseconds.
            offset_ms: Target audio start offset in milliseconds.
            method_name: Method label for the sample.

        Returns:
            SampleCandidate | None: Highest-scoring consensus candidate.
        """
        candidates = self._score_clusters(
            hits=hits,
            chunks=chunks,
            total_sample_ms=total_sample_ms,
            offset_ms=offset_ms,
            method_name=method_name,
        )
        return candidates[0] if candidates else None

    def _score_clusters(
        self,
        hits: list[ChunkHit],
        chunks: list[SampleChunk],
        total_sample_ms: float,
        offset_ms: int,
        method_name: str,
    ) -> list[SampleCandidate]:
        """Clusters chunk hits by predicted timestamp and returns all scored.

        Args:
            hits: All chunk hits collected for the sample.
            chunks: All chunks belonging to the sample.
            total_sample_ms: Total duration of the sample in milliseconds.
            offset_ms: Target audio start offset in milliseconds.
            method_name: Method label for the sample.

        Returns:
            list[SampleCandidate]: Candidates sorted by confidence descending.
        """
        sorted_hits = sorted(hits, key=lambda h: h.predicted_game_start_ms)
        clusters: list[list[ChunkHit]] = []
        current: list[ChunkHit] = [sorted_hits[0]]

        for hit in sorted_hits[1:]:
            anchor_ms = current[0].predicted_game_start_ms
            if hit.predicted_game_start_ms - anchor_ms <= (
                self.consensus_tolerance_ms
            ):
                current.append(hit)
            else:
                clusters.append(current)
                current = [hit]
        clusters.append(current)

        candidates: list[SampleCandidate] = []
        for cluster in clusters:
            total_weight = sum(h.score for h in cluster)
            if total_weight <= 0.0:
                continue

            consensus_ms = int(
                round(
                    sum(h.predicted_game_start_ms * h.score for h in cluster)
                    / total_weight
                )
            )
            available_chunks = sum(
                1
                for c in chunks
                if (consensus_ms - (total_sample_ms - c.start_offset_ms))
                >= (offset_ms - 50.0)
            )
            unique_matched = len({h.chunk_start_offset_ms for h in cluster})
            consensus_ratio = min(
                1.0,
                unique_matched / max(1, available_chunks),
            )
            mean_score = float(np.mean([h.score for h in cluster]))
            confidence = float(
                np.clip(
                    mean_score * (0.65 + 0.35 * consensus_ratio),
                    0.0,
                    1.0,
                )
            )

            candidates.append(
                SampleCandidate(
                    method=method_name,
                    timestamp_ms=consensus_ms,
                    confidence=confidence,
                    consensus_ratio=consensus_ratio,
                )
            )

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates


class GameStartDetector:
    """Combines start-sound sample matching and siren matching for game start.

    Evaluates both detection methods and resolves the most reliable start time,
    method identifier, and combined confidence score in [0.0, 1.0].

    Attributes:
        audio_matcher: AudioMatcher instance for siren matching.
        start_sound_matcher: StartSoundMatcher for pre-game sample matching.
        agreement_tolerance_ms: Max difference in ms for both methods to agree.
    """

    def __init__(
        self,
        audio_matcher: AudioMatcher | None = None,
        start_sound_matcher: StartSoundMatcher | None = None,
        agreement_tolerance_ms: int = DEFAULT_AGREEMENT_TOLERANCE_MS,
    ) -> None:
        """Initializes GameStartDetector with both matchers.

        Args:
            audio_matcher: Optional AudioMatcher instance.
            start_sound_matcher: Optional StartSoundMatcher instance.
            agreement_tolerance_ms: Max ms difference for method agreement.
        """
        self.audio_matcher = (
            audio_matcher if audio_matcher is not None else AudioMatcher()
        )
        self.start_sound_matcher = (
            start_sound_matcher
            if start_sound_matcher is not None
            else StartSoundMatcher(audio_matcher=self.audio_matcher)
        )
        self.agreement_tolerance_ms = agreement_tolerance_ms

    def detect(
        self,
        video_or_audio_path: str | Path,
        reference_sound_path: str | Path | None = None,
        start_sounds_dir: str | Path | None = None,
        config: AudioMatchConfig | str | Path | None = None,
        threshold: float | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        template_duration_ms: int | None = None,
        min_energy_ratio: float | None = None,
        two_stage: bool = False,
        cluster_sequence: bool = False,
    ) -> AudioMatchResult | None:
        """Detects game start using start-sound samples and/or siren matching.

        Args:
            video_or_audio_path: Path to target video or audio file.
            reference_sound_path: Optional path to siren reference WAV.
            start_sounds_dir: Optional directory of pre-game start-sound WAVs.
            config: Optional AudioMatchConfig or path to YAML config file.
            threshold: Optional confidence threshold override.
            start_ms: Optional search start offset in milliseconds.
            end_ms: Optional search end offset in milliseconds.
            freq_min_hz: Optional lower frequency cutoff in Hz for siren.
            freq_max_hz: Optional upper frequency cutoff in Hz for siren.
            template_duration_ms: Optional template crop duration in ms.
            min_energy_ratio: Optional minimum in-band energy ratio.
            two_stage: Whether to use two-stage siren matching.
            cluster_sequence: Whether to cluster repeated siren blasts.

        Returns:
            AudioMatchResult | None: Most reliable game-start match, or None.
        """
        match_cfg = (
            config
            if isinstance(config, AudioMatchConfig)
            else (load_sound_config(config) if config is not None else None)
        )

        eff_ref = reference_sound_path or (
            match_cfg.reference_sound_path if match_cfg is not None else None
        )
        eff_start_dir = start_sounds_dir or (
            match_cfg.start_sounds_dir if match_cfg is not None else None
        )
        eff_threshold = (
            threshold
            if threshold is not None
            else (
                match_cfg.threshold
                if match_cfg is not None
                else DEFAULT_AUDIO_THRESHOLD
            )
        )

        sample_matches: list[AudioMatchResult] = []
        if eff_start_dir is not None:
            sample_matcher = self._resolve_start_sound_matcher(match_cfg)
            sample_matches = sample_matcher.match_directory(
                video_or_audio_path=video_or_audio_path,
                start_sounds_dir=eff_start_dir,
                threshold=eff_threshold,
                start_ms=start_ms,
                end_ms=end_ms,
            )

        siren_matches: list[AudioMatchResult] = []
        if eff_ref is not None:
            siren_matches = self._run_siren_matcher(
                video_or_audio_path=video_or_audio_path,
                reference_sound_path=eff_ref,
                match_cfg=match_cfg,
                threshold=eff_threshold,
                start_ms=start_ms,
                end_ms=end_ms,
                freq_min_hz=freq_min_hz,
                freq_max_hz=freq_max_hz,
                template_duration_ms=template_duration_ms,
                min_energy_ratio=min_energy_ratio,
                two_stage=two_stage,
                cluster_sequence=cluster_sequence,
            )

        eff_agree_tol = (
            match_cfg.agreement_tolerance_ms
            if match_cfg is not None
            and match_cfg.agreement_tolerance_ms is not None
            else self.agreement_tolerance_ms
        )
        return self.resolve_best_match(
            sample_matches=sample_matches,
            siren_matches=siren_matches,
            agreement_tolerance_ms=eff_agree_tol,
        )

    def _resolve_start_sound_matcher(
        self, match_cfg: AudioMatchConfig | None
    ) -> StartSoundMatcher:
        """Returns a StartSoundMatcher configured with any config overrides.

        Args:
            match_cfg: Optional loaded AudioMatchConfig.

        Returns:
            StartSoundMatcher: Configured matcher instance.
        """
        if match_cfg is None:
            return self.start_sound_matcher

        has_override = any(
            v is not None
            for v in (
                match_cfg.chunk_duration_ms,
                match_cfg.chunk_step_ms,
                match_cfg.consensus_tolerance_ms,
                match_cfg.sample_min_freq_hz,
                match_cfg.sample_max_freq_hz,
            )
        )
        if not has_override:
            return self.start_sound_matcher

        base = self.start_sound_matcher
        return StartSoundMatcher(
            audio_matcher=self.audio_matcher,
            chunk_duration_ms=(
                match_cfg.chunk_duration_ms
                if match_cfg.chunk_duration_ms is not None
                else base.chunk_duration_ms
            ),
            chunk_step_ms=(
                match_cfg.chunk_step_ms
                if match_cfg.chunk_step_ms is not None
                else base.chunk_step_ms
            ),
            consensus_tolerance_ms=(
                match_cfg.consensus_tolerance_ms
                if match_cfg.consensus_tolerance_ms is not None
                else base.consensus_tolerance_ms
            ),
            min_freq_hz=(
                match_cfg.sample_min_freq_hz
                if match_cfg.sample_min_freq_hz is not None
                else base.min_freq_hz
            ),
            max_freq_hz=(
                match_cfg.sample_max_freq_hz
                if match_cfg.sample_max_freq_hz is not None
                else base.max_freq_hz
            ),
        )

    def _run_siren_matcher(
        self,
        video_or_audio_path: str | Path,
        reference_sound_path: str | Path,
        match_cfg: AudioMatchConfig | None,
        threshold: float,
        start_ms: int | None,
        end_ms: int | None,
        freq_min_hz: float | None,
        freq_max_hz: float | None,
        template_duration_ms: int | None,
        min_energy_ratio: float | None,
        two_stage: bool,
        cluster_sequence: bool,
    ) -> list[AudioMatchResult]:
        """Runs the existing siren matcher with resolved parameters.

        Args:
            video_or_audio_path: Path to target media file.
            reference_sound_path: Path to siren reference WAV.
            match_cfg: Optional loaded AudioMatchConfig.
            threshold: Minimum confidence threshold.
            start_ms: Optional search start offset in milliseconds.
            end_ms: Optional search end offset in milliseconds.
            freq_min_hz: Optional lower frequency cutoff in Hz.
            freq_max_hz: Optional upper frequency cutoff in Hz.
            template_duration_ms: Optional template crop duration in ms.
            min_energy_ratio: Optional minimum energy ratio.
            two_stage: Whether to use two-stage matching.
            cluster_sequence: Whether to cluster repeated blasts.

        Returns:
            list[AudioMatchResult]: Candidate siren matches.
        """
        eff_fmin = (
            freq_min_hz
            if freq_min_hz is not None
            else (match_cfg.freq_min_hz if match_cfg is not None else None)
        )
        eff_fmax = (
            freq_max_hz
            if freq_max_hz is not None
            else (match_cfg.freq_max_hz if match_cfg is not None else None)
        )
        eff_tdur = (
            template_duration_ms
            if template_duration_ms is not None
            else (
                match_cfg.template_duration_ms
                if match_cfg is not None
                else None
            )
        )
        eff_eratio = (
            min_energy_ratio
            if min_energy_ratio is not None
            else (
                match_cfg.min_energy_ratio if match_cfg is not None else None
            )
        )

        if two_stage:
            return self.audio_matcher.match_two_stage(
                video_or_audio_path=video_or_audio_path,
                reference_sound_path=reference_sound_path,
                threshold=threshold,
                start_ms=start_ms,
                end_ms=end_ms,
                freq_min_hz=eff_fmin,
                freq_max_hz=eff_fmax,
                template_duration_ms=eff_tdur,
                min_energy_ratio=eff_eratio,
            )

        return self.audio_matcher.match(
            video_or_audio_path=video_or_audio_path,
            reference_sound_path=reference_sound_path,
            threshold=threshold,
            start_ms=start_ms,
            end_ms=end_ms,
            freq_min_hz=eff_fmin,
            freq_max_hz=eff_fmax,
            template_duration_ms=eff_tdur,
            min_energy_ratio=eff_eratio,
            cluster_sequence=cluster_sequence,
        )

    def resolve_best_match(
        self,
        sample_matches: list[AudioMatchResult],
        siren_matches: list[AudioMatchResult],
        agreement_tolerance_ms: int | None = None,
    ) -> AudioMatchResult | None:
        """Selects the most reliable game-start match from both methods.

        Args:
            sample_matches: Matches from StartSoundMatcher, sorted descending.
            siren_matches: Matches from siren AudioMatcher, sorted descending.
            agreement_tolerance_ms: Optional override for agreement tolerance.

        Returns:
            AudioMatchResult | None: Selected game-start result with combined
                confidence in [0.0, 1.0], or None if both lists are empty.
        """
        best_sample = sample_matches[0] if sample_matches else None
        best_siren = siren_matches[0] if siren_matches else None

        if best_sample is None and best_siren is None:
            return None
        if best_sample is not None and best_siren is None:
            return best_sample
        if best_siren is not None and best_sample is None:
            return AudioMatchResult(
                timestamp_ms=best_siren.timestamp_ms,
                confidence=float(np.clip(best_siren.confidence, 0.0, 1.0)),
                method=best_siren.method or DEFAULT_START_SOUND_METHOD,
            )

        assert best_sample is not None and best_siren is not None
        diff_ms = abs(best_sample.timestamp_ms - best_siren.timestamp_ms)
        eff_tol = (
            agreement_tolerance_ms
            if agreement_tolerance_ms is not None
            else self.agreement_tolerance_ms
        )

        if diff_ms <= eff_tol:
            combined_conf = 1.0 - (
                (1.0 - best_sample.confidence) * (1.0 - best_siren.confidence)
            )
            chosen_ts = (
                best_sample.timestamp_ms
                if best_sample.confidence >= best_siren.confidence
                else best_siren.timestamp_ms
            )
            chosen_method = (
                best_sample.method
                if best_sample.confidence >= best_siren.confidence
                else best_siren.method
            )
            return AudioMatchResult(
                timestamp_ms=chosen_ts,
                confidence=float(np.clip(combined_conf, 0.0, 1.0)),
                method=chosen_method,
            )

        # Conflict: prefer start-sound sample with slight reliability weight
        sample_weighted = best_sample.confidence * 1.1
        if sample_weighted >= best_siren.confidence:
            return AudioMatchResult(
                timestamp_ms=best_sample.timestamp_ms,
                confidence=float(
                    np.clip(
                        best_sample.confidence * CONFLICT_PENALTY_FACTOR,
                        0.0,
                        1.0,
                    )
                ),
                method=best_sample.method,
            )

        return AudioMatchResult(
            timestamp_ms=best_siren.timestamp_ms,
            confidence=float(
                np.clip(
                    best_siren.confidence * CONFLICT_PENALTY_FACTOR,
                    0.0,
                    1.0,
                )
            ),
            method=best_siren.method,
        )
