import asyncio
import pytest
from lflive.db import LiveDatabase
from lflive.emitter import OutputEmitter
from lflive.state.game_state import LiveGameState
from lflive.tdf_listener import TdfListener, detect_encoding


def test_detect_encoding() -> None:
    enc, rem = detect_encoding(b'\xff\xfeHello')
    assert enc == 'utf-16-le'
    assert rem == b'Hello'

    enc, rem = detect_encoding(b'\xfe\xffHello')
    assert enc == 'utf-16-be'
    assert rem == b'Hello'

    enc, rem = detect_encoding(b'\xef\xbb\xbfHello')
    assert enc == 'utf-8'
    assert rem == b'Hello'

    enc, rem = detect_encoding(b'3\x00\t\x000\x00')
    assert enc == 'utf-16-le'
    assert rem == b'3\x00\t\x000\x00'

    enc, rem = detect_encoding(b'3\t0\tPlayer')
    assert enc == 'utf-8'
    assert rem == b'3\t0\tPlayer'


def test_tdf_listener_lifecycle() -> None:
    async def _run() -> None:
        listener = TdfListener(port=0, host='127.0.0.1')
        await listener.start()
        assert listener.is_running is True
        assert listener.bound_port > 0
        await listener.stop()
        assert listener.is_running is False

    asyncio.run(_run())


def test_tdf_listener_receive_utf8() -> None:
    async def _run() -> None:
        received_lines: list[str] = []
        state = LiveGameState()
        state.current_time_ms = 9999
        db = LiveDatabase(':memory:')
        db.init_db()

        listener = TdfListener(
            port=0,
            host='127.0.0.1',
            game_state=state,
            db=db,
            line_callback=lambda line: received_lines.append(line),
        )
        await listener.start()

        _, writer = await asyncio.open_connection(
            '127.0.0.1', listener.bound_port
        )
        writer.write(b'0\t0\tTest Game\r\n1\t0\tSM5\r\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        await asyncio.sleep(0.1)

        assert state.current_time_ms == 0
        assert state.is_game_over is True
        assert received_lines == ['0\t0\tTest Game', '1\t0\tSM5']

        await listener.stop()

    asyncio.run(_run())


def test_tdf_listener_receive_utf16le_with_bom() -> None:
    async def _run() -> None:
        received_lines: list[str] = []
        listener = TdfListener(
            port=0,
            host='127.0.0.1',
            line_callback=lambda line: received_lines.append(line),
        )
        await listener.start()

        _, writer = await asyncio.open_connection(
            '127.0.0.1', listener.bound_port
        )
        content = '3\t0\t#1A2B\tPlayer1\r\n4\t100\t0201\r\n'
        payload = b'\xff\xfe' + content.encode('utf-16-le')
        writer.write(payload)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        await asyncio.sleep(0.1)

        assert received_lines == [
            '3\t0\t#1A2B\tPlayer1',
            '4\t100\t0201',
        ]

        await listener.stop()

    asyncio.run(_run())


def test_tdf_listener_log_tdf(capsys: pytest.CaptureFixture[str]) -> None:
    async def _run() -> None:
        listener = TdfListener(
            port=0,
            host='127.0.0.1',
            log_tdf=True,
        )
        await listener.start()

        _, writer = await asyncio.open_connection(
            '127.0.0.1', listener.bound_port
        )
        writer.write(b';comment line\r\n3\t0\tData\r\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        await asyncio.sleep(0.1)

        captured = capsys.readouterr()
        assert ';comment line' in captured.out
        assert '3\t0\tData' in captured.out

        await listener.stop()

    asyncio.run(_run())


def test_tdf_listener_with_emitter(capsys: pytest.CaptureFixture[str]) -> None:
    async def _run() -> None:
        state = LiveGameState()
        emitter = OutputEmitter(log_output=True)
        listener = TdfListener(
            port=0,
            host='127.0.0.1',
            game_state=state,
            emitter=emitter,
        )
        await listener.start()

        _, writer = await asyncio.open_connection(
            '127.0.0.1', listener.bound_port
        )
        writer.write(b'2\t0\tFire\t11\tFire\t#FF5000\r\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        await asyncio.sleep(0.1)

        captured = capsys.readouterr()
        assert '98\t0\n' in captured.out
        assert '15\t0\t1\tFire\t#FF5000\n' in captured.out
        assert '99\t0\n' in captured.out

        await listener.stop()

    asyncio.run(_run())
