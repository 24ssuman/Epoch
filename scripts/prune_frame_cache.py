"""Remove saved sky frames that can never be reused (offline). Dry run unless --apply is given.

A frame's cache key includes the size and modification time of every model file (backend code, catalogs, kernels,
comets, references). A frame created before the newest of those files changed was keyed on an older model, so no
request can ever load it again. Only such frames are removed; everything else is kept. --vacuum then shrinks the file.
"""
import sys,argparse,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA,ROOT
from backend import frame_cache

def newest_model_change():
    paths=list((ROOT/'backend').glob('*.py'))
    for folder in ('kernels','catalogs','comets','references'):paths.extend(p for p in (DATA/folder).rglob('*') if p.is_file())
    newest=max(paths,key=lambda p:p.stat().st_mtime)
    return newest.stat().st_mtime,newest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--vacuum',action='store_true');a=parser.parse_args()
    cutoff,newest=newest_model_change();db_path=frame_cache.DIRECTORY/'frames.sqlite3'
    db=sqlite3.connect(db_path,timeout=60)
    total,size=db.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(payload)),0) FROM frames').fetchone()
    stale,stale_size=db.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(payload)),0) FROM frames WHERE created<?',(cutoff,)).fetchone()
    print(f'Newest model file: {newest.relative_to(ROOT)}')
    print(f'Frames: {total} ({size/1e6:.1f} MB). Unreachable (created before that change): {stale} ({stale_size/1e6:.1f} MB). Kept: {total-stale}.')
    if a.apply:
        with db:
            db.execute('DELETE FROM frames WHERE created<?',(cutoff,))
            db.execute('DELETE FROM frame_dates WHERE key NOT IN (SELECT key FROM frames)')
        print('Removed unreachable frames.')
        if a.vacuum:
            before=db_path.stat().st_size;db.execute('VACUUM');print(f'Vacuumed: {before/1e6:.1f} MB -> {db_path.stat().st_size/1e6:.1f} MB on disk.')
    else:print('Dry run; pass --apply (and --vacuum) to remove them.')
    db.close()
