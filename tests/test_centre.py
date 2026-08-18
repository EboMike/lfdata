import pytest

from lfdata.model import LFCentre


def test_lf_centre_lookup() -> None:
    centre = LFCentre.from_code('4-43')
    assert centre == LFCentre.INVASION
    assert centre.country_code == 4
    assert centre.location_code == 43
    assert centre.arena_name == 'Invasion'
    assert centre.centre_code == '4-43'


def test_lf_centre_all_lookup() -> None:
    brisbane = LFCentre.from_code('1-1')
    assert brisbane.arena_name == 'Brisbane'

    darmstadt = LFCentre.from_code('21-70')
    assert darmstadt.arena_name == 'LaserTag Darmstadt'

    cheltanham = LFCentre.from_code('7-13')
    assert cheltanham.arena_name == 'Cheltanham'

    wollongong = LFCentre.from_code('1-58')
    assert wollongong == LFCentre.WOLLONGONG_REVOLUTION
    assert wollongong.country_code == 1
    assert wollongong.location_code == 58
    assert wollongong.arena_name == 'Wollongong Revolution'
    assert wollongong.centre_code == '1-58'


def test_lf_centre_invalid_lookup() -> None:
    with pytest.raises(ValueError) as exc_info:
        LFCentre.from_code('99-99')
    assert 'Invalid centre code: 99-99' in str(exc_info.value)
