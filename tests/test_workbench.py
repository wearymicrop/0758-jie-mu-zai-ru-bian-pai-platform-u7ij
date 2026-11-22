from app.sources import load_sample


def test_every_module_routes_real_sections(client, dirty):
    assert client.get('/api/health').json()['status']=='ok'
    for key,value in dirty.items():
        assert client.get(f'/api/samples/dirty/{key}').json()==value


def test_preview_and_missing_sample(client):
    assert client.get('/api/samples/clean').json()['reconcile']['scheduled']==15
    assert client.get('/api/samples/no').status_code==404


def test_custom_accepts_existing_sample_body(client):
    response=client.post('/api/runs',json=load_sample('clean'))
    assert response.json()['sample']=='自备数据'
    assert response.json()['result']['reconcile']['scheduled']==15


def test_html_has_seven_navigation_links(client):
    response=client.get('/')
    assert response.status_code==200
    assert response.text.count('data-view=')==7
    assert client.get('/static/curtain.js').status_code==200
