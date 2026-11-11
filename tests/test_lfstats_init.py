from lfdata.lfstats import CompetitionInfo, LFStatsFetcher


def test_lfstats_init_exports() -> None:
    assert LFStatsFetcher is not None
    assert CompetitionInfo is not None
