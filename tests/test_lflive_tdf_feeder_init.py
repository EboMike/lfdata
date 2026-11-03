import lflive.tdf_feeder


def test_feeder_init_exports() -> None:
    assert hasattr(lflive.tdf_feeder, 'TdfFeeder')
    assert hasattr(lflive.tdf_feeder, 'TdfFeederArgs')
    assert hasattr(lflive.tdf_feeder, 'TdfFileReader')
    assert hasattr(lflive.tdf_feeder, 'TdfLine')
    assert hasattr(lflive.tdf_feeder, 'parse_args')
