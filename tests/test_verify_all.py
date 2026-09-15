from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lfdata.verify_all import TdfDirectoryVerifier, main


def test_nonexistent_directory() -> None:
    verifier = TdfDirectoryVerifier('nonexistent_dir_path_12345')
    assert verifier.find_tdf_files() == []
    assert not verifier.verify_all()


def test_path_is_file(tmp_path: Path) -> None:
    file_path = tmp_path / 'test.txt'
    file_path.write_text('content')
    verifier = TdfDirectoryVerifier(str(file_path))
    assert verifier.find_tdf_files() == []
    assert not verifier.verify_all()


def test_empty_directory(tmp_path: Path) -> None:
    verifier = TdfDirectoryVerifier(str(tmp_path))
    assert verifier.find_tdf_files() == []
    assert verifier.verify_all()


def test_find_tdf_files_case_insensitive(tmp_path: Path) -> None:
    (tmp_path / 'game1.tdf').write_text('content1')
    (tmp_path / 'game2.TDF').write_text('content2')
    (tmp_path / 'other.txt').write_text('other')

    verifier = TdfDirectoryVerifier(str(tmp_path))
    tdf_files = verifier.find_tdf_files()
    filenames = [f.name for f in tdf_files]
    assert filenames == ['game1.tdf', 'game2.TDF']


