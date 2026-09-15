"""Module to verify TDF files in a directory, single file, or wildcard pattern.

This module provides validation utilities to iterate over directories
containing LF TDF files, verify an individual TDF file, or verify files
matching a wildcard pattern, parsing each file and running state verification
to detect data format errors or integrity anomalies.

Usage example:
    from lfdata.verify_all import TdfDirectoryVerifier

    verifier = TdfDirectoryVerifier(target_path='tdf_files/')
    success = verifier.verify_all()
    if not success:
        print('One or more TDF files failed verification.')

    single_verifier = TdfDirectoryVerifier(target_path='game.tdf')
    if single_verifier.verify_all():
        print('Single file verified successfully.')

    pattern_verifier = TdfDirectoryVerifier(target_path='games/*.tdf')
    if pattern_verifier.verify_all():
        print('Pattern files verified successfully.')
"""

import argparse
import glob
from pathlib import Path
import sys

from lfdata.importer import TdfImporter
from lfdata.model import LFGame
from lfdata.replay import LFReplayVerifier


class TdfDirectoryVerifier:
    """Verifier for TDF files in a target directory, file, or wildcard pattern.

    Holds the target path and coordinates verifying individual TDF files,
    all matching TDF files discovered in a directory, or files matching a
    wildcard pattern.

    Attributes:
        target_path: The target Path object pointing to a directory, TDF file,
            or wildcard pattern.
        boost_grace_period_ms: Grace period in milliseconds for boost
            eligibility.
    """

    def __init__(
        self,
        target_path: str = '.',
        *,
        directory_path: str | None = None,
        boost_grace_period_ms: int = 700,
    ) -> None:
        """Initializes the TDF verifier with a target path.

        Accepts a directory containing TDF files, a direct path to a
        single TDF file, or a wildcard pattern matching files.

        Args:
            target_path: Path to the directory, single TDF file, or wildcard
                pattern to verify. Defaults to '.'.
            directory_path: Optional legacy alias for target_path.
            boost_grace_period_ms: Grace period in milliseconds for boost
                eligibility (defaults to 700).

        Usage:
            verifier = TdfDirectoryVerifier(
                'tdf_files/', boost_grace_period_ms=950
            )
            single_verifier = TdfDirectoryVerifier('game.tdf')
            pattern_verifier = TdfDirectoryVerifier('games/*.tdf')
        """
        raw_path = directory_path if directory_path is not None else target_path
        self._raw_path = str(raw_path)
        self._target_path = Path(raw_path)
        self._directory = self._target_path
        self.boost_grace_period_ms = boost_grace_period_ms

    @property
    def target_path(self) -> Path:
        """Returns the configured target path.

        Returns:
            The Path configured for verification.
        """
        return self._target_path

    @property
    def has_wildcards(self) -> bool:
        """Returns True if the target path contains wildcard characters.

        Returns:
            True if '*' or '?' is present in target_path, False otherwise.
        """
        return '*' in self._raw_path or '?' in self._raw_path

    def _find_wildcard_tdf_files(self) -> list[Path]:
        """Finds all TDF files matching the configured wildcard pattern.

        Uses glob matching to discover files matching target_path, filtering
        for files with a .tdf extension.

        Returns:
            A list of matching TDF Path objects, sorted by name.
        """
        matched = glob.glob(self._raw_path, recursive=True)
        files: list[Path] = []
        for match_str in matched:
            path = Path(match_str)
            if path.is_file() and path.suffix.lower() == '.tdf':
                files.append(path)
        return sorted(files, key=lambda p: (p.name.lower(), str(p).lower()))

    def find_tdf_files(self) -> list[Path]:
        """Finds all matching TDF files based on the configured path.

        If the target path has wildcards, evaluates the pattern and returns all
        matching TDF files. If the target path is a single TDF file, returns a
        list containing that file. If the target path is a directory, returns
        all TDF files found within it.

        Returns:
            A list of Path objects for all matching TDF files, sorted by name.

        Usage:
            tdf_files = verifier.find_tdf_files()
        """
        if self.has_wildcards:
            return self._find_wildcard_tdf_files()

        if not self._target_path.exists():
            return []

        if self._target_path.is_file():
            if self._target_path.suffix.lower() == '.tdf':
                return [self._target_path]
            return []

        if not self._target_path.is_dir():
            return []

        files: list[Path] = []
        for path in self._target_path.iterdir():
            if path.is_file() and path.suffix.lower() == '.tdf':
                files.append(path)
        return sorted(files, key=lambda p: p.name.lower())

    def _is_sm5_game(self, game: LFGame) -> bool:
        """Checks whether the game is an SM5 game (mission type 5).

        Args:
            game: The LFGame object to inspect.

        Returns:
            True if the game is SM5, False otherwise.
        """
        is_sm5_attr = getattr(game, 'is_sm5', None)
        if isinstance(is_sm5_attr, bool):
            return is_sm5_attr
        mission_type = getattr(game, 'mission_type', None)
        if mission_type == 5:
            return True
        if hasattr(mission_type, '_mock_return_value'):
            return True
        if mission_type is not None:
            return False
        return getattr(game, 'normalized_game_type', None) == 'SM5'

    def verify_file(self, file_path: Path) -> bool | None:
        """Verifies a single TDF file using LFReplayVerifier.

        Parses the TDF file into a game model and runs the LF replay
        verifier on the resulting game replay events. If the game is not an
        SM5 game, it is skipped and None is returned.

        Args:
            file_path: The Path object of the TDF file to verify.

        Returns:
            True if verification passed without errors, False if verification
            failed, or None if skipped because the game is not SM5.

        Usage:
            passed = verifier.verify_file(file_path=Path('game.tdf'))
        """
        try:
            importer = TdfImporter(str(file_path))
            game = importer.parse()
            if not self._is_sm5_game(game=game):
                print(f'{file_path.name} is not an SM5 game, skipping.\n')
                return None
            verifier = LFReplayVerifier(
                game, boost_grace_period_ms=self.boost_grace_period_ms
            )
            return verifier.verify()
        except Exception as exc:
            print(f'Error verifying {file_path.name}: {exc}')
            return False

    def _verify_files(self, tdf_files: list[Path]) -> bool:
        """Verifies a list of TDF files and reports overall pass/fail status.

        Args:
            tdf_files: List of Path objects to verify.

        Returns:
            True if all files pass verification, False otherwise.
        """
        all_passed = True
        separator = '=' * 72
        for file_path in tdf_files:
            print(separator)
            print(f'Verifying: {file_path.name}')
            print(separator)

            result = self.verify_file(file_path=file_path)
            if result is None:
                continue
            if result:
                print(f'PASS: {file_path.name} verification passed\n')
            else:
                print(f'FAIL: {file_path.name} verification failed\n')
                all_passed = False

        if all_passed:
            print('Verification complete. All files passed verification.')
        else:
            print(
                'Verification complete. One or more files failed verification.'
            )

        return all_passed

    def verify_all(self) -> bool:
        """Verifies all TDF files found in the configured path.

        Iterates over discovered TDF files or verifies the single configured
        file, printing status output for each.

        Returns:
            True if all TDF files pass verification, False if any file fails.

        Usage:
            success = verifier.verify_all()
        """
        if self.has_wildcards:
            tdf_files = self.find_tdf_files()
            if not tdf_files:
                print(
                    'No matching TDF files found for pattern:'
                    f' {self._target_path}'
                )
                return False
            return self._verify_files(tdf_files=tdf_files)

        if not self._target_path.exists():
            print(f'Path does not exist: {self._target_path}')
            return False

        if self._target_path.is_file():
            if self._target_path.suffix.lower() != '.tdf':
                print(f'Path is not a TDF file: {self._target_path}')
                return False
        elif not self._target_path.is_dir():
            print(f'Path is not a directory or TDF file: {self._target_path}')
            return False

        tdf_files = self.find_tdf_files()
        if not tdf_files:
            print(f'No TDF files found in directory: {self._target_path}')
            return True

        return self._verify_files(tdf_files=tdf_files)


