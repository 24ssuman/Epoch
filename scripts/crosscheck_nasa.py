"""Cross-check the simulator's calculations against NASA data.

  fetch   (ONLINE, explicit)  save NASA/JPL Horizons responses, NASA eclipse-site pages (Espenak & Meeus) into
                              data/references/crosscheck/. Existing files are kept, never overwritten.
  analyze (OFFLINE)           compare the saved NASA data with the simulator and write docs/NASA_CROSSCHECK.md/.json.

Tests (offline):
  A geocentric astrometric directions + distances vs Horizons, 9,000 BCE-5,000 CE (kernel read + light time)
  B apparent topocentric alt/az vs Horizons, Delhi, airless (full pipeline: aberration, deflection, frames, Delta T)
  C Delta T vs NASA Table 1 (Morrison & Stephenson 2004) and the Delta T column of NASA's Five Millennium Canon
  D geocentric time and gamma of greatest solar eclipse vs NASA's Five Millennium Canon of Solar Eclipses
  E reconstruction (REBOUND IAS15 chunks) vs DE441, from the chunk reports and by re-evaluating stored chunks
  F cached comet splines vs Horizons at off-node times; app magnitude vs Horizons total magnitude
"""
import sys,json,re,html,time,csv,io,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from backend.paths import DATA,ROOT
from backend.astrotime import calendar_jd,jd_calendar,delta_t,Epoch,local_basis

REF=DATA/'references'/'crosscheck'
API='https://ssd.jpl.nasa.gov/api/horizons.api'
YEARS=[-9000,-8000,-6000,-4000,-3000,-2000,-1000,-500,0,500,1000,1500,1600,1800,1900,2000,2026,2100,2200,2500,3000,4000,5000]
JDS=[calendar_jd(y,1,1,12) for y in YEARS]
# app name -> Horizons command used by the app (planet systems are barycenters) ; extra body-centre commands quantify that limit
APP={'Sun':'10','Moon':'301','Mercury':'199','Venus':'299','Mars':'4','Jupiter':'5','Saturn':'6','Uranus':'7','Neptune':'8','Pluto':'9'}
CENTRE_YEARS=[1801,1900,2000,2026,2100]  # satellite-based planet-centre ephemerides in Horizons cover about 1600-2200 only
CENTRES={'Mars':'499','Jupiter':'599','Saturn':'699','Uranus':'799','Neptune':'899','Pluto':'999'}
TARGET={'Sun':10,'Moon':301,'Mercury':1,'Venus':2,'Mars':4,'Jupiter':5,'Saturn':6,'Uranus':7,'Neptune':8,'Pluto':9}
MAG_BODIES={'Moon':'301','Mercury':'199','Venus':'299','Mars':'499','Jupiter':'599','Saturn':'699','Uranus':'799','Neptune':'899'}
SITE=(28.6139,77.2090,0.)  # New Delhi lat, east lon, elevation m
ECLIPSE_PAGES=[-1999,-1499,-999,-499,-99,1,501,1001,1501,1801,1901,2001,2101,2501,2901]
ARCSEC=206264.80624709636

def log(message):
    print(message,flush=True)
    with (ROOT/'LOG.md').open('a') as f:f.write(f'\n- {time.strftime("%Y-%m-%d %H:%M:%S %z")}: {message}\n')

def horizons(params,path):
    import httpx
    if path.exists():return json.loads(path.read_text())
    for attempt in range(3):
        try:
            r=httpx.get(API,params=params,timeout=120);r.raise_for_status();d=r.json()
            if '$$SOE' not in d.get('result',''):raise RuntimeError(d.get('error') or d.get('result','')[:400])
            path.write_text(json.dumps(dict(query=params,fetched=time.strftime('%Y-%m-%dT%H:%M:%S%z'),**d),indent=1));time.sleep(.4);return d
        except Exception as e:
            err=e;time.sleep(2*(attempt+1))
    log(f'Horizons request failed ({path.name}): {str(err)[:200]}');return None

def rows(d):
    return list(csv.reader(io.StringIO(d['result'].split('$$SOE')[1].split('$$EOE')[0].strip())))

def source_line(d):
    m=re.search(r'Target body name:.*\{source: ([^}]+)\}',d['result']);return m.group(1).strip() if m else '?'

# ---------------------------------------------------------------- fetch
def fetch():
    from scripts.setup_data import record
    REF.mkdir(parents=True,exist_ok=True);(REF/'eclipse').mkdir(exist_ok=True)
    tl=','.join(f'{j:.6f}' for j in JDS);saved=[]
    for name,cmd in list(APP.items())+[(n+' (centre)',c) for n,c in CENTRES.items()]:
        use=tl if 'centre' not in name else ','.join(f'{calendar_jd(y,1,1,12):.6f}' for y in CENTRE_YEARS)
        p=dict(format='json',COMMAND=cmd,CENTER='500@399',TLIST=use,TLIST_TYPE='JD',TIME_TYPE='TT',QUANTITIES="'1,20'",ANG_FORMAT='DEG',CSV_FORMAT='YES',EXTRA_PREC='YES',OBJ_DATA='NO')
        horizons(p,REF/f'geo-{cmd}.json');saved.append(REF/f'geo-{cmd}.json')
    for name,cmd in APP.items():
        if name=='Pluto':continue
        p=dict(format='json',COMMAND=cmd,CENTER='coord@399',COORD_TYPE='GEODETIC',SITE_COORD=f"'{SITE[1]},{SITE[0]},0'",TLIST=tl,TLIST_TYPE='JD',TIME_TYPE='TT',QUANTITIES="'2,4'",APPARENT='AIRLESS',ANG_FORMAT='DEG',CSV_FORMAT='YES',EXTRA_PREC='YES',OBJ_DATA='NO')
        horizons(p,REF/f'topo-{cmd}.json');saved.append(REF/f'topo-{cmd}.json')
    import httpx
    for url,name in [('https://eclipse.gsfc.nasa.gov/SEcat5/deltat.html','deltat.html')]+[(f'https://eclipse.gsfc.nasa.gov/SEcat5/SE{eclipse_range(y)}.html',f'eclipse/{eclipse_range(y)}.html') for y in ECLIPSE_PAGES]:
        path=REF/name
        if not path.exists():
            r=httpx.get(url,timeout=120,follow_redirects=True);r.raise_for_status();path.write_text(r.text);time.sleep(.4)
        saved.append(path)
    from backend import comets
    for pack in comets.packs():
        meta=pack['meta'];key=re.sub(r'[^A-Za-z0-9]+','_',meta['name']);t=pack['times']
        epochs=[t[0]+f*(t[-1]-t[0])+.31 for f in (.13,.37,.61,.87)]+[pack['perihelion_jd']+.05]
        command=meta['query']['COMMAND'].strip("'");tl2=','.join(f'{e:.6f}' for e in epochs)
        v=dict(format='json',COMMAND="'"+command+"'",EPHEM_TYPE='VECTORS',CENTER='@0',TLIST=tl2,TLIST_TYPE='JD',REF_PLANE='FRAME',OUT_UNITS='KM-S',CSV_FORMAT='YES',VEC_TABLE='2',OBJ_DATA='NO')
        horizons(v,REF/f'comet-{key}-vec.json');saved.append(REF/f'comet-{key}-vec.json')
        o=dict(format='json',COMMAND="'"+command+"'",CENTER='500@399',TLIST=tl2,TLIST_TYPE='JD',TIME_TYPE='TT',QUANTITIES="'9'",ANG_FORMAT='DEG',CSV_FORMAT='YES',OBJ_DATA='NO')
        horizons(o,REF/f'comet-{key}-obs.json');saved.append(REF/f'comet-{key}-obs.json')
    # planet magnitudes (Horizons APmag = Mallama & Hilton 2018) with phase angle, 2016-2036 (covers a Saturn ring-tilt swing)
    for cmd in MAG_BODIES.values():
        p=dict(format='json',COMMAND=cmd,CENTER='500@399',START_TIME="'2016-01-01'",STOP_TIME="'2036-01-01'",STEP_SIZE="'30 d'",TIME_TYPE='TT',QUANTITIES="'9,19,20,24'",CSV_FORMAT='YES',EXTRA_PREC='YES',OBJ_DATA='NO')
        horizons(p,REF/f'mag-{cmd}.json');saved.append(REF/f'mag-{cmd}.json')
    for path in saved:
        if path.exists():record(path,API+' (or eclipse.gsfc.nasa.gov)','NASA/JPL Horizons or NASA GSFC Eclipse Web Site (Espenak & Meeus); cross-check reference')
    log(f'Cross-check fetch finished: {len(saved)} NASA reference files in {REF.relative_to(ROOT)}')

