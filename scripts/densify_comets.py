"""Add dense JPL Horizons samples around sungrazing perihelia (online, explicit). Existing packs are not modified.

Hourly samples cannot resolve a perihelion passage at ~1-2 solar radii (several hundred km/s): the cached cubic spline was
off by up to 28,000 km (40 arcsec) there (docs/NASA_CROSSCHECK.md F). This saves 5-minute vectors for +/-1 day around
perihelion to data/comets/dense/<pack>.npz; backend/comets.py merges them into the spline.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
from backend.paths import DATA,guard
from backend import comets
from scripts.install_comets import fetch_vectors,API
from scripts.setup_data import record,log
import httpx

QMAX_AU=.03;HALF_WINDOW_DAYS=1.;STEP='5 m'

if __name__=='__main__':
    folder=DATA/'comets'/'dense';folder.mkdir(exist_ok=True)
    for path in sorted((DATA/'comets').glob('*.npz')):
        pack=next(p for p in comets.packs() if p['meta']['name']==json.loads(str(np.load(path)['metadata']))['name'])
        if pack['perihelion_au']>QMAX_AU:continue
        out=folder/path.name
        if out.exists():print('kept',out.name);continue
        guard(5_000_000);peri=pack['perihelion_jd'];command=pack['meta']['query']['COMMAND'].strip("'")
        times,positions,text,params=fetch_vectors(command,f'JD{peri-HALF_WINDOW_DAYS:.6f}',f'JD{peri+HALF_WINDOW_DAYS:.6f}',STEP)
        meta=dict(name=pack['meta']['name'],source='JPL Horizons; '+command,query=params,purpose=f'dense samples +/-{HALF_WINDOW_DAYS:g} d around perihelion, step {STEP}')
        np.savez_compressed(out,jd=times,position_km=positions,metadata=json.dumps(meta));out.with_suffix('.txt').write_text(text)
        record(out,API+'?'+str(httpx.QueryParams(params)),'NASA/JPL Horizons; retain orbit solution metadata')
        log(f'Dense perihelion samples for {pack["meta"]["name"]}: {len(times)} vectors, step {STEP}, +/-{HALF_WINDOW_DAYS:g} d around JD {peri:.4f}.');print('OK',pack['meta']['name'],len(times))
