"""Persistent exact sky frames; never interpolate apparent positions silently."""
from .paths import DATA, ROOT, guard
from pathlib import Path
from contextlib import contextmanager
from functools import lru_cache
import hashlib, json, sqlite3, threading, time, zlib, os

DIRECTORY=DATA/'playback'
MAX_BYTES=512_000_000
LOCK=threading.RLock()
SCHEMA='exact-sky-v1'

@contextmanager
def database():
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DIRECTORY/'frames.sqlite3',timeout=30)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS frames (key TEXT PRIMARY KEY, payload BLOB NOT NULL, created REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS frame_dates (key TEXT PRIMARY KEY, jd REAL)')
        yield db
        db.commit()
    finally:db.close()

@lru_cache(maxsize=4096)
def path_label(path,root):
    return os.path.relpath(path,root)

def stamp(path):
    s=path.stat();return (path_label(str(path),str(ROOT)),s.st_size,s.st_mtime_ns)

# Directory membership is checked cheaply; existing file stamps are still checked on
# every request so in-place edits cannot serve stale science. Reports are parsed once
# per file revision, rather than hundreds of JSON reads per frame.
_ASSETS = {'directories': (), 'paths': ()}

def asset_paths():
    roots=[ROOT/'backend',*(DATA/f for f in ('kernels','catalogs','comets','references')),DATA/'jobs/calibration']
    with LOCK:
        directories=_ASSETS['directories']
        if not directories or any((p.stat().st_mtime_ns if p.exists() else None)!=t for p,t in directories):
            dirs=set(roots);paths=[]
            for root in roots:
                if not root.exists():continue
                for p in root.rglob('*'):
                    if p.is_dir() and p.name!='__pycache__':dirs.add(p)
                    elif p.is_file() and (root!=ROOT/'backend' or p.parent==root and p.suffix=='.py'):paths.append(p)
            _ASSETS.update(directories=tuple((p,p.stat().st_mtime_ns if p.exists() else None) for p in sorted(dirs)),paths=tuple(sorted(paths)))
        return _ASSETS['paths']

@lru_cache(maxsize=4096)
def report_metadata(path,size,mtime):
    try:
        r=json.loads(Path(path).read_text());a,b=r['interval_jd']
        return (float(a),float(b)) if r.get('accepted') else None
    except (ValueError,KeyError,OSError,TypeError):return None

@lru_cache(maxsize=8)
def indexed_reports(signature):
    reports=[]
    for path,size,mtime in signature:
        interval=report_metadata(path,size,mtime)
        if interval is not None:
            report=Path(path);reports.append((interval,report,report.with_suffix('.npz')))
    return sorted(reports,key=lambda r:r[0][0])

def trajectory_reports():
    from . import jobs
    if not jobs.JOB_DIR.exists():return ()
    entries=list(os.scandir(jobs.JOB_DIR));names={e.name for e in entries};signature=[]
    for e in entries:
        if f'-{jobs.VERSION}-' not in e.name or not e.name.endswith('.json') or e.name[:-5]+'.npz' not in names:continue
        try:
            st=e.stat();signature.append((e.path,st.st_size,st.st_mtime_ns))
        except OSError:continue
    return indexed_reports(tuple(sorted(signature)))

@lru_cache(maxsize=8)
def revision_hash(signature):
    return hashlib.sha256(json.dumps([SCHEMA,signature],sort_keys=True).encode()).hexdigest()

def model_revision(jd):
    from . import jobs
    paths=list(asset_paths())
    for (a,b),report,pack in trajectory_reports():
        # Apparent planet directions also evaluate retarded epochs (all current
        # solar-system light times fit comfortably inside this two-day guard).
        if a<=jd and b>=jd-2:paths.extend((report,pack))
    # Version is explicit even if this epoch has no accepted coverage yet.
    return revision_hash((jobs.VERSION,tuple(stamp(p) for p in sorted(paths))))

def data_revision():
    """Bootstrap signal for scientific asset/coverage changes, excluding worker status."""
    from . import jobs
    paths=[*asset_paths()]
    for _,report,pack in trajectory_reports():paths.extend((report,pack))
    return revision_hash((jobs.VERSION,tuple(stamp(p) for p in sorted(paths))))

def key_for(inputs):
    return hashlib.sha256(json.dumps([model_revision(inputs[0]),inputs],separators=(',',':')).encode()).hexdigest()

def load(key):
    with LOCK,database() as db:
        row=db.execute('SELECT payload FROM frames WHERE key=?',(key,)).fetchone()
    if row:
        try:return json.loads(zlib.decompress(row[0]))
        except (ValueError,zlib.error):return None
    return None

def store(key,result):
    payload=zlib.compress(json.dumps(result,separators=(',',':'),allow_nan=False).encode(),3)
    with LOCK,database() as db:
        # Summing every payload costs ~0.15 s on a full cache; count it once, then track inserts (only this process writes frames).
        if _USED[0] is None:_USED[0]=db.execute('SELECT COALESCE(SUM(LENGTH(payload)),0) FROM frames').fetchone()[0]
        if _USED[0]+len(payload)>MAX_BYTES:return 'Playback cache limit reached; existing frames preserved'
        try:guard(len(payload)+65536)
        except RuntimeError as e:return str(e)
        if db.execute('INSERT OR IGNORE INTO frames VALUES (?,?,?)',(key,payload,time.time())).rowcount:_USED[0]+=len(payload)
        db.execute('INSERT OR IGNORE INTO frame_dates VALUES (?,?)',(key,result.get('jd')))
    return None
_USED=[None]

# Serialize duplicate requests so an aborted browser request can finish and be reused.
COMPUTE_LOCK=threading.RLock()
class SupersededError(Exception):pass

def get_or_compute(inputs,compute,progress=None):
    started=time.perf_counter()
    while not COMPUTE_LOCK.acquire(timeout=.05):
        if progress and hasattr(progress,'is_current') and not progress.is_current():raise SupersededError('Newer playback frame requested')
    try:
        if progress and hasattr(progress,'is_current') and not progress.is_current():raise SupersededError('Newer playback frame requested')
        t0=time.perf_counter();key=key_for(inputs);key_ms=(time.perf_counter()-t0)*1000
        t0=time.perf_counter();result=load(key);lookup_ms=(time.perf_counter()-t0)*1000
        if result is not None:
            result['playback_cache']=dict(hit=True,stored=True,load_ms=(time.perf_counter()-started)*1000,mode='exact-frame',note='Loaded stored sky frame; scientific calculation skipped')
            result['playback_cache']['timings_ms']=dict(key_ms=key_ms,lookup_ms=lookup_ms,store_ms=0.,request_ms=(time.perf_counter()-started)*1000)
            if progress:progress(4,1,1,'Loaded stored sky frame; no scientific recalculation')
            return result
        result=compute();t0=time.perf_counter();warning=store(key,result);store_ms=(time.perf_counter()-t0)*1000
        result['playback_cache']=dict(hit=False,stored=warning is None,mode='exact-frame',note=warning or 'Calculated once and stored for reuse')
        result['playback_cache']['timings_ms']=dict(key_ms=key_ms,lookup_ms=lookup_ms,store_ms=store_ms,request_ms=(time.perf_counter()-started)*1000)
        return result
    finally:COMPUTE_LOCK.release()


def statistics():
    """Index legacy frame dates once without rewriting or deleting their payloads."""
    with LOCK,database() as db:
        missing=db.execute('SELECT f.key,f.payload FROM frames f LEFT JOIN frame_dates d ON f.key=d.key WHERE d.key IS NULL').fetchall()
        for key,payload in missing:
            try:jd=json.loads(zlib.decompress(payload)).get('jd')
            except (ValueError,zlib.error):jd=None
            db.execute('INSERT OR IGNORE INTO frame_dates VALUES (?,?)',(key,jd))
        count,size=db.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(payload)),0) FROM frames').fetchone()
        distinct,start,end=db.execute('SELECT COUNT(DISTINCT jd),MIN(jd),MAX(jd) FROM frame_dates').fetchone()
    return dict(frames=count,distinct_dates=distinct,start_jd=start,end_jd=end,payload_bytes=size,limit_bytes=MAX_BYTES,
                continuous=False,note='Exact sampled dates only; gaps between frames are not calculated sky coverage. Includes retained older-model frames, which may need recalculation.')
