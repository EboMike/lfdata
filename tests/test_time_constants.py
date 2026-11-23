from lfdata.model.constants.time import (
    MS_PER_CENTISECOND,
    MS_PER_MINUTE,
    MS_PER_SECOND,
    SECONDS_PER_MINUTE,
    TimerMode,
)


def test_time_constants() -> None:
    assert MS_PER_CENTISECOND == 10
    assert MS_PER_SECOND == 1000
    assert SECONDS_PER_MINUTE == 60
    assert MS_PER_MINUTE == 60000


def test_timer_mode_enum() -> None:
    assert TimerMode.REMAINING.value == 'remaining'
    assert TimerMode.ELAPSED.value == 'elapsed'
    assert TimerMode.from_str('remaining') == TimerMode.REMAINING
    assert TimerMode.from_str('elapsed') == TimerMode.ELAPSED
    assert TimerMode.from_str('ELAPSED') == TimerMode.ELAPSED
    assert TimerMode.from_str('  elapsed  ') == TimerMode.ELAPSED
    assert TimerMode.from_str(None) == TimerMode.REMAINING
    assert TimerMode.from_str('') == TimerMode.REMAINING
    assert TimerMode.from_str('invalid') == TimerMode.REMAINING
