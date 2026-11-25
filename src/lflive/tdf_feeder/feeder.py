"""Asynchronous real-time TCP feeder streaming TDF data in UTF-16LE.

This module provides `TdfFeeder`, which connects to a live parser server via
TCP and transmits timestamped TDF lines paced in real time.

Usage example:
    from lflive.tdf_feeder.feeder import TdfFeeder
    from lflive.tdf_feeder.reader import TdfLine

    feeder = TdfFeeder(
        host='127.0.0.1',
        port=8000,
        lines=[TdfLine(text='4\\t0000000\\t0100', time_ms=0)],
    )
    await feeder.feed()
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from lflive.tdf_feeder.reader import TdfLine

MISSION_TIMESTAMP_FORMAT = '%Y%m%d%H%M%S'
TDF_RECORD_MISSION = '1'


def _current_local_time() -> datetime:
    """Returns the current local system time.

    Reads the system clock in UTC and converts it to the local timezone so
    the returned datetime is timezone-aware.

    Returns:
        datetime: Current local system time.
    """
    return datetime.now(timezone.utc).astimezone()


class TdfFeeder:
    """Streams timestamped TDF lines to a TCP server in paced real time.

    Attributes:
        host: Target server host address string.
        port: Target server TCP port number.
        lines: Sequence of timestamped TdfLine records to transmit.
        speed: Playback speed multiplier (default 1.0 = real-time).
        line_callback: Optional callback invoked after each line is sent.
        rewrite_timestamps: Whether to rewrite game timestamps to now.
    """

    def __init__(
        self,
        host: str,
        port: int,
        lines: Sequence[TdfLine],
        speed: float = 1.0,
        line_callback: Callable[[int, int, str], None] | None = None,
        rewrite_timestamps: bool = False,
    ) -> None:
        """Initializes the TDF feeder.

        Args:
            host: Target IP address or hostname.
            port: Target TCP port number.
            lines: Chronological list of TdfLine instances.
            speed: Playback speed multiplier (greater than 0).
            line_callback: Optional callable called with (idx, total, text).
            rewrite_timestamps: Whether to rewrite game timestamps to now.

        Raises:
            ValueError: If speed is less than or equal to 0.
        """
        if speed <= 0:
            raise ValueError('Speed multiplier must be greater than 0.')

        self.host = host
        self.port = port
        self.lines = list(lines)
        self.speed = speed
        self.line_callback = line_callback
        self.rewrite_timestamps = rewrite_timestamps

    async def feed(self) -> int:
        """Connects via TCP, streams all lines paced by time, and closes socket.

        Returns:
            int: Total count of lines transmitted.

        Raises:
            ConnectionRefusedError: If the target server is unreachable.
            OSError: On network transmission errors.

        Usage example:
            sent_count = await feeder.feed()
            print(f'Sent {sent_count} lines.')
        """
        _, writer = await asyncio.open_connection(
            host=self.host, port=self.port
        )
        try:
            return await self._stream_lines(writer=writer)
        finally:
            writer.close()
            await writer.wait_closed()

    async def _stream_lines(self, writer: asyncio.StreamWriter) -> int:
        """Transmits lines in UTF-16LE according to their timestamps.

        Args:
            writer: Active StreamWriter connected to target server.

        Returns:
            int: Number of lines sent.
        """
        # Write initial UTF-16LE byte order marker
        writer.write(b'\xff\xfe')
        await writer.drain()

        start_wall_clock = time.monotonic()
        start_timestamp = (
            _current_local_time().strftime(MISSION_TIMESTAMP_FORMAT)
            if self.rewrite_timestamps
            else ''
        )
        total_lines = len(self.lines)

        for index, item in enumerate(self.lines):
            await self._wait_for_timestamp(
                target_time_ms=item.time_ms,
                start_clock=start_wall_clock,
            )

            line_text = item.text
            if self.rewrite_timestamps:
                line_text = self._rewrite_line_timestamp(
                    text=line_text,
                    timestamp_str=start_timestamp,
                )

            line_bytes = (line_text + '\r\n').encode('utf-16-le')
            writer.write(line_bytes)
            await writer.drain()

            if self.line_callback:
                self.line_callback(index + 1, total_lines, line_text)

        return total_lines

    def _rewrite_line_timestamp(self, text: str, timestamp_str: str) -> str:
        """Rewrites the wall-clock start timestamp on a mission TDF line.

        If the line is a type 1 mission record with at least 6 tab-delimited
        fields, replaces the start timestamp field with ``timestamp_str``.

        Args:
            text: Raw TDF line text without trailing newlines.
            timestamp_str: Formatted timestamp string (YYYYMMDDHHMMSS).

        Returns:
            str: Rewritten line text, or original text if not applicable.
        """
        stripped = text.strip()
        if not stripped or stripped.startswith(';'):
            return text

        parts = text.split('\t')
        if parts[0].strip() != TDF_RECORD_MISSION or len(parts) < 6:
            return text

        start_index = 4 if len(parts) >= 7 else 3
        parts[start_index] = timestamp_str
        return '\t'.join(parts)

    async def _wait_for_timestamp(
        self, target_time_ms: int, start_clock: float
    ) -> None:
        """Paces execution so the current line is sent at the target time.

        Args:
            target_time_ms: Expected game timestamp in milliseconds.
            start_clock: Reference start monotonic clock in seconds.
        """
        if target_time_ms <= 0:
            return

        elapsed_ms = (time.monotonic() - start_clock) * 1000.0
        scheduled_target_ms = target_time_ms / self.speed
        wait_ms = scheduled_target_ms - elapsed_ms

        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000.0)
