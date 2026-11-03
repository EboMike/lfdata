from pathlib import Path
from lflive.__main__ import main


def test_main_execution(tmp_path: Path) -> None:
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
