"""Asynchronous TCP listener for incoming Laserforce TDF streams.

This module provides `TdfListener`, which accepts incoming TCP connections
streaming live TDF game data, initializes a new game session, handles character
encoding detection (UTF-16LE, UTF-8 BOM), and streams received lines into the
active game state.

Usage example:
    from lflive.state.game_state import LiveGameState
    from lflive.tdf_listener import TdfListener

    state = LiveGameState()
    listener = TdfListener(port=8000, game_state=state, log_tdf=True)
    await listener.start()
"""

import asyncio
import codecs
from collections.abc import Callable

from lflive.db import LiveDatabase
from lflive.ingestor import TdfIngestor
from lflive.state.game_state import LiveGameState


def detect_encoding(initial_bytes: bytes) -> tuple[str, bytes]:
    """Detects text stream encoding and strips leading byte order markers.

    Args:
        initial_bytes: Raw initial bytes received from stream.

    Returns:
        tuple[str, bytes]: Tuple of (encoding_name, remaining_bytes).

    Usage example:
        encoding, payload = detect_encoding(b'\\xff\\xfeHello')
        assert encoding == 'utf-16-le'
    """
    if initial_bytes.startswith(b'\xff\xfe'):
        return 'utf-16-le', initial_bytes[2:]
    if initial_bytes.startswith(b'\xfe\xff'):
        return 'utf-16-be', initial_bytes[2:]
    if initial_bytes.startswith(b'\xef\xbb\xbf'):
        return 'utf-8', initial_bytes[3:]
    if len(initial_bytes) >= 2 and initial_bytes[1] == 0:
        return 'utf-16-le', initial_bytes
    return 'utf-8', initial_bytes


class TdfListener:
    """Asynchronous TCP listener server receiving TDF file streams.

    Attributes:
        port: TCP port number to listen on.
        host: Host address string to bind the server.
        log_tdf: Flag indicating whether received lines are printed to stdout.
        game_state: Optional LiveGameState instance managed by this listener.
        db: Optional LiveDatabase instance to reset on new sessions.
        ingestor: Optional TdfIngestor instance parsing lines into game state.
        line_callback: Optional callable invoked for every received line.
        is_running: Boolean flag indicating if the server is active.
        active_connection: Boolean flag indicating if a client is connected.
    """

    def __init__(
        self,
        port: int,
        host: str = '0.0.0.0',
        log_tdf: bool = False,
        game_state: LiveGameState | None = None,
        db: LiveDatabase | None = None,
        ingestor: TdfIngestor | None = None,
        line_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initializes the TDF listener configuration.

        Args:
            port: Port number to bind the server.
            host: Interface host address to listen on.
            log_tdf: Whether to print received lines to standard output.
            game_state: Optional game state container to associate and reset.
            db: Optional database manager to reset on session start.
            ingestor: Optional ingestor to parse lines into the game state.
            line_callback: Optional callback invoked for every received line.
        """
        self.port = port
        self.host = host
        self.log_tdf = log_tdf
        self.game_state = game_state
        self.db = db
        if ingestor is not None:
            self.ingestor: TdfIngestor | None = ingestor
        elif game_state is not None:
            self.ingestor = TdfIngestor(game_state=game_state)
        else:
            self.ingestor = None

        self.line_callback = line_callback
        self.is_running = False
        self.active_connection = False
        self._server: asyncio.Server | None = None

    @property
    def bound_port(self) -> int:
        """Returns the actual bound TCP port number."""
        if self._server and self._server.sockets:
            return int(self._server.sockets[0].getsockname()[1])
        return self.port

    async def start(self) -> None:
        """Starts the asynchronous TCP server listener.

        Raises:
            OSError: If binding to the specified port fails.

        Usage example:
            listener = TdfListener(port=8000)
            await listener.start()
        """
        self._server = await asyncio.start_server(
            client_connected_cb=self._handle_client,
            host=self.host,
            port=self.port,
        )
        self.is_running = True

    async def stop(self) -> None:
        """Stops the TCP server and closes all listening sockets.

        Usage example:
            await listener.stop()
        """
        self.is_running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handles an incoming TCP client connection streaming TDF data.

        Resets existing game state, initializes a new session, and decodes
        streaming chunks into lines.

        Args:
            reader: StreamReader for the connected client socket.
            writer: StreamWriter for the connected client socket.
        """
        self.active_connection = True
        self._start_new_session()

        try:
            await self._read_stream(reader=reader)
        finally:
            self.active_connection = False
            if self.game_state:
                self.game_state.is_game_over = True
            writer.close()
            await writer.wait_closed()

    def _start_new_session(self) -> None:
        """Initializes in-memory and database states for a new game session."""
        if self.game_state:
            self.game_state.reset()
        if self.ingestor:
            self.ingestor.reset()
        if self.db:
            self.db.reset_session()

    async def _read_stream(self, reader: asyncio.StreamReader) -> None:
        """Reads and decodes data chunks incrementally from the stream reader.

        Args:
            reader: StreamReader to read raw bytes from.
        """
        initial_chunk = await reader.read(4096)
        if not initial_chunk:
            return

        encoding, payload = detect_encoding(initial_bytes=initial_chunk)
        decoder = codecs.getincrementaldecoder(encoding)(errors='replace')

        buffer = decoder.decode(payload, final=False)
        buffer = self._dispatch_completed_lines(text_buffer=buffer)

        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            text = decoder.decode(chunk, final=False)
            buffer += text
            buffer = self._dispatch_completed_lines(text_buffer=buffer)

        final_text = decoder.decode(b'', final=True)
        buffer += final_text
        if buffer.strip():
            self._handle_line(line=buffer.rstrip('\r\n'))

    def _dispatch_completed_lines(self, text_buffer: str) -> str:
        """Extracts complete newline-terminated lines and dispatches them.

        Args:
            text_buffer: Accumulator text buffer.

        Returns:
            str: Remaining uncompleted text trailing the last newline.
        """
        lines = text_buffer.split('\n')
        for line in lines[:-1]:
            cleaned_line = line.rstrip('\r')
            self._handle_line(line=cleaned_line)
        return lines[-1]

    def _handle_line(self, line: str) -> None:
        """Processes a single extracted TDF line.

        Logs the line if log_tdf is enabled, ingests it into game state,
        and invokes line callbacks.

        Args:
            line: The parsed TDF line string.
        """
        if self.log_tdf:
            print(line)
        if self.ingestor:
            self.ingestor.ingest_line(line=line)
        if self.line_callback:
            self.line_callback(line)
