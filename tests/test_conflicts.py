from app.modules.conflicts.occupancy import audit_holds, blockers
from app.modules.conflicts.inspection import invalid_resources


def test_prior_holds_intersection(dirty):
    assert dirty['conflicts']['overlaps'] == [dict(resource='stage:主舞台',left='H01',right='H04',start=580,end=595)]


def test_holds_source_index(dirty):
    assert dirty['conflicts']['issues'][0]['source_index'] == 5
    assert dirty['conflicts']['issues'][0]['code'] == 'INVALID_HOLD'


def test_unknown_stage(dirty):
    assert dirty['conflicts']['order_issues']['X04'] == {'code':'UNKNOWN_STAGE','related':['天桥']}


def test_missing_skill(dirty):
    assert dirty['conflicts']['order_issues']['X09']['code'] == 'UNKNOWN_ROLE'


def test_boundary_at_hold_end(clean):
    holds=clean['conflicts']['holds']['stage:主舞台']
    assert blockers(holds,595,640) == []
    assert blockers(holds,594,640)[0]['id'] == 'H01'


def test_duplicate_hold_marks_resource_uncertain(clean):
    cal=clean['calendars']
    result=audit_holds({**cal,'holds':[cal['holds'][0],cal['holds'][0]]})
    assert not result['holds']
    assert invalid_resources(result) == {'stage:主舞台'}


def test_parallel_reserved_resources_not_conflicts(clean):
    assert clean['conflicts']['overlaps'] == []
