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
import json
import os
from pathlib import Path
from typing import Any
import yaml

from lfdata.video.audio_matcher import AudioMatchResult, AudioMatcher


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
    """

    video_path: str
    expected_timestamp_ms: int
    tolerance_ms: int = 500
    search_start_ms: int | None = None
    search_end_ms: int | None = None
    description: str = ''


@dataclasses.dataclass
class SoundDefinition:
    """Structured definition of a sound effect to find with test cases.

    Attributes:
        name: Unique identifier for the sound.
        reference_sound_path: Path to reference sound effect WAV/audio file.
        freq_min_hz: Optional lower frequency bound in Hz.
        freq_max_hz: Optional upper frequency bound in Hz.
        threshold: Minimum confidence threshold (default: 0.2).
        description: Optional description of this sound effect.
        test_cases: List of example video test cases.
    """

    name: str
    reference_sound_path: str
    freq_min_hz: float | None = None
    freq_max_hz: float | None = None
    threshold: float = 0.2
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
    """

    __test__ = False

    test_case: AudioTestCase
    passed: bool
    detected_timestamp_ms: int | None
    error_ms: int | None
    confidence: float | None
    top_false_positive_confidence: float | None
    message: str = ''


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
    """

    best_freq_min_hz: float | None
    best_freq_max_hz: float | None
    best_threshold: float
    best_accuracy: float
    best_mean_error_ms: float | None
    summary: BenchmarkSummary


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
            FileNotFoundError: If the YAML file does not exist.
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

        test_cases: list[AudioTestCase] = []
        raw_cases = raw_data.get('test_cases', [])
        for case_data in raw_cases:
            if not isinstance(case_data, dict):
                continue
            video_p = case_data.get('video_path')
            if not video_p:
                continue
            resolved_video_p = self._resolve_path(base_dir, video_p)
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
                )
            )

        return SoundDefinition(
            name=str(name),
            reference_sound_path=resolved_ref_path,
            freq_min_hz=raw_data.get('freq_min_hz'),
            freq_max_hz=raw_data.get('freq_max_hz'),
            threshold=float(raw_data.get('threshold', 0.2)),
            description=raw_data.get('description', ''),
            test_cases=test_cases,
        )

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

        data: dict[str, Any] = {
            'name': sound_def.name,
            'description': sound_def.description,
            'reference_sound_path': sound_def.reference_sound_path,
            'freq_min_hz': sound_def.freq_min_hz,
            'freq_max_hz': sound_def.freq_max_hz,
            'threshold': sound_def.threshold,
            'test_cases': [
                {
                    'video_path': tc.video_path,
                    'expected_timestamp_ms': tc.expected_timestamp_ms,
                    'tolerance_ms': tc.tolerance_ms,
                    'search_start_ms': tc.search_start_ms,
                    'search_end_ms': tc.search_end_ms,
                    'description': tc.description,
                }
                for tc in sound_def.test_cases
            ],
        }

        with open(dest_path, 'w', encoding='utf-8') as file_obj:
            yaml.dump(data, file_obj, sort_keys=False, indent=2)

    def evaluate_test_case(
        self,
        sound_def: SoundDefinition,
        test_case: AudioTestCase,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        threshold: float | None = None,
    ) -> TestCaseEvaluationResult:
        """Evaluates audio matching on a single test case.

        Args:
            sound_def: Sound definition containing reference sound.
            test_case: The test case to evaluate.
            freq_min_hz: Optional lower frequency bound override.
            freq_max_hz: Optional upper frequency bound override.
            threshold: Optional confidence threshold override.

        Returns:
            TestCaseEvaluationResult: Detailed outcome of the test case.
        """
        video_path = Path(test_case.video_path)
        if not video_path.exists():
            return TestCaseEvaluationResult(
                test_case=test_case,
                passed=False,
                detected_timestamp_ms=None,
                error_ms=None,
                confidence=None,
                top_false_positive_confidence=None,
                message=f'Video file not found: {video_path}',
            )

        eff_min = (
            freq_min_hz if freq_min_hz is not None else sound_def.freq_min_hz
        )
        eff_max = (
            freq_max_hz if freq_max_hz is not None else sound_def.freq_max_hz
        )
        eff_thresh = (
            threshold if threshold is not None else sound_def.threshold
        )

        try:
            matches = self._matcher.match(
                video_or_audio_path=test_case.video_path,
                reference_sound_path=sound_def.reference_sound_path,
                threshold=eff_thresh,
                start_ms=test_case.search_start_ms,
                end_ms=test_case.search_end_ms,
                freq_min_hz=eff_min,
                freq_max_hz=eff_max,
            )
        except Exception as err:
            return TestCaseEvaluationResult(
                test_case=test_case,
                passed=False,
                detected_timestamp_ms=None,
                error_ms=None,
                confidence=None,
                top_false_positive_confidence=None,
                message=f'Matcher failed: {err}',
            )

        return self._evaluate_matches(test_case, matches)

    def evaluate(
        self,
        sound_def: SoundDefinition,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        threshold: float | None = None,
    ) -> BenchmarkSummary:
        """Evaluates all test cases in a sound definition.

        Args:
            sound_def: Sound definition with example test cases.
            freq_min_hz: Optional lower frequency bound override.
            freq_max_hz: Optional upper frequency bound override.
            threshold: Optional confidence threshold override.

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

    def tune(
        self,
        sound_def: SoundDefinition,
        min_freq_candidates: list[float] | None = None,
        max_freq_candidates: list[float] | None = None,
        threshold_candidates: list[float] | None = None,
    ) -> TuningResult:
        """Finds optimal frequency bounds and thresholds across test cases.

        Evaluates parameter combinations and selects the one with highest
        accuracy, lowest timing error, and highest false-positive margin.

        Args:
            sound_def: Sound definition with test cases.
            min_freq_candidates: List of lower frequency cutoffs to evaluate.
            max_freq_candidates: List of upper frequency cutoffs to evaluate.
            threshold_candidates: List of thresholds to evaluate.

        Returns:
            TuningResult: Optimal parameter values and benchmark summary.
        """
        min_freqs = min_freq_candidates or [
            sound_def.freq_min_hz or 1000.0,
            1200.0,
            1400.0,
            1600.0,
        ]
        max_freqs = max_freq_candidates or [
            sound_def.freq_max_hz or 2500.0,
            2200.0,
            2400.0,
            2600.0,
        ]
        thresholds = threshold_candidates or [0.15, 0.20, 0.25]

        best_tuple: tuple[float, float, float] | None = None
        best_summary: BenchmarkSummary | None = None
        best_score = -1e9

        for f_min in min_freqs:
            for f_max in max_freqs:
                if f_min >= f_max:
                    continue
                for thresh in thresholds:
                    summary = self.evaluate(
                        sound_def=sound_def,
                        freq_min_hz=f_min,
                        freq_max_hz=f_max,
                        threshold=thresh,
                    )
                    score = self._compute_tuning_score(summary)
                    if score > best_score or best_summary is None:
                        best_score = score
                        best_tuple = (f_min, f_max, thresh)
                        best_summary = summary

        if best_tuple is None or best_summary is None:
            # Fallback to current parameters
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
        )

    def _evaluate_matches(
        self,
        test_case: AudioTestCase,
        matches: list[AudioMatchResult],
    ) -> TestCaseEvaluationResult:
        """Determines if matches satisfy ground-truth tolerance criteria.

        Args:
            test_case: Test case containing expected timestamp and tolerance.
            matches: List of match results returned by the audio matcher.

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
            )

        expected = test_case.expected_timestamp_ms
        tol = test_case.tolerance_ms

        in_tolerance: list[AudioMatchResult] = []
        out_of_tolerance: list[AudioMatchResult] = []

        for m in matches:
            if abs(m.timestamp_ms - expected) <= tol:
                in_tolerance.append(m)
            else:
                out_of_tolerance.append(m)

        top_fp_conf = (
            max((m.confidence for m in out_of_tolerance), default=None)
            if out_of_tolerance
            else None
        )

        if not in_tolerance:
            best_fp = matches[0]
            err = best_fp.timestamp_ms - expected
            return TestCaseEvaluationResult(
                test_case=test_case,
                passed=False,
                detected_timestamp_ms=best_fp.timestamp_ms,
                error_ms=err,
                confidence=best_fp.confidence,
                top_false_positive_confidence=top_fp_conf,
                message=f'Match at {best_fp.timestamp_ms}ms outside tolerance.',
            )

        best_hit = in_tolerance[0]
        err = best_hit.timestamp_ms - expected
        return TestCaseEvaluationResult(
            test_case=test_case,
            passed=True,
            detected_timestamp_ms=best_hit.timestamp_ms,
            error_ms=err,
            confidence=best_hit.confidence,
            top_false_positive_confidence=top_fp_conf,
            message='Match detected within tolerance.',
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

    tune_parser = subparsers.add_parser(
        'tune', help='Fine-tune frequency bounds and thresholds.'
    )
    tune_parser.add_argument('config', help='Path to sound config YAML file.')
    tune_parser.add_argument(
        '--save', action='store_true', help='Save best parameters to config.'
    )
    tune_parser.add_argument('--json', action='store_true', help='Output JSON.')

    args = parser.parse_args()
    runner = AudioBenchmarkRunner()
    sound_def = runner.load_from_yaml(args.config)

    if args.command == 'evaluate':
        summary = runner.evaluate(
            sound_def=sound_def,
            freq_min_hz=args.freq_min,
            freq_max_hz=args.freq_max,
            threshold=args.threshold,
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
            runner.save_to_yaml(sound_def, args.config)
            print(f'Updated config saved to {args.config}')

        if args.json:
            print(json.dumps(dataclasses.asdict(tuning), indent=2))
        else:
            _print_tuning(tuning)


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
        err_str = f'{r.error_ms:+d}ms' if r.error_ms is not None else 'N/A'
        conf_str = f'{r.confidence:.4f}' if r.confidence is not None else 'N/A'
        exp_ms = r.test_case.expected_timestamp_ms
        det_ms = r.detected_timestamp_ms
        print(
            f'  {i}. [{status}] expected: {exp_ms}ms, '
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
    print(f'Accuracy: {tuning.best_accuracy * 100:.1f}%')
    if tuning.best_mean_error_ms is not None:
        print(f'Mean Error: {tuning.best_mean_error_ms:.1f} ms')


if __name__ == '__main__':
    main()
