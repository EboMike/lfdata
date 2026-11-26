"""Structured definition and benchmarking for audio template matching.

Provides data structures to define reference sound effects, associated
example videos with ground-truth timestamps, evaluation metrics, and
automated parameter tuning to optimize frequency cutoffs and thresholds.

Usage example:
    from lfdata.video.audio_benchmark import (
        AudioBenchmarkRunner,
        SoundDefinition,
    )

    runner = AudioBenchmarkRunner()
    sound_def = runner.load_from_yaml('config.yaml')
    summary = runner.evaluate(sound_def)
    print(f'Accuracy: {summary.accuracy * 100:.1f}%')
"""

import argparse
import dataclasses
import enum
import json
from pathlib import Path
import yaml

from lfdata.video.audio_matcher import (
    AudioMatchDiagnostic,
    AudioMatchResult,
    AudioMatcher,
)
from lfdata.video.constants import (
    DEFAULT_AUDIO_THRESHOLD,
    DEFAULT_AUDIO_TOLERANCE_MS,
    DEFAULT_CHUNK_DURATION_MS,
    DEFAULT_CHUNK_STEP_MS,
    DEFAULT_CONSENSUS_TOLERANCE_MS,
    DEFAULT_SAMPLE_HIGH_PASS_HZ,
    DEFAULT_SAMPLE_MAX_FREQ_HZ,
)
from lfdata.video.start_sound_matcher import StartSoundMatcher


class AudioTargetType(str, enum.Enum):
    """Target sound type that a training/benchmark data point is for.

    Attributes:
        SIREN: The primary siren / reference sound in SoundDefinition.
        AUDIO_FILE: A specific audio file (e.g. a pre-game start sound).
    """

    SIREN = 'siren'
    AUDIO_FILE = 'audio_file'


@dataclasses.dataclass
class AudioTestCase:
    """An example video or audio test case with expected sound timestamp.

    Attributes:
        video_path: Path to target video or audio file.
        expected_timestamp_ms: Ground-truth or approximate timestamp in ms.
        tolerance_ms: Acceptable error window in ms (default: 500).
        search_start_ms: Optional start offset in ms to restrict search.
        search_end_ms: Optional end offset in ms to restrict search.
        description: Optional notes about this test example.
        target_type: Whether this training data point is for the siren or a
            specific audio file.
        target_audio_path: Path to the specific audio file when target_type is
            AudioTargetType.AUDIO_FILE, or None for AudioTargetType.SIREN.
    """

    video_path: str
    expected_timestamp_ms: int
    tolerance_ms: int = DEFAULT_AUDIO_TOLERANCE_MS
    search_start_ms: int | None = None
    search_end_ms: int | None = None
    description: str = ''
    target_type: AudioTargetType = AudioTargetType.SIREN
    target_audio_path: str | None = None

    def __post_init__(self) -> None:
        """Validates target_type and target_audio_path consistency.

        Raises:
            ValueError: If target_type is invalid or target_audio_path does not
                match target_type.
        """
        if not isinstance(self.target_type, AudioTargetType):
            self.target_type = AudioTargetType(str(self.target_type))
        if (
            self.target_type == AudioTargetType.AUDIO_FILE
            and not self.target_audio_path
        ):
            raise ValueError(
                'target_audio_path is required when target_type is '
                f"'{AudioTargetType.AUDIO_FILE.value}'."
            )
        if (
            self.target_type == AudioTargetType.SIREN
            and self.target_audio_path is not None
        ):
            raise ValueError(
                'target_audio_path cannot be set when target_type is '
                f"'{AudioTargetType.SIREN.value}'."
            )


@dataclasses.dataclass
class SoundDefinition:
    """Structured definition of a sound effect to find with test cases.

    Attributes:
        name: Unique identifier for the sound.
        reference_sound_path: Path to reference sound effect WAV/audio file.
        freq_min_hz: Optional lower frequency bound in Hz.
        freq_max_hz: Optional upper frequency bound in Hz.
        threshold: Minimum confidence threshold (default: 0.2).
        template_duration_ms: Optional template duration in ms to crop to.
        min_energy_ratio: Optional minimum in-band energy ratio for gating.
        start_sounds_dir: Optional directory of pre-game start-sound samples.
        chunk_duration_ms: Optional chunk duration in ms for start sounds.
        chunk_step_ms: Optional chunk step size in ms for start sounds.
        consensus_tolerance_ms: Optional cluster tolerance in ms for samples.
        sample_min_freq_hz: Optional high-pass cutoff in Hz for start sounds.
        sample_max_freq_hz: Optional upper freq cutoff in Hz for start sounds.
        agreement_tolerance_ms: Optional max ms diff for method agreement.
        description: Optional description of this sound effect.
        test_cases: List of example video test cases.
    """

    name: str
    reference_sound_path: str
    freq_min_hz: float | None = None
    freq_max_hz: float | None = None
    threshold: float = DEFAULT_AUDIO_THRESHOLD
    template_duration_ms: int | None = None
    min_energy_ratio: float | None = None
    start_sounds_dir: str | None = None
    chunk_duration_ms: int | None = None
    chunk_step_ms: int | None = None
    consensus_tolerance_ms: int | None = None
    sample_min_freq_hz: float | None = None
    sample_max_freq_hz: float | None = None
    agreement_tolerance_ms: int | None = None
    description: str = ''
    test_cases: list[AudioTestCase] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class TestCaseEvaluationResult:
    """Evaluation result for a single test case.

    Attributes:
        test_case: The evaluated test case.
        passed: Whether a detection occurred within tolerance.
        detected_timestamp_ms: Detected timestamp in ms, or None.
        error_ms: Difference (detected - expected) in ms, or None.
        confidence: Confidence score of the match, or None.
        top_false_positive_confidence: Highest score outside tolerance, or None.
        message: Informative status or error message.
        diagnostic: Optional detailed diagnostic information.
    """

    __test__ = False

    test_case: AudioTestCase
    passed: bool
    detected_timestamp_ms: int | None
    error_ms: int | None
    confidence: float | None
    top_false_positive_confidence: float | None
    message: str = ''
    diagnostic: AudioMatchDiagnostic | None = None
    __test__ = False


@dataclasses.dataclass
class TestCaseAnalysis:
    """Detailed diagnostic analysis for a single test case.

    Attributes:
        test_case: The analyzed test case.
        evaluation: Evaluation result with passed status.
        diagnostic: AudioMatchDiagnostic with peak and penalty breakdown.
        root_cause: Identified cause for failure (or 'PASS').
        recommendation: Actionable suggestion to achieve detection.
    """

    test_case: AudioTestCase
    evaluation: TestCaseEvaluationResult
    diagnostic: AudioMatchDiagnostic | None
    root_cause: str
    recommendation: str
    __test__ = False


@dataclasses.dataclass
class BenchmarkSummary:
    """Summary of benchmark evaluation across all test cases.

    Attributes:
        sound_name: Name of the evaluated sound.
        total_cases: Total number of test cases.
        passed_cases: Number of successful test cases.
        accuracy: Pass rate between 0.0 and 1.0.
        mean_error_ms: Average absolute error in ms for passed cases.
        case_results: Detailed results for each test case.
    """

    sound_name: str
    total_cases: int
    passed_cases: int
    accuracy: float
    mean_error_ms: float | None
    case_results: list[TestCaseEvaluationResult]


@dataclasses.dataclass(frozen=True)
class ConfigurationSuggestion:
    """A concrete configuration adjustment suggested by failure analysis.

    Attributes:
        name: Short descriptive name for the suggestion.
        rationale: Detailed rationale explaining why this change is suggested.
        freq_min_hz: Suggested freq_min_hz, or None if unchanged.
        freq_max_hz: Suggested freq_max_hz, or None if unchanged.
        threshold: Suggested threshold, or None if unchanged.
        template_duration_ms: Suggested template duration, or None if unchanged.
        min_energy_ratio: Suggested min energy ratio, or None if unchanged.
    """

    name: str
    rationale: str
    freq_min_hz: float | None = None
    freq_max_hz: float | None = None
    threshold: float | None = None
    template_duration_ms: int | None = None
    min_energy_ratio: float | None = None
    __test__ = False


@dataclasses.dataclass
class IterationCandidateResult:
    """Outcome of evaluating a suggested configuration candidate.

    Attributes:
        suggestion: The candidate configuration that was evaluated.
        summary: Benchmark evaluation summary with candidate parameters.
        score: Calculated composite ranking score.
    """

    suggestion: ConfigurationSuggestion
    summary: BenchmarkSummary
    score: float
    __test__ = False


@dataclasses.dataclass
class BenchmarkAnalysis:
    """Summary of comprehensive benchmark analysis across all test cases.

    Attributes:
        sound_name: Name of evaluated sound.
        total_cases: Total number of test cases.
        passed_cases: Number of passing test cases.
        min_true_peak_confidence: Lowest true hit confidence across all cases.
        max_false_positive_confidence: Highest false positive confidence.
        reconciling_threshold: Threshold passing all cases (if margin > 0).
        case_analyses: Detailed analysis for each test case.
        suggestions: Concrete suggested configuration adjustments.
        iteration_results: Evaluated suggestion results if iterate was run.
        best_iteration: Winning candidate result if iterate was run.
    """

    sound_name: str
    total_cases: int
    passed_cases: int
    min_true_peak_confidence: float | None
    max_false_positive_confidence: float | None
    reconciling_threshold: float | None
    case_analyses: list[TestCaseAnalysis]
    suggestions: list[ConfigurationSuggestion] = dataclasses.field(
        default_factory=list
    )
    iteration_results: list[IterationCandidateResult] | None = None
    best_iteration: IterationCandidateResult | None = None


