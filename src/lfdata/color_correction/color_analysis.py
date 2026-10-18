"""Command-line utility for analyzing video luminance and color correction.

This module provides the executable CLI entry point to analyze GoPro video
footage taken in laser tag arenas, assess luminance distributions, evaluate
bright light exposure risks, and produce recommended color grading settings.

Usage example:
    $ color-analysis arena_clip.mp4
    $ color-analysis --sample_interval_ms 1000 --format json clip.mp4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from lfdata.color_correction.color_analysis_types import (
    AnalysisOutputFormat,
    ColorAnalysisResult,
)
from lfdata.color_correction.color_analyzer import (
    DEFAULT_ANALYSIS_MAX_FRAMES,
    DEFAULT_ANALYSIS_SAMPLE_INTERVAL_MS,
    ColorAnalyzer,
)
from lfdata.color_correction.suggested_lut import (
    DEFAULT_SUGGESTED_LUT_SIZE,
    save_suggested_lut,
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for the color analysis CLI.

    Returns:
        argparse.ArgumentParser: Configured argument parser.

    Usage example:
        parser = build_arg_parser()
    """
    parser = argparse.ArgumentParser(
        prog='color_analysis',
        description=(
            'Analyze video luminance properties and assess required color '
            'correction parameters for laser tag arena footage.'
        ),
    )
    parser.add_argument(
        'video',
        nargs='?',
        type=str,
        default=None,
        help='Path to the video file to analyze.',
    )
    parser.add_argument(
        '--input',
        '-i',
        dest='input_video',
        type=str,
        default=None,
        help='Alternative flag to specify input video file path.',
    )
    parser.add_argument(
        '--sample_interval_ms',
        type=int,
        default=DEFAULT_ANALYSIS_SAMPLE_INTERVAL_MS,
        help='Millisecond interval between sampled frames (default: 2000 ms).',
    )
    parser.add_argument(
        '--max_frames',
        type=int,
        default=DEFAULT_ANALYSIS_MAX_FRAMES,
        help='Maximum number of video frames to sample (default: 120).',
    )
    parser.add_argument(
        '--format',
        '-f',
        type=str,
        default='text',
        choices=['text', 'json'],
        help='Output format: text (human-readable) or json (default: text).',
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default=None,
        help='File path to write results to. Defaults to standard output.',
    )
    parser.add_argument(
        '--export_lut',
        '--lut_out',
        dest='export_lut',
        type=str,
        default=None,
        help='Output path to write suggested 3D LUT (.cube file).',
    )
    parser.add_argument(
        '--lut_size',
        type=int,
        default=DEFAULT_SUGGESTED_LUT_SIZE,
        help='Grid dimension size of exported 3D LUT (default: 33).',
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Include per-frame sample metrics in JSON output or verbose text.',
    )
    return parser


def format_text_report(
    result: ColorAnalysisResult,
    verbose: bool = False,
    suggested_lut_path: str | None = None,
) -> str:
    """Formats the color analysis result into a structured text report.

    Args:
        result: The ColorAnalysisResult object to format.
        verbose: If True, appends per-frame luminance breakdown.
        suggested_lut_path: Optional path where suggested LUT was exported.

    Returns:
        str: Formatted human-readable report.

    Usage example:
        report = format_text_report(result=analysis_res, verbose=False)
    """
    lines: list[str] = []
    bar = '=' * 78
    sub_bar = '-' * 78

    lines.append(bar)
    lines.append(f'COLOR ANALYSIS REPORT: {result.video_path}')
    lines.append(bar)

    _append_video_properties(lines=lines, result=result)
    lines.append(sub_bar)
    _append_luminance_distribution(lines=lines, result=result)
    lines.append(sub_bar)
    _append_tone_breakdown(lines=lines, result=result)
    lines.append(sub_bar)
    _append_temporal_profile(lines=lines, result=result)
    lines.append(sub_bar)
    _append_recommendations(
        lines=lines, result=result, suggested_lut_path=suggested_lut_path
    )

    if verbose and result.frame_samples:
        lines.append(sub_bar)
        _append_frame_samples(lines=lines, result=result)

    lines.append(bar)
    return '\n'.join(lines)


def _append_video_properties(
    lines: list[str], result: ColorAnalysisResult
) -> None:
    """Appends video container properties to the report lines.

    Args:
        lines: List of output report strings.
        result: The analysis result data.
    """
    duration_sec = result.duration_ms / 1000.0
    lines.append('Video Properties:')
    lines.append(f'  Resolution:       {result.width}x{result.height}')
    lines.append(
        f'  Duration:         {duration_sec:.1f}s ({result.duration_ms} ms)'
    )
    lines.append(f'  Frame Rate:       {result.fps:.2f} fps')
    lines.append(f'  Total Frames:     {result.frame_count}')
    lines.append(
        f'  Frames Analyzed:  {result.temporal_metrics.frames_analyzed} '
        f'(sampled every {result.sample_interval_ms} ms)'
    )