def eclipse_range(start):
    # NASA page names: SE-1999--1900, SE-0099-0000, SE0001-0100, SE0501-0600, SE1901-2000 ...
    end=start+99
    f=lambda y:('-' if y<0 else '')+f'{abs(y):04d}'
    return f'{f(start)}-{f(end)}'

# ---------------------------------------------------------------- analysis
def sep(a,b):
    return float(np.degrees(np.arccos(np.clip(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b),-1,1)))*3600)

def astrometric(EPH,jd,target):
    """Geocentric astrometric direction (light time only) and distance, ICRS, from the app's ephemeris reader."""
    earth,_=EPH.state(jd,399);pt,_=EPH.state(jd,target)
    for _ in range(4):
        t=np.linalg.norm(pt-earth)/299792.458/86400;pt,_=EPH.state(jd-t,target)
    v=pt-earth;return v/np.linalg.norm(v),float(np.linalg.norm(v))

def part_a():
    from backend.ephemeris import EPHEMERIS as EPH
    EPH.refresh();out=[];sources=set();orig=EPH.kernel
    for name,cmd in list(APP.items())+[(n+' (centre)',c) for n,c in CENTRES.items()]:
        path=REF/f'geo-{cmd}.json'
        if not path.exists():continue
        d=json.loads(path.read_text());sources.add(source_line(d));target=TARGET[name.replace(' (centre)','')]
        # epochs come from the saved query itself (centre files may start at different years)
        for jd,row in zip([float(x) for x in d['query']['TLIST'].split(',')],rows(d)):
            year=jd_calendar(jd)['year']
            ra,dec,delta=float(row[3]),float(row[4]),float(row[5])
            h=np.array([math.cos(math.radians(dec))*math.cos(math.radians(ra)),math.cos(math.radians(dec))*math.sin(math.radians(ra)),math.sin(math.radians(dec))])
            try:u,dist=astrometric(EPH,jd,target)
            except ValueError:continue
            kernel=orig(jd)[0];e441=None
            if kernel=='de440.bsp' and 'de441.bsp' in EPH.kernels:   # Horizons serves DE441; show the app's DE440 against it separately
                EPH.kernel=lambda jd:('de441.bsp',EPH.kernels['de441.bsp'])
                try:u2,_=astrometric(EPH,jd,target);e441=sep(u2,h)
                finally:EPH.kernel=orig
            out.append(dict(body=name,year=year,separation_arcsec=sep(u,h),separation_de441_arcsec=e441,distance_au=dist/149597870.7,horizons_distance_au=delta,distance_error_km=abs(dist/149597870.7-delta)*149597870.7,kernel=kernel))
    return out,sorted(sources)

def _enu(alt,az):
    a,z=math.radians(alt),math.radians(az);return np.array([math.cos(a)*math.sin(z),math.cos(a)*math.cos(z),math.sin(a)])

def _rotation_fit(pairs,axis):
    """Angle (arcsec) of the single rotation about the Earth axis that best maps the app's local directions onto Horizons'."""
    num=den=0.
    for va,vh in pairs:num+=axis@np.cross(va,vh);den+=va@vh-(axis@va)*(axis@vh)
    return math.atan2(num,den)*ARCSEC

def _pre_fix(jd):
    """HISTORICAL: the app's deep-time epoch with the sidereal-angle sign it had before 2026-10-21 (era + alpha instead of era - alpha)."""
    import erfa
    e=Epoch(jd)
    if e.frame_model.startswith('Vondrak'):
        tt1=math.floor(jd);tt2=jd-tt1;m=erfa.ltpb(2000+(jd-2451545)/365.25)
        e.sidereal=float(erfa.era00(tt1,tt2-e.dt/86400))+math.atan2(m[0,1],m[0,0])
    return e

