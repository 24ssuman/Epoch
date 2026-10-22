"""Retain JPL states and published GMs for massive asteroid perturbers."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA
from scripts.setup_data import record,log
import httpx,json,re,csv,io
ASTEROIDS=[1,2,3,4,7,10,15,16,31,52,65,87,88,107,511,704]
p=DATA/'kernels/asteroids.json'
rows=json.loads(p.read_text()) if p.exists() else []
constants={int(k):float(v) for k,v in re.findall(r'BODY(\d+)_GM\s*=\s*\(\s*([\d.Ee+\-]+)',(DATA/'kernels/gm_de440.tpc').read_text())}
for item in rows:
    if item['id'] in constants:item['gm_km3_s2']=constants[item['id']];item['gm_source']='JPL gm_de440.tpc'
p.write_text(json.dumps(rows,indent=2))
for n in ASTEROIDS:
    if any(x['number']==n for x in rows):continue
    params={'format':'json','COMMAND':f'{n};','EPHEM_TYPE':'VECTORS','CENTER':'@0','TLIST':'2451545.0','REF_PLANE':'FRAME','OUT_UNITS':'KM-S','CSV_FORMAT':'YES','VEC_TABLE':'2'}
    try:
        r=httpx.get('https://ssd.jpl.nasa.gov/api/horizons.api',params=params,timeout=120);r.raise_for_status();text=r.json()['result']
        if '$$SOE' not in text:raise ValueError(text[:500])
        m=re.search(r'GM\s*=\s*([\d.Ee+\-]+)',text)
        if not m and 2000000+n not in constants:raise ValueError('No published GM supplied; will not invent a mass')
        row=next(csv.reader(io.StringIO(text.split('$$SOE')[1].split('$$EOE')[0].strip())))
        item=dict(number=n,id=2000000+n,gm_km3_s2=constants.get(2000000+n,float(m[1]) if m else 0),position_km=[float(v) for v in row[2:5]],velocity_km_s=[float(v) for v in row[5:8]],source='JPL Horizons J2000 state; GM from target metadata',query=params)
        (DATA/'kernels'/f'asteroid-{n}-source.txt').write_text(text)
        rows.append(item);p.write_text(json.dumps(rows,indent=2));log(f'Installed massive asteroid {n} J2000 state and published GM')
    except Exception as e:log(f'Asteroid {n} source unavailable: {e}')
if p.exists():record(p,'https://ssd.jpl.nasa.gov/api/horizons.api','NASA/JPL Horizons; orbit solutions and GMs retained per target')
