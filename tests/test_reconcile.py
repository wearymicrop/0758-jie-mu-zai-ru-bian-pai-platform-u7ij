from app.modules.reconcile.audit import reconcile


def test_dirty_waterfall(dirty):
    d=dirty['reconcile']
    assert [d[k] for k in ['scheduled','pending','isolated','source_issues','row_gap']] == [15,3,6,4,0]


def test_late_is_placed(dirty):
    assert dirty['reconcile']['late'] == [{'id':'A03','line':3,'minutes':15}]
    assert dirty['reconcile']['scheduled'] == 15


def test_existing_holds_not_new_collisions(dirty):
    assert dirty['reconcile']['collisions'] == []
    assert dirty['reconcile']['hold_clashes'] == 1


def test_clean_has_no_gaps(clean):
    assert clean['reconcile']['row_gap'] == 0
    assert clean['reconcile']['late_count'] == 0
    assert clean['reconcile']['status'] == 'MATCHED'


def test_missing_canonical_detected(clean):
    cut={'jobs':clean['schedule']['jobs'][1:]}
    result=reconcile(clean['orders'],cut,clean['conflicts'])
    assert result['status'] == 'MISMATCH'
    assert result['missing'] == ['A01']


def test_reaudit_catches_resource_overlap(clean):
    jobs=[dict(x) for x in clean['schedule']['jobs']]
    jobs[1].update(start=600, end=645, stage_end=645)
    bad=reconcile(clean['orders'],{'jobs':jobs},clean['conflicts'])
    assert ['A01','A02','stage'] in bad['collisions']


def test_reaudit_catches_dependency_violation(clean):
    jobs=[dict(x) for x in clean['schedule']['jobs']]
    jobs[1].update(start=500,end=545,stage_end=545)
    bad=reconcile(clean['orders'],{'jobs':jobs},clean['conflicts'])
    assert ['A02','A01'] in bad['premature']
