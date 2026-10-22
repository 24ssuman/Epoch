"""Cache individually bounded JPL comet apparitions; no millennial Kepler extrapolation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA,ROOT,guard
from scripts.setup_data import record,log
import httpx,json,csv,re,io
import numpy as np
API='https://ssd.jpl.nasa.gov/api/horizons.api'
PACKS=[('Halley 1986','DES=1P; CAP;','1985-01-01','1987-12-31',5.5),('Halley 2061','DES=1P; CAP;','2060-01-01','2062-12-31',5.5),('Encke 2026','DES=2P; CAP;','2025-01-01','2028-12-31',11.5),('Hale–Bopp 1997','DES=C/1995 O1;','1996-01-01','1998-12-31',-1.0)]

# Additional apparitions (2026-10-21). (name, Horizons command, start, stop, fallback H, step, file key).
# Sungrazers (perihelion < 0.02 AU) use 1-2 h steps so the cubic spline resolves the perihelion passage.
# 'CAP<YYYY' selects the last apparition solution before that year. BC dates use Horizons' 'BC YYYY-Mon-DD' form.
MORE=[
 ('Halley 1910','DES=1P; CAP<1911;','1909-06-01','1911-06-30',5.5,'12 h','Halley-1910'),
 ('Halley 1835','DES=1P; CAP<1836;','1835-01-01','1836-06-30',5.5,'12 h','Halley-1835'),
 ('Halley 1759','DES=1P; CAP<1760;','1758-06-01','1759-12-31',5.5,'12 h','Halley-1759'),
 ('Halley 1066','DES=1P; CAP<1067;','1065-12-01','1066-09-30',5.5,'12 h','Halley-1066'),
 ('Halley 837','DES=1P; CAP<838;','AD 836-Dec-01','AD 837-Sep-30',5.5,'12 h','Halley-0837'),
 ('Halley 12 BCE','DES=1P; CAP<-10;','BC 12-Jun-01','BC 12-Dec-31',5.5,'12 h','Halley-BCE0012'),
 ('Halley 240 BCE','DES=1P; CAP<-238;','BC 240-Jan-01','BC 240-Sep-30',5.5,'12 h','Halley-BCE0240'),
 ('Great Comet 1811','DES=C/1811 F1;','1811-03-01','1812-08-31',0.,'12 h','GreatComet-1811'),
 ('Donati 1858','DES=C/1858 L1;','1858-06-01','1859-03-31',3.,'12 h','Donati-1858'),
 ('Great September Comet 1882','DES=C/1882 R1-B;',  # split into fragments A-D after perihelion; B is the main nucleus orbit
 '1882-08-25','1883-03-31',.8,'1 h','GreatSeptember-1882'),
 ('Great January Comet 1910','DES=C/1910 A1;','1909-12-20','1910-05-31',5.,'2 h','GreatJanuary-1910'),
 ('Ikeya–Seki 1965','DES=C/1965 S1-A;','1965-09-20','1966-01-31',6.,'1 h','IkeyaSeki-1965'),
 ('Bennett 1970','DES=C/1969 Y1;','1970-01-01','1970-08-31',4.,'12 h','Bennett-1970'),
 ('Kohoutek 1973','DES=C/1973 E1;','1973-06-01','1974-06-30',5.,'12 h','Kohoutek-1973'),
 ('West 1976','DES=C/1975 V1-A;','1975-11-01','1976-07-31',5.,'6 h','West-1976'),
 ('Swift–Tuttle 1992','DES=109P; CAP<1993;','1992-01-01','1993-06-30',4.,'12 h','SwiftTuttle-1992'),
 ('Hyakutake 1996','DES=C/1996 B2;','1996-01-01','1996-08-31',7.,'6 h','Hyakutake-1996'),
 ('Tempel–Tuttle 1998','DES=55P; CAP<1999;','1997-06-01','1998-12-31',9.,'12 h','TempelTuttle-1998'),
 ('McNaught 2007','DES=C/2006 P1;','2006-10-01','2007-06-30',5.,'6 h','McNaught-2007'),
 ('Lovejoy 2011','DES=C/2011 W3;','2011-11-27','2012-04-30',14.,'1 h','Lovejoy-2011'),
 ('ISON 2013','DES=C/2012 S1;','2013-01-01','2013-11-28',8.,'2 h','ISON-2013'),
 ('NEOWISE 2020','DES=C/2020 F3;','2020-03-27','2020-12-31',8.,'6 h','NEOWISE-2020'),
 ('Pons–Brooks 2024','DES=12P; CAP<2025;','2023-06-01','2024-12-31',5.,'12 h','PonsBrooks-2024'),
 ('Tsuchinshan–ATLAS 2024','DES=C/2023 A3;','2024-03-01','2025-03-31',6.,'6 h','TsuchinshanATLAS-2024'),
 ('Swift–Tuttle 2126','DES=109P; CAP;','2126-01-01','2127-03-31',4.,'12 h','SwiftTuttle-2126'),
]

def fetch_vectors(command,start,stop,step='12 h'):
    params={'format':'json','COMMAND':"'"+command+"'",'EPHEM_TYPE':'VECTORS','CENTER':'@0','START_TIME':"'"+start+"'",'STOP_TIME':"'"+stop+"'",'STEP_SIZE':"'"+step+"'",'REF_PLANE':'FRAME','OUT_UNITS':'KM-S','CSV_FORMAT':'YES','VEC_TABLE':'2'}
    with httpx.Client(timeout=120) as c:
        r=c.get(API,params=params);r.raise_for_status();d=r.json()
    text=d.get('result','')
    if '$$SOE' not in text:raise RuntimeError(d.get('error',text[:1500]))
    rows=list(csv.reader(io.StringIO(text.split('$$SOE')[1].split('$$EOE')[0].strip())))
    times=np.array([float(r[0]) for r in rows]);positions=np.array([[float(x) for x in r[2:5]] for r in rows])
    return times,positions,text,params

if __name__=='__main__':
    (DATA/'comets').mkdir(exist_ok=True)
    jobs=[(name,command,start,stop,H,'12 h',f'{name.split()[0]}-{start[:4]}') for name,command,start,stop,H in PACKS]+MORE
    for name,command,start,stop,H,step,key in jobs:
        path=DATA/'comets'/f'{key}.npz'
        if path.exists():continue
        try:
            guard(2_000_000);times,p,text,params=fetch_vectors(command,start,stop,step)
            meta=dict(name=name,H=H,source='JPL Horizons; '+command,query=params,uncertainty='Orbit covariance not propagated in this cached pack; not an accuracy guarantee',photometry='Approximate total-magnitude H; constant activity exponent 4')
            np.savez_compressed(path,jd=times,position_km=p,metadata=json.dumps(meta))
            path.with_suffix('.txt').write_text(text)
            record(path,API+'?'+str(httpx.QueryParams(params)),'NASA/JPL Horizons; retain orbit solution metadata')
            log(f'Cached bounded comet apparition {name}, {start} to {stop} ({len(times)} samples, step {step}); no claims outside this interval.');print('OK',name,len(times))
        except Exception as e:log(f'Comet {name} not installed: {str(e)[:300]}');print('FAILED',name,str(e)[:300])