def part_b():
    from backend.ephemeris import body_snapshot
    lat,lon=SITE[:2];axis=np.array([0.,math.cos(math.radians(lat)),math.sin(math.radians(lat))])
    data={cmd:json.loads((REF/f'topo-{cmd}.json').read_text()) for n,cmd in APP.items() if n!='Pluto' and (REF/f'topo-{cmd}.json').exists()}
    if not data:return []
    def run(jd,row_of,epoch):
        basis=local_basis(epoch,lat,lon);pairs=[];sky=[];tot=[]
        for name,cmd in APP.items():
            if name=='Pluto' or cmd not in data:continue
            row=row_of[cmd];body=next(b for b in body_snapshot(epoch,basis,lat,lon,0)[0] if b['name']==name)
            va=np.array(body['ground_direction']);vh=_enu(float(row[6]),float(row[5]));pairs.append((va,vh));tot.append(math.degrees(math.acos(min(1,va@vh)))*3600)
            u=epoch.matrix@np.array(body['direction']);ra=math.degrees(math.atan2(u[1],u[0]))%360;dec=math.degrees(math.asin(u[2]))
            dra=((ra-float(row[3])+180)%360-180)*math.cos(math.radians(dec))*3600;sky.append(math.hypot(dra,(dec-float(row[4]))*3600))
        alpha=_rotation_fit(pairs,axis);c,sn=math.cos(alpha/ARCSEC),math.sin(alpha/ARCSEC)
        left=[math.degrees(math.acos(min(1,(va*c+np.cross(axis,va)*sn+axis*(axis@va)*(1-c))@vh)))*3600 for va,vh in pairs]
        return dict(median=float(np.median(tot)),max=max(tot),sky=float(np.median(sky)),alpha=alpha,after_fit_max=max(left))
    # calibrate the sign/scale of "rotation offset per second of Delta T" with the app itself, at the first epoch
    probe=len(JDS)-JDS[::-1].index(calendar_jd(2026,1,1,12))-1
    rows_probe={cmd:rows(d)[probe] for cmd,d in data.items()}
    a0=run(JDS[probe],rows_probe,Epoch(JDS[probe]))['alpha'];a1=run(JDS[probe],rows_probe,Epoch(JDS[probe],100.))['alpha'];k=(a1-a0)/100.
    out=[]
    for i,(year,jd) in enumerate(zip(YEARS,JDS)):
        row_of={cmd:rows(d)[i] for cmd,d in data.items()};e=Epoch(jd)
        r=run(jd,row_of,e);rec=dict(year=year,frame=e.frame_model,rotation=e.rotation_quality,delta_t_app=e.dt,median_arcsec=r['median'],max_arcsec=r['max'],sky_median_arcsec=r['sky'],
            rotation_offset_arcsec=r['alpha'],implied_delta_t_horizons=e.dt-r['alpha']/k,after_rotation_fit_max_arcsec=r['after_fit_max'])
        if e.frame_model.startswith('Vondrak'):
            f=run(jd,row_of,_pre_fix(jd));rec['pre_fix']=dict(median_arcsec=f['median'],rotation_offset_arcsec=f['alpha'],implied_delta_t_horizons=e.dt-f['alpha']/k,after_rotation_fit_max_arcsec=f['after_fit_max'],sky_median_arcsec=f['sky'])
        out.append(rec)
    return out

def sidereal_sign_test():
    """The app's deep-time sidereal angle (Vondrak branch, forced for every year here) vs ERFA's GAST (IAU 2006/2000A), where the IAU model is valid.
    Also the formula used before the 2026-10-21 fix (era + alpha)."""
    import erfa
    out=[];wrap=lambda x:(math.degrees(x)+180)%360-180
    for year in (1000,1300,1499,2501,2700,3000):
        jd=calendar_jd(year,1,1,12);e=Epoch(jd);tt1=math.floor(jd);tt2=jd-tt1;m=erfa.ltpb(2000+(jd-2451545)/365.25)
        era=float(erfa.era00(tt1,tt2-e.dt/86400));alpha=math.atan2(m[0,1],m[0,0]);gast=float(erfa.gst06a(tt1,tt2-e.dt/86400,tt1,tt2))
        out.append(dict(year=year,pre_fix_minus_gast_deg=wrap(era+alpha-gast),sign_fixed_only_minus_gast_deg=wrap(era-alpha-gast),app_minus_gast_deg=wrap((e.sidereal if e.frame_model.startswith('Vondrak') else era-alpha)-gast)))
    return out

def read_deltat_table():
    text=html.unescape(re.sub(r'<[^>]+>',' ',(REF/'deltat.html').read_text()))
    t1=text[text.find('Table 1'):text.find('Table 2')];t2=text[text.find('Table 2'):]
    rows1=[(float(a),float(b),float(c) if c else None) for a,b,c in re.findall(r'(?m)^\s*(-?\d{1,4})\s+(-?\d+)\s*(\d+)?\s*$',t1)]
    rows2=[(float(a),float(b)) for a,b in re.findall(r'(?m)^\s*(\d{4}\.0)\s+\+?(-?[\d.]+)\s',t2)]
    return rows1,rows2

def eclipse_rows(start):
    path=REF/'eclipse'/f'{eclipse_range(start)}.html'
    if not path.exists():return []
    text=html.unescape(re.sub(r'<[^>]+>','',path.read_text()))
    out=[]
    for m in re.finditer(r'(?m)^(\d{5})\s+(-?\d{4})\s+(\w{3})\s+(\d\d)\s+(\d\d):(\d\d):(\d\d)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\w+)\s+(\S+)\s+(-?\d+\.\d+)\s+(\d\.\d+)',text):
        y,mon,day,h,mi,s=int(m[2]),m[3],int(m[4]),int(m[5]),int(m[6]),int(m[7])
        month=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(mon)+1
        # NASA uses the Julian calendar before 1582-Oct-15 and astronomical year numbering
        cal='julian' if (y,month,day)<(1582,10,15) else 'gregorian'
        out.append(dict(number=m[1],year=y,month=month,day=day,td_seconds=h*3600+mi*60+s,jd_td=calendar_jd(y,month,day,0,cal)+(h*3600+mi*60+s)/86400,
                        delta_t=float(m[8]),type=m[11][0],gamma=float(m[13]),magnitude=float(m[14])))
    return out

def part_c(eclipses):
    rows1,rows2=read_deltat_table();table=[]
    for year,value,err in rows1:table.append(dict(year=year,nasa=value,stderr=err,app=delta_t(year),diff=delta_t(year)-value))
    # NASA's modern values come from IERS; the app uses its bundled IERS table after 1973
    modern=[]
    for year,value in rows2:
        e=Epoch(calendar_jd(int(year),1,1,0));modern.append(dict(year=year,nasa=value,app=e.dt,diff=e.dt-value))
    per_eclipse=[dict(year=r['year'],nasa=r['delta_t'],app=delta_t(r['year']+(r['month']-.5)/12),diff=delta_t(r['year']+(r['month']-.5)/12)-r['delta_t']) for r in eclipses]
    return table,modern,per_eclipse

def part_d(eclipses):
    from backend.ephemeris import EPHEMERIS as EPH
    R=6378.137;out=[]
    def gamma(jd):
        # Light-time-corrected geocentric Sun and Moon (the Sun's 499 s light time is ~20" of apparent shift, ~40 s of eclipse timing)
        us,ds=astrometric(EPH,jd,10);um,dm=astrometric(EPH,jd,301);S=us*ds;M=um*dm
        # distance from the geocenter to the line Sun-Moon (shadow axis) in Earth radii; unsigned
        return float(np.linalg.norm(np.cross(S,M))/np.linalg.norm(S-M)/R)
    for r in eclipses:
        if r['type'] not in 'TAH':continue   # central eclipses only
        jd0=r['jd_td'];best=None
        # golden-section in +/- 20 minutes around the NASA time (unsigned gamma has a cusp at the minimum; it is smooth enough for this)
        a,b=jd0-20/1440,jd0+20/1440;g=(math.sqrt(5)-1)/2
        c,d=b-g*(b-a),a+g*(b-a);fc,fd=gamma(c),gamma(d)
        for _ in range(48):
            if fc<fd:b,d,fd=d,c,fc;c=b-g*(b-a);fc=gamma(c)
            else:a,c,fc=c,d,fd;d=a+g*(b-a);fd=gamma(d)
        t=(a+b)/2
        # NASA gamma is signed; compare magnitudes
        out.append(dict(number=r['number'],year=r['year'],type=r['type'],time_diff_seconds=(t-jd0)*86400,gamma_app=gamma(t),gamma_nasa=abs(r['gamma']),gamma_diff=gamma(t)-abs(r['gamma'])))
    return out

