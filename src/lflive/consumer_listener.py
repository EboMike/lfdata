"""Asynchronous TCP listener and broadcaster for visualization consumers.

This module provides `ConsumerListener`, which manages incoming visualizer
client connections over TCP, emits presync game state to newly connected
clients, and broadcasts real-time protocol updates with optional preroll delay.

Usage example:
    from lflive.consumer_listener import ConsumerListener
    from lflive.emitter import OutputEmitter
    from lflive.state.game_state import LiveGameState

    state = LiveGameState()
    emitter = OutputEmitter()
    listener = ConsumerListener(port=8001, game_state=state, emitter=emitter)
    await listener.start()
"""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lflive.emitter import OutputEmitter
    from lflive.state.game_state import LiveGameState


class ConsumerListener:
    """Asynchronous TCP server broadcasting protocol lines to consumers.

    Attributes:
        port: TCP port number to listen on.
        host: Host address string to bind the server.
        game_state: Optional LiveGameState instance for presync generation.
        emitter: Optional OutputEmitter providing emitted lines and presync.
        preroll_ms: Preroll delay in milliseconds for outbound messages.
        is_running: Boolean flag indicating if the server is active.
    """

    def __init__(
        self,
        port: int,
        host: str = '0.0.0.0',
        game_state: 'LiveGameState | None' = None,
        emitter: 'OutputEmitter | None' = None,
        preroll_ms: int = 0,
    ) -> None:
        """Initializes the consumer listener.

        Configures network parameters, state container reference, emitter,
        and preroll broadcast delay.

        Args:
            port: Port number to bind the server.
            host: Interface host address to listen on.
            game_state: Optional game state container for presync snapshots.
            emitter: Optional output emitter to broadcast protocol lines.
            preroll_ms: Optional delay in milliseconds applied to broadcasts.
        """
        self.port = port
        self.host = host
        self.game_state = game_state
        self.emitter = emitter
        self.preroll_ms = max(0, preroll_ms)
        self.is_running = False

        self._clients: set[asyncio.StreamWriter] = set()
        self._queue: asyncio.Queue[tuple[float, str]] | None = None
        self._worker_task: asyncio.Task[None] | None = None
        self._server: asyncio.Server | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def active_consumer_count(self) -> int:
        """Returns the number of currently connected visualizer clients.

        Inspects the internal collection of active socket writers.

        Returns:
            The total count of active client connections.
        """
        return len(self._clients)

    @property
    def bound_port(self) -> int:
        """Returns the actual bound OS listening port.

        Retrieves the assigned port number from the server socket, which is
        particularly useful when port 0 is specified for dynamic port selection.

        Returns:
            Integer port number the server is listening on.
        """
        if self._server and self._server.sockets:
            return int(self._server.sockets[0].getsockname()[1])
        return self.port

    async def start(self) -> None:
        """Starts the consumer listener server and broadcast queue worker.

        Binds the TCP server, registers broadcast listener callbacks, and
        initiates the delayed outbound queue consumer.

        Raises:
            OSError: If binding to the specified port fails.

        Usage example:
            listener = ConsumerListener(port=8001)
            await listener.start()
        """
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self.is_running = True
        self._worker_task = asyncio.create_task(self._queue_worker())
        if self.emitter:
            self.emitter.add_listener(self.broadcast_line)
        self._server = await asyncio.start_server(
            client_connected_cb=self._handle_client,
            host=self.host,
            port=self.port,
        )

    async def stop(self) -> None:
        """Stops the consumer listener server, worker, and disconnects clients.

        Cancels background workers, unbinds listening sockets, closes all active
        client writer streams, and unregisters broadcast listeners.

        Usage example:
            await listener.stop()
        """
        self.is_running = False
        if self.emitter:
            self.emitter.remove_listener(self.broadcast_line)
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for writer in list(self._clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()

    def broadcast_line(self, line: str) -> None:
        """Schedules or enqueues a formatted protocol line for broadcasting.

        Calculates release timestamp according to preroll delay and adds
        the message to the delivery queue thread-safely.

        Args:
            line: Tab-delimited protocol line without trailing newline.

        Usage example:
            listener.broadcast_line('1\t1000\t1\t500')
        """
        if not self.is_running or self._queue is None:
            return
        if self._loop and self._loop.is_running():
            now = self._loop.time()
            release_time = now + (self.preroll_ms / 1000.0)
            try:
                self._loop.call_soon_threadsafe(
                    self._queue.put_nowait, (release_time, line)
                )
            except RuntimeError:
                pass

    async def _queue_worker(self) -> None:
        """Processes queued outbound lines, respecting preroll delays.

        Pulls scheduled messages from the queue, pauses until their release
        timestamp has arrived, and transmits them to all connected clients.
        """
        while self.is_running and self._queue is not None:
            try:
                release_time, line = await self._queue.get()
            except asyncio.CancelledError:
                break
            if self._loop:
                now = self._loop.time()
                delay = release_time - now
                if delay > 0:
                    await asyncio.sleep(delay)
            await self._send_to_all(line=line)
            self._queue.task_done()

    async def _send_to_all(self, line: str) -> None:
        """Broadcasts a line to all currently connected clients.

        Encodes line in UTF-8 with trailing newline and writes to every active
        client writer, dropping disconnected sockets cleanly.

        Args:
            line: Formatted protocol line string.
        """
        if not self._clients:
            return
        payload = (line + '\r\n').encode('utf-8')
        dead_clients: list[asyncio.StreamWriter] = []
        for writer in list(self._clients):
            try:
                writer.write(payload)
                await writer.drain()
            except (ConnectionError, OSError):
                dead_clients.append(writer)

        for dead in dead_clients:
            self._clients.discard(dead)
            try:
                dead.close()
                await dead.wait_closed()
            except Exception:
                pass

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handles incoming consumer connection lifecycle.

        Registers the new client socket, transmits initial presync snapshot,
        and awaits client closure or disconnect.

        Args:
            reader: Incoming stream reader.
            writer: Outgoing stream writer.
        """
        self._clients.add(writer)
        await self._send_presync(writer=writer)
        try:
            while self.is_running:
                data = await reader.read(1024)
                if not data:
                    break
        except (ConnectionError, OSError):
            pass
        finally:
            self._clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _send_presync(self, writer: asyncio.StreamWriter) -> None:
        """Sends initial snapshot state to newly joined consumer.

        Followed by PRESYNC_END (Type 24). If preroll delay is active, state is
        reconstructed as of (current_time_ms - preroll_ms).

        Args:
            writer: Stream writer connected to the new consumer.
        """
        if not self.game_state or not self.emitter:
            return
        if not self.game_state.teams and not self.game_state.players:
            return

        effective_state = self.game_state
        if self.preroll_ms > 0 and self.game_state.current_time_ms > 0:
            target_ms = max(
                0, self.game_state.current_time_ms - self.preroll_ms
            )
            effective_state = self.game_state.get_state_at(time_ms=target_ms)

        events = self.emitter.generate_presync_events(
            game_state=effective_state
        )
        payload = ''.join(ev + '\r\n' for ev in events).encode('utf-8')
        try:
            writer.write(payload)
            await writer.drain()
        except (ConnectionError, OSError):
            pass
