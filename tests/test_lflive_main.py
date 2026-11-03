import asyncio
from pathlib import Path
import pytest
from lflive.__main__ import main, run_server
from lflive.config import LFLiveConfig


def test_main_execution(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    test_db = tmp_path / 'main_test.db'
    code = main(
        [
            '--database',
            str(test_db),
            '--tdf_port',
            '8123',
            '--consumer_port',
            '8124',
            '--log_tdf',
            '--log_output',
        ]
    )
    assert code == 0
    assert test_db.exists()
    captured = capsys.readouterr()
    assert 'Log Output: True' in captured.out
    assert 'Log TDF: True' in captured.out


def test_run_server_lifecycle(tmp_path: Path) -> None:
    async def _run() -> None:
        cfg = LFLiveConfig(
            database_path=str(tmp_path / 'server_test.db'),
            tdf_port=0,
            log_output=True,
        )
        task = asyncio.create_task(run_server(cfg))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_run())
