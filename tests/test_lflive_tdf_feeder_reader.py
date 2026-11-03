from pathlib import Path
import pytest
from lflive.tdf_feeder.reader import TdfFileReader, TdfLine


def test_reader_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / 'missing.tdf'
    reader = TdfFileReader(missing)
    with pytest.raises(FileNotFoundError):
        reader.read_lines()


def test_reader_utf8_file(tmp_path: Path) -> None:
    sample_file = tmp_path / 'game_utf8.tdf'
    content = (
        ';0/info\n'
        '0\t2.0\n'
        '1\t5\tSM5\n'
        '2\t0\tFire\n'
        '4\t0000000\t0100\t* Mission Start *\n'
        '3\t0001000\t#P1\tplayer\tAce\n'
        '4\t0010500\t0201\t* Miss *\n'
        ';4/event comment\n'
        '5\t0020000\t#P1\t100\n'
    )
    sample_file.write_text(content, encoding='utf-8')

    reader = TdfFileReader(sample_file)
    lines = reader.read_lines()

    assert len(lines) == 9
    assert lines[0] == TdfLine(text=';0/info', time_ms=0)
    assert lines[1] == TdfLine(text='0\t2.0', time_ms=0)
    assert lines[4] == TdfLine(
        text='4\t0000000\t0100\t* Mission Start *', time_ms=0
    )
    assert lines[5] == TdfLine(
        text='3\t0001000\t#P1\tplayer\tAce', time_ms=1000
    )
    assert lines[6] == TdfLine(text='4\t0010500\t0201\t* Miss *', time_ms=10500)
    assert lines[7] == TdfLine(text=';4/event comment', time_ms=10500)
    assert lines[8] == TdfLine(text='5\t0020000\t#P1\t100', time_ms=20000)


def test_reader_utf16le_with_bom(tmp_path: Path) -> None:
    sample_file = tmp_path / 'game_utf16.tdf'
    text = (
        '4\t0000000\t0100\t* Start *\n'
        '9\t0005000\t#P1\t0\n'
        '11\t0006000\t#P1\t14\n'
        '12\t0007000\t#P1\t29\n'
        '13\t0008000\t#P1\t4\n'
        '6\t0009000\t#P1\n'
    )
    data = b'\xff\xfe' + text.encode('utf-16-le')
    sample_file.write_bytes(data)

    reader = TdfFileReader(sample_file)
    lines = reader.read_lines()

    assert len(lines) == 6
    assert lines[0].time_ms == 0
    assert lines[1].time_ms == 5000
    assert lines[2].time_ms == 6000
    assert lines[3].time_ms == 7000
    assert lines[4].time_ms == 8000
    assert lines[5].time_ms == 9000


def test_reader_undecodable_file(tmp_path: Path) -> None:
    invalid_file = tmp_path / 'bad.tdf'
    # Write invalid byte sequences for UTF-8 and odd-length UTF-16
    invalid_file.write_bytes(b'\xff\x00\xff')
    reader = TdfFileReader(invalid_file)
    with pytest.raises(ValueError):
        reader.read_lines()
