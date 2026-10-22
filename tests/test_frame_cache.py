"""Exact frame persistence prevents repeated scientific calculations."""
from backend import frame_cache as cache
from backend.app import app
from fastapi.testclient import TestClient


def test_persists_across_requests_and_settings_do_not_collide(tmp_path,monkeypatch):
    monkeypatch.setattr(cache,'DIRECTORY',tmp_path)
    monkeypatch.setattr(cache,'model_revision',lambda jd:'model-a')
    calls=[]
    def compute():calls.append(1);return {'stars':[{'id':'Sirius'}]}
    inputs=(2451545.,51.,0.,0.,0.,100,4.5)
    first=cache.get_or_compute(inputs,compute)
    assert first['playback_cache']['stored'] and not first['playback_cache']['hit']
    second=cache.get_or_compute(inputs,lambda:1/0)
    assert second['stars']==first['stars'] and second['playback_cache']['hit']
    cache.get_or_compute((*inputs[:-1],6.5),compute)
    monkeypatch.setattr(cache,'model_revision',lambda jd:'model-b')
    assert not cache.get_or_compute(inputs,compute)['playback_cache']['hit']
    assert len(calls)==3


def test_budget_preserves_existing_results(tmp_path,monkeypatch):
    monkeypatch.setattr(cache,'DIRECTORY',tmp_path)
    assert cache.store('kept',{'stars':[]}) is None
    monkeypatch.setattr(cache,'MAX_BYTES',0)
    assert 'limit' in cache.store('extra',{'stars':[1]})
    assert cache.load('kept')=={'stars':[]}
    assert cache.load('extra') is None


def test_progress_requests_also_use_disk_cache(tmp_path,monkeypatch):
    import importlib
    api=importlib.import_module('backend.app')
    monkeypatch.setattr(cache,'DIRECTORY',tmp_path)
    monkeypatch.setattr(cache,'model_revision',lambda jd:'test')
    calls=[]
    def compute(*args,**kwargs):calls.append(1);return {'stars':[]}
    monkeypatch.setattr(api,'compute_snapshot',compute)
    client=TestClient(app)
    params=dict(jd=2451545,limit=100,max_magnitude=4.5,progress_id='cache-first')
    assert not client.get('/api/snapshot',params=params).json()['playback_cache']['hit']
    params['progress_id']='cache-second'
    assert client.get('/api/snapshot',params=params).json()['playback_cache']['hit']
    assert client.get('/api/calculation-progress/cache-second').json()['cached']
    assert len(calls)==1


def test_storage_coverage_counts_samples_and_merges_trajectory_time(tmp_path,monkeypatch):
    import importlib
    api=importlib.import_module('backend.app')
    monkeypatch.setattr(cache,'DIRECTORY',tmp_path)
    cache.store('a',{'jd':2451545.})
    cache.store('b',{'jd':2451547.})
    cache.store('c',{'jd':2451545.})
    monkeypatch.setattr(api.jobs,'coverage',lambda:[{'interval_jd':[2451545.,2451555.]},{'interval_jd':[2451550.,2451560.]},{'interval_jd':[2451570.,2451572.]}])
    d=TestClient(app).get('/api/storage-coverage').json()
    assert d['frames']['frames']==3 and d['frames']['distinct_dates']==2
    assert d['frames']['start_jd']==2451545. and d['frames']['end_jd']==2451547.
    assert not d['frames']['continuous']
    assert d['trajectories']['days']==17 and len(d['trajectories']['intervals'])==2


def test_obsolete_playback_request_does_not_wait_for_compute_lock():
    import threading
    from backend import progress
    held=threading.Event();release=threading.Event()
    def hold():
        with cache.COMPUTE_LOCK:held.set();release.wait(3)
    thread=threading.Thread(target=hold);thread.start();held.wait(2)
    old=progress.begin('playback-test-1');progress.begin('playback-test-2')
    try:
        import pytest
        with pytest.raises(cache.SupersededError):cache.get_or_compute((2451545.,),lambda:1/0,old)
    finally:release.set();thread.join(3)
