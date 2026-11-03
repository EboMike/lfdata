import asyncio
import time
from lflive.constants import DATA_TYPE_PLAYER_SCORE, DATA_TYPE_PRESYNC_END
from lflive.consumer_listener import ConsumerListener
from lflive.emitter import OutputEmitter
from lflive.state.game_state import LiveGameState


def test_consumer_listener_lifecycle() -> None:
    async def _run() -> None:
        listener = ConsumerListener(port=0, host='127.0.0.1')
        await listener.start()
        assert listener.is_running is True
        assert listener.bound_port > 0
        assert listener.active_consumer_count == 0
        await listener.stop()
        assert listener.is_running is False

    asyncio.run(_run())


def test_consumer_listener_presync_on_connect() -> None:
    async def _run() -> None:
        state = LiveGameState(game_type='SM5', duration_seconds=900)
        state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
        state.add_player(1, '#P1', 'Ace', 1, 'commander')
        emitter = OutputEmitter()

        listener = ConsumerListener(
            port=0,
            host='127.0.0.1',
            game_state=state,
            emitter=emitter,
        )
        await listener.start()

        reader, writer = await asyncio.open_connection(
            '127.0.0.1', listener.bound_port
        )
        assert listener.active_consumer_count == 1

        received_lines: list[str] = []
        while True:
            line_bytes = await reader.readline()
            if not line_bytes:
                break
            line = line_bytes.decode('utf-8').rstrip('\r\n')
            received_lines.append(line)
            if line.startswith(str(DATA_TYPE_PRESYNC_END)):
                break

        assert any('Fire' in line for line in received_lines)
        assert any('Ace' in line for line in received_lines)
        assert received_lines[-1].startswith(str(DATA_TYPE_PRESYNC_END))

        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.05)
        assert listener.active_consumer_count == 0

        await listener.stop()

    asyncio.run(_run())


def test_consumer_listener_broadcast_multiple_clients() -> None:
    async def _run() -> None:
        emitter = OutputEmitter()
        listener = ConsumerListener(
            port=0,
            host='127.0.0.1',
            emitter=emitter,
            preroll_ms=0,
        )
        await listener.start()

        r1, w1 = await asyncio.open_connection('127.0.0.1', listener.bound_port)
        r2, w2 = await asyncio.open_connection('127.0.0.1', listener.bound_port)
        await asyncio.sleep(0.05)
        assert listener.active_consumer_count == 2

        # Emit an event through the emitter
        emitter.emit(DATA_TYPE_PLAYER_SCORE, 1000, 1, 200)

        line1 = (await r1.readline()).decode('utf-8').rstrip('\r\n')
        line2 = (await r2.readline()).decode('utf-8').rstrip('\r\n')

        expected = f'{DATA_TYPE_PLAYER_SCORE}\t1000\t1\t200'
        assert line1 == expected
        assert line2 == expected

        w1.close()
        w2.close()
        await w1.wait_closed()
        await w2.wait_closed()
        await listener.stop()

    asyncio.run(_run())


def test_consumer_listener_preroll_delay() -> None:
    async def _run() -> None:
        emitter = OutputEmitter()
        listener = ConsumerListener(
            port=0,
            host='127.0.0.1',
            emitter=emitter,
            preroll_ms=100,
        )
        await listener.start()

        r, w = await asyncio.open_connection('127.0.0.1', listener.bound_port)
        await asyncio.sleep(0.05)

        start_time = time.time()
        emitter.emit(DATA_TYPE_PLAYER_SCORE, 2000, 1, 500)

        line = (await r.readline()).decode('utf-8').rstrip('\r\n')
        elapsed = time.time() - start_time

        assert line == f'{DATA_TYPE_PLAYER_SCORE}\t2000\t1\t500'
        # With 100ms preroll, elapsed time should be at least 0.08s
        assert elapsed >= 0.08

        w.close()
        await w.wait_closed()
        await listener.stop()

    asyncio.run(_run())


def test_consumer_listener_presync_with_preroll_boundary() -> None:
    async def _run() -> None:
        state = LiveGameState(game_type='SM5', duration_seconds=900)
        state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
        p = state.add_player(1, '#P1', 'Ace', 1, 'commander')
        p.score = 100
        state.record_change(1000, 'player', 1, 'score', '100')
        state.current_time_ms = 10000

        # Change at 9000ms
        p.score = 500
        state.record_change(9000, 'player', 1, 'score', '500')

        emitter = OutputEmitter()
        # 5000ms preroll delay -> presync at 10000 - 5000 = 5000ms (score should be 100)
        listener = ConsumerListener(
            port=0,
            host='127.0.0.1',
            game_state=state,
            emitter=emitter,
            preroll_ms=5000,
        )
        await listener.start()

        reader, writer = await asyncio.open_connection(
            '127.0.0.1', listener.bound_port
        )
        received_lines: list[str] = []
        while True:
            line_bytes = await reader.readline()
            if not line_bytes:
                break
            line = line_bytes.decode('utf-8').rstrip('\r\n')
            received_lines.append(line)
            if line.startswith(str(DATA_TYPE_PRESYNC_END)):
                break

        score_lines = [
            line
            for line in received_lines
            if line.startswith(f'{DATA_TYPE_PLAYER_SCORE}\t')
        ]
        assert len(score_lines) > 0
        # Score at 5000ms was 100
        assert score_lines[0] == f'{DATA_TYPE_PLAYER_SCORE}\t5000\t1\t100'

        writer.close()
        await writer.wait_closed()
        await listener.stop()

    asyncio.run(_run())

