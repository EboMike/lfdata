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

    with patch.object(verifier, 'verify_file', side_effect=mock_verify_side_effect):
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
        patch('lfdata.verify_all.TdfDirectoryVerifier.verify_all', return_value=True),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_main_failure(tmp_path: Path) -> None:
    test_args = ['verify_all.py', str(tmp_path)]
    with (
        patch('sys.argv', test_args),
        patch('lfdata.verify_all.TdfDirectoryVerifier.verify_all', return_value=False),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