def test_verify_file_success(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'valid.tdf'
    tdf_file.write_text('dummy')

    verifier = TdfDirectoryVerifier(str(tmp_path))

    with (
        patch('lfdata.verify_all.TdfImporter'),
        patch('lfdata.verify_all.LFReplayVerifier') as mock_verifier_cls,
    ):
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = True
        mock_verifier_cls.return_value = mock_verifier

        assert verifier.verify_file(tdf_file) is True


def test_verify_file_exception(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'corrupt.tdf'
    tdf_file.write_text('corrupt data')

    verifier = TdfDirectoryVerifier(str(tmp_path))

    with patch('lfdata.verify_all.TdfImporter') as mock_importer_cls:
        mock_importer_cls.side_effect = ValueError('Invalid TDF syntax')
        assert verifier.verify_file(tdf_file) is False


def test_verify_all_mixed_results(tmp_path: Path) -> None:
    (tmp_path / 'pass.tdf').write_text('pass')
    (tmp_path / 'fail.tdf').write_text('fail')

    verifier = TdfDirectoryVerifier(str(tmp_path))

    def mock_verify_side_effect(file_path: Path) -> bool:
        return file_path.name == 'pass.tdf'

    with patch.object(
        verifier, 'verify_file', side_effect=mock_verify_side_effect
    ):
        assert verifier.verify_all() is False


def test_verify_all_all_passed(tmp_path: Path) -> None:
    (tmp_path / 'pass1.tdf').write_text('pass1')
    (tmp_path / 'pass2.tdf').write_text('pass2')

    verifier = TdfDirectoryVerifier(str(tmp_path))

    with patch.object(verifier, 'verify_file', return_value=True):
        assert verifier.verify_all() is True


def test_main_success(tmp_path: Path) -> None:
    (tmp_path / 'test.tdf').write_text('data')

    test_args = ['verify_all.py', str(tmp_path)]
    with (
        patch('sys.argv', test_args),
        patch(
            'lfdata.verify_all.TdfDirectoryVerifier.verify_all',
            return_value=True,
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_main_failure(tmp_path: Path) -> None:
    test_args = ['verify_all.py', str(tmp_path)]
    with (
        patch('sys.argv', test_args),
        patch(
            'lfdata.verify_all.TdfDirectoryVerifier.verify_all',
            return_value=False,
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_find_tdf_files_single_file(tmp_path: Path) -> None:
    single_file = tmp_path / 'single.tdf'
    single_file.write_text('dummy')

    verifier = TdfDirectoryVerifier(str(single_file))
    tdf_files = verifier.find_tdf_files()
    assert tdf_files == [single_file]


def test_verify_all_single_file_success(tmp_path: Path) -> None:
    single_file = tmp_path / 'single.tdf'
    single_file.write_text('dummy')

    verifier = TdfDirectoryVerifier(str(single_file))
    with patch.object(verifier, 'verify_file', return_value=True):
        assert verifier.verify_all() is True


def test_verify_all_single_file_failure(tmp_path: Path) -> None:
    single_file = tmp_path / 'single.tdf'
    single_file.write_text('dummy')

    verifier = TdfDirectoryVerifier(str(single_file))
    with patch.object(verifier, 'verify_file', return_value=False):
        assert verifier.verify_all() is False


def test_target_path_property(tmp_path: Path) -> None:
    verifier = TdfDirectoryVerifier(str(tmp_path))
    assert verifier.target_path == tmp_path


def test_directory_path_legacy_kwarg(tmp_path: Path) -> None:
    verifier = TdfDirectoryVerifier(directory_path=str(tmp_path))
    assert verifier.target_path == tmp_path


def test_main_single_file(tmp_path: Path) -> None:
    single_file = tmp_path / 'single.tdf'
    single_file.write_text('dummy')

    test_args = ['verify_all.py', str(single_file)]
    with (
        patch('sys.argv', test_args),
        patch(
            'lfdata.verify_all.TdfDirectoryVerifier.verify_all',
            return_value=True,
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_boost_grace_period_ms_defaults_and_options(tmp_path: Path) -> None:
    verifier_default = TdfDirectoryVerifier(str(tmp_path))
    assert verifier_default.boost_grace_period_ms == 700

    verifier_custom = TdfDirectoryVerifier(
        str(tmp_path), boost_grace_period_ms=950
    )
    assert verifier_custom.boost_grace_period_ms == 950


def test_verify_file_passes_boost_grace_period_ms(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'game.tdf'
    tdf_file.write_text('dummy')

    verifier = TdfDirectoryVerifier(str(tmp_path), boost_grace_period_ms=950)
    with (
        patch('lfdata.verify_all.TdfImporter'),
        patch('lfdata.verify_all.LFReplayVerifier') as mock_verifier_cls,
    ):
        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = True
        mock_verifier_cls.return_value = mock_verifier

        assert verifier.verify_file(tdf_file) is True
        mock_verifier_cls.assert_called_once_with(
            mock_verifier_cls.call_args[0][0],
            boost_grace_period_ms=950,
        )


def test_main_with_boost_grace_period_arg(tmp_path: Path) -> None:
    test_args = [
        'verify_all.py',
        str(tmp_path),
        '--boost_grace_period_ms',
        '950',
    ]
    with (
        patch('sys.argv', test_args),
        patch('lfdata.verify_all.TdfDirectoryVerifier') as mock_verifier_cls,
    ):
        mock_verifier = MagicMock()
        mock_verifier.verify_all.return_value = True
        mock_verifier_cls.return_value = mock_verifier

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_verifier_cls.assert_called_once_with(
            target_path=str(tmp_path),
            boost_grace_period_ms=950,
        )


def test_main_with_boost_grace_period_alias_arg(tmp_path: Path) -> None:
    test_args = [
        'verify_all.py',
        str(tmp_path),
        '--boost_grace_period',
        '950',
    ]
    with (
        patch('sys.argv', test_args),
        patch('lfdata.verify_all.TdfDirectoryVerifier') as mock_verifier_cls,
    ):
        mock_verifier = MagicMock()
        mock_verifier.verify_all.return_value = True
        mock_verifier_cls.return_value = mock_verifier

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_verifier_cls.assert_called_once_with(
            target_path=str(tmp_path),
            boost_grace_period_ms=950,
        )


def test_has_wildcards_property(tmp_path: Path) -> None:
    verifier_plain = TdfDirectoryVerifier(str(tmp_path))
    assert not verifier_plain.has_wildcards

    verifier_star = TdfDirectoryVerifier(str(tmp_path / '*.tdf'))
    assert verifier_star.has_wildcards

    verifier_question = TdfDirectoryVerifier(str(tmp_path / 'game?.tdf'))
    assert verifier_question.has_wildcards


def test_find_tdf_files_wildcard_asterisk(tmp_path: Path) -> None:
    (tmp_path / 'sm5_alpha.tdf').write_text('content1')
    (tmp_path / 'sm5_beta.tdf').write_text('content2')
    (tmp_path / 'other.tdf').write_text('content3')
    (tmp_path / 'sm5_gamma.txt').write_text('content4')

    verifier = TdfDirectoryVerifier(str(tmp_path / 'sm5_*.tdf'))
    tdf_files = verifier.find_tdf_files()
    filenames = [f.name for f in tdf_files]
    assert filenames == ['sm5_alpha.tdf', 'sm5_beta.tdf']


def test_find_tdf_files_wildcard_question_mark(tmp_path: Path) -> None:
    (tmp_path / 'match1.tdf').write_text('content1')
    (tmp_path / 'match2.tdf').write_text('content2')
    (tmp_path / 'match10.tdf').write_text('content3')

    verifier = TdfDirectoryVerifier(str(tmp_path / 'match?.tdf'))
    tdf_files = verifier.find_tdf_files()
    filenames = [f.name for f in tdf_files]
    assert filenames == ['match1.tdf', 'match2.tdf']


def test_find_tdf_files_wildcard_ignores_non_tdf(tmp_path: Path) -> None:
    (tmp_path / 'test1.txt').write_text('text1')
    (tmp_path / 'test2.log').write_text('text2')

    verifier = TdfDirectoryVerifier(str(tmp_path / 'test*.*'))
    tdf_files = verifier.find_tdf_files()
    assert tdf_files == []


def test_find_tdf_files_wildcard_no_match(tmp_path: Path) -> None:
    verifier = TdfDirectoryVerifier(str(tmp_path / 'nonexistent_*.tdf'))
    assert verifier.find_tdf_files() == []


def test_verify_all_wildcard_all_passed(tmp_path: Path) -> None:
    (tmp_path / 'pass1.tdf').write_text('p1')
    (tmp_path / 'pass2.tdf').write_text('p2')

    verifier = TdfDirectoryVerifier(str(tmp_path / 'pass*.tdf'))
    with patch.object(verifier, 'verify_file', return_value=True):
        assert verifier.verify_all() is True


def test_verify_all_wildcard_one_failed(tmp_path: Path) -> None:
    (tmp_path / 'pass1.tdf').write_text('p1')
    (tmp_path / 'fail1.tdf').write_text('f1')

    verifier = TdfDirectoryVerifier(str(tmp_path / '*.tdf'))

    def mock_verify(file_path: Path) -> bool:
        return 'pass' in file_path.name

    with patch.object(verifier, 'verify_file', side_effect=mock_verify):
        assert verifier.verify_all() is False


def test_verify_all_wildcard_no_matches(tmp_path: Path) -> None:
    verifier = TdfDirectoryVerifier(str(tmp_path / 'nonexistent_*.tdf'))
    assert verifier.verify_all() is False


def test_main_wildcard_success(tmp_path: Path) -> None:
    (tmp_path / 'main1.tdf').write_text('m1')
    (tmp_path / 'main2.tdf').write_text('m2')

    test_args = ['verify_all.py', str(tmp_path / 'main*.tdf')]
    with (
        patch('sys.argv', test_args),
        patch(
            'lfdata.verify_all.TdfDirectoryVerifier.verify_all',
            return_value=True,
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_main_multiple_paths_all_passed(tmp_path: Path) -> None:
    file1 = tmp_path / 'f1.tdf'
    file2 = tmp_path / 'f2.tdf'
    file1.write_text('f1')
    file2.write_text('f2')

    test_args = ['verify_all.py', str(file1), str(file2)]
    with (
        patch('sys.argv', test_args),
        patch(
            'lfdata.verify_all.TdfDirectoryVerifier.verify_all',
            return_value=True,
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_main_multiple_paths_one_failed(tmp_path: Path) -> None:
    file1 = tmp_path / 'f1.tdf'
    file2 = tmp_path / 'f2.tdf'
    file1.write_text('f1')
    file2.write_text('f2')

    test_args = ['verify_all.py', str(file1), str(file2)]

    def mock_verify_all(self: TdfDirectoryVerifier) -> bool:
        return 'f1' in str(self.target_path)

    with (
        patch('sys.argv', test_args),
        patch(
            'lfdata.verify_all.TdfDirectoryVerifier.verify_all',
            mock_verify_all,
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
