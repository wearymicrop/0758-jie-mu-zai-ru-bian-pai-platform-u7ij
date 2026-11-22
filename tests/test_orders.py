from app.modules.orders.intake import collect
from app.sources import load_sample


def test_clean_intake(clean):
    assert clean['orders']['counts'] == dict(input=15, accepted=15, duplicates=0, empty=0, isolated=0)


def test_bom_and_source_line(dirty):  # TRAP-02
    first = dirty['orders']['orders'][0]
    assert (first['id'], first['line']) == ('A01', 1)


def test_conflicting_rollback(dirty):  # TRAP-14
    rows = [r for r in dirty['orders']['rows'] if r.get('id') == 'X10']
    assert [r['code'] for r in rows] == ['DUPLICATE_CONFLICT'] * 2
    assert not any(v['id'] == 'X10' for v in dirty['orders']['orders'])


def test_exact_replay(dirty):
    row = next(r for r in dirty['orders']['rows'] if r['code'] == 'DUPLICATE_REPLAY')
    assert (row['line'], row['id']) == (27, 'A01')


def test_sentinel_refused(dirty):  # TRAP-07
    assert dirty['orders']['rows'][-1]['code'] == 'BAD_ORDER'
    assert '未知' in dirty['orders']['rows'][-1]['raw']


def test_truncated_record(dirty):  # TRAP-16
    row = next(r for r in dirty['orders']['rows'] if r['code'] == 'BAD_JSON')
    assert row['line'] == 29


def test_blank_distinguished():  # TRAP-18
    assert collect('')['counts']['input'] == 0
    assert collect('\n')['rows'][0]['code'] == 'EMPTY_ROW'
    assert collect('{}\n')['rows'][0]['code'] == 'BAD_ORDER'


def test_dependency_order_normalized():
    raw = load_sample('clean')['orders'].splitlines()[0]
    result = collect(raw.replace('}', ',"needs":["Y","X","Y"]}')+'\n'+raw.replace('}', ',"needs":["X","Y"]}'))
    assert result['orders'][0]['needs'] == ['X','Y']
    assert result['counts']['duplicates'] == 1
