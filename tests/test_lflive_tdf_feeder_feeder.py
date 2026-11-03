import asyncio
import pytest
from lflive.tdf_feeder.feeder import TdfFeeder
from lflive.tdf_feeder.reader import TdfLine


def test_feeder_invalid_speed() -> None:
    with pytest.raises(ValueError):
        TdfFeeder(
            host='127.0.0.1',
            port=8000,
            lines=[],
            speed=0.0,
        )
    with pytest.raises(ValueError):
        TdfFeeder(
            host='127.0.0.1',
            port=8000,
            lines=[],
            speed=-1.0,
        )


def test_feeder_stream_success() -> None:
    async def _run() -> None:
        received_raw = bytearray()
        server_done = asyncio.Event()

        async def _mock_client(
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
            server_done.set()

        server = await asyncio.start_server(
            client_connected_cb=_mock_client,
            host='127.0.0.1',
            port=0,
        )
        port = int(server.sockets[0].getsockname()[1])

        lines = [
            TdfLine(text='0\t2.0\t8.5', time_ms=0),
            TdfLine(text='4\t0000050\t0100', time_ms=50),
            TdfLine(text='4\t0000100\t0201', time_ms=100),
        ]
        callbacks: list[tuple[int, int, str]] = []

        feeder = TdfFeeder(
            host='127.0.0.1',
            port=port,
            lines=lines,
            speed=10.0,  # 10x speed so test finishes in ~10ms
            line_callback=lambda idx, tot, txt: callbacks.append(
                (idx, tot, txt)
            ),
        )

        sent_count = await feeder.feed()
        assert sent_count == 3
        assert len(callbacks) == 3
        assert callbacks[0] == (1, 3, '0\t2.0\t8.5')
        assert callbacks[2] == (3, 3, '4\t0000100\t0201')

        await asyncio.wait_for(server_done.wait(), timeout=2.0)
        server.close()
        await server.wait_closed()

        # Check BOM and decoded UTF-16LE text
        assert received_raw.startswith(b'\xff\xfe')
        decoded = received_raw[2:].decode('utf-16-le')
        expected = '0\t2.0\t8.5\r\n4\t0000050\t0100\r\n4\t0000100\t0201\r\n'
        assert decoded == expected

    asyncio.run(_run())


def test_feeder_connection_refused() -> None:
    async def _run() -> None:
        feeder = TdfFeeder(
            host='127.0.0.1',
            port=59999,  # Port with no listening server
            lines=[TdfLine(text='test', time_ms=0)],
        )
        with pytest.raises(ConnectionRefusedError):
            await feeder.feed()

    asyncio.run(_run())
