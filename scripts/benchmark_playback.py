#!/usr/bin/env python3
"""Offline exact-frame benchmark. Artifacts and isolated cache stay in the workspace."""
from pathlib import Path
import argparse,datetime,json,statistics,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app import compute_snapshot,snapshot_cached,json_response
from backend.astrotime import calendar_jd
from backend import frame_cache,jobs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'tmp/performance/benchmark.json')
    parser.add_argument('--samples',type=int,default=12)
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT):parser.error('Output must stay inside this workspace')
    if args.samples<3:parser.error('Use at least three samples')
    baselines=json.loads(args.baseline.read_text()) if args.baseline else []
    cases=baselines or [dict(case=name,jd=calendar_jd(year,month,day,hour),view=view,horizon_only=horizon) for name,year,month,day,hour,view,horizon in [
        ('modern-ground',2026,10,22,16,'ground',True),('ancient-ground',-5000,6,1,16,'ground',True),
        ('deep-ground',-14500,6,1,16,'ground',True),('modern-space-api',2026,10,22,16,'space',False),('comet-ground',2024,10,9,16,'ground',True)]]
    work=ROOT/'tmp/performance';work.mkdir(parents=True,exist_ok=True)
    run=Path(tempfile.mkdtemp(prefix='benchmark-',dir=work));(run/'README.md').write_text('# Benchmark artifacts\nIsolated exact-frame cache for this benchmark run; preserved after measurement.\n')
    frame_cache.DIRECTORY=run/'cache';frame_cache._USED[0]=None
    results=[]
    for case in cases:
        name=case['case'];jd=case['jd'];view=case['view'];horizon=case['horizon_only']
        actual=compute_snapshot(jd,22.5726,88.3639,0,0,9000,view=view,horizon_only=horizon)
        equivalent=None
        reference=args.baseline.parent/(name+'.baseline.json') if args.baseline else None
        if reference and reference.exists():
            expected=json.loads(reference.read_text());actual['calculation'].pop('timings_ms');expected['calculation'].pop('timings_ms')
            assert actual==expected,f'Scientific output changed: {name}'
            equivalent=True
        # Warm imports, assets, workspace guard, interval packs and SQLite before timing.
        snapshot_cached(jd-.00001,22.5726,88.3639,0,0,9000,view=view,horizon_only=horizon)
        cold=[];stored=[]
        for k in range(args.samples):
            epoch=jd+k*.000001
            for samples in (cold,stored):
                start=time.perf_counter();result=snapshot_cached(epoch,22.5726,88.3639,0,0,9000,view=view,horizon_only=horizon);json_response(result)
                samples.append(dict(wall_ms=(time.perf_counter()-start)*1000,calculation_ms=0. if result['playback_cache']['hit'] else result['calculation']['timings_ms']['total_ms'],**result['playback_cache']['timings_ms']))
        median=lambda samples,key:statistics.median(r[key] for r in samples)
        entry=dict(case=name,jd_tt=jd,view=view,horizon_only=horizon,observer=dict(lat_deg=22.5726,lon_deg=88.3639,elevation_m=0,delta_t_offset_s=0),scientifically_identical=equivalent,
                   uncached_median_ms=median(cold,'wall_ms'),cached_median_ms=median(stored,'wall_ms'),calculation_median_ms=median(cold,'calculation_ms'),revision_median_ms=median(cold,'key_ms'),uncached_samples=cold,cached_samples=stored)
        if case.get('runs'):
            before=statistics.median(r['total_ms']+r['revision_ms'] for r in case['runs'])
            after=statistics.median(r['calculation_ms']+r['key_ms'] for r in cold)
            entry.update(baseline_calculation_and_revision_ms=before,calculation_and_revision_speedup=before/after)
        results.append(entry);print(name,json.dumps({k:v for k,v in entry.items() if k.endswith('_ms') or k.endswith('speedup') or k=='scientifically_identical'}),flush=True)
    report=dict(recorded_at=datetime.datetime.now().astimezone().isoformat(),units='milliseconds wall-clock; Julian dates in TT',source='Installed local JPL/catalog/comet/accepted reconstruction data; no downloads',reconstruction_status=jobs.status().get('status'),
        limitations='Warm-process measurements on this machine; JSON serialization and isolated persistent cache included, HTTP/browser/GPU excluded. No astronomical interpolation or scientific accuracy change. Space case tests the preserved backend API; the UI now supports ground view only.',cases=results)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