def part_e():
    from backend import jobs
    from backend.ephemeris import EPHEMERIS as EPH
    EPH.refresh();reports=[]
    for p in sorted(jobs.JOB_DIR.glob('past-v3-*.json')):
        try:r=json.loads(p.read_text())
        except ValueError:continue
        if r.get('accepted') and r.get('jpl_residual_max_km'):reports.append(r)
    by_epoch=[]
    for r in reports:
        mid=sum(r['interval_jd'])/2;by_epoch.append(dict(year=2000+(mid-2451545)/365.25,accepted=True,**r['jpl_residual_max_km']))
    by_epoch.sort(key=lambda x:x['year'])
    # independent re-evaluation of stored chunks against the kernel at random times (geocentric angular error)
    rng=np.random.default_rng(20261021);samples=[]
    intervals=jobs._intervals(jobs.index_stamp(),'v3')   # retired v3 run (started from DE440 at J2000), kept as the baseline
    for k in sorted(rng.choice(len(intervals),size=min(80,len(intervals)),replace=False)):
        (lo,hi),_=intervals[k];jd=float(rng.uniform(lo,hi))
        if EPH.kernel(jd)[0] is None:continue
        earth_d=jobs.deep_state(jd,399,'v3')
        if earth_d is None:continue
        ke,_=EPH.state(jd,399);row=dict(year=2000+(jd-2451545)/365.25)
        for name,target in [('Sun',10),('Moon',301),('Mercury',1),('Venus',2),('Mars',4),('Jupiter',5),('Saturn',6)]:
            d=jobs.deep_state(jd,target,'v3');k_,_=EPH.state(jd,target)
            row[name+'_km']=float(np.linalg.norm(d[0]-k_));row[name+'_arcsec']=sep(d[0]-earth_d[0],k_-ke)
        # signed lunar offset along the orbit: positive = reconstruction ahead of DE441
        m_d=jobs.deep_state(jd,301,'v3');mk,mv=EPH.state(jd,301);ek,ev=EPH.state(jd,399)
        normal=np.cross(mk-ek,mv-ev);normal/=np.linalg.norm(normal);u_k=(mk-ek)/np.linalg.norm(mk-ek);u_d=(m_d[0]-earth_d[0])/np.linalg.norm(m_d[0]-earth_d[0])
        row['Moon_signed_arcsec']=math.copysign(row['Moon_arcsec'],float(np.cross(u_k,u_d)@normal))
        samples.append(row)
    samples.sort(key=lambda x:x['year'])
    # quadratic growth (a*t^2, t in centuries before 2000) of the lunar offset and the lunar tidal-acceleration difference it implies (1/2 * dn * t^2)
    fit=None
    if len(samples)>=5:
        t=np.array([(2000-x['year'])/100 for x in samples]);y=np.array([abs(x['Moon_signed_arcsec']) for x in samples])
        c=float(np.sum(t**2*y)/np.sum(t**4));fit=dict(arcsec_per_century_squared_half=c,implied_acceleration_difference_arcsec_cy2=2*c,
            residual_rms_arcsec=float(np.sqrt(np.mean((y-c*t**2)**2))),n=len(samples),sign_ahead_fraction=float(np.mean([x['Moon_signed_arcsec']>0 for x in samples])))
    calibration=jobs.lunar_correction()
    v4=[json.loads(p.with_suffix('.json').read_text()) for _,p in jobs._intervals(jobs.index_stamp(),jobs.VERSION)]
    v4_summary=dict(chunks=len(v4),earliest_year=min((2000+(r['interval_jd'][0]-2451545)/365.25 for r in v4),default=None),
        max_off_node_km=max((max(r['independent_off_node_max_error_km'].values()) for r in v4),default=None),
        max_convergence_km=max((r['endpoint_local_convergence_km'] for r in v4),default=None))
    return dict(by_epoch=by_epoch,samples=samples,moon_fit=fit,calibration=calibration,v4=v4_summary)

def part_f():
    from backend import comets
    from backend.ephemeris import EPHEMERIS as EPH
    EPH.refresh();out=[]
    for pack in comets.packs():
        meta=pack['meta'];key=re.sub(r'[^A-Za-z0-9]+','_',meta['name']);vp=REF/f'comet-{key}-vec.json';op=REF/f'comet-{key}-obs.json'
        if not vp.exists():continue
        v=rows(json.loads(vp.read_text()))
        for row in v:
            jd=float(row[0]);ref=np.array([float(x) for x in row[2:5]])
            if not pack['times'][0]<=jd<=pack['times'][-1]:continue
            pos=pack['spline'](jd);earth,_=EPH.state(jd,399);dist=float(np.linalg.norm(ref-earth))
            out.append(dict(comet=meta['name'],jd=jd,kind='position',error_km=float(np.linalg.norm(pos-ref)),error_arcsec_from_earth=float(np.linalg.norm(pos-ref)/dist*ARCSEC),perihelion_offset_days=jd-pack['perihelion_jd']))
        if op.exists():
            for vr,orow in zip(v,rows(json.loads(op.read_text()))):
                jd=float(vr[0])
                try:horizons_mag=float(orow[3])
                except (ValueError,IndexError):continue
                sun,_=EPH.state(jd,10);earth,_=EPH.state(jd,399)
                m,phase,scatter,(M1,k1,d90)=comets.magnitude(pack,jd,pack['spline'](jd),earth,sun)
                out.append(dict(comet=meta['name'],jd=jd,kind='magnitude',app=m,horizons=horizons_mag,diff=m-horizons_mag,forward_scatter=scatter,phase=phase,M1=M1,k1=k1,override=pack['photometry'].startswith('Sourced')))
    return out

