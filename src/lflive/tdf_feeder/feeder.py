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

import asyncio
import time
from collections.abc import Callable, Sequence

from lflive.tdf_feeder.reader import TdfLine


class TdfFeeder:
    """Streams timestamped TDF lines to a TCP server in paced real time.

    Attributes:
        host: Target server host address string.
        port: Target server TCP port number.
        lines: Sequence of timestamped TdfLine records to transmit.
        speed: Playback speed multiplier (default 1.0 = real-time).
        line_callback: Optional callback invoked after each line is sent.
    """

    def __init__(
        self,
        host: str,
        port: int,
        lines: Sequence[TdfLine],
        speed: float = 1.0,
        line_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """Initializes the TDF feeder.

        Args:
            host: Target IP address or hostname.
            port: Target TCP port number.
            lines: Chronological list of TdfLine instances.
            speed: Playback speed multiplier (greater than 0).
            line_callback: Optional callable called with (idx, total, text).

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
        total_lines = len(self.lines)

        for index, item in enumerate(self.lines):
            await self._wait_for_timestamp(
                target_time_ms=item.time_ms,
                start_clock=start_wall_clock,
            )

            line_bytes = (item.text + '\r\n').encode('utf-16-le')
            writer.write(line_bytes)
            await writer.drain()

            if self.line_callback:
                self.line_callback(index + 1, total_lines, item.text)

        return total_lines

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