@dataclasses.dataclass
class TuningResult:
    """Optimal parameters found during tuning sweep.

    Attributes:
        best_freq_min_hz: Optimal lower frequency bound in Hz.
        best_freq_max_hz: Optimal upper frequency bound in Hz.
        best_threshold: Optimal confidence threshold.
        best_accuracy: Pass rate achieved with best parameters.
        best_mean_error_ms: Mean absolute error in ms for passed cases.
        summary: Full benchmark summary of the best configuration.
        best_chunk_duration_ms: Optimal chunk duration in ms for start sounds.
        best_chunk_step_ms: Optimal chunk step in ms for start sounds.
        best_consensus_tolerance_ms: Optimal cluster tolerance in ms.
        best_sample_min_freq_hz: Optimal high-pass cutoff in Hz for samples.
        best_sample_max_freq_hz: Optimal upper freq cutoff in Hz for samples.
    """

    best_freq_min_hz: float | None
    best_freq_max_hz: float | None
    best_threshold: float
    best_accuracy: float
    best_mean_error_ms: float | None
    summary: BenchmarkSummary
    best_chunk_duration_ms: int | None = None
    best_chunk_step_ms: int | None = None
    best_consensus_tolerance_ms: int | None = None
    best_sample_min_freq_hz: float | None = None
    best_sample_max_freq_hz: float | None = None