def _append_luminance_distribution(
    lines: list[str], result: ColorAnalysisResult
) -> None:
    """Appends aggregate luminance percentiles to report lines.

    Args:
        lines: List of output report strings.
        result: The analysis result data.
    """
    m = result.global_metrics
    lines.append('Luminance Distribution (Rec. 709):')
    lines.append(f'  Mean Luminance:   {m.mean_luminance:.4f}')
    lines.append(f'  Median Luminance: {m.median_luminance:.4f}')
    lines.append(f'  Std Deviation:    {m.std_luminance:.4f}')
    lines.append(
        f'  Min / Max:        {m.min_luminance:.4f} / {m.max_luminance:.4f}'
    )
    lines.append('  Percentiles:')
    lines.append(
        f'    p10: {m.p10:.4f}   p25: {m.p25:.4f}   p50: {m.median_luminance:.4f}'
    )
    lines.append(
        f'    p75: {m.p75:.4f}   p90: {m.p90:.4f}   p95: {m.p95:.4f}   '
        f'p99: {m.p99:.4f}'
    )


def _append_tone_breakdown(
    lines: list[str], result: ColorAnalysisResult
) -> None:
    """Appends tone zone percentages to report lines.

    Args:
        lines: List of output report strings.
        result: The analysis result data.
    """
    m = result.global_metrics
    deep_pct = m.deep_shadow_fraction * 100.0
    shadow_pct = m.shadow_fraction * 100.0
    mid_pct = m.midtone_fraction * 100.0
    hi_pct = m.highlight_fraction * 100.0
    blown_pct = m.blown_fraction * 100.0

    lines.append('Tone Zone Breakdown:')
    lines.append(f'  Deep Shadows (<5%):     {deep_pct:5.1f}%')
    lines.append(f'  Shadows (<15%):         {shadow_pct:5.1f}%')
    lines.append(f'  Midtones (15-70%):      {mid_pct:5.1f}%')
    lines.append(f'  Highlights (>=70%):     {hi_pct:5.1f}%')
    lines.append(f'  Blown Peaks (>=95%):    {blown_pct:5.1f}%')
    lines.append(f'  Dynamic Range (p95-p10): {m.dynamic_range:.4f}')


def _append_temporal_profile(
    lines: list[str], result: ColorAnalysisResult
) -> None:
    """Appends temporal stability metrics across frames to report lines.

    Args:
        lines: List of output report strings.
        result: The analysis result data.
    """
    t = result.temporal_metrics
    lines.append('Temporal Profile Across Video:')
    lines.append(f'  Mean Frame Mean:  {t.mean_frame_mean:.4f}')
    lines.append(f'  Std Frame Mean:   {t.std_frame_mean:.4f}')
    lines.append(
        f'  Min / Max Means:  {t.min_frame_mean:.4f} / {t.max_frame_mean:.4f}'
    )
    lines.append(f'  Variation Coeff:  {t.temporal_variation:.4f}')
    stability_desc = 'Stable' if t.is_temporally_stable else 'Variable'
    lines.append(f'  Status:           {stability_desc}')


def _append_recommendations(
    lines: list[str],
    result: ColorAnalysisResult,
    suggested_lut_path: str | None = None,
) -> None:
    """Appends color correction recommendations and rationale notes.

    Args:
        lines: List of output report strings.
        result: The analysis result data.
        suggested_lut_path: Optional path where suggested LUT was exported.
    """
    r = result.recommendations
    lines.append('Color Correction Assessment:')
    lines.append(f'  Need Level:       {r.need_level.value.upper()}')
    lines.append('  Recommended Settings (Applied to Video as a Whole):')
    lines.append(f'    Shadows Lift:       {r.recommended_shadow_lift:+.3f}')
    lines.append(f'    Gamma:               {r.recommended_gamma:.3f}')
    lines.append(
        f'    Highlight Rolloff:   {r.recommended_highlight_rolloff:.3f}'
    )
    lines.append(f'    Brightness:         {r.recommended_brightness:+.3f}')
    lines.append(f'    Contrast:            {r.recommended_contrast:.3f}')
    if suggested_lut_path:
        lines.append(f'    Exported 3D LUT:    {suggested_lut_path}')

    lines.append('  Assessment Notes:')
    for note in r.summary_notes:
        lines.append(f'    * {note}')


