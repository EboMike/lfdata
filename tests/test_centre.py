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

    ricany = LFCentre.from_code('20-7')
    assert ricany == LFCentre.RICANY
    assert ricany.country_code == 20
    assert ricany.location_code == 7
    assert ricany.arena_name == 'Lasergame Říčany'
    assert ricany.centre_code == '20-7'

    stuttgart = LFCentre.from_code('21-8')
    assert stuttgart == LFCentre.STUTTGART
    assert stuttgart.country_code == 21
    assert stuttgart.location_code == 8
    assert stuttgart.arena_name == 'PowerLaser Stuttgart'
    assert stuttgart.centre_code == '21-8'

    lost_worlds = LFCentre.from_code('4-80')
    assert lost_worlds == LFCentre.LOST_WORLDS
    assert lost_worlds.country_code == 4
    assert lost_worlds.location_code == 80
    assert lost_worlds.arena_name == 'Lost Worlds'
    assert lost_worlds.centre_code == '4-80'

    leeds = LFCentre.from_code('7-20')
    assert leeds == LFCentre.LEEDS
    assert leeds.country_code == 7
    assert leeds.location_code == 20
    assert leeds.arena_name == 'Leeds'
    assert leeds.centre_code == '7-20'


def test_lf_centre_invalid_lookup() -> None:
    with pytest.raises(ValueError) as exc_info:
        LFCentre.from_code('99-99')
    assert 'Invalid centre code: 99-99' in str(exc_info.value)