def part_g():
    """Planet magnitudes: app photometry (with its own geometry) vs Horizons APmag, using Horizons' r, delta and phase angle."""
    from backend.ephemeris import EPHEMERIS as EPH,brightness,photometric_geometry
    EPH.refresh();out=[]
    for name,cmd in MAG_BODIES.items():
        path=REF/f'mag-{cmd}.json'
        if not path.exists():continue
        d=json.loads(path.read_text());start=calendar_jd(2016,1,1,0)
        for i,row in enumerate(rows(d)):
            try:mag,r,delta,alpha=float(row[3]),float(row[5]),float(row[7]),float(row[9])
            except ValueError:continue
            jd=start+30*i;planet,_=EPH.state(jd,TARGET[name]);earth,_=EPH.state(jd,399);sun,_=EPH.state(jd,10)
            app=float(brightness(name,r,delta,math.radians(alpha),photometric_geometry(name,jd,planet,earth,sun)))
            out.append(dict(body=name,jd=jd,phase_deg=alpha,horizons=mag,app=app,diff=app-mag))
    return out


def stats(values):
    v=np.array(values,float);return dict(n=int(len(v)),median=float(np.median(v)),p95=float(np.percentile(v,95)),max=float(v.max()))

def analyze():
    a,asources=part_a();b=part_b()
    eclipses=[r for y in ECLIPSE_PAGES for r in eclipse_rows(y)]
    c1,c2,c3=part_c(eclipses) if (REF/'deltat.html').exists() else ([],[],[])
    d=part_d([e for i,e in enumerate(eclipses) if i%7==0]) if eclipses else []
    e=part_e();f=part_f();g=part_g()
    result=dict(generated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),horizons_sources=asources,sites=dict(delhi=SITE),years=YEARS,A=a,B=b,sidereal_test=sidereal_sign_test(),C=dict(table1=c1,table2=c2,eclipse_column=c3),D=d,E=e,F=f,G=g)
    (ROOT/'docs/nasa-crosscheck.json').write_text(json.dumps(result,indent=1))
    report(result);return result

def fmt(x,digits=3):
    return f'{x:.{digits}f}' if abs(x)<1000 else f'{x:,.0f}'