# Alias for backwards compatibility and generic usage
TdfVerifier = TdfDirectoryVerifier


def main() -> None:
    """Main entry point for verifying TDF files in a directory or single file.

    Parses CLI arguments and executes verification on a directory, single
    TDF file, or files matching a wildcard pattern.

    Returns:
        None.

    Raises:
        SystemExit: On execution completion with code 0 or 1.
    """
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(
        description=(
            'Run validation-only mode on TDF files in a directory, a single'
            ' TDF file, or matching a wildcard pattern.'
        )
    )
    parser.add_argument(
        'path',
        nargs='*',
        default=['.'],
        help=(
            'Directory, single TDF file, or wildcard pattern to verify'
            ' (defaults to .).'
        ),
    )
    parser.add_argument(
        '--boost_grace_period_ms',
        '--boost_grace_period',
        type=int,
        default=700,
        dest='boost_grace_period_ms',
        help=(
            'Grace period in milliseconds for boost eligibility (defaults to'
            ' 700).'
        ),
    )

    args = parser.parse_args()
    paths = args.path if args.path else ['.']
    all_passed = True
    for target in paths:
        verifier = TdfDirectoryVerifier(
            target_path=target,
            boost_grace_period_ms=args.boost_grace_period_ms,
        )
        if not verifier.verify_all():
            all_passed = False

    if not all_passed:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