def _append_frame_samples(
    lines: list[str], result: ColorAnalysisResult
) -> None:
    """Appends per-frame sample metrics for verbose debugging.

    Args:
        lines: List of output report strings.
        result: The analysis result data.
    """
    lines.append('Per-Frame Samples:')
    lines.append('  Timestamp(ms) | FrameIdx | MeanLum | MedianLum | Shadow%')
    lines.append('  ' + '-' * 54)
    for sample in result.frame_samples:
        lines.append(
            f'  {sample.timestamp_ms:13d} | {sample.frame_index:8d} | '
            f'{sample.mean_luminance:7.4f} | {sample.median_luminance:9.4f} | '
            f'{sample.shadow_fraction * 100.0:6.1f}%'
        )


def format_json_report(result: ColorAnalysisResult) -> str:
    """Serializes the color analysis result to a JSON string.

    Args:
        result: The ColorAnalysisResult object to serialize.

    Returns:
        str: JSON formatted string.

    Usage example:
        json_str = format_json_report(result=analysis_res)
    """
    return json.dumps(result.to_dict(), indent=2)


def run_analysis(
    video_path: str,
    sample_interval_ms: int,
    max_frames: int,
    output_format: AnalysisOutputFormat,
    output_stream: TextIO,
    verbose: bool = False,
    export_lut_path: str | None = None,
    lut_size: int = DEFAULT_SUGGESTED_LUT_SIZE,
) -> int:
    """Executes color analysis on a video file and writes formatted output.

    Args:
        video_path: Path to target video file.
        sample_interval_ms: Sampling interval in milliseconds.
        max_frames: Maximum number of frames to sample.
        output_format: Text or JSON format.
        output_stream: Destination stream for output text.
        verbose: Whether to include verbose per-frame data.
        export_lut_path: Optional file path to save suggested 3D LUT.
        lut_size: Dimension size of 3D LUT (default: 33).

    Returns:
        int: Exit status code (0 for success, non-zero for error).

    Usage example:
        exit_code = run_analysis(
            video_path='clip.mp4',
            sample_interval_ms=2000,
            max_frames=100,
            output_format=AnalysisOutputFormat.TEXT,
            output_stream=sys.stdout,
            verbose=False,
            export_lut_path='grade.cube',
        )
    """
    analyzer = ColorAnalyzer(
        sample_interval_ms=sample_interval_ms,
        max_frames=max_frames,
    )
    result = analyzer.analyze(
        video_path=video_path,
        include_frame_samples=verbose,
    )

    if export_lut_path:
        save_suggested_lut(
            recommendations=result.recommendations,
            file_path=export_lut_path,
            lut_size=lut_size,
            title=f'Suggested Grade - {Path(video_path).stem}',
        )

    if output_format == AnalysisOutputFormat.JSON:
        res_dict = result.to_dict()
        if export_lut_path:
            res_dict['suggested_lut_path'] = str(export_lut_path)
        output_stream.write(json.dumps(res_dict, indent=2) + '\n')
    else:
        output_stream.write(
            format_text_report(
                result=result,
                verbose=verbose,
                suggested_lut_path=export_lut_path,
            )
            + '\n'
        )

    return 0


def main() -> None:
    """Main CLI entrypoint for the color-analysis binary.

    Parses command-line options, performs luminance analysis on the provided
    video file, and writes the resulting report to stdout or output file.
    """
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = build_arg_parser()
    args = parser.parse_args()

    video_path = args.video or args.input_video
    if not video_path:
        parser.print_help()
        sys.exit(1)

    try:
        output_format = AnalysisOutputFormat.from_str(args.format)
    except ValueError as exc:
        sys.stderr.write(f'Error: {exc}\n')
        sys.exit(1)

    try:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as out_f:
                exit_code = run_analysis(
                    video_path=video_path,
                    sample_interval_ms=args.sample_interval_ms,
                    max_frames=args.max_frames,
                    output_format=output_format,
                    output_stream=out_f,
                    verbose=args.verbose,
                    export_lut_path=args.export_lut,
                    lut_size=args.lut_size,
                )
        else:
            exit_code = run_analysis(
                video_path=video_path,
                sample_interval_ms=args.sample_interval_ms,
                max_frames=args.max_frames,
                output_format=output_format,
                output_stream=sys.stdout,
                verbose=args.verbose,
                export_lut_path=args.export_lut,
                lut_size=args.lut_size,
            )
        sys.exit(exit_code)
    except (FileNotFoundError, ValueError) as err:
        sys.stderr.write(f'Error: {err}\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
