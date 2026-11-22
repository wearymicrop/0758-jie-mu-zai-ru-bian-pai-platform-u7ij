import pytest

from app.errors import DomainError
from app.modules.calendars.intervals import intersect, merge, overlaps
from app.modules.calendars.registry import choices, load
from app.sources import load_sample


def test_venue_clipping(clean):
    assert clean['calendars']['effective_stages']['主舞台'] == [[540,750],[780,1140]]


def test_technician_clipping(clean):
    assert clean['calendars']['effective_tech']['L1'] == [[540,735],[780,1110]]


def test_role_roster(clean):
    assert choices(clean['calendars'],'灯光') == ['L1','L2']


def test_adjacent_endpoints():  # TRAP-23
    assert overlaps([0,5],[5,10]) is False
    assert intersect([[0,5]],[[5,10]]) == []


def test_union_has_no_double_booked_minutes():
    assert merge([[12,20],[0,5],[4,12],[3,6]]) == [[0,20]]


def test_bad_calendar():
    raw = load_sample('clean')['calendar']
    raw['venue'] = [[200,100]]
    with pytest.raises(DomainError, match='日历字段或时段无效'):
        load(raw)


def test_cross_day_clipped_to_venue():
    raw = load_sample('clean')['calendar']
    raw['venue'] = [[1430,1470]]
    raw['stages']['主舞台'] = [[1400,1500]]
    assert load(raw)['effective_stages']['主舞台'] == [[1430,1470]]