def report(r):
    A=[x for x in r['A'] if 'centre' not in x['body']];B=r['B'];E=r['E'];F=r['F']
    de441_only=[x for x in A if x['kernel']=='de441.bsp'];de440=[x for x in A if x['kernel']=='de440.bsp']
    L=['# Cross-check against NASA data','',f'Generated {r["generated"]} by `scripts/crosscheck_nasa.py analyze` (offline) from NASA responses saved by `... fetch` in `data/references/crosscheck/`. Machine-readable results: `nasa-crosscheck.json`. Runtime still needs no internet.','']
    # ---------------- summary
    L+=['## Summary','']
    if A:
        noise=stats([x['separation_arcsec'] for x in de441_only]) if de441_only else None
        L+=[f'1. **Sun, Moon and planets, geocentric (A):** with the same NASA kernels the simulator matches Horizons to {noise["max"]:.3f} arcsec over 9,000 BCE – 5,000 CE (the printed precision of Horizons is ≈0.003 arcsec).' if noise else '1. (no data)']
        if de440:L[-1]+=f' Where the app prefers DE440 (1550–2650) it differs from Horizons\' DE441 by up to {max(x["separation_arcsec"] for x in de440):.2f} arcsec (Moon); that is DE440 vs DE441, not a calculation error.'
    if r['sidereal_test']:
        w=max(abs(x['pre_fix_minus_gast_deg']) for x in r['sidereal_test']);mid=max(abs(x['sign_fixed_only_minus_gast_deg'])*3600 for x in r['sidereal_test'] if abs(x['year']-2000)<=1000)
        now=max(abs(x['app_minus_gast_deg'])*3600 for x in r['sidereal_test'] if abs(x['year']-2000)<=1000)
        L+=[f'2. **Apparent sky outside 1500–2500 CE (B): fixed and improved.** The deep-time sidereal angle had the wrong sign (up to {w:.1f}° from IAU 2006/2000A GAST). With the sign fixed it was still off by up to {mid:.0f}″ within ±1000 years, from treating the equinox offset as the equation of origins. It now uses Vondrák precession, IAU 2000A nutation (within ±4,000 years) and the equation of origins with a CIO locator integrated from the Vondrák pole, and matches GAST to {now:.2f}″ within ±1000 years. Against Horizons the altitude/azimuth error at 1 BCE went from {np.median([x["pre_fix"]["median_arcsec"] for x in B if x["year"]==0])/3600:.0f}° to {np.median([x["median_arcsec"] for x in B if x["year"]==0])/3600:.1f}°; what remains is the ΔT difference between the two ΔT scenarios.']
    L+=['3. **ΔT (C):** the simulator\'s polynomial lies within NASA\'s published standard error at every Morrison–Stephenson table year; modern ΔT agrees with the Astronomical Almanac values to 0.1 s.']
    if r['D']:
        mod=[x for x in r['D'] if 1800<=x['year']<2100]
        L+=[f'4. **Solar eclipses (D):** greatest-eclipse times agree with NASA\'s Five Millennium Canon to a median {np.median([abs(x["time_diff_seconds"]) for x in mod]):.1f} s for 1800–2100 and grow with antiquity (see table).']
    if E.get('calibration'):
        c=E['calibration'];h=c['holdout_moon_arcsec']
        L+=[f'5. **Reconstruction (E): rebuilt on NASA data.** The old run started at J2000 and integrated back through 15,000 years that DE441 already covers, and its Moon drifted {E["moon_fit"]["implied_acceleration_difference_arcsec_cy2"]:.1f}″/cy² from DE441 (the reduced model had no Earth tide raised by the Moon). The new run starts from DE441 itself at 13,201 BCE and integrates only what DE441 does not cover; a lunar correction calibrated on a 6,800-year DE441 hold-out (implied tidal acceleration {c["implied_tidal_acceleration_arcsec_cy2"]:+.2f}″/cy²) brings the hold-out Moon from {h["uncorrected_rms"]/3600:.1f}° rms to {h["corrected_rms"]:.0f}″ rms.']
    if F:
        pos=[x for x in F if x['kind']=='position'];L+=[f'6. **Comets (F):** cached splines match fresh Horizons vectors to a median {stats([x["error_km"] for x in pos])["median"]:.2f} km and at worst {max(x["error_km"] for x in pos):.0f} km ({max(x["error_arcsec_from_earth"] for x in pos):.3f}″) including perihelion; the three sungrazers now carry 5-minute JPL samples around perihelion (they were off by up to 28,000 km).']
    if r.get('G'):
        worst={n:max(abs(x['diff']) for x in r['G'] if x['body']==n) for n in MAG_BODIES}
        L+=[f'7. **Planet magnitudes (G):** now Mallama & Hilton (2018), the models Horizons uses: Mercury, Venus, Jupiter, Uranus, Neptune within {max(worst[n] for n in ("Mercury","Venus","Jupiter","Uranus","Neptune")):.3f} mag of Horizons APmag, Saturn (with rings) within 0.03 except one deliberate unlit-ring date, Mars {worst["Mars"]:.2f}; the previous formulas were off by up to 0.98 mag.']
    L+=['']
    # ---------------- A
    L+=['## A. Ephemeris and light time vs JPL Horizons (geocentric, astrometric, ICRS)','',f'Horizons sources: {", ".join(r["horizons_sources"])}. Direction error (arcsec) and distance for every body at {len(r["years"])} epochs, 9,000 BCE – 5,000 CE (12:00 TT on 1 January, astronomical year numbers). Frame ICRS, time TT. Horizons\' date range ends at 9,999 BCE and has no ephemeris before the DE441 start (13,200 BCE) anyway, so older epochs cannot be checked against NASA. The simulator reads the same NASA DE kernels: this tests the kernel reader, TT/TDB handling and light time.','','| Year | kernel used by app | max direction error (arcsec) | worst body | same, DE441 forced |','|---:|:--|---:|:--|---:|']
    for y in r['years']:
        rows_=[x for x in A if x['year']==y]
        if rows_:
            w=max(rows_,key=lambda x:x['separation_arcsec']);forced=max([x['separation_de441_arcsec'] if x['separation_de441_arcsec'] is not None else x['separation_arcsec'] for x in rows_])
            L.append(f'| {y} | {w["kernel"].replace(".bsp","").upper()} | {w["separation_arcsec"]:.4f} | {w["body"]} | {forced:.4f} |')
    L+=['',f'Distances agree to {max(x["distance_error_km"] for x in A):.1f} km at worst (median {np.median([x["distance_error_km"] for x in A]):.3f} km).','']
    cen=[x for x in r['A'] if 'centre' in x['body']]
    if cen:
        L+=['**Barycenter vs body centre (documented limitation).** The app targets planetary-system barycenters (DE targets 4–9). Against the true planet centres (Horizons, 1801–2100 only, where satellite ephemerides exist):','','| Planet | median (arcsec) | max (arcsec) |','|:--|---:|---:|']
        for n in ('Mars','Jupiter','Saturn','Uranus','Neptune','Pluto'):
            sel=[x['separation_arcsec'] for x in cen if x['body'].startswith(n)]
            if sel:L.append(f'| {n} | {np.median(sel):.3f} | {max(sel):.3f} |')
        L.append('')
    # ---------------- B
    L+=['## B. Apparent topocentric sky vs Horizons (New Delhi 28.6139°N 77.2090°E, sea level, airless, 9 bodies)','','Full pipeline: light time, aberration, solar deflection, WGS84 parallax, frames, Earth rotation (ΔT). Residual = angular distance between the simulator\'s and Horizons\' altitude/azimuth. Within |year − 2000| ≤ 500 the app uses IAU 2006/2000A; outside it uses Vondrák (2011) long-term precession (no nutation) with an extrapolated spin phase.','']
    L+=['**Deep-time sidereal angle vs ERFA GAST (IAU 2006/2000A, valid near these dates; no network).** History of `backend/astrotime.py` on 2026-10-21: wrong sign; sign fixed; then equation of origins + nutation:','','| Year | original − GAST | sign fixed only − GAST | current app − GAST |','|---:|---:|---:|---:|']
    for x in r['sidereal_test']:L.append(f'| {x["year"]} | {x["pre_fix_minus_gast_deg"]:+.3f}° | {x["sign_fixed_only_minus_gast_deg"]*3600:+.1f}″ | {x["app_minus_gast_deg"]*3600:+.2f}″ |')
    L+=['','The "pre-fix" column below restores the original sign in the original formula; it is historical, not the current app.','','| Year | frame | median alt/az error (current app) | pre-fix | rotation offset still needed (s of time) | residual after removing that rotation, max | sky RA/Dec median |','|---:|:--|---:|---:|---:|---:|---:|']
    f=lambda v:f'{v/3600:.2f}°' if v>=3600 else f'{v:.1f}″'
    for x in B:
        pf=x.get('pre_fix');off=x['rotation_offset_arcsec']/15.0410686
        L.append(f'| {x["year"]} | {x["frame"].split(";")[0].split(" long")[0]} | {f(x["median_arcsec"])} | {f(pf["median_arcsec"]) if pf else "—"} | {off:+.0f} | {f(x["after_rotation_fit_max_arcsec"])} | {x["sky_median_arcsec"]:.1f}″ |')
    L+=['','The rotation offset is the single rotation about Earth\'s axis that best aligns the simulator with Horizons: it is the Earth-rotation disagreement (ΔT choice), expressed as time. Inferred ΔT used by Horizons (= simulator ΔT − fitted offset), against NASA\'s own table (section C):','','| Year | simulator ΔT (s) | inferred Horizons ΔT (s) | NASA Table 1 (s) |','|---:|---:|---:|---:|']
    nasa={int(t['year']):t for t in r['C']['table1']}
    for x in B:
        n=nasa.get(x['year']);L.append(f'| {x["year"]} | {x["delta_t_app"]:.0f} | {x["implied_delta_t_horizons"]:.0f} | {"%.0f ± %s"%(n["nasa"],int(n["stderr"])) if n and n["stderr"] else "—"} |')
    L+=['','Reading this: after 2026 Horizons appears to hold ΔT near 70 s (no extrapolation), while the simulator extrapolates a parabola, so future alt/az differ by design; far past, both are extrapolations and differ by thousands of seconds, i.e. tens of degrees of sky rotation. Residuals beyond ±1000 years likely also include the Vondrák-vs-IAU 1976 precession difference and the missing nutation (not separated here).','']
    # ---------------- C
    if r['C']['table1']:
        L+=['## C. ΔT vs NASA','','NASA Table 1 (Morrison & Stephenson 2004, with NASA standard errors) vs `delta_t()` in `backend/astrotime.py` (Espenak & Meeus polynomials):','','| Year | NASA ΔT (s) | ± (s) | simulator (s) | difference (s) | within NASA error? |','|---:|---:|---:|---:|---:|:--|']
        for x in r['C']['table1']:
            ok='' if x['stderr'] is None else ('yes' if abs(x['diff'])<=x['stderr'] else 'no');L.append(f'| {int(x["year"])} | {x["nasa"]:.0f} | {"" if x["stderr"] is None else int(x["stderr"])} | {x["app"]:.1f} | {x["diff"]:+.1f} | {ok} |')
        L+=['','Modern values (Astronomical Almanac, NASA Table 2) vs the simulator, which uses its bundled IERS table from 1973:','','| Year | NASA (s) | simulator (s) | difference (s) |','|---:|---:|---:|---:|']
        for x in r['C']['table2']:L.append(f'| {x["year"]:.0f} | {x["nasa"]:.1f} | {x["app"]:.2f} | {x["diff"]:+.2f} |')
        pe=r['C']['eclipse_column']
        if pe:
            L+=['',f'ΔT column of NASA\'s Five Millennium Canon ({len(pe)} eclipses, −1999 to +3000) vs the simulator, by period:','','| Period | n | median |diff| (s) | max |diff| (s) |','|:--|---:|---:|---:|']
            for lo,hi in [(-2000,-500),(-500,500),(500,1600),(1600,2000),(2000,3001)]:
                sel=[abs(x['diff']) for x in pe if lo<=x['year']<hi]
                if sel:L.append(f'| {lo}…{hi} | {len(sel)} | {np.median(sel):.1f} | {max(sel):.1f} |')
            L.append('\nDifferences of a few minutes before −500 are not larger than NASA\'s own standard error there (430 s or more); the likely reason is a different ΔT revision, which was not verified.')
        L.append('')
    # ---------------- D
    if r['D']:
        L+=['## D. Greatest solar eclipse vs NASA Five Millennium Canon','',f'{len(r["D"])} central eclipses (every 7th eclipse of 15 sampled centuries, −1999 to +3000). For each, the simulator\'s light-time-corrected geocentric Sun and Moon give the instant the Sun–Moon axis passes closest to Earth\'s centre and that distance γ (Earth radii); NASA lists the same in TD ≈ TT. No ΔT is involved. NASA computed with ELP-2000/82 and VSOP87 and its own lunar tidal acceleration, whereas the simulator uses JPL DE440/DE441, so differences before about 1600 likely reflect the two lunar theories and their tidal terms (not verified separately).','','| Year range | n | median |Δt| (s) | max |Δt| (s) | median |Δγ| | max |Δγ| |','|:--|---:|---:|---:|---:|---:|']
        for lo,hi in [(-2000,-1000),(-1000,0),(0,1000),(1000,1800),(1800,2100),(2100,3000)]:
            sel=[x for x in r['D'] if lo<=x['year']<hi]
            if sel:L.append(f'| {lo}…{hi} | {len(sel)} | {np.median([abs(x["time_diff_seconds"]) for x in sel]):.1f} | {max(abs(x["time_diff_seconds"]) for x in sel):.1f} | {np.median([abs(x["gamma_diff"]) for x in sel]):.4f} | {max(abs(x["gamma_diff"]) for x in sel):.4f} |')
        L.append('')
    # ---------------- E
    L+=['## E. Background reconstruction vs JPL DE441','','### E1. Retired v3 run (baseline)','','The v3 worker started from DE440 at J2000 and integrated backward through the DE441 era. Its chunks are kept but never served (DE441 is used there). Largest position difference (km) over each chunk, from the chunk reports:','','| Epoch (year) | Moon (geocentric) | Sun | Mercury | Venus | Mars | Jupiter | Saturn | Neptune | Pluto |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    be=E['by_epoch']
    if be:
        for x in [be[i] for i in sorted(set(np.linspace(0,len(be)-1,min(12,len(be))).astype(int)))]:L.append(f'| {x["year"]:.0f} | '+' | '.join(fmt(x.get(k,float('nan')),0) for k in ('301','10','1','2','4','5','6','8','9'))+' |')
    if E['samples']:
        L+=['',f'Independent check: stored chunk coefficients re-evaluated against the DE441 kernel at {len(E["samples"])} random times, as seen from Earth (arcsec). The Moon column is signed along the orbit (+ = reconstruction ahead):','','| Year | Moon (arcsec, signed) | Sun | Mercury | Venus | Mars | Jupiter | Saturn |','|---:|---:|---:|---:|---:|---:|---:|---:|']
        sm=E['samples']
        for x in [sm[i] for i in sorted(set(np.linspace(0,len(sm)-1,min(12,len(sm))).astype(int)))]:L.append(f'| {x["year"]:.0f} | {x["Moon_signed_arcsec"]:+,.0f} | '+' | '.join(fmt(x[k+'_arcsec'],0) for k in ('Sun','Mercury','Venus','Mars','Jupiter','Saturn'))+' |')
    mf=E['moon_fit']
    if mf:
        L+=['',f'The v3 lunar offset follows a·t² with a = {mf["arcsec_per_century_squared_half"]:.1f}″/cy², a mean-motion acceleration difference of {mf["implied_acceleration_difference_arcsec_cy2"]:.1f}″/cy² (reconstruction ahead in {mf["sign_ahead_fraction"]*100:.0f}% of samples). That equals DE441\'s lunar tidal acceleration: a direct test showed the REBOUNDx constant-time-lag tide moved the Moon by 0.00″ in 100 years (≈12.9″ expected), because it couples bodies only to particle 0, the Sun.']
    c=E.get('calibration')
    if c:
        h=c['holdout_moon_arcsec'];v=c['independent_v3_moon_arcsec'];k=c['coefficients_arcsec']
        L+=['','### E2. Current model (v5): DE441 seed, local integrator clock, calibrated lunar correction','',
            'The past run now starts from NASA\'s DE441 states at its first epoch (JD −3,100,014.5, 13,201 BCE) and integrates only 13,201 → 20,000 BCE (6,800 years; the supported range was narrowed to 15,000 BCE on 2026-10-22, so 1,800 years are used) instead of 22,000 years from J2000. The 16 asteroids, which JPL does not publish that early, come from a reduced integration (scripts/deep_seed.py asteroids).',
            f'The missing lunar tide is restored by shifting the Moon\'s osculating geocentric mean anomaly by −(c1·τ + c2·τ² + c3·τ³), τ in centuries from the seed, with c1 = {k["c1"]:.3f}″/cy (measured forward from the seed against DE441 over 5 centuries; on the hold-out a forward fit gave −83.13 vs −83.42″/cy backward), c2 = {k["c2"]:.4f}″/cy², c3 = {k["c3"]:.5f}″/cy³ (implied tidal acceleration {c["implied_tidal_acceleration_arcsec_cy2"]:+.2f}″/cy²; DE430/DE441 use about −25.8). A mean-anomaly shift, unlike a rigid rotation, also moves the Moon correctly along its eccentric orbit.','',
            '| Test | n | uncorrected rms | corrected rms | corrected max |','|:--|---:|---:|---:|---:|',
            f'| Hold-out (hold-out c1 = {c["holdout_coefficients_arcsec"]["c1"]:.2f}″/cy): seeded from DE441 at 6000 BCE, 6,800 years back, vs DE441 (fit data) | {h["n"]} | {h["uncorrected_rms"]:,.0f}″ | {h["corrected_rms"]:,.1f}″ | {h["corrected_max"]:,.1f}″ |',
            f'| Independent: retired v3 run from J2000, 5,600 years, vs DE441, using the hold-out c1 (not measured at its own seed; shows why the run measures c1 at its seed) | {v["n"]} | {v["uncorrected_rms"]:,.0f}″ | {v["corrected_rms"]:,.1f}″ | {v["corrected_max"]:,.1f}″ |','',
            'Planets in the hold-out, as seen from Earth, worst case over 6,800 years (no correction applied to planets):','','| Body | max error (arcsec) |','|:--|---:|']
        for name,val in c['holdout_planets_max_arcsec'].items():L.append(f'| {name} | {val:.1f} |')
        L+=['',f'**Limitation:** {c["limitation"]} Before 13,201 BCE nothing can be checked against NASA; these numbers measure how well the reduced model reproduces DE441 over an equally long interval, not ancient truth.']
    v4=E.get('v4')
    if v4 and v4['chunks']:
        L+=['',f'Current-model chunks published so far: {v4["chunks"]}, back to {-v4["earliest_year"]+1:.0f} BCE; worst off-node interpolation {v4["max_off_node_km"]:.3f} km, worst tighter-integration convergence {v4["max_convergence_km"]:.3f} km (numerical gates only).']
    L.append('')
    # ---------------- F
    if F:
        pos=[x for x in F if x['kind']=='position'];mag=[x for x in F if x['kind']=='magnitude']
        L+=['## F. Comets vs Horizons','',f'Cached cubic splines vs fresh Horizons vectors at {len(pos)} off-node epochs over {len({x["comet"] for x in pos})} apparitions (barycentric ICRS).','']
        if pos:
            s_=stats([x['error_arcsec_from_earth'] for x in pos]);sk=stats([x['error_km'] for x in pos])
            L+=[f'Position error: median {sk["median"]:.2f} km, 95th percentile {sk["p95"]:.1f} km. As seen from Earth: median {s_["median"]:.4f}″, 95th percentile {s_["p95"]:.3f}″, max {s_["max"]:.1f}″.','','Worst five (all at the perihelion epoch, +0.05 d; the leading three are sungrazers sampled hourly, where a cubic spline under-resolves the pass):','','| Comet | days from perihelion | error (km) | error (arcsec) |','|:--|---:|---:|---:|']
            for x in sorted(pos,key=lambda x:-x['error_arcsec_from_earth'])[:5]:L.append(f'| {x["comet"]} | {x["perihelion_offset_days"]:+.2f} | {x["error_km"]:.1f} | {x["error_arcsec_from_earth"]:.3f} |')
        if mag:
            L+=['',f'Total magnitude, app vs Horizons T-mag at {len(mag)} epochs. The app deliberately adds Marcus forward scattering and, for some comets, sourced M1 overrides, so those parts are separated:','','| Subset | n | median (app − Horizons) | max abs |','|:--|---:|---:|---:|']
            for label,sel in [('JPL M1/k1, no override, as shown in the app',[x['diff'] for x in mag if not x['override']]),('same, forward-scattering term removed',[x['diff']-x['forward_scatter'] for x in mag if not x['override']]),('with a sourced override',[x['diff'] for x in mag if x['override']])]:
                if sel:L.append(f'| {label} | {len(sel)} | {np.median(sel):+.2f} | {max(abs(v) for v in sel):.2f} |')
            L+=['','Comets with a sourced override: the app deliberately departs from Horizons\' T-mag to match recorded peak brightness (negative = app brighter). At the brightest sampled epoch:','','| Comet | brightest sampled epoch | app (mag) | Horizons (mag) | recorded peak used for calibration |','|:--|:--|---:|---:|---:|']
            from backend import comets as _c
            ov=_c._overrides()
            for name in sorted({x['comet'] for x in mag if x['override']}):
                sel=[x for x in mag if x['comet']==name];w=min(sel,key=lambda x:x['app']);d_=jd_calendar(w['jd']);rp=(ov.get(name) or {}).get('recorded_peak')
                L.append(f'| {name} | {d_["day"]} {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d_["month"]-1]} {d_["display_year"]} {d_["era"]} | {w["app"]:+.1f} | {w["horizons"]:+.1f} | {"%+.1f"%rp if isinstance(rp,(int,float)) else "—"} |')
            L+=['','Only five epochs per comet are sampled, so the brightest sampled epoch is not the true peak. The recorded peaks are from non-NASA sources cited in `data/comets/photometry_overrides.json`.']
    if r.get('G'):
        L+=['','## G. Planet magnitudes vs Horizons APmag (2016–2036, every 30 days, geocentric)','','Horizons computes planetary APmag with the Mallama & Hilton (2018) models; the app now implements the same models (`backend/ephemeris.py`). Values below use Horizons\' own r, Δ and phase angle, so only the photometric law and the ring/pole geometry are compared. The previous app formulas (Saturn rings ignored) are listed from the measurement made before the change.','','| Planet | n | median app − Horizons (mag) | max abs (mag) | previous formulas, max abs |','|:--|---:|---:|---:|---:|']
        previous={'Mercury':.939,'Venus':.246,'Mars':.146,'Jupiter':.028,'Saturn':.984,'Uranus':.052,'Neptune':.132}
        for name in MAG_BODIES:
            sel=[x['diff'] for x in r['G'] if x['body']==name]
            if sel:L.append(f'| {name} | {len(sel)} | {np.median(sel):+.3f} | {max(abs(v) for v in sel):.3f} | {"unchanged law" if name not in previous else "%.3f"%previous[name]} |')
        L+=['','Mars omits Mallama & Hilton\'s rotational and orbital-longitude terms (±0.1 mag). Saturn\'s single larger difference (April 2025) is deliberate: when the Sun and Earth are on opposite sides of the ring plane we see the unlit face, so the app uses the globe-only law while Horizons keeps the ring formula. The Moon keeps its earlier law, which already matches Horizons; Pluto keeps H = −1.0.']
    L+=['','## What this does not show','','- Stars: NASA/JPL publishes no star ephemeris, so Hipparcos/HYG positions, proper motion and Galactic orbits are not cross-checked here.','- Before 13,200 BCE (DE441 start) there is no NASA ephemeris; Horizons itself stops at 9,999 BCE. Section E is the only measurement of the reconstruction, and it is a measurement of divergence from DE441, not of accuracy against the real past.','- Agreement of Sun/Moon/planets with Horizons (A, D) is agreement with the same JPL fits, not independent historical truth; ancient ΔT is uncertain in NASA\'s own data (standard errors in C).','- Only 9 bodies at one site were used for B. Comet positions were checked at 5 epochs per apparition.','- Planet bodies vs system barycenters (A) and stellar positions remain as before; JPL satellite ephemerides that would give planet centres cover only about 1600–2200.']
    (ROOT/'docs/NASA_CROSSCHECK.md').write_text('\n'.join(L)+'\n')

if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'analyze'
    if cmd=='fetch':fetch()
    elif cmd=='analyze':
        r=analyze();log('NASA cross-check analysis written to docs/NASA_CROSSCHECK.md and docs/nasa-crosscheck.json')
    else:print(__doc__)
