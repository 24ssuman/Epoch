from fastapi.testclient import TestClient
from backend.app import app
import numpy as np
from backend.astrotime import calendar_jd
client=TestClient(app)

def test_offline_service_interfaces():
    assert client.get('/api/health').json()['offline']
    assert client.get('/').status_code==200
    data=client.get('/api/bootstrap').json();assert data['star_count']>100000
    assert client.get('/api/search',params={'q':'Sirius'}).json()[0]['name']=='Sirius'
    assert client.get('/api/calendar',params={'year':1900,'month':2,'day':29}).status_code==422
    assert client.get('/api/snapshot',params={'jd':2451545,'lat':91}).status_code==422

def test_extreme_dates_preserve_explicit_missing_data():
    for year in [-14999,-13500,5000]:
        response=client.get('/api/snapshot',params={'jd':calendar_jd(year),'limit':100})
        assert response.status_code==200,response.text[:500]
        data=response.json();assert data['time']['rotation_quality']=='assumed-rotation'
        assert len(data['stars'])==100
        assert all(np.isfinite(s['direction']).all() for s in data['stars'])
        if not data['solar_system_available']:assert data['coverage_message'] and data['bodies']==[]

def test_object_detail_and_size_metadata():
    d=client.get('/api/object/hip:32349',params={'jd':2451545}).json()
    assert d['name']=='Sirius' and d['units']
    assert 'size_quality' in d

def test_current_night_finder_and_bounded_comets():
    jd=calendar_jd(2026,10,21,12)
    data=client.get('/api/next-night',params={'jd':jd,'lat':22.5726,'lon':88.3639}).json()
    assert jd<=data['jd']<jd+3
    s=client.get('/api/snapshot',params={'jd':data['jd'],'lat':22.5726,'lon':88.3639,'limit':100}).json()
    assert s['day_phase']=='Night'
    assert all(c['validity_jd'][0]<=data['jd']<=c['validity_jd'][1] for c in s['comets'])

def test_live_progress_reports_real_processed_items(monkeypatch):
    import threading
    from backend import progress
    from backend.app import compute_snapshot
    original=progress.begin('test-live-progress')
    reached=threading.Event();release=threading.Event();out=[]
    def update(stage,processed=0,total=1,detail=''):
        original(stage,processed,total,detail)
        if stage==3 and processed==250:
            reached.set();assert release.wait(10)
    def work():
        out.append(compute_snapshot(2451545.,0,0,0,0,500,update));progress.finish('test-live-progress')
    thread=threading.Thread(target=work);thread.start()
    assert reached.wait(10)
    state=client.get('/api/calculation-progress/test-live-progress').json()
    assert state['status']=='calculating'
    assert state['processed']==250 and state['total']==500
    assert state['stages_completed']==3 and state['percent']==70
    release.set();thread.join(10)
    assert out and client.get('/api/calculation-progress/test-live-progress').json()['percent']==100

def test_bright_first_filter_skips_detailed_faint_star_work():
    response=client.get('/api/snapshot',params={'jd':2451545.,'limit':9000,'max_magnitude':5.76,'progress_id':'test-bright-first'})
    assert response.status_code==200,response.text[:300]
    bright=response.json();magnitudes=[s['magnitude'] for s in bright['stars']]
    assert 3000<len(magnitudes)<4500 and max(s['magnitude'] for s in bright['stars'] if not s.get('book_star'))<=5.76  # common limit (book stars only as a rounding margin)
    assert magnitudes==sorted(magnitudes)
    assert bright['stellar_work']['skipped_detailed']>110000
    state=client.get('/api/calculation-progress/test-bright-first').json()
    if not state.get('cached'):
        assert len(state['preview']['stars'])==128
        assert state['preview']['stars'][0]['name']=='Sirius'
    faint=client.get('/api/snapshot',params={'jd':2451545.,'limit':9000,'max_magnitude':6.5}).json()
    assert len(faint['stars'])==len(bright['stars'])
    assert faint['stellar_work']['max_magnitude']==5.76


def test_prominent_only_policy_including_cache_search_and_selection():
    from backend.catalog import CATALOG
    data=client.get('/api/snapshot',params={'jd':2451545.,'max_magnitude':20,'limit':9000}).json()
    assert data['stars'] and all(s['magnitude']<=5.76 or s.get('book_star') for s in data['stars'])
    assert data['stellar_work']['max_magnitude']==5.76
    repeated=client.get('/api/snapshot',params={'jd':2451545.,'max_magnitude':20,'limit':9000,'progress_id':'major-only-repeat'}).json()
    assert repeated['playback_cache']['hit']
    assert all(s['magnitude']<=5.76 or s.get('book_star') for s in repeated['stars'])
    faint=next(r for r in CATALOG.rows if r['mag']>9 and r['id'].startswith('hip:'))
    assert all(r['id']!=faint['id'] for r in client.get('/api/search',params={'q':faint['id'],'jd':2451545.}).json())
    assert client.get('/api/object/'+faint['id'],params={'jd':2451545.}).status_code==404
