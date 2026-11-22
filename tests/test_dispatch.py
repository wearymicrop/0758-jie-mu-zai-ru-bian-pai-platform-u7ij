import sqlite3
from concurrent.futures import ThreadPoolExecutor

from app.config import db_path


def test_run_end_to_end_attachment(client):
    result=client.post('/api/runs',json={'sample':'dirty'}).json()
    response=client.get(f"/api/runs/{result['id']}/export")
    assert response.headers['content-disposition'].startswith('attachment;')
    assert response.json()['result']['reconcile']['late_count'] == 1
    assert response.json()['manifest']['files'].keys() == {'orders','calendar'}


def test_persistence_and_replay(client):
    first=client.post('/api/runs',json={'sample':'dirty'}).json()
    verified=client.post(f"/api/runs/{first['id']}/rerun").json()
    assert verified == {**first,'reused':True}
    assert client.get(f"/api/runs/{first['id']}").json()['id'] == first['id']


def test_concurrent_idempotence(client):
    def create(_):
        return client.post('/api/runs',json={'sample':'clean'}).json()
    with ThreadPoolExecutor(4) as pool:
        results=list(pool.map(create,range(4)))
    assert len({r['id'] for r in results})==1
    assert [r['reused'] for r in results].count(False)==1
    with sqlite3.connect(db_path()) as conn:
        assert conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==1


def test_unknown_archive(client):
    response=client.get('/api/runs/not-registered')
    assert response.status_code == 404
    assert response.json()['code'] == 'RUN_NOT_FOUND'


def test_invalid_source_untouched(client):
    response=client.post('/api/runs',json={'orders':'{}','calendar':{}})
    assert response.status_code==422
    assert response.json()['code']=='BAD_CALENDAR'
    with sqlite3.connect(db_path()) as conn:
        assert conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==0


def test_dispatch_sorted_and_attributed(dirty):
    stage=next(row for row in dirty['dispatch']['stages'] if row['stage']=='主舞台')
    order=stage['steps'][0]
    assert (order['id'],order['technician'],order['line'],order['stage_end'])==('A01','许茂',1,650)
    assert [r['start'] for r in stage['steps']]==sorted(r['start'] for r in stage['steps'])


def test_dispatch_does_not_lose_pending_evidence(dirty):
    work=next(row for row in dirty['dispatch']['deferred'] if row['id']=='X03')
    assert work['related']==['X02'] and work['status']=='pending'
