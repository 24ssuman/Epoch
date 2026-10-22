"""Regression checks for exact-frame optimizations; no performance timing thresholds."""
import json
from pathlib import Path
import numpy as np
import pytest
from backend import frame_cache as cache, jobs
from backend.app import compute_snapshot
from backend.catalog import CATALOG, bv_rgb, PC_KM
from backend.sanskrit import SANSKRIT


@pytest.fixture
def revision_workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(cache,'ROOT',tmp_path)
    monkeypatch.setattr(cache,'DATA',tmp_path/'data')
    monkeypatch.setattr(cache,'_ASSETS',{'directories':(),'paths':()})
    monkeypatch.setattr(jobs,'JOB_DIR',tmp_path/'data/jobs')
    monkeypatch.setattr(jobs,'VERSION','test-current')
    jobs.JOB_DIR.mkdir(parents=True)
    (tmp_path/'backend').mkdir()
    (tmp_path/'backend/model.py').write_text('model = 1')
    return jobs.JOB_DIR


def chunk(folder,name,interval,accepted=True):
    report=folder/(name+'.json');report.write_text(json.dumps(dict(interval_jd=interval,accepted=accepted)))
    report.with_suffix('.npz').write_bytes(b'fake pack for dependency checks')
    return report


def test_active_version_and_new_coverage_invalidate_only_matching_epochs(revision_workspace):
    folder=revision_workspace
    before=cache.model_revision(100);other=cache.model_revision(500)
    chunk(folder,'past-v3-old',[90,110])
    assert cache.model_revision(100)==before
    report=chunk(folder,'past-test-current-new',[90,110])
    assert cache.model_revision(100)!=before
    assert cache.model_revision(500)==other
    current=cache.model_revision(100)
    (folder/'status.json').write_text('{"status":"running","completed":1}')
    (folder/'control.json').write_text('{"pause_requested":false}')
    assert cache.model_revision(100)==current
    report.with_suffix('.npz').write_bytes(b'replacement accepted pack')
    assert cache.model_revision(100)!=current


def test_report_metadata_is_reused_but_edits_and_calibration_invalidate(revision_workspace):
    folder=revision_workspace
    report=chunk(folder,'past-test-current-new',[90,110],accepted=False)
    before=cache.model_revision(100)
    hits=cache.indexed_reports.cache_info().hits
    misses=cache.report_metadata.cache_info().misses
    assert cache.model_revision(100)==before
    assert cache.indexed_reports.cache_info().hits>hits
    assert cache.report_metadata.cache_info().misses==misses
    report.write_text(json.dumps(dict(interval_jd=[90,110],accepted=True)))
    accepted=cache.model_revision(100)
    assert accepted!=before
    calibration=folder/'calibration';calibration.mkdir()
    (calibration/'lunar_correction.json').write_text('{"coefficient":1}')
    calibrated=cache.model_revision(100)
    assert calibrated!=accepted
    (calibration/'lunar_correction.json').write_text('{"coefficient":200}')
    assert cache.model_revision(100)!=calibrated


def test_static_dependencies_detect_in_place_edits_and_added_files(revision_workspace):
    before=cache.model_revision(100)
    (cache.ROOT/'backend/model.py').write_text('model = 200')
    changed=cache.model_revision(100);assert changed!=before
    (cache.ROOT/'backend/extra.py').write_text('extra = 1')
    assert cache.model_revision(100)!=changed


def test_stellar_static_fields_stay_exact_and_do_not_stat_per_star(monkeypatch):
    original=SANSKRIT.load;calls=[]
    def counted():calls.append(1);return original()
    monkeypatch.setattr(SANSKRIT,'load',counted)
    result=compute_snapshot(2461335.125,22.5726,88.3639,0,0,9000,view='ground',horizon_only=True)
    assert len(result['stars'])>1000 and len(calls)<40
    for star in result['stars'][::137]:
        row=CATALOG.rows[CATALOG.id_index[star['id']]]
        bv=row.get('bv');bp=row.get('bp_rp')
        if bv is None:bv=.65 if bp is None else np.clip(.75*bp-.1,-.4,2.5)
        assert star['color']==bv_rgb(float(bv))
        for key,value in SANSKRIT.fields(row['id'],row['name'],False).items():assert star[key]==value
        measured=CATALOG.diameters.get(star['id'])
        if measured and np.isfinite(CATALOG.distance[CATALOG.id_index[star['id']]]):
            radius=measured['diameter_mas']/206264806.247/2*CATALOG.distance[CATALOG.id_index[star['id']]]*PC_KM
            assert star['radius_km']==radius


def test_object_detail_uses_full_observer_inputs():
    from fastapi.testclient import TestClient
    from backend.app import app
    params=dict(jd=2461335.125,lat=22.5726,lon=88.3639,elevation=2200,dt=340.)
    detail=TestClient(app).get('/api/object/Moon',params=params).json()
    expected=compute_snapshot(**params,limit=1)['bodies']
    moon=next(b for b in expected if b['id']=='Moon')
    assert detail['ground_direction']==moon['ground_direction']
    assert detail['direction']==moon['direction']


def test_playback_can_disable_preview_work(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    from backend import progress
    monkeypatch.setattr(cache,'DIRECTORY',tmp_path)
    monkeypatch.setattr(cache,'model_revision',lambda jd:'preview-off')
    response=TestClient(app).get('/api/snapshot',params=dict(jd=2461335.125,progress_id='preview-off-1',preview=False))
    assert response.status_code==200
    assert 'preview' not in progress.read('preview-off-1')
    assert response.json()['playback_cache']['timings_ms']['key_ms']>=0
