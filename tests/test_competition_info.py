import pytest

from lfdata.lfstats.competition_info import CompetitionInfo


def test_competition_info_initialization() -> None:
    info = CompetitionInfo(
        name='Syracuse Trios 2026',
        slug='syracuse_trios_2026',
    )
    assert info.name == 'Syracuse Trios 2026'
    assert info.slug == 'syracuse_trios_2026'
    assert repr(info) == (
        "CompetitionInfo(name='Syracuse Trios 2026', "
        "slug='syracuse_trios_2026')"
    )


def test_competition_info_unpacking() -> None:
    info = CompetitionInfo(
        name='Internationals 2026',
        slug='internationals_2026',
    )
    name, slug = info
    assert name == 'Internationals 2026'
    assert slug == 'internationals_2026'


def test_competition_info_indexing() -> None:
    info = CompetitionInfo(name='Autumn Cup', slug='autumn_cup')
    assert info['name'] == 'Autumn Cup'
    assert info['slug'] == 'autumn_cup'

    with pytest.raises(KeyError, match='Invalid field'):
        _ = info['invalid_key']

