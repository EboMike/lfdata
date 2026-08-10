"""Module to verify all TDF files in a specified directory.

This module provides batch validation utilities to iterate over directories containing
Laserforce TDF files, parsing each file and running state verification to detect
data format errors or integrity anomalies.

Usage example:
    from lfdata.verify_all import TdfDirectoryVerifier

    verifier = TdfDirectoryVerifier(directory_path='tdf_files/')
    success = verifier.verify_all()
    if not success:
        print('One or more TDF files failed verification.')
"""

import argparse
from pathlib import Path
import sys

from lfdata.importer import TdfImporter
from lfdata.replay import LFReplayVerifier


class TdfDirectoryVerifier:
    """Batch verifier for TDF files in a target directory.

    Holds the target directory path and coordinates iterating over TDF files,
    invoking importers and game replay state verifiers for each file.
    """

    def __init__(self, directory_path: str) -> None:
        """Initializes the directory verifier.

        Args:
            directory_path: Path to the directory containing TDF files.
        """
        self._directory = Path(directory_path)

    def find_tdf_files(self) -> list[Path]:
        """Finds all TDF files in the configured directory.

        Returns:
            A list of Path objects for all matching TDF files, sorted by name.
        """
        if not self._directory.exists() or not self._directory.is_dir():
            return []

        files: list[Path] = []
        for path in self._directory.iterdir():
            if path.is_file() and path.suffix.lower() == '.tdf':
                files.append(path)
        return sorted(files, key=lambda p: p.name.lower())

    def verify_file(self, file_path: Path) -> bool:
        """Verifies a single TDF file using LFReplayVerifier.

        Args:
            file_path: The Path object of the TDF file to verify.

        Returns:
            True if verification passed without errors, False otherwise.
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
        """Verifies all TDF files found in the directory.

        Returns:
            True if all TDF files pass verification, False if any file fails.
        """
        if not self._directory.exists():
            print(f'Directory does not exist: {self._directory}')
            return False

        if not self._directory.is_dir():
            print(f'Path is not a directory: {self._directory}')
            return False

        tdf_files = self.find_tdf_files()
        if not tdf_files:
            print(f'No TDF files found in directory: {self._directory}')
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


def main() -> None:
    """Main entry point for verifying TDF files in a directory."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(
        description='Run validation-only mode on all TDF files in a directory.'
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Directory containing TDF files to verify (defaults to .).',
    )

    args = parser.parse_args()
    verifier = TdfDirectoryVerifier(directory_path=args.directory)
    success = verifier.verify_all()
    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
