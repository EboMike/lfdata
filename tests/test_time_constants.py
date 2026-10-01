from lfdata.model.constants.time import (
    MS_PER_MINUTE,
    MS_PER_SECOND,
    SECONDS_PER_MINUTE,
)


def test_time_constants():
    assert MS_PER_SECOND == 1000
    assert SECONDS_PER_MINUTE == 60
    assert MS_PER_MINUTE == 60000
