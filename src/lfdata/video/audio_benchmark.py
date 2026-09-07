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
from pathlib import Path
from typing import Any
import yaml

from lfdata.video.audio_matcher import (
    AudioMatchDiagnostic,
    AudioMatchResult,
    AudioMatcher,
)


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
    """

    sound_name: str
    total_cases: int
    passed_cases: int
    min_true_peak_confidence: float | None
    max_false_positive_confidence: float | None
    reconciling_threshold: float | None
    case_analyses: list[TestCaseAnalysis]


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
            matches, diag = self._matcher.match_diagnostic(
                video_or_audio_path=test_case.video_path,
                reference_sound_path=sound_def.reference_sound_path,
                expected_timestamp_ms=test_case.expected_timestamp_ms,
                tolerance_ms=test_case.tolerance_ms,
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
                diagnostic=None,
            )

        return self._evaluate_matches(test_case, matches, diagnostic=diag)

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

    def analyze(
        self,
        sound_def: SoundDefinition,
        freq_min_hz: float | None = None,
        freq_max_hz: float | None = None,
        threshold: float | None = None,
    ) -> BenchmarkAnalysis:
        """Analyzes test cases with detailed failure diagnostics.

        Evaluates each test case, computes true-positive peaks and
        false-positive ceilings, identifies failure root causes, and
        calculates reconciling thresholds.

        Args:
            sound_def: Sound definition containing reference and test cases.
            freq_min_hz: Optional lower frequency cutoff in Hz override.
            freq_max_hz: Optional upper frequency cutoff in Hz override.
            threshold: Optional threshold override.

        Returns:
            BenchmarkAnalysis: Comprehensive analysis across all test cases.
        """
        eff_thresh = (
            threshold if threshold is not None else sound_def.threshold
        )
        case_analyses: list[TestCaseAnalysis] = []
        true_peaks: list[float] = []
        false_positives: list[float] = []

        for tc in sound_def.test_cases:
            res = self.evaluate_test_case(
                sound_def=sound_def,
                test_case=tc,
                freq_min_hz=freq_min_hz,
                freq_max_hz=freq_max_hz,
                threshold=threshold,
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

        passed_count = sum(1 for c in case_analyses if c.evaluation.passed)
        return BenchmarkAnalysis(
            sound_name=sound_def.name,
            total_cases=len(case_analyses),
            passed_cases=passed_count,
            min_true_peak_confidence=min_tp,
            max_false_positive_confidence=max_fp,
            reconciling_threshold=reconciling_thresh,
            case_analyses=case_analyses,
        )

    def tune(
        self,
        sound_def: SoundDefinition,
        min_freq_candidates: list[float] | None = None,
        max_freq_candidates: list[float] | None = None,
        threshold_candidates: list[float] | None = None,
    ) -> TuningResult:
        """Finds optimal frequency bounds and thresholds across test cases.

        Evaluates parameter combinations, performs failure analysis to
        discover reconciling thresholds that maintain passes across all cases,
        and adaptively expands search boundaries when test cases fail.

        Args:
            sound_def: Sound definition with test cases.
            min_freq_candidates: Optional lower frequency cutoffs to evaluate.
            max_freq_candidates: Optional upper frequency cutoffs to evaluate.
            threshold_candidates: Optional thresholds to evaluate.

        Returns:
            TuningResult: Optimal parameter values and benchmark summary.
        """
        min_freqs = list(min_freq_candidates) if min_freq_candidates else [
            sound_def.freq_min_hz or 1000.0,
            1200.0,
            1400.0,
            1600.0,
        ]
        max_freqs = list(max_freq_candidates) if max_freq_candidates else [
            sound_def.freq_max_hz or 2500.0,
            2200.0,
            2400.0,
            2600.0,
        ]
        thresholds = list(threshold_candidates) if threshold_candidates else [
            0.15,
            0.20,
            0.25,
        ]

        best_tuple: tuple[float, float, float] | None = None
        best_summary: BenchmarkSummary | None = None
        best_score = -1e9
        evaluated_pairs: set[tuple[float, float]] = set()

        def _eval_pair(f_min: float, f_max: float) -> None:
            nonlocal best_tuple, best_summary, best_score
            pair = (f_min, f_max)
            if pair in evaluated_pairs or f_min >= f_max:
                return
            evaluated_pairs.add(pair)

            analysis = self.analyze(
                sound_def=sound_def,
                freq_min_hz=f_min,
                freq_max_hz=f_max,
            )

            tested_thresh = list(thresholds)
            if analysis.reconciling_threshold is not None:
                tested_thresh.append(analysis.reconciling_threshold)

            for thresh in tested_thresh:
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
        )

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
                diagnostic=diagnostic,
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
        '--freq-min', type=float, help='Override freq_min'
    )
    analyze_parser.add_argument(
        '--freq-max', type=float, help='Override freq_max'
    )
    analyze_parser.add_argument(
        '--threshold', type=float, help='Override thresh'
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

    elif args.command == 'analyze':
        analysis = runner.analyze(
            sound_def=sound_def,
            freq_min_hz=args.freq_min,
            freq_max_hz=args.freq_max,
            threshold=args.threshold,
        )
        if args.json:
            print(json.dumps(dataclasses.asdict(analysis), indent=2))
        else:
            _print_analysis(analysis)


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
        exp_ms = a.test_case.expected_timestamp_ms
        det_ms = a.evaluation.detected_timestamp_ms
        det_str = f'{det_ms}ms' if det_ms is not None else 'None'
        print(f'  {i}. [{status}] expected: {exp_ms}ms, detected: {det_str}')
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


if __name__ == '__main__':
    main()
