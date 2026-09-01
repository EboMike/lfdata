from pathlib import Path
from unittest.mock import patch


from lfdata.video.hud_merger import HudMergeOptions, VideoMetadata
from lfdata.video.hudmerge import (
    build_argument_parser,
    main,
    parse_options,
    run_merge,
)


def test_build_argument_parser_required_arguments():
    parser = build_argument_parser()
    args = parser.parse_args(['gopro.mp4', 'hud.mp4', 'alpha.mp4'])
    assert args.gopro == 'gopro.mp4'
    assert args.hud == 'hud.mp4'
    assert args.hud_alpha == 'alpha.mp4'
    assert args.output is None
    assert args.fade_duration_ms == 5000
    assert args.crf == 18
    assert args.preset == 'medium'
    assert args.lut is None
    assert args.dry_run is False


def test_build_argument_parser_custom_options():
    parser = build_argument_parser()
    args = parser.parse_args(
        [
            'gopro.mp4',
            'hud.mp4',
            'alpha.mp4',
            '-o',
            'custom_out.mp4',
            '--fade_duration_ms',
            '3000',
            '--crf',
            '22',
            '--preset',
            'veryslow',
            '--lut',
            'color/grade.cube',
            '--dry-run',
        ]
    )
    assert args.output == 'custom_out.mp4'
    assert args.fade_duration_ms == 3000
    assert args.crf == 22
    assert args.preset == 'veryslow'
    assert args.lut == 'color/grade.cube'
    assert args.dry_run is True


def test_build_argument_parser_cube_alias():
    parser = build_argument_parser()
    args = parser.parse_args(
        ['gopro.mp4', 'hud.mp4', 'alpha.mp4', '--cube', 'my_grade.cube']
    )
    assert args.lut == 'my_grade.cube'


def test_parse_options_default_output():
    parser = build_argument_parser()
    args = parser.parse_args(['videos/gopro.mp4', 'hud.mp4', 'alpha.mp4'])
    options = parse_options(args=args)

    assert options.gopro_path == Path('videos/gopro.mp4')
    assert options.hud_path == Path('hud.mp4')
    assert options.hud_alpha_path == Path('alpha.mp4')
    assert options.output_path == Path('videos/gopro-merged.mp4')
    assert options.lut_path is None


def test_parse_options_with_lut():
    parser = build_argument_parser()
    args = parser.parse_args(
        ['gopro.mp4', 'hud.mp4', 'alpha.mp4', '--lut', 'grades/lut.cube']
    )
    options = parse_options(args=args)

    assert options.lut_path == Path('grades/lut.cube')


def test_parse_options_custom_output():
    parser = build_argument_parser()
    args = parser.parse_args(
        ['gopro.mp4', 'hud.mp4', 'alpha.mp4', '-o', 'final.mp4']
    )
    options = parse_options(args=args)

    assert options.output_path == Path('final.mp4')


def test_run_merge_dry_run(capsys):
    options = HudMergeOptions(
        gopro_path=Path('gopro.mp4'),
        hud_path=Path('hud.mp4'),
        hud_alpha_path=Path('alpha.mp4'),
        output_path=Path('merged.mp4'),
    )
    dummy_meta = VideoMetadata(
        width=1920,
        height=1080,
        duration_ms=60000,
        has_audio=False,
    )

    with patch(
        'lfdata.video.hud_merger.HudMerger.probe_video',
        return_value=dummy_meta,
    ):
        code = run_merge(options=options, dry_run=True)
        assert code == 0
        captured = capsys.readouterr()
        assert 'Dry run FFmpeg command:' in captured.out
        assert 'ffmpeg' in captured.out


def test_run_merge_live():
    options = HudMergeOptions(
        gopro_path=Path('gopro.mp4'),
        hud_path=Path('hud.mp4'),
        hud_alpha_path=Path('alpha.mp4'),
        output_path=Path('merged.mp4'),
    )

    with patch('lfdata.video.hud_merger.HudMerger.merge') as mock_merge:
        code = run_merge(options=options, dry_run=False)
        assert code == 0
        mock_merge.assert_called_once_with(options=options)


def test_main_success():
    with patch(
        'lfdata.video.hudmerge.run_merge', return_value=0
    ) as mock_run_merge:
        exit_code = main(['gopro.mp4', 'hud.mp4', 'alpha.mp4'])
        assert exit_code == 0
        mock_run_merge.assert_called_once()


def test_main_error_handling(capsys):
    with patch(
        'lfdata.video.hudmerge.run_merge',
        side_effect=RuntimeError('Probing failed'),
    ):
        exit_code = main(['gopro.mp4', 'hud.mp4', 'alpha.mp4'])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert 'Error: Probing failed' in captured.err
