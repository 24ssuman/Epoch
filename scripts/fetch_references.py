"""Online one-time independent reference acquisition, saved for offline tests."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA
from scripts.setup_data import record,log
from backend.astrotime import calendar_jd
import httpx,json,csv,io
path=DATA/'references';path.mkdir(exist_ok=True)
rows=[]
for year,month,day in [(1900,1,1),(2000,1,1),(2026,10,21)]:
 for name,body in [('Sun',10),('Moon',301),('Mercury',199),('Venus',299),('Mars',4),('Jupiter',5),('Saturn',6),('Uranus',7),('Neptune',8)]:
  jd=calendar_jd(year,month,day,12)
  file=path/f'{name}-{year}.json'
  params={'format':'json','COMMAND':str(body),'EPHEM_TYPE':'OBSERVER','CENTER':'coord@399','COORD_TYPE':'GEODETIC','SITE_COORD':"'0,51.4769,0'",'TLIST':str(jd),'TIME_TYPE':'TT','QUANTITIES':"'2,4'",'ANG_FORMAT':'DEG','APPARENT':'AIRLESS','CSV_FORMAT':'YES','EXTRA_PREC':'YES'}
  try:
   if file.exists():d=json.loads(file.read_text())
   else:
    r=httpx.get('https://ssd.jpl.nasa.gov/api/horizons.api',params=params,timeout=90);r.raise_for_status();d=r.json();file.write_text(json.dumps(d,indent=2))
   text=d.get('result','')
   if '$$SOE' not in text:raise ValueError(text[:300])
   row=next(csv.reader(io.StringIO(text.split('$$SOE')[1].split('$$EOE')[0].strip())))
   rows.append(dict(name=name,jd_tt=jd,ra_deg=float(row[3]),dec_deg=float(row[4]),az_deg=float(row[5]),alt_deg=float(row[6]),lat=51.4769,lon=0,source_file=file.name,query=params))
   log(f'Saved independent Horizons apparent topocentric reference: {name} {year}')
  except Exception as e:log(f'Reference acquisition failed for {name} {year}: {e}')
(path/'horizons.json').write_text(json.dumps(rows,indent=2));record(path/'horizons.json','https://ssd.jpl.nasa.gov/api/horizons.api','NASA/JPL Horizons; reference frame IAU76/80, TT, airless topocentric Greenwich')
