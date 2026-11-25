import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from lflive.tdf_feeder.__main__ import main


def test_main_connection_refused(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'sample.tdf'
    tdf_file.write_text('4\t0000000\t0100\n', encoding='utf-8')

    code = main(
        [
            str(tdf_file),
            '127.0.0.1:59998',
        ]
    )
    assert code == 2


def test_main_success_stream(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'game.tdf'
    tdf_file.write_text(
        '0\t2.0\n4\t0000020\t0100\n',
        encoding='utf-8',
    )

    ready_event = threading.Event()
    stop_event = threading.Event()
    port_holder: list[int] = []

    def _server_thread() -> None:
        async def _srv() -> None:
            async def _handler(
                reader: asyncio.StreamReader,
                writer: asyncio.StreamWriter,
            ) -> None:
                while await reader.read(4096):
                    pass
                writer.close()
                await writer.wait_closed()

            server = await asyncio.start_server(
                client_connected_cb=_handler,
                host='127.0.0.1',
                port=0,
            )
            port_holder.append(int(server.sockets[0].getsockname()[1]))
            ready_event.set()

            while not stop_event.is_set():
                await asyncio.sleep(0.05)

            server.close()
            await server.wait_closed()

        asyncio.run(_srv())

    t = threading.Thread(target=_server_thread, daemon=True)
    t.start()
    ready_event.wait(timeout=3.0)

    code = main(
        [
            str(tdf_file),
            f'127.0.0.1:{port_holder[0]}',
            '--speed',
            '50.0',
        ]
    )
    assert code == 0

    stop_event.set()
    t.join(timeout=2.0)


def test_main_rewrite_timestamps(tmp_path: Path) -> None:
    tdf_file = tmp_path / 'game.tdf'
    tdf_file.write_text(
        '1\t5\tSpace Marines 5\t20261019201054\t900000\t0\n4\t0000010\t0100\n',
        encoding='utf-8',
    )

    ready_event = threading.Event()
    stop_event = threading.Event()
    port_holder: list[int] = []
    received_raw = bytearray()

    def _server_thread() -> None:
        async def _srv() -> None:
            async def _handler(
                reader: asyncio.StreamReader,
                writer: asyncio.StreamWriter,
            ) -> None:
                while True:
                    chunk = await reader.read(4096)
                    if not chunk:
                        break
                    received_raw.extend(chunk)
                writer.close()
                await writer.wait_closed()

            server = await asyncio.start_server(
                client_connected_cb=_handler,
                host='127.0.0.1',
                port=0,
            )
            port_holder.append(int(server.sockets[0].getsockname()[1]))
            ready_event.set()

            while not stop_event.is_set():
                await asyncio.sleep(0.05)

            server.close()
            await server.wait_closed()

        asyncio.run(_srv())

    t = threading.Thread(target=_server_thread, daemon=True)
    t.start()
    ready_event.wait(timeout=3.0)

    fixed_now = datetime(2026, 11, 20, 3, 15, 3, tzinfo=timezone.utc)
    with patch(
        'lflive.tdf_feeder.feeder._current_local_time',
        return_value=fixed_now,
    ):
        code = main(
            [
                str(tdf_file),
                f'127.0.0.1:{port_holder[0]}',
                '--speed',
                '50.0',
                '--rewrite_timestamps',
            ]
        )
    assert code == 0

    stop_event.set()
    t.join(timeout=2.0)

    decoded = received_raw[2:].decode('utf-16-le')
    expected = (
        '1\t5\tSpace Marines 5\t20261120031503\t900000\t0\r\n'
        '4\t0000010\t0100\r\n'
    )
    assert decoded == expected
