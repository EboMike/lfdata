"""Module to verify TDF files in a specified directory or a single TDF file.

This module provides validation utilities to iterate over directories
containing LF TDF files or verify an individual TDF file, parsing each file
and running state verification to detect data format errors or integrity
anomalies.

Usage example:
    from lfdata.verify_all import TdfDirectoryVerifier

    verifier = TdfDirectoryVerifier(target_path='tdf_files/')
    success = verifier.verify_all()
    if not success:
        print('One or more TDF files failed verification.')

    single_verifier = TdfDirectoryVerifier(target_path='game.tdf')
    if single_verifier.verify_all():
        print('Single file verified successfully.')
"""

import argparse
from pathlib import Path
import sys

from lfdata.importer import TdfImporter
from lfdata.replay import LFReplayVerifier


class TdfDirectoryVerifier:
    """Verifier for TDF files in a target directory or single TDF file.

    Holds the target path and coordinates verifying individual TDF files or
    all matching TDF files discovered in a directory.

    Attributes:
        target_path: The target Path object pointing to a directory or TDF file.
    """

    def __init__(
        self,
        target_path: str = '.',
        *,
        directory_path: str | None = None,
    ) -> None:
        """Initializes the TDF verifier with a target path.

        Accepts either a directory containing TDF files or a direct path to a
        single TDF file.

        Args:
            target_path: Path to the directory or single TDF file to verify.
                Defaults to '.'.
            directory_path: Optional legacy alias for target_path.

        Usage:
            verifier = TdfDirectoryVerifier('tdf_files/')
            single_verifier = TdfDirectoryVerifier('game.tdf')
        """
        raw_path = directory_path if directory_path is not None else target_path
        self._target_path = Path(raw_path)
        self._directory = self._target_path

    @property
    def target_path(self) -> Path:
        """Returns the configured target path.

        Returns:
            The Path configured for verification.
        """
        return self._target_path

    def find_tdf_files(self) -> list[Path]:
        """Finds all matching TDF files based on the configured path.

        If the target path is a single TDF file, returns a list containing that
        file. If the target path is a directory, returns all TDF files found
        within it.

        Returns:
            A list of Path objects for all matching TDF files, sorted by name.

        Usage:
            tdf_files = verifier.find_tdf_files()
        """
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

    def verify_file(self, file_path: Path) -> bool:
        """Verifies a single TDF file using LFReplayVerifier.

        Parses the TDF file into a game model and runs the LF replay
        verifier on the resulting game replay events.

        Args:
            file_path: The Path object of the TDF file to verify.

        Returns:
            True if verification passed without errors, False otherwise.

        Usage:
            passed = verifier.verify_file(file_path=Path('game.tdf'))
        """
        try:
            importer = TdfImporter(str(file_path))
            game = importer.parse()
            verifier = LFReplayVerifier(game)
            return verifier.verify()
        except Exception as exc:
            print(f'Error verifying {file_path.name}: {exc}')
            return False

    def verify_all(self) -> bool:
        """Verifies all TDF files found in the configured path.

        Iterates over discovered TDF files or verifies the single configured
        file, printing status output for each.

        Returns:
            True if all TDF files pass verification, False if any file fails.

        Usage:
            success = verifier.verify_all()
        """
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

        all_passed = True
        separator = '=' * 72
        for file_path in tdf_files:
            print(separator)
            print(f'Verifying: {file_path.name}')
            print(separator)

            success = self.verify_file(file_path=file_path)
            if success:
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


# Alias for backwards compatibility and generic usage
TdfVerifier = TdfDirectoryVerifier


def main() -> None:
    """Main entry point for verifying TDF files in a directory or single file.

    Parses CLI arguments and executes verification on either a directory of
    TDF files or a single specified TDF file.

    Returns:
        None.

    Raises:
        SystemExit: On execution completion with code 0 or 1.
    """
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(
        description=(
            'Run validation-only mode on TDF files in a directory or a single'
            ' TDF file.'
        )
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory or single TDF file to verify (defaults to .).',
    )

    args = parser.parse_args()
    verifier = TdfDirectoryVerifier(target_path=args.path)
    success = verifier.verify_all()
    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