class AudioBenchmarkRunner:
    """Runs evaluations and parameter tuning for sound definitions.

    Loads and saves YAML configurations, evaluates test cases, computes
    performance metrics, and optimizes frequency ranges and thresholds.
    """

    def __init__(self, matcher: AudioMatcher | None = None) -> None:
        """Initializes the benchmark runner.

        Args:
            matcher: Optional custom AudioMatcher instance.
        """
        self._matcher = matcher if matcher is not None else AudioMatcher()

    def load_from_yaml(self, path: str | Path) -> SoundDefinition:
        """Loads a SoundDefinition and test cases from a YAML file.

        Relative file paths are resolved relative to the YAML file's directory.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            SoundDefinition: Parsed sound definition and test cases.

        Raises:
            FileNotFoundError: If the YAML file, reference sound, or any test
                case video does not exist.
            ValueError: If required fields are missing in the YAML file.
        """
        yaml_path = Path(path).resolve()
        if not yaml_path.exists():
            raise FileNotFoundError(f'Config file not found: {yaml_path}')

        with open(yaml_path, 'r', encoding='utf-8') as file_obj:
            raw_data = yaml.safe_load(file_obj)

        if not isinstance(raw_data, dict):
            raise ValueError(f'Invalid YAML configuration in {yaml_path}')

        name = raw_data.get('name')
        if not name:
            raise ValueError("Missing required field 'name' in config.")

        ref_path = raw_data.get('reference_sound_path')
        if not ref_path:
            raise ValueError(
                "Missing required field 'reference_sound_path' in config."
            )

        base_dir = yaml_path.parent
        resolved_ref_path = self._resolve_path(base_dir, ref_path)
        if not Path(resolved_ref_path).exists():
            raise FileNotFoundError(
                f'Reference sound file not found: {resolved_ref_path}'
            )

        raw_start_dir = raw_data.get('start_sounds_dir')
        resolved_start_dir = (
            self._resolve_path(base_dir, str(raw_start_dir))
            if raw_start_dir
            else None
        )

        test_cases: list[AudioTestCase] = []
        raw_cases = raw_data.get('test_cases', [])
        for case_data in raw_cases:
            if not isinstance(case_data, dict):
                continue
            video_p = case_data.get('video_path')
            if not video_p:
                continue
            resolved_video_p = self._resolve_path(base_dir, video_p)
            if not Path(resolved_video_p).exists():
                raise FileNotFoundError(
                    f'Test case video file not found: {resolved_video_p}'
                )
            target_type, resolved_target_audio = self._parse_test_case_target(
                case_data=case_data,
                base_dir=base_dir,
                start_sounds_dir=resolved_start_dir,
            )
            test_cases.append(
                AudioTestCase(
                    video_path=resolved_video_p,
                    expected_timestamp_ms=int(
                        case_data.get('expected_timestamp_ms', 0)
                    ),
                    tolerance_ms=int(case_data.get('tolerance_ms', 500)),
                    search_start_ms=case_data.get('search_start_ms'),
                    search_end_ms=case_data.get('search_end_ms'),
                    description=case_data.get('description', ''),
                    target_type=target_type,
                    target_audio_path=resolved_target_audio,
                )
            )

        return SoundDefinition(
            name=str(name),
            reference_sound_path=resolved_ref_path,
            freq_min_hz=raw_data.get('freq_min_hz'),
            freq_max_hz=raw_data.get('freq_max_hz'),
            threshold=float(raw_data.get('threshold', 0.2)),
            template_duration_ms=(
                int(raw_data['template_duration_ms'])
                if 'template_duration_ms' in raw_data
                and raw_data['template_duration_ms'] is not None
                else None
            ),
            min_energy_ratio=(
                float(raw_data['min_energy_ratio'])
                if 'min_energy_ratio' in raw_data
                and raw_data['min_energy_ratio'] is not None
                else None
            ),
            start_sounds_dir=resolved_start_dir,
            chunk_duration_ms=(
                int(raw_data['chunk_duration_ms'])
                if raw_data.get('chunk_duration_ms') is not None
                else None
            ),
            chunk_step_ms=(
                int(raw_data['chunk_step_ms'])
                if raw_data.get('chunk_step_ms') is not None
                else None
            ),
            consensus_tolerance_ms=(
                int(raw_data['consensus_tolerance_ms'])
                if raw_data.get('consensus_tolerance_ms') is not None
                else None
            ),
            sample_min_freq_hz=(
                float(raw_data['sample_min_freq_hz'])
                if raw_data.get('sample_min_freq_hz') is not None
                else None
            ),
            sample_max_freq_hz=(
                float(raw_data['sample_max_freq_hz'])
                if raw_data.get('sample_max_freq_hz') is not None
                else None
            ),
            agreement_tolerance_ms=(
                int(raw_data['agreement_tolerance_ms'])
                if raw_data.get('agreement_tolerance_ms') is not None
                else None
            ),
            description=raw_data.get('description', ''),
            test_cases=test_cases,
        )

    def _parse_test_case_target(
        self,
        case_data: dict[str, object],
        base_dir: Path,
        start_sounds_dir: str | None,
    ) -> tuple[AudioTargetType, str | None]:
        """Parses and validates target_type and target_audio_path for a case.

        Args:
            case_data: Raw dictionary for one test case from YAML.
            base_dir: Directory containing the YAML file.
            start_sounds_dir: Optional resolved start-sounds directory.

        Returns:
            tuple[AudioTargetType, str | None]: Parsed target type and
                resolved target audio file path (or None for siren).

        Raises:
            ValueError: If target_type is invalid or target_audio_path is
                missing/conflicting.
            FileNotFoundError: If target_audio_path does not exist.
        """
        raw_target_type = case_data.get('target_type')
        raw_target_audio = case_data.get('target_audio_path')

        if raw_target_type is None:
            target_type = (
                AudioTargetType.AUDIO_FILE
                if raw_target_audio
                else AudioTargetType.SIREN
            )
        else:
            try:
                target_type = AudioTargetType(str(raw_target_type))
            except ValueError as err:
                valid = ', '.join(t.value for t in AudioTargetType)
                raise ValueError(
                    f"Invalid target_type '{raw_target_type}'. "
                    f'Must be one of: {valid}.'
                ) from err

        if target_type == AudioTargetType.SIREN:
            if raw_target_audio:
                raise ValueError(
                    "Test case with target_type 'siren' cannot specify "
                    "'target_audio_path'."
                )
            return target_type, None

        if not raw_target_audio:
            raise ValueError(
                "Test case with target_type 'audio_file' must specify "
                "'target_audio_path'."
            )

        target_str = str(raw_target_audio)
        resolved_target = self._resolve_path(base_dir, target_str)
        if (
            not Path(resolved_target).exists()
            and start_sounds_dir is not None
            and not Path(target_str).is_absolute()
        ):
            in_start_dir = self._resolve_path(
                Path(start_sounds_dir), target_str
            )
            if Path(in_start_dir).exists():
                resolved_target = in_start_dir

        if not Path(resolved_target).exists():
            raise FileNotFoundError(
                f'Target audio file not found: {resolved_target}'
            )
        return target_type, resolved_target

    def save_to_yaml(
        self, sound_def: SoundDefinition, path: str | Path
    ) -> None:
        """Saves a SoundDefinition to a YAML configuration file.

        Args:
            sound_def: SoundDefinition instance to serialize.
            path: Destination path for the YAML file.
        """
        dest_path = Path(path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, object] = {
            'name': sound_def.name,
            'description': sound_def.description,
            'reference_sound_path': sound_def.reference_sound_path,
            'freq_min_hz': sound_def.freq_min_hz,
            'freq_max_hz': sound_def.freq_max_hz,
            'threshold': sound_def.threshold,
        }
        if sound_def.template_duration_ms is not None:
            data['template_duration_ms'] = sound_def.template_duration_ms
        if sound_def.min_energy_ratio is not None:
            data['min_energy_ratio'] = sound_def.min_energy_ratio
        if sound_def.start_sounds_dir is not None:
            data['start_sounds_dir'] = sound_def.start_sounds_dir
        if sound_def.chunk_duration_ms is not None:
            data['chunk_duration_ms'] = sound_def.chunk_duration_ms
        if sound_def.chunk_step_ms is not None:
            data['chunk_step_ms'] = sound_def.chunk_step_ms
        if sound_def.consensus_tolerance_ms is not None:
            data['consensus_tolerance_ms'] = sound_def.consensus_tolerance_ms
        if sound_def.sample_min_freq_hz is not None:
            data['sample_min_freq_hz'] = sound_def.sample_min_freq_hz
        if sound_def.sample_max_freq_hz is not None:
            data['sample_max_freq_hz'] = sound_def.sample_max_freq_hz
        if sound_def.agreement_tolerance_ms is not None:
            data['agreement_tolerance_ms'] = sound_def.agreement_tolerance_ms

        serialized_cases: list[dict[str, object]] = []
        for tc in sound_def.test_cases:
            case_dict: dict[str, object] = {
                'video_path': tc.video_path,
                'expected_timestamp_ms': tc.expected_timestamp_ms,
                'tolerance_ms': tc.tolerance_ms,
                'search_start_ms': tc.search_start_ms,
                'search_end_ms': tc.search_end_ms,
                'target_type': tc.target_type.value,
            }
            if tc.target_audio_path is not None:
                case_dict['target_audio_path'] = tc.target_audio_path
            case_dict['description'] = tc.description
            serialized_cases.append(case_dict)
        data['test_cases'] = serialized_cases

        with open(dest_path, 'w', encoding='utf-8') as file_obj:
            yaml.dump(data, file_obj, sort_keys=False, indent=2)

    def evaluate_test_case(
        self,
        sound_def: SoundDefinition,
        test_case: AudioTestCase,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        threshold: float | None = None,
        template_duration_ms: int | None = None,
        min_energy_ratio: float | None = None,
        chunk_duration_ms: int | None = None,
        chunk_step_ms: int | None = None,
        consensus_tolerance_ms: int | None = None,
        sample_min_freq_hz: float | None = None,
        sample_max_freq_hz: float | None = None,
        ignore_search_window: bool = False,
    ) -> TestCaseEvaluationResult:
        """Evaluates audio matching on a single test case.

        Args:
            sound_def: Sound definition containing reference sound.
            test_case: The test case to evaluate.
            freq_min_hz: Optional lower frequency bound override.
            freq_max_hz: Optional upper frequency bound override.
            threshold: Optional confidence threshold override.
            template_duration_ms: Optional template duration in ms override.
            min_energy_ratio: Optional min energy ratio override.
            chunk_duration_ms: Optional chunk duration override for samples.
            chunk_step_ms: Optional chunk step override for samples.
            consensus_tolerance_ms: Optional cluster tolerance override.
            sample_min_freq_hz: Optional high-pass cutoff for samples.
            sample_max_freq_hz: Optional upper freq cutoff for samples.
            ignore_search_window: If True, ignores test_case search bounds
                and searches the entire file.

        Returns:
            TestCaseEvaluationResult: Detailed outcome of the test case.

        Raises:
            FileNotFoundError: If the video or reference sound file is missing.
            RuntimeError: If audio decoding or extraction fails.
            ValueError: If audio duration is shorter than the reference sound.
        """
        video_path = Path(test_case.video_path)
        if not video_path.exists():
            raise FileNotFoundError(f'Video file not found: {video_path}')

        search_start = (
            None if ignore_search_window else test_case.search_start_ms
        )
        search_end = None if ignore_search_window else test_case.search_end_ms

        eff_thresh = threshold if threshold is not None else sound_def.threshold
        eff_energy_ratio = (
            min_energy_ratio
            if min_energy_ratio is not None
            else sound_def.min_energy_ratio
        )

        if (
            test_case.target_type == AudioTargetType.AUDIO_FILE
            and test_case.target_audio_path is not None
        ):
            target_audio_file = Path(test_case.target_audio_path)
            if not target_audio_file.exists():
                raise FileNotFoundError(
                    f'Target audio file not found: {target_audio_file}'
                )
            eff_chunk_dur = (
                chunk_duration_ms
                if chunk_duration_ms is not None
                else (
                    sound_def.chunk_duration_ms
                    if sound_def.chunk_duration_ms is not None
                    else DEFAULT_CHUNK_DURATION_MS
                )
            )
            eff_chunk_step = (
                chunk_step_ms
                if chunk_step_ms is not None
                else (
                    sound_def.chunk_step_ms
                    if sound_def.chunk_step_ms is not None
                    else DEFAULT_CHUNK_STEP_MS
                )
            )
            eff_consensus_tol = (
                consensus_tolerance_ms
                if consensus_tolerance_ms is not None
                else (
                    sound_def.consensus_tolerance_ms
                    if sound_def.consensus_tolerance_ms is not None
                    else DEFAULT_CONSENSUS_TOLERANCE_MS
                )
            )
            eff_sample_fmin = (
                sample_min_freq_hz
                if sample_min_freq_hz is not None
                else (
                    sound_def.sample_min_freq_hz
                    if sound_def.sample_min_freq_hz is not None
                    else DEFAULT_SAMPLE_HIGH_PASS_HZ
                )
            )
            eff_sample_fmax = (
                sample_max_freq_hz
                if sample_max_freq_hz is not None
                else (
                    sound_def.sample_max_freq_hz
                    if sound_def.sample_max_freq_hz is not None
                    else DEFAULT_SAMPLE_MAX_FREQ_HZ
                )
            )
            sample_matcher = StartSoundMatcher(
                audio_matcher=self._matcher,
                chunk_duration_ms=eff_chunk_dur,
                chunk_step_ms=eff_chunk_step,
                consensus_tolerance_ms=eff_consensus_tol,
                min_freq_hz=eff_sample_fmin,
                max_freq_hz=eff_sample_fmax,
            )
            matches, diag = sample_matcher.match_sample_diagnostic(
                video_or_audio_path=test_case.video_path,
                sample_path=target_audio_file,
                expected_timestamp_ms=test_case.expected_timestamp_ms,
                tolerance_ms=test_case.tolerance_ms,
                threshold=eff_thresh,
                start_ms=search_start,
                end_ms=search_end,
            )
            return self._evaluate_matches(test_case, matches, diagnostic=diag)

        eff_min = (
            freq_min_hz if freq_min_hz is not None else sound_def.freq_min_hz
        )
        eff_max = (
            freq_max_hz if freq_max_hz is not None else sound_def.freq_max_hz
        )
        eff_duration_ms = (
            template_duration_ms
            if template_duration_ms is not None
            else sound_def.template_duration_ms
        )

        matches, diag = self._matcher.match_diagnostic(
            video_or_audio_path=test_case.video_path,
            reference_sound_path=sound_def.reference_sound_path,
            expected_timestamp_ms=test_case.expected_timestamp_ms,
            tolerance_ms=test_case.tolerance_ms,
            threshold=eff_thresh,
            start_ms=search_start,
            end_ms=search_end,
            freq_min_hz=eff_min,
            freq_max_hz=eff_max,
            template_duration_ms=eff_duration_ms,
            min_energy_ratio=eff_energy_ratio,
            two_stage=(eff_duration_ms is not None and eff_duration_ms > 0),
        )

        return self._evaluate_matches(test_case, matches, diagnostic=diag)

    def evaluate(
        self,
        sound_def: SoundDefinition,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        threshold: float | None = None,
        template_duration_ms: int | None = None,
        min_energy_ratio: float | None = None,
        ignore_search_window: bool = False,
    ) -> BenchmarkSummary:
        """Evaluates all test cases in a sound definition.

        Args:
            sound_def: Sound definition with example test cases.
            freq_min_hz: Optional lower frequency bound override.
            freq_max_hz: Optional upper frequency bound override.
            threshold: Optional confidence threshold override.
            template_duration_ms: Optional template duration in ms override.
            min_energy_ratio: Optional min energy ratio override.
            ignore_search_window: If True, ignores test_case search bounds.

        Returns:
            BenchmarkSummary: Aggregated benchmark summary and case results.
        """
        results: list[TestCaseEvaluationResult] = []
        for tc in sound_def.test_cases:
            res = self.evaluate_test_case(
                sound_def=sound_def,
                test_case=tc,
                freq_min_hz=freq_min_hz,
                freq_max_hz=freq_max_hz,
                threshold=threshold,
                template_duration_ms=template_duration_ms,
                min_energy_ratio=min_energy_ratio,
                ignore_search_window=ignore_search_window,
            )
            results.append(res)

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        accuracy = (passed / total) if total > 0 else 0.0

        errors = [
            abs(r.error_ms)
            for r in results
            if r.passed and r.error_ms is not None
        ]
        mean_error = (sum(errors) / len(errors)) if errors else None

        return BenchmarkSummary(
            sound_name=sound_def.name,
            total_cases=total,
            passed_cases=passed,
            accuracy=accuracy,
            mean_error_ms=mean_error,
            case_results=results,
        )

    def analyze(
        self,
        sound_def: SoundDefinition,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        threshold: float | None = None,
        template_duration_ms: int | None = None,
        min_energy_ratio: float | None = None,
        iterate: bool = False,
        ignore_search_window: bool = False,
    ) -> BenchmarkAnalysis:
        """Analyzes test cases with detailed failure diagnostics.

        Evaluates each test case, computes true-positive peaks and
        false-positive ceilings, identifies failure root causes, calculates
        reconciling thresholds, generates suggested configuration changes, and
        optionally iterates through suggestions to find the best configuration.

        Args:
            sound_def: Sound definition containing reference and test cases.
            freq_min_hz: Optional lower frequency cutoff in Hz override.
            freq_max_hz: Optional upper frequency cutoff in Hz override.
            threshold: Optional threshold override.
            template_duration_ms: Optional template duration in ms override.
            min_energy_ratio: Optional min energy ratio override.
            iterate: If True, evaluates each suggested configuration change.
            ignore_search_window: If True, ignores test_case search bounds.

        Returns:
            BenchmarkAnalysis: Comprehensive analysis across all test cases.
        """
        eff_thresh = threshold if threshold is not None else sound_def.threshold
        eff_fmin = (
            freq_min_hz if freq_min_hz is not None else sound_def.freq_min_hz
        )
        eff_fmax = (
            freq_max_hz if freq_max_hz is not None else sound_def.freq_max_hz
        )
        eff_duration_ms = (
            template_duration_ms
            if template_duration_ms is not None
            else sound_def.template_duration_ms
        )
        eff_energy_ratio = (
            min_energy_ratio
            if min_energy_ratio is not None
            else sound_def.min_energy_ratio
        )
        case_analyses: list[TestCaseAnalysis] = []
        true_peaks: list[float] = []
        false_positives: list[float] = []

        for tc in sound_def.test_cases:
            res = self.evaluate_test_case(
                sound_def=sound_def,
                test_case=tc,
                freq_min_hz=eff_fmin,
                freq_max_hz=eff_fmax,
                threshold=eff_thresh,
                template_duration_ms=eff_duration_ms,
                min_energy_ratio=eff_energy_ratio,
                ignore_search_window=ignore_search_window,
            )
            diag = res.diagnostic
            root_cause = 'PASS'
            recommendation = 'Detection successful within tolerance.'

            if not res.passed:
                if diag is None or diag.expected_peak_confidence is None:
                    root_cause = 'NO_SIGNAL'
                    recommendation = (
                        'No peak detected near expected timestamp. Verify '
                        'timestamp or widen search window/frequency bounds.'
                    )
                else:
                    exp_conf = diag.expected_peak_confidence
                    top_fp = diag.top_false_positive_confidence
                    raw_corr = diag.expected_peak_raw_correlation or 0.0
                    vocal_pen = diag.expected_peak_vocal_penalty or 1.0

                    if (
                        raw_corr >= 0.25
                        and vocal_pen < 0.6
                        and exp_conf < eff_thresh
                    ):
                        root_cause = 'VOCAL_PENALTY_SUPPRESSION'
                        recommendation = (
                            f'Raw correlation was {raw_corr:.3f}, but vocal '
                            f'penalty {vocal_pen:.3f} reduced confidence to '
                            f'{exp_conf:.3f}. Try increasing freq_min_hz.'
                        )
                    elif top_fp is not None and top_fp >= exp_conf:
                        root_cause = 'FALSE_POSITIVE_DOMINANCE'
                        fp_ts = diag.top_false_positive_timestamp_ms
                        recommendation = (
                            f'Out-of-tolerance noise at {fp_ts}ms '
                            f'({top_fp:.3f}) exceeds true peak '
                            f'({exp_conf:.3f}). Restrict search window or '
                            f'adjust frequency band.'
                        )
                    else:
                        root_cause = 'THRESHOLD_TOO_HIGH'
                        recom = (
                            round((exp_conf + top_fp) / 2.0, 3)
                            if top_fp is not None
                            else round(exp_conf * 0.9, 3)
                        )
                        recommendation = (
                            f'Peak exists at expected time with confidence '
                            f'{exp_conf:.3f} (threshold is {eff_thresh:.3f}). '
                            f'Lower threshold to ~{recom:.3f} to pass.'
                        )

            if diag is not None:
                if diag.expected_peak_confidence is not None:
                    true_peaks.append(diag.expected_peak_confidence)
                if diag.top_false_positive_confidence is not None:
                    false_positives.append(diag.top_false_positive_confidence)

            case_analyses.append(
                TestCaseAnalysis(
                    test_case=tc,
                    evaluation=res,
                    diagnostic=diag,
                    root_cause=root_cause,
                    recommendation=recommendation,
                )
            )

        min_tp = min(true_peaks) if true_peaks else None
        max_fp = max(false_positives) if false_positives else None
        reconciling_thresh: float | None = None

        if min_tp is not None:
            if max_fp is None:
                reconciling_thresh = round(min_tp * 0.85, 3)
            elif min_tp > max_fp:
                reconciling_thresh = round((min_tp + max_fp) / 2.0, 3)

        ref_duration_ms: float = 0.0
        ref_audio = self._matcher._load_audio(sound_def.reference_sound_path)
        ref_duration_ms = (len(ref_audio) / self._matcher.sample_rate) * 1000.0

        suggestions: list[ConfigurationSuggestion] = []
        has_vocal_pen = any(
            c.root_cause == 'VOCAL_PENALTY_SUPPRESSION' for c in case_analyses
        )
        has_fp_dom = any(
            c.root_cause == 'FALSE_POSITIVE_DOMINANCE' for c in case_analyses
        )
        has_thresh_high = any(
            c.root_cause == 'THRESHOLD_TOO_HIGH' for c in case_analyses
        )

        if reconciling_thresh is not None and reconciling_thresh != eff_thresh:
            margin_info = (
                f' (margin: {min_tp - max_fp:+.3f})'
                if min_tp is not None and max_fp is not None
                else ''
            )
            fp_info = f'{max_fp:.3f}' if max_fp is not None else '0.000'
            suggestions.append(
                ConfigurationSuggestion(
                    name='Reconciling Threshold',
                    freq_min_hz=eff_fmin,
                    freq_max_hz=eff_fmax,
                    threshold=reconciling_thresh,
                    template_duration_ms=eff_duration_ms,
                    min_energy_ratio=eff_energy_ratio,
                    rationale=(
                        f'Discovered threshold between min true peak '
                        f'({min_tp:.3f}) and false positive ceiling '
                        f'({fp_info}){margin_info} that passes all cases.'
                    ),
                )
            )

        if has_vocal_pen:
            curr_fmin = eff_fmin or 1000.0
            raised_fmin = round(max(curr_fmin + 200.0, 1400.0), 1)
            suggestions.append(
                ConfigurationSuggestion(
                    name='Mitigate Vocal Suppression',
                    freq_min_hz=raised_fmin,
                    freq_max_hz=eff_fmax,
                    threshold=reconciling_thresh or eff_thresh,
                    template_duration_ms=eff_duration_ms,
                    min_energy_ratio=eff_energy_ratio,
                    rationale=(
                        f'Increases freq_min_hz from {curr_fmin} to '
                        f'{raised_fmin} to reduce vocal penalty suppression.'
                    ),
                )
            )

        if has_fp_dom:
            curr_fmax = eff_fmax or 2500.0
            narrowed_fmax = round(max(curr_fmax - 200.0, 2000.0), 1)
            suggestions.append(
                ConfigurationSuggestion(
                    name='Narrow Upper Frequency Band',
                    freq_min_hz=eff_fmin,
                    freq_max_hz=narrowed_fmax,
                    threshold=reconciling_thresh or eff_thresh,
                    template_duration_ms=eff_duration_ms,
                    min_energy_ratio=eff_energy_ratio,
                    rationale=(
                        f'Restricts freq_max_hz from {curr_fmax} to '
                        f'{narrowed_fmax} to filter out out-of-band energy.'
                    ),
                )
            )

        if (
            min_tp is not None
            and max_fp is not None
            and min_tp > max_fp
            and (min_tp - max_fp) > 0.08
        ):
            safe_th = round(min_tp * 0.75 + max_fp * 0.25, 3)
            if safe_th != reconciling_thresh:
                suggestions.append(
                    ConfigurationSuggestion(
                        name='High-Margin Safe Threshold',
                        freq_min_hz=eff_fmin,
                        freq_max_hz=eff_fmax,
                        threshold=safe_th,
                        template_duration_ms=eff_duration_ms,
                        min_energy_ratio=eff_energy_ratio,
                        rationale=(
                            f'Sets threshold at {safe_th:.3f} closer to false '
                            f'positive floor ({max_fp:.3f}) for extra margin.'
                        ),
                    )
                )

        if (
            has_thresh_high
            and max_fp is None
            and min_tp is not None
            and reconciling_thresh is None
        ):
            lowered_th = round(min_tp * 0.85, 3)
            suggestions.append(
                ConfigurationSuggestion(
                    name='Lower Threshold',
                    freq_min_hz=eff_fmin,
                    freq_max_hz=eff_fmax,
                    threshold=lowered_th,
                    template_duration_ms=eff_duration_ms,
                    min_energy_ratio=eff_energy_ratio,
                    rationale=(
                        f'Lowers threshold from {eff_thresh:.3f} to '
                        f'{lowered_th:.3f} below observed peak ({min_tp:.3f}).'
                    ),
                )
            )

        if ref_duration_ms > 1500.0 and eff_duration_ms is None:
            suggestions.append(
                ConfigurationSuggestion(
                    name='Crop Template to 800ms',
                    freq_min_hz=eff_fmin,
                    freq_max_hz=eff_fmax,
                    threshold=eff_thresh,
                    template_duration_ms=800,
                    min_energy_ratio=eff_energy_ratio,
                    rationale=(
                        f'Reference audio is {ref_duration_ms:.0f}ms long. '
                        'Cropping template to the initial 800ms blast avoids '
                        'reverberation and echo decay mismatches.'
                    ),
                )
            )

        if eff_energy_ratio is None:
            suggestions.append(
                ConfigurationSuggestion(
                    name='Apply In-Band Energy Gating',
                    freq_min_hz=eff_fmin,
                    freq_max_hz=eff_fmax,
                    threshold=eff_thresh,
                    template_duration_ms=eff_duration_ms,
                    min_energy_ratio=0.1,
                    rationale=(
                        'Gates correlation scores by relative in-band energy '
                        'to suppress phantom matches during quiet sections.'
                    ),
                )
            )

        if (
            ref_duration_ms > 1500.0
            and eff_duration_ms is None
            and eff_energy_ratio is None
        ):
            suggestions.append(
                ConfigurationSuggestion(
                    name='Crop Template to 800ms with Energy Gating',
                    freq_min_hz=eff_fmin,
                    freq_max_hz=eff_fmax,
                    threshold=eff_thresh,
                    template_duration_ms=800,
                    min_energy_ratio=0.1,
                    rationale=(
                        'Combines 800ms template cropping with in-band energy '
                        'gating to reject reverberation and quiet room noise.'
                    ),
                )
            )

        iteration_results: list[IterationCandidateResult] | None = None
        best_iteration: IterationCandidateResult | None = None

        if iterate and suggestions:
            iteration_results = []
            best_score = -1e9

            base_sug = ConfigurationSuggestion(
                name='Current Configuration',
                freq_min_hz=eff_fmin,
                freq_max_hz=eff_fmax,
                threshold=eff_thresh,
                template_duration_ms=eff_duration_ms,
                min_energy_ratio=eff_energy_ratio,
                rationale='Existing configuration settings before change.',
            )
            candidates_to_eval = [base_sug] + list(suggestions)

            for cand_sug in candidates_to_eval:
                cand_def = SoundDefinition(
                    name=sound_def.name,
                    reference_sound_path=sound_def.reference_sound_path,
                    freq_min_hz=cand_sug.freq_min_hz,
                    freq_max_hz=cand_sug.freq_max_hz,
                    threshold=(
                        cand_sug.threshold
                        if cand_sug.threshold is not None
                        else eff_thresh
                    ),
                    template_duration_ms=(
                        cand_sug.template_duration_ms
                        if cand_sug.template_duration_ms is not None
                        else eff_duration_ms
                    ),
                    min_energy_ratio=(
                        cand_sug.min_energy_ratio
                        if cand_sug.min_energy_ratio is not None
                        else eff_energy_ratio
                    ),
                    start_sounds_dir=sound_def.start_sounds_dir,
                    description=sound_def.description,
                    test_cases=sound_def.test_cases,
                )
                summary = self.evaluate(
                    cand_def, ignore_search_window=ignore_search_window
                )
                score = self._compute_tuning_score(summary)
                cand_res = IterationCandidateResult(
                    suggestion=cand_sug,
                    summary=summary,
                    score=score,
                )
                iteration_results.append(cand_res)
                if score > best_score:
                    best_score = score
                    best_iteration = cand_res

        passed_count = sum(1 for c in case_analyses if c.evaluation.passed)
        return BenchmarkAnalysis(
            sound_name=sound_def.name,
            total_cases=len(case_analyses),
            passed_cases=passed_count,
            min_true_peak_confidence=min_tp,
            max_false_positive_confidence=max_fp,
            reconciling_threshold=reconciling_thresh,
            case_analyses=case_analyses,
            suggestions=suggestions,
            iteration_results=iteration_results,
            best_iteration=best_iteration,
        )

    def tune(
        self,
        sound_def: SoundDefinition,
        min_freq_candidates: list[float] | None = None,
        max_freq_candidates: list[float] | None = None,
        threshold_candidates: list[float] | None = None,
        chunk_duration_candidates: list[int] | None = None,
        chunk_step_candidates: list[int] | None = None,
        consensus_tolerance_candidates: list[int] | None = None,
        sample_min_freq_candidates: list[float] | None = None,
        sample_max_freq_candidates: list[float] | None = None,
    ) -> TuningResult:
        """Finds optimal parameters for siren and start-sound samples.

        Evaluates parameter combinations for both siren matching (frequency
        bounds) and pre-game start-sound sample matching (chunk duration/step,
        consensus tolerance, sample frequency band), performs failure analysis
        to discover reconciling thresholds, and adaptively expands search
        boundaries when siren test cases fail.

        Args:
            sound_def: Sound definition with test cases.
            min_freq_candidates: Optional lower frequency cutoffs for siren.
            max_freq_candidates: Optional upper frequency cutoffs for siren.
            threshold_candidates: Optional thresholds to evaluate.
            chunk_duration_candidates: Optional chunk durations in ms.
            chunk_step_candidates: Optional chunk step sizes in ms.
            consensus_tolerance_candidates: Optional cluster tolerances in ms.
            sample_min_freq_candidates: Optional high-pass cutoffs for samples.
            sample_max_freq_candidates: Optional upper freq cutoffs for samples.

        Returns:
            TuningResult: Optimal parameter values and benchmark summary.
        """
        min_freqs = (
            list(min_freq_candidates)
            if min_freq_candidates
            else [
                sound_def.freq_min_hz or 1000.0,
                1200.0,
                1400.0,
                1600.0,
            ]
        )
        max_freqs = (
            list(max_freq_candidates)
            if max_freq_candidates
            else [
                sound_def.freq_max_hz or 2500.0,
                2200.0,
                2400.0,
                2600.0,
            ]
        )
        thresholds = (
            list(threshold_candidates)
            if threshold_candidates
            else [
                0.15,
                0.20,
                0.25,
            ]
        )

        siren_cases = [
            tc
            for tc in sound_def.test_cases
            if tc.target_type == AudioTargetType.SIREN
        ]
        audio_file_cases = [
            tc
            for tc in sound_def.test_cases
            if tc.target_type == AudioTargetType.AUDIO_FILE
        ]

        best_sample_params: tuple[int, int, int, float, float] | None = None
        if audio_file_cases:
            best_sample_params = self._tune_sample_parameters(
                sound_def=sound_def,
                audio_file_cases=audio_file_cases,
                thresholds=thresholds,
                chunk_duration_candidates=chunk_duration_candidates,
                chunk_step_candidates=chunk_step_candidates,
                consensus_tolerance_candidates=consensus_tolerance_candidates,
                sample_min_freq_candidates=sample_min_freq_candidates,
                sample_max_freq_candidates=sample_max_freq_candidates,
            )

        best_tuple: tuple[float, float, float] | None = None
        best_summary: BenchmarkSummary | None = None
        best_score = -1e9
        evaluated_pairs: set[tuple[float, float]] = set()
        audio_file_cache: dict[float, list[TestCaseEvaluationResult]] = {}

        def _get_audio_file_results(
            thresh: float,
        ) -> list[TestCaseEvaluationResult]:
            if thresh not in audio_file_cache:
                s_dur = best_sample_params[0] if best_sample_params else None
                s_step = best_sample_params[1] if best_sample_params else None
                s_tol = best_sample_params[2] if best_sample_params else None
                s_fmin = best_sample_params[3] if best_sample_params else None
                s_fmax = best_sample_params[4] if best_sample_params else None
                audio_file_cache[thresh] = [
                    self.evaluate_test_case(
                        sound_def=sound_def,
                        test_case=tc,
                        threshold=thresh,
                        chunk_duration_ms=s_dur,
                        chunk_step_ms=s_step,
                        consensus_tolerance_ms=s_tol,
                        sample_min_freq_hz=s_fmin,
                        sample_max_freq_hz=s_fmax,
                    )
                    for tc in audio_file_cases
                ]
            return audio_file_cache[thresh]

        def _combine_summary(
            siren_results: list[TestCaseEvaluationResult],
            audio_results: list[TestCaseEvaluationResult],
        ) -> BenchmarkSummary:
            siren_iter = iter(siren_results)
            audio_iter = iter(audio_results)
            ordered: list[TestCaseEvaluationResult] = []
            for tc in sound_def.test_cases:
                if tc.target_type == AudioTargetType.AUDIO_FILE:
                    ordered.append(next(audio_iter))
                else:
                    ordered.append(next(siren_iter))
            total = len(ordered)
            passed = sum(1 for r in ordered if r.passed)
            accuracy = (passed / total) if total > 0 else 0.0
            errors = [
                abs(r.error_ms)
                for r in ordered
                if r.passed and r.error_ms is not None
            ]
            mean_error = (sum(errors) / len(errors)) if errors else None
            return BenchmarkSummary(
                sound_name=sound_def.name,
                total_cases=total,
                passed_cases=passed,
                accuracy=accuracy,
                mean_error_ms=mean_error,
                case_results=ordered,
            )

        def _eval_pair(f_min: float, f_max: float) -> None:
            nonlocal best_tuple, best_summary, best_score
            pair = (f_min, f_max)
            if pair in evaluated_pairs or f_min >= f_max:
                return
            evaluated_pairs.add(pair)

            siren_def = dataclasses.replace(sound_def, test_cases=siren_cases)
            analysis = self.analyze(
                sound_def=siren_def,
                freq_min_hz=f_min,
                freq_max_hz=f_max,
            )

            tested_thresh = list(thresholds)
            if analysis.reconciling_threshold is not None:
                tested_thresh.append(analysis.reconciling_threshold)

            for thresh in tested_thresh:
                siren_summary = self.evaluate(
                    sound_def=siren_def,
                    freq_min_hz=f_min,
                    freq_max_hz=f_max,
                    threshold=thresh,
                )
                audio_results = _get_audio_file_results(thresh)
                summary = _combine_summary(
                    siren_summary.case_results, audio_results
                )
                score = self._compute_tuning_score(summary)
                if score > best_score or best_summary is None:
                    best_score = score
                    best_tuple = (f_min, f_max, thresh)
                    best_summary = summary

        if not siren_cases and audio_file_cases:
            analysis = self.analyze(sound_def=sound_def)
            tested_thresh = list(thresholds)
            if analysis.reconciling_threshold is not None:
                tested_thresh.append(analysis.reconciling_threshold)
            base_fmin = sound_def.freq_min_hz or 0.0
            base_fmax = sound_def.freq_max_hz or 0.0
            for thresh in tested_thresh:
                summary = _combine_summary([], _get_audio_file_results(thresh))
                score = self._compute_tuning_score(summary)
                if score > best_score or best_summary is None:
                    best_score = score
                    best_tuple = (base_fmin, base_fmax, thresh)
                    best_summary = summary
        else:
            # 1. Initial grid sweep
            for f_min in min_freqs:
                for f_max in max_freqs:
                    _eval_pair(f_min, f_max)

        # 2. Adaptive sweep if any test case is failing
        if (
            best_summary is not None
            and best_summary.accuracy < 1.0
            and not min_freq_candidates
            and not max_freq_candidates
        ):
            cur_fmin = best_tuple[0] if best_tuple else None
            cur_fmax = best_tuple[1] if best_tuple else None
            cur_th = best_tuple[2] if best_tuple else None

            adaptive_analysis = self.analyze(
                sound_def=sound_def,
                freq_min_hz=cur_fmin,
                freq_max_hz=cur_fmax,
                threshold=cur_th,
            )

            adaptive_min: list[float] = []
            adaptive_max: list[float] = []

            for ca in adaptive_analysis.case_analyses:
                if ca.evaluation.passed:
                    continue
                if ca.root_cause == 'VOCAL_PENALTY_SUPPRESSION':
                    adaptive_min.extend([1600.0, 1800.0, 2000.0])
                elif ca.root_cause == 'FALSE_POSITIVE_DOMINANCE':
                    adaptive_min.extend([1300.0, 1500.0])
                    adaptive_max.extend([2100.0, 2300.0])
                elif ca.root_cause == 'NO_SIGNAL':
                    adaptive_min.extend([800.0, 1000.0])
                    adaptive_max.extend([2800.0, 3000.0])

            base_min = cur_fmin or 1400.0
            base_max = cur_fmax or 2400.0

            for f_min in set(adaptive_min):
                _eval_pair(f_min, base_max)
            for f_max in set(adaptive_max):
                _eval_pair(base_min, f_max)
            for f_min in set(adaptive_min):
                for f_max in set(adaptive_max):
                    _eval_pair(f_min, f_max)

        if best_tuple is None or best_summary is None:
            best_summary = self.evaluate(sound_def)
            best_tuple = (
                sound_def.freq_min_hz or 0.0,
                sound_def.freq_max_hz or 0.0,
                sound_def.threshold,
            )

        return TuningResult(
            best_freq_min_hz=best_tuple[0],
            best_freq_max_hz=best_tuple[1],
            best_threshold=best_tuple[2],
            best_accuracy=best_summary.accuracy,
            best_mean_error_ms=best_summary.mean_error_ms,
            summary=best_summary,
            best_chunk_duration_ms=(
                best_sample_params[0] if best_sample_params else None
            ),
            best_chunk_step_ms=(
                best_sample_params[1] if best_sample_params else None
            ),
            best_consensus_tolerance_ms=(
                best_sample_params[2] if best_sample_params else None
            ),
            best_sample_min_freq_hz=(
                best_sample_params[3] if best_sample_params else None
            ),
            best_sample_max_freq_hz=(
                best_sample_params[4] if best_sample_params else None
            ),
        )

    def _tune_sample_parameters(
        self,
        sound_def: SoundDefinition,
        audio_file_cases: list[AudioTestCase],
        thresholds: list[float],
        chunk_duration_candidates: list[int] | None = None,
        chunk_step_candidates: list[int] | None = None,
        consensus_tolerance_candidates: list[int] | None = None,
        sample_min_freq_candidates: list[float] | None = None,
        sample_max_freq_candidates: list[float] | None = None,
    ) -> tuple[int, int, int, float, float]:
        """Tunes StartSoundMatcher parameters across audio_file test cases.

        Args:
            sound_def: Parent SoundDefinition.
            audio_file_cases: Subset of test cases targeting specific files.
            thresholds: Threshold candidates to evaluate.
            chunk_duration_candidates: Optional chunk duration candidates.
            chunk_step_candidates: Optional chunk step candidates.
            consensus_tolerance_candidates: Optional cluster tolerances.
            sample_min_freq_candidates: Optional sample high-pass cutoffs.
            sample_max_freq_candidates: Optional sample upper freq cutoffs.

        Returns:
            tuple[int, int, int, float, float]: Winning (chunk_duration_ms,
                chunk_step_ms, consensus_tolerance_ms, sample_min_freq_hz,
                sample_max_freq_hz).
        """
        base_dur = sound_def.chunk_duration_ms or DEFAULT_CHUNK_DURATION_MS
        durations = list(
            dict.fromkeys(
                chunk_duration_candidates
                if chunk_duration_candidates
                else [base_dur, 1000, 1500, 2000]
            )
        )
        base_tol = (
            sound_def.consensus_tolerance_ms or DEFAULT_CONSENSUS_TOLERANCE_MS
        )
        tolerances = list(
            dict.fromkeys(
                consensus_tolerance_candidates
                if consensus_tolerance_candidates
                else [base_tol, 200, 350]
            )
        )
        base_fmin = (
            sound_def.sample_min_freq_hz
            if sound_def.sample_min_freq_hz is not None
            else DEFAULT_SAMPLE_HIGH_PASS_HZ
        )
        min_freqs = list(
            dict.fromkeys(
                sample_min_freq_candidates
                if sample_min_freq_candidates
                else [base_fmin, 150.0, 300.0]
            )
        )
        base_fmax = (
            sound_def.sample_max_freq_hz
            if sound_def.sample_max_freq_hz is not None
            else DEFAULT_SAMPLE_MAX_FREQ_HZ
        )
        max_freqs = list(
            dict.fromkeys(
                sample_max_freq_candidates
                if sample_max_freq_candidates
                else [base_fmax]
            )
        )

        best_params: tuple[int, int, int, float, float] = (
            base_dur,
            sound_def.chunk_step_ms or max(1, base_dur // 2),
            base_tol,
            base_fmin,
            base_fmax,
        )
        best_score = -1e9
        sample_def = dataclasses.replace(sound_def, test_cases=audio_file_cases)
        eval_thresh = thresholds[0] if thresholds else sound_def.threshold

        for dur in durations:
            steps = (
                list(dict.fromkeys(chunk_step_candidates))
                if chunk_step_candidates
                else [
                    (
                        sound_def.chunk_step_ms
                        if sound_def.chunk_step_ms is not None
                        else max(1, dur // 2)
                    )
                ]
            )
            for step in steps:
                if step > dur:
                    continue
                for tol in tolerances:
                    for fmin in min_freqs:
                        for fmax in max_freqs:
                            if fmin >= fmax:
                                continue
                            results = [
                                self.evaluate_test_case(
                                    sound_def=sample_def,
                                    test_case=tc,
                                    threshold=eval_thresh,
                                    chunk_duration_ms=dur,
                                    chunk_step_ms=step,
                                    consensus_tolerance_ms=tol,
                                    sample_min_freq_hz=fmin,
                                    sample_max_freq_hz=fmax,
                                )
                                for tc in audio_file_cases
                            ]
                            total = len(results)
                            passed = sum(1 for r in results if r.passed)
                            errors = [
                                abs(r.error_ms)
                                for r in results
                                if r.passed and r.error_ms is not None
                            ]
                            summary = BenchmarkSummary(
                                sound_name=sound_def.name,
                                total_cases=total,
                                passed_cases=passed,
                                accuracy=(passed / total) if total else 0.0,
                                mean_error_ms=(
                                    (sum(errors) / len(errors))
                                    if errors
                                    else None
                                ),
                                case_results=results,
                            )
                            score = self._compute_tuning_score(summary)
                            if score > best_score:
                                best_score = score
                                best_params = (dur, step, tol, fmin, fmax)

        return best_params

    def _evaluate_matches(
        self,
        test_case: AudioTestCase,
        matches: list[AudioMatchResult],
        diagnostic: AudioMatchDiagnostic | None = None,
    ) -> TestCaseEvaluationResult:
        """Determines if matches satisfy ground-truth tolerance criteria.

        Args:
            test_case: Test case containing expected timestamp and tolerance.
            matches: List of match results returned by the audio matcher.
            diagnostic: Optional diagnostic information.

        Returns:
            TestCaseEvaluationResult: Outcome details.
        """
        if not matches:
            return TestCaseEvaluationResult(
                test_case=test_case,
                passed=False,
                detected_timestamp_ms=None,
                error_ms=None,
                confidence=None,
                top_false_positive_confidence=None,
                message='No matches detected above threshold.',
                diagnostic=diagnostic,
            )

        expected = test_case.expected_timestamp_ms
        tol = test_case.tolerance_ms

        out_of_tolerance = [
            m for m in matches if abs(m.timestamp_ms - expected) > tol
        ]
        top_fp_conf = (
            max((m.confidence for m in out_of_tolerance), default=None)
            if out_of_tolerance
            else None
        )

        top_match = matches[0]
        err = top_match.timestamp_ms - expected
        if abs(err) > tol:
            return TestCaseEvaluationResult(
                test_case=test_case,
                passed=False,
                detected_timestamp_ms=top_match.timestamp_ms,
                error_ms=err,
                confidence=top_match.confidence,
                top_false_positive_confidence=top_fp_conf,
                message=(
                    f'Top match at {top_match.timestamp_ms}ms outside '
                    'tolerance.'
                ),
                diagnostic=diagnostic,
            )

        return TestCaseEvaluationResult(
            test_case=test_case,
            passed=True,
            detected_timestamp_ms=top_match.timestamp_ms,
            error_ms=err,
            confidence=top_match.confidence,
            top_false_positive_confidence=top_fp_conf,
            message='Match detected within tolerance.',
            diagnostic=diagnostic,
        )

    def _compute_tuning_score(self, summary: BenchmarkSummary) -> float:
        """Computes a scalar score to rank benchmark configurations.

        Args:
            summary: Evaluated benchmark summary.

        Returns:
            float: Composite score prioritizing pass rate, low error, margin.
        """
        score = summary.accuracy * 1000.0
        if summary.mean_error_ms is not None:
            score -= summary.mean_error_ms * 0.1

        for r in summary.case_results:
            if r.passed and r.confidence is not None:
                score += r.confidence * 10.0
                if r.top_false_positive_confidence is not None:
                    margin = r.confidence - r.top_false_positive_confidence
                    score += margin * 20.0
        return score

    def _resolve_path(self, base_dir: Path, file_path: str) -> str:
        """Resolves a file path relative to a base directory if not absolute.

        Args:
            base_dir: Parent directory of the configuration file.
            file_path: Absolute or relative file path string.

        Returns:
            str: Resolved path as a string.
        """
        p = Path(file_path)
        if p.is_absolute():
            return str(p)
        return str((base_dir / p).resolve())


def main() -> None:
    """Command line entry point for audio benchmark evaluation and tuning."""
    parser = argparse.ArgumentParser(
        description='Benchmark and fine-tune audio template matching.'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    eval_parser = subparsers.add_parser(
        'evaluate', help='Evaluate test cases in a sound config.'
    )
    eval_parser.add_argument('config', help='Path to sound config YAML file.')
    eval_parser.add_argument('--json', action='store_true', help='Output JSON.')
    eval_parser.add_argument('--freq-min', type=float, help='Override freq_min')
    eval_parser.add_argument('--freq-max', type=float, help='Override freq_max')
    eval_parser.add_argument('--threshold', type=float, help='Override thresh')
    eval_parser.add_argument(
        '--template-duration', type=int, help='Override template duration ms'
    )
    eval_parser.add_argument(
        '--min-energy-ratio', type=float, help='Override min energy ratio'
    )
    eval_parser.add_argument(
        '--full-video',
        action='store_true',
        help='Ignore search_start_ms/search_end_ms and search full files.',
    )

    tune_parser = subparsers.add_parser(
        'tune', help='Fine-tune frequency bounds and thresholds.'
    )
    tune_parser.add_argument('config', help='Path to sound config YAML file.')
    tune_parser.add_argument(
        '--save', action='store_true', help='Save best parameters to config.'
    )
    tune_parser.add_argument('--json', action='store_true', help='Output JSON.')

    analyze_parser = subparsers.add_parser(
        'analyze', help='Diagnose failures and analyze test cases in a config.'
    )
    analyze_parser.add_argument(
        'config', help='Path to sound config YAML file.'
    )
    analyze_parser.add_argument(
        '--json', action='store_true', help='Output JSON.'
    )
    analyze_parser.add_argument(
        '--iterate',
        action='store_true',
        help='Evaluate suggested changes and find the best configuration.',
    )
    analyze_parser.add_argument(
        '--save',
        action='store_true',
        help='Save best parameters from iteration to config file.',
    )
    analyze_parser.add_argument(
        '--freq-min', type=float, help='Override freq_min'
    )
    analyze_parser.add_argument(
        '--freq-max', type=float, help='Override freq_max'
    )
    analyze_parser.add_argument(
        '--threshold', type=float, help='Override thresh'
    )
    analyze_parser.add_argument(
        '--template-duration', type=int, help='Override template duration ms'
    )
    analyze_parser.add_argument(
        '--min-energy-ratio', type=float, help='Override min energy ratio'
    )
    analyze_parser.add_argument(
        '--full-video',
        action='store_true',
        help='Ignore search_start_ms/search_end_ms and search full files.',
    )

    args = parser.parse_args()
    runner = AudioBenchmarkRunner()
    sound_def = runner.load_from_yaml(args.config)

    if args.command == 'evaluate':
        summary = runner.evaluate(
            sound_def=sound_def,
            freq_min_hz=args.freq_min,
            freq_max_hz=args.freq_max,
            threshold=args.threshold,
            template_duration_ms=args.template_duration,
            min_energy_ratio=args.min_energy_ratio,
            ignore_search_window=args.full_video,
        )
        if args.json:
            print(json.dumps(dataclasses.asdict(summary), indent=2))
        else:
            _print_summary(summary)

    elif args.command == 'tune':
        tuning = runner.tune(sound_def=sound_def)
        if args.save:
            sound_def.freq_min_hz = tuning.best_freq_min_hz
            sound_def.freq_max_hz = tuning.best_freq_max_hz
            sound_def.threshold = tuning.best_threshold
            if tuning.best_chunk_duration_ms is not None:
                sound_def.chunk_duration_ms = tuning.best_chunk_duration_ms
            if tuning.best_chunk_step_ms is not None:
                sound_def.chunk_step_ms = tuning.best_chunk_step_ms
            if tuning.best_consensus_tolerance_ms is not None:
                sound_def.consensus_tolerance_ms = (
                    tuning.best_consensus_tolerance_ms
                )
            if tuning.best_sample_min_freq_hz is not None:
                sound_def.sample_min_freq_hz = tuning.best_sample_min_freq_hz
            if tuning.best_sample_max_freq_hz is not None:
                sound_def.sample_max_freq_hz = tuning.best_sample_max_freq_hz
            runner.save_to_yaml(sound_def, args.config)
            print(f'Updated config saved to {args.config}')

        if args.json:
            print(json.dumps(dataclasses.asdict(tuning), indent=2))
        else:
            _print_tuning(tuning)

    elif args.command == 'analyze':
        analysis = runner.analyze(
            sound_def=sound_def,
            freq_min_hz=args.freq_min,
            freq_max_hz=args.freq_max,
            threshold=args.threshold,
            template_duration_ms=args.template_duration,
            min_energy_ratio=args.min_energy_ratio,
            iterate=args.iterate,
            ignore_search_window=args.full_video,
        )
        if args.save and analysis.best_iteration is not None:
            best_s = analysis.best_iteration.suggestion
            if best_s.freq_min_hz is not None:
                sound_def.freq_min_hz = best_s.freq_min_hz
            if best_s.freq_max_hz is not None:
                sound_def.freq_max_hz = best_s.freq_max_hz
            if best_s.threshold is not None:
                sound_def.threshold = best_s.threshold
            if best_s.template_duration_ms is not None:
                sound_def.template_duration_ms = best_s.template_duration_ms
            if best_s.min_energy_ratio is not None:
                sound_def.min_energy_ratio = best_s.min_energy_ratio
            runner.save_to_yaml(sound_def, args.config)
            print(f'Updated config saved to {args.config}')

        if args.json:
            print(json.dumps(dataclasses.asdict(analysis), indent=2))
        else:
            _print_analysis(analysis)


def _format_test_case_target(test_case: AudioTestCase) -> str:
    """Formats a human-readable target label for a test case.

    Args:
        test_case: The test case to describe.

    Returns:
        str: 'siren' or the audio file basename.
    """
    if (
        test_case.target_type == AudioTargetType.AUDIO_FILE
        and test_case.target_audio_path is not None
    ):
        return f'file:{Path(test_case.target_audio_path).name}'
    return test_case.target_type.value


def _print_summary(summary: BenchmarkSummary) -> None:
    """Prints a formatted evaluation report to stdout.

    Args:
        summary: BenchmarkSummary instance to print.
    """
    print(f'Sound: {summary.sound_name}')
    print(
        f'Passed: {summary.passed_cases}/{summary.total_cases} '
        f'({summary.accuracy * 100:.1f}%)'
    )
    if summary.mean_error_ms is not None:
        print(f'Mean Error: {summary.mean_error_ms:.1f} ms')
    print('\nCase Details:')
    for i, r in enumerate(summary.case_results, 1):
        status = 'PASS' if r.passed else 'FAIL'
        target_label = _format_test_case_target(r.test_case)
        err_str = f'{r.error_ms:+d}ms' if r.error_ms is not None else 'N/A'
        conf_str = f'{r.confidence:.4f}' if r.confidence is not None else 'N/A'
        exp_ms = r.test_case.expected_timestamp_ms
        det_ms = r.detected_timestamp_ms
        print(
            f'  {i}. [{status}] ({target_label}) expected: {exp_ms}ms, '
            f'detected: {det_ms}ms (err: {err_str}, conf: {conf_str}) - '
            f'{r.message}'
        )


def _print_tuning(tuning: TuningResult) -> None:
    """Prints a formatted tuning report to stdout.

    Args:
        tuning: TuningResult instance to print.
    """
    print(f'Best freq_min: {tuning.best_freq_min_hz} Hz')
    print(f'Best freq_max: {tuning.best_freq_max_hz} Hz')
    print(f'Best threshold: {tuning.best_threshold}')
    if tuning.best_chunk_duration_ms is not None:
        print(f'Best chunk_duration_ms: {tuning.best_chunk_duration_ms} ms')
    if tuning.best_chunk_step_ms is not None:
        print(f'Best chunk_step_ms: {tuning.best_chunk_step_ms} ms')
    if tuning.best_consensus_tolerance_ms is not None:
        print(
            'Best consensus_tolerance_ms: '
            f'{tuning.best_consensus_tolerance_ms} ms'
        )
    if tuning.best_sample_min_freq_hz is not None:
        print(f'Best sample_min_freq_hz: {tuning.best_sample_min_freq_hz} Hz')
    if tuning.best_sample_max_freq_hz is not None:
        print(f'Best sample_max_freq_hz: {tuning.best_sample_max_freq_hz} Hz')
    print(f'Accuracy: {tuning.best_accuracy * 100:.1f}%')
    if tuning.best_mean_error_ms is not None:
        print(f'Mean Error: {tuning.best_mean_error_ms:.1f} ms')


def _print_analysis(analysis: BenchmarkAnalysis) -> None:
    """Prints a formatted failure diagnosis and analysis report to stdout.

    Args:
        analysis: BenchmarkAnalysis instance to print.
    """
    print(f'Sound: {analysis.sound_name}')
    accuracy = (
        (analysis.passed_cases / analysis.total_cases * 100.0)
        if analysis.total_cases > 0
        else 0.0
    )
    print(
        f'Passed: {analysis.passed_cases}/{analysis.total_cases} '
        f'({accuracy:.1f}%)'
    )
    if analysis.min_true_peak_confidence is not None:
        min_tp = analysis.min_true_peak_confidence
        print(f'Min True Peak Confidence: {min_tp:.4f}')
    if analysis.max_false_positive_confidence is not None:
        max_fp = analysis.max_false_positive_confidence
        print(f'Max False Positive Confidence: {max_fp:.4f}')
    if analysis.reconciling_threshold is not None:
        rec_th = analysis.reconciling_threshold
        print(f'Reconciling Threshold: {rec_th:.3f} (passes all cases)')
    else:
        print(
            'Reconciling Threshold: None (false positive ceiling >= true peak)'
        )

    print('\nCase Analyses:')
    for i, a in enumerate(analysis.case_analyses, 1):
        status = 'PASS' if a.evaluation.passed else 'FAIL'
        target_label = _format_test_case_target(a.test_case)
        exp_ms = a.test_case.expected_timestamp_ms
        det_ms = a.evaluation.detected_timestamp_ms
        det_str = f'{det_ms}ms' if det_ms is not None else 'None'
        print(
            f'  {i}. [{status}] ({target_label}) expected: {exp_ms}ms, '
            f'detected: {det_str}'
        )
        if not a.evaluation.passed:
            print(f'     Root Cause: {a.root_cause}')
            if (
                a.diagnostic
                and a.diagnostic.expected_peak_timestamp_ms is not None
            ):
                d = a.diagnostic
                raw_s = (
                    f'{d.expected_peak_raw_correlation:.3f}'
                    if d.expected_peak_raw_correlation is not None
                    else 'N/A'
                )
                voc_s = (
                    f'{d.expected_peak_vocal_penalty:.3f}'
                    if d.expected_peak_vocal_penalty is not None
                    else 'N/A'
                )
                conf_s = (
                    f'{d.expected_peak_confidence:.4f}'
                    if d.expected_peak_confidence is not None
                    else 'N/A'
                )
                print(
                    f'     Target Peak: {d.expected_peak_timestamp_ms}ms '
                    f'(conf: {conf_s}, raw: {raw_s}, vocal_penalty: {voc_s})'
                )
            if (
                a.diagnostic
                and a.diagnostic.top_false_positive_confidence is not None
            ):
                d = a.diagnostic
                fp_conf = d.top_false_positive_confidence
                print(
                    f'     Top False Positive: '
                    f'{d.top_false_positive_timestamp_ms}ms '
                    f'(conf: {fp_conf:.4f})'
                )
            print(f'     Recommendation: {a.recommendation}')

    if analysis.suggestions:
        print('\nSuggested Configuration Changes:')
        for i, sug in enumerate(analysis.suggestions, 1):
            print(f'  {i}. [{sug.name}]')
            params: list[str] = []
            if sug.freq_min_hz is not None:
                params.append(f'freq_min_hz: {sug.freq_min_hz}')
            if sug.freq_max_hz is not None:
                params.append(f'freq_max_hz: {sug.freq_max_hz}')
            if sug.threshold is not None:
                params.append(f'threshold: {sug.threshold}')
            if sug.template_duration_ms is not None:
                params.append(
                    f'template_duration_ms: {sug.template_duration_ms}'
                )
            if sug.min_energy_ratio is not None:
                params.append(f'min_energy_ratio: {sug.min_energy_ratio}')
            for p in params:
                print(f'     {p}')
            print(f'     Rationale: {sug.rationale}')

    if analysis.iteration_results is not None:
        print('\nIteration Mode Results:')
        for i, it in enumerate(analysis.iteration_results, 1):
            s = it.suggestion
            sum_ = it.summary
            is_best = ' [BEST]' if analysis.best_iteration is it else ''
            p_parts: list[str] = []
            if s.freq_min_hz is not None:
                p_parts.append(f'fmin={s.freq_min_hz}')
            if s.freq_max_hz is not None:
                p_parts.append(f'fmax={s.freq_max_hz}')
            if s.threshold is not None:
                p_parts.append(f'thresh={s.threshold}')
            if s.template_duration_ms is not None:
                p_parts.append(f'dur={s.template_duration_ms}ms')
            if s.min_energy_ratio is not None:
                p_parts.append(f'min_energy={s.min_energy_ratio}')
            p_str = ', '.join(p_parts)
            err_str = (
                f'{sum_.mean_error_ms:.1f}ms'
                if sum_.mean_error_ms is not None
                else 'N/A'
            )
            print(
                f'  {i}. [{s.name}] ({p_str}) -> '
                f'Passed: {sum_.passed_cases}/{sum_.total_cases} '
                f'({sum_.accuracy * 100:.1f}%), err: {err_str}{is_best}'
            )

        if analysis.best_iteration is not None:
            b_sug = analysis.best_iteration.suggestion
            b_sum = analysis.best_iteration.summary
            print('\nRecommended Best Configuration:')
            if b_sug.freq_min_hz is not None:
                print(f'  freq_min_hz: {b_sug.freq_min_hz}')
            if b_sug.freq_max_hz is not None:
                print(f'  freq_max_hz: {b_sug.freq_max_hz}')
            if b_sug.threshold is not None:
                print(f'  threshold: {b_sug.threshold}')
            if b_sug.template_duration_ms is not None:
                print(f'  template_duration_ms: {b_sug.template_duration_ms}')
            if b_sug.min_energy_ratio is not None:
                print(f'  min_energy_ratio: {b_sug.min_energy_ratio}')
            print(
                f'  Accuracy: {b_sum.passed_cases}/{b_sum.total_cases} '
                f'({b_sum.accuracy * 100:.1f}%)'
            )


if __name__ == '__main__':
    main()
