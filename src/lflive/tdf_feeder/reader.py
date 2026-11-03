"""TDF file reader and timestamp parser for real-time streaming simulation.

This module reads tab-delimited TDF game files with various character encodings
(UTF-16LE, UTF-8) and extracts target millisecond timestamps for each line.

Usage example:
    from lflive.tdf_feeder.reader import TdfFileReader

    reader = TdfFileReader('assets/game.tdf')
    lines = reader.read_lines()
    for item in lines:
        print(item.time_ms, item.text)
"""

import dataclasses
from pathlib import Path


@dataclasses.dataclass
class TdfLine:
    """Represents a TDF text line with its target playback timestamp.

    Attributes:
        text: Raw text string of the line without trailing newlines.
        time_ms: Playback elapsed time offset in milliseconds.
    """

    text: str
    time_ms: int


class TdfFileReader:
    """Reads and parses TDF files into timestamped line objects.

    Attributes:
        file_path: Relative or absolute path to the TDF file.
    """

    def __init__(self, file_path: str | Path) -> None:
        """Initializes the reader with a file path.

        Args:
            file_path: Path to the TDF file to parse.
        """
        self.file_path = Path(file_path)

    def read_lines(self) -> list[TdfLine]:
        """Reads file contents, decodes text, and assigns millisecond timestamps.

        Returns:
            list[TdfLine]: Chronological list of timestamped lines.

        Raises:
            FileNotFoundError: If the target file does not exist.
            ValueError: If the file cannot be decoded with supported encodings.

        Usage example:
            lines = reader.read_lines()
            assert len(lines) > 0
        """
        raw_text = self._read_file_content()
        return self._parse_lines(content=raw_text)

    def _read_file_content(self) -> str:
        """Reads file bytes and decodes using UTF-16 or UTF-8 encodings.

        Returns:
            str: Decoded file content.

        Raises:
            FileNotFoundError: If the file is missing.
            ValueError: If all decoding attempts fail.
        """
        if not self.file_path.is_file():
            raise FileNotFoundError(f'TDF file not found: {self.file_path}')

        raw_bytes = self.file_path.read_bytes()

        for encoding in ('utf-16-le', 'utf-16', 'utf-8-sig', 'utf-8'):
            try:
                decoded = raw_bytes.decode(encoding)
                if decoded.startswith('\ufeff'):
                    decoded = decoded[1:]
                return decoded
            except UnicodeDecodeError:
                continue

        raise ValueError(
            f'Unable to decode TDF file with supported encodings: '
            f'{self.file_path}'
        )

    def _parse_lines(self, content: str) -> list[TdfLine]:
        """Parses decoded text into timestamped TdfLine entries.

        Args:
            content: Raw text content of the TDF file.

        Returns:
            list[TdfLine]: List of parsed TdfLine instances.
        """
        result: list[TdfLine] = []
        current_time_ms = 0

        for raw_line in content.splitlines():
            line = raw_line.rstrip('\r\n')
            extracted_time_ms = self._extract_timestamp_ms(line=line)
            if extracted_time_ms is not None:
                current_time_ms = extracted_time_ms

            result.append(
                TdfLine(
                    text=line,
                    time_ms=current_time_ms,
                )
            )

        return result

    def _extract_timestamp_ms(self, line: str) -> int | None:
        """Extracts the millisecond timestamp from a TDF line if present.

        Args:
            line: Single line of TDF data.

        Returns:
            int | None: Millisecond offset integer, or None if not applicable.
        """
        stripped = line.strip()
        if not stripped or stripped.startswith(';'):
            return None

        parts = stripped.split('\t')
        if len(parts) < 2:
            return None

        record_type = parts[0]
        if record_type in ('3', '4', '5', '6', '9', '11', '12', '13'):
            try:
                return int(parts[1])
            except ValueError:
                return None

        return None

