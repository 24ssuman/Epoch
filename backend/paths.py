from pathlib import Path
import os, threading, time
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
TMP = ROOT / 'tmp'
# Prevent scientific packages from writing into the user's home directory.
os.environ.setdefault('XDG_CACHE_HOME', str(TMP / 'cache'))
os.environ.setdefault('XDG_CONFIG_HOME', str(TMP / 'config'))
os.environ.setdefault('MPLCONFIGDIR', str(TMP / 'matplotlib'))
os.environ.setdefault('ASTROPY_CACHE_DIR', str(TMP / 'astropy'))
for key in ('XDG_CACHE_HOME','XDG_CONFIG_HOME','MPLCONFIGDIR','ASTROPY_CACHE_DIR'):
    Path(os.environ[key]).mkdir(parents=True,exist_ok=True)
os.environ.setdefault('TMPDIR',str(TMP))
BUDGET = 10_000_000_000

def size_bytes():
    return sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink())

_SCAN = {'bytes': None, 'at': 0., 'reserved': 0, 'reserved_at_start': 0, 'scanning': False}
_SCAN_LOCK = threading.Lock()

def _rescan():
    started = time.monotonic(); total = size_bytes()
    with _SCAN_LOCK:
        # Reservations made before the walk started are now counted on disk; ones made during it are kept.
        _SCAN.update(bytes=total, at=started, scanning=False, reserved=max(0, _SCAN['reserved'] - _SCAN['reserved_at_start']))

def guard(extra=0, max_age=60.):
    # Walking the whole workspace takes ~0.5 s. The first check scans synchronously; afterwards a scan older than
    # max_age is refreshed in a background thread while the last result plus bytes reserved since then is used.
    # That keeps the check conservative within this process; another process's writes are seen at the next rescan.
    with _SCAN_LOCK:
        now = time.monotonic()
        if _SCAN['bytes'] is None:
            _SCAN.update(bytes=size_bytes(), at=now, reserved=0)
        elif now - _SCAN['at'] > max_age and not _SCAN['scanning']:
            _SCAN.update(scanning=True, reserved_at_start=_SCAN['reserved']); threading.Thread(target=_rescan, daemon=True).start()
        if _SCAN['bytes'] + _SCAN['reserved'] + extra > BUDGET:
            raise RuntimeError('10 GB workspace budget would be exceeded; files preserved. Job can resume after storage is addressed.')
        _SCAN['reserved'] += extra
