from .paths import ROOT,DATA
from .astrotime import Epoch,calendar_jd,jd_calendar,local_basis,MIN_YEAR,MAX_YEAR
from .sanskrit import SANSKRIT
from .ephemeris import EPHEMERIS,body_snapshot,AU
from .catalog import CATALOG,STAR_LIMIT
from . import jobs, frame_cache, comets
from fastapi import FastAPI,HTTPException,Query
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
import numpy as np
import json, math, time
from . import progress as calculation_progress
from functools import lru_cache
from datetime import datetime,timezone

app=FastAPI(title='Epoch offline astronomy',version='0.1.0')
class JobRequest(BaseModel):
    action:str='start'
    end_year:int=Field(MIN_YEAR,ge=MIN_YEAR,le=MAX_YEAR)
    chunk_years:float=Field(10,ge=.1,le=100)

@app.get('/api/health')
def health():return dict(status='ok',offline=True,version='0.1.0')
@app.get('/api/bootstrap')
def bootstrap():
    now=datetime.now(timezone.utc)
    jd=calendar_jd(now.year,now.month,now.day,now.hour+now.minute/60+now.second/3600)+69.184/86400
    EPHEMERIS.refresh();CATALOG.load()
    return dict(jd=jd,data_revision=frame_cache.data_revision(),locations=[dict(name=n,lat=a,lon=o) for n,a,o in [('Greenwich',51.4769,0),('Kolkata',22.5726,88.3639),('New Delhi',28.6139,77.209),('San Diego',32.7157,-117.1611),('Mauna Kea',19.8206,-155.4681),('Sydney',-33.8688,151.2093),('Cape Town',-33.9249,18.4241),('North Pole',90,0)]],
        kernels=list(EPHEMERIS.kernels),star_count=len(CATALOG.rows),range=[calendar_jd(MIN_YEAR),calendar_jd(MAX_YEAR,12,31)],catalog_note='Gaia DR3 + Hipparcos' if any('Gaia' in r['source'] for r in CATALOG.rows[:100]) else 'HYG/Hipparcos; Gaia installation may be pending')

def compute_snapshot(jd,lat,lon,elevation,dt,limit,progress=None,max_magnitude=12.,only_star=None,view='space',horizon_only=False):
    max_magnitude=min(max_magnitude,STAR_LIMIT) # Common star limit, including object-detail requests.
    started=time.perf_counter();timings={}
    if progress:progress(0,0,1,'Converting TT to TDB and modelled UT1; orienting Earth')
    epoch=Epoch(jd,dt);basis=local_basis(epoch,lat,lon)
    timings['time_and_frame_ms']=(time.perf_counter()-started)*1000;t0=time.perf_counter()
    if progress:progress(0,1,1,'Time scales and observer basis ready')
    available=True;message='';bodies=[];obs=np.zeros(3);ov=np.zeros(3)
    try:bodies,obs,ov=body_snapshot(epoch,basis,lat,lon,elevation,progress)
    except ValueError as e:available=False;message=str(e)
    for b in bodies:b.update(SANSKRIT.body_fields(b['id']))
    timings['solar_system_ms']=(time.perf_counter()-t0)*1000;t0=time.perf_counter()
    stellar_stats={}
    def publish_preview(stars):
        if not progress or not hasattr(progress,'preview'):return
        sun=next((b for b in bodies if b['name']=='Sun'),None)
        alt=sun.get('altitude_deg',-90) if sun else -90
        dayphase='Daylight' if alt>-.833 else 'Civil twilight' if alt>-6 else 'Nautical twilight' if alt>-12 else 'Astronomical twilight' if alt>-18 else 'Night'
        progress.preview(dict(jd=jd,date=epoch.calendar,time=epoch.metadata(),basis=basis.tolist(),bodies=bodies,stars=stars,comets=[],solar_system_available=available,coverage_message=message,source=EPHEMERIS.source(jd),day_phase=dayphase,stellar_dynamics='Bright-star preview; remaining selected stars are being prepared',star_count=len(CATALOG.rows),shown_stars=len(stars),limitations=[],preview=True,calculation=dict(timings_ms={'total_ms':(time.perf_counter()-started)*1000},time=epoch.metadata(),observer=dict(latitude_deg=lat,longitude_deg=lon,elevation_m=elevation,barycentric_position_km=obs.tolist(),barycentric_velocity_km_s=ov.tolist()),counts=dict(catalog=len(CATALOG.rows),stars=len(stars),solar_system=len(bodies),comets=0),basis=basis.tolist())))
    stars,dynamics=CATALOG.snapshot(epoch,basis,obs,ov,limit,progress,max_magnitude,publish_preview if not progress or getattr(progress,'include_preview',True) else None,stellar_stats,only_star,view,horizon_only)
    timings['stellar_ms']=(time.perf_counter()-t0)*1000;t0=time.perf_counter()
    if progress:progress(4,0,1,'Checking bounded comet apparitions and assembling response')
    comets=comet_snapshot(epoch,basis,obs) if available else []
    sun=next((b for b in bodies if b['name']=='Sun'),None)
    phase='unavailable'
    if sun:
        alt=sun['altitude_deg'];phase='Daylight' if alt>-.833 else 'Civil twilight' if alt>-6 else 'Nautical twilight' if alt>-12 else 'Astronomical twilight' if alt>-18 else 'Night'
    timings['comets_ms']=(time.perf_counter()-t0)*1000;timings['total_ms']=(time.perf_counter()-started)*1000
    return dict(stellar_work=stellar_stats,preview=False,calculation=dict(timings_ms=timings,time=epoch.metadata(),observer=dict(latitude_deg=lat,longitude_deg=lon,elevation_m=elevation,barycentric_position_km=obs.tolist(),barycentric_velocity_km_s=ov.tolist()),counts=dict(catalog=len(CATALOG.rows),stars=len(stars),solar_system=len(bodies),comets=len(comets)),basis=basis.tolist()),jd=jd,date=epoch.calendar,time=epoch.metadata(),basis=basis.tolist(),bodies=bodies,stars=stars,comets=comets,
        solar_system_available=available,coverage_message=message,source=EPHEMERIS.source(jd),day_phase=phase,
        stellar_dynamics=dynamics,star_count=len(CATALOG.rows),shown_stars=len(stars),
        star_fields=dict(frame='ground_direction: local east-north-up unit vector; direction: ICRS apparent; space_direction: ICRS heliocentric (space views only)',time_scale='TDB',units=dict(distance_pc='pc',magnitude='V for Hipparcos / G for Gaia',radius_km='km',angular_radius_deg='deg'),view=view,horizon_only=horizon_only,
            detail_note=f'Per-star source, measurement epoch, motion completeness and diameter provenance come from /api/object/<id>. All stars to the common magnitude limit {STAR_LIMIT} are included.'),
        comet_note='Comets are shown only inside individually cached JPL intervals. Missing objects are not extrapolated.',
        limitations=['Colors use measured color-index / blackbody approximations; calibrated spectra are not bundled.',
        'Brightness assumes constant stellar luminosity and extinction; unknown ancient variability is not reconstructed.',
        'Deep-time rotation, atmospheric conditions and Earth geography are assumed, not historical measurements.',
        'Planetary barycenters are used for giant-planet centers; Saturn ring photometry is approximate.'])

def snapshot_cached(jd,lat,lon,elevation,dt,limit,max_magnitude=12.,progress=None,view='space',horizon_only=False):
    inputs=(round(jd,8),float(lat),float(lon),float(elevation),float(dt),int(limit),float(min(max_magnitude,STAR_LIMIT)),view,bool(horizon_only))
    return frame_cache.get_or_compute(inputs,lambda:compute_snapshot(*inputs[:6],progress=progress,max_magnitude=inputs[6],view=view,horizon_only=bool(horizon_only)),progress)

def json_response(data):
    # Pre-serialized: FastAPI's generic encoder costs more than the star calculation for a full frame.
    return Response(content=json.dumps(data,separators=(',',':'),allow_nan=False),media_type='application/json')

@app.get('/api/snapshot')
def snapshot(jd:float,lat:float=Query(51.4769,ge=-90,le=90),lon:float=Query(0,ge=-180,le=180),elevation:float=Query(0,ge=-500,le=100000),dt:float=Query(0,ge=-1e10,le=1e10),limit:int=Query(9000,ge=100,le=30000),progress_id:str=Query('',max_length=100),max_magnitude:float=Query(12.,ge=-2,le=20),view:str=Query('space',pattern='^(ground|space)$'),horizon_only:bool=False,preview:bool=True):
    if not np.isfinite(jd) or not calendar_jd(MIN_YEAR)<=jd<=calendar_jd(MAX_YEAR,12,31)+.99999:raise HTTPException(422,'Date outside supported interval')
    if not progress_id:return json_response(snapshot_cached(jd,lat,lon,elevation,dt,limit,max_magnitude,view=view,horizon_only=horizon_only))
    update=calculation_progress.begin(progress_id);update.include_preview=preview
    try:
        result=snapshot_cached(jd,lat,lon,elevation,dt,limit,max_magnitude,update,view,horizon_only)
        calculation_progress.finish(progress_id,cached=result['playback_cache']['hit']);return json_response(result)
    except frame_cache.SupersededError as e:
        calculation_progress.finish(progress_id,str(e));raise HTTPException(409,str(e))
    except Exception as e:
        calculation_progress.finish(progress_id,str(e));raise

@app.get('/api/calendar')
def calendar(year:int,month:int=1,day:int=1,hour:float=0,system:str='gregorian'):
    if system not in ('gregorian','julian'):raise HTTPException(422,'Unknown calendar')
    try:jd=calendar_jd(year,month,day,hour,system);return dict(jd=jd,date=jd_calendar(jd,system))
    except ValueError as e:raise HTTPException(422,str(e))
@app.get('/api/date')
def date(jd:float,system:str='gregorian'):return jd_calendar(jd,system)
@app.get('/api/search')
def search(q:str=Query('',max_length=100),jd:float=2451545.):
    CATALOG.load();q=q.lower().strip()
    from .ephemeris import BODIES
    found=[dict(id=n,name=n,type='planet',**SANSKRIT.body_fields(n)) for n in BODIES if q in n.lower() or SANSKRIT.matches(n,q)]
    brightness=CATALOG.screen_magnitudes(Epoch(jd,0.).year);book=CATALOG.book_mask();named=SANSKRIT.named_ids()
    # Only stars that can be shown are searched (prominent at this epoch, or named in the book).
    for i in np.where((brightness<=STAR_LIMIT)|book)[0]:
        r=CATALOG.rows[i];english=SANSKRIT.english(r['id'],r['name'])
        if q in r['name'].lower() or q in r['id'].lower() or q in english.lower() or (r['id'] in named and SANSKRIT.matches(r['id'],q)):found.append(dict(id=r['id'],**SANSKRIT.fields(r['id'],r['name'],False),type='star',source=r['source'],magnitude=round(float(brightness[i]),2)))
    # Comets: matched by name or by the book's word for comet; only those inside their cached window at this date.
    found.extend(dict(id=c['id'],name=c['name'],type='comet',sanskrit_name=f"Dhūmaketu ({c['name']})",sanskrit_devanagari=f"धूमकेतु ({c['name']})") for c in comets.catalog()
                 if c['start_jd']<=jd<=c['end_jd'] and (q in c['name'].lower() or q in ('comet','dhumaketu','धूमकेतु')))
    found.sort(key=lambda f:(f['type']=='star',f.get('magnitude',0)))  # planets and comets first, then stars brightest first
    return found[:40] if q else []
@app.get('/api/object/{object_id:path}')
def object_detail(object_id:str,jd:float,lat:float=51.4769,lon:float=0,elevation:float=0,dt:float=0):
    s=compute_snapshot(jd,lat,lon,float(elevation),float(dt),1,max_magnitude=20.,only_star=object_id)
    target=next((r for r in s['bodies']+s['stars']+s['comets'] if r['id']==object_id),None)
    if not target:raise HTTPException(404,'Object not visible in the current catalog subset or unsupported at this epoch')
    if target.get('direction') is None:return dict(target,units='km physical radius; AU heliocentric position',frame='ICRS',time_scale='TDB',rise_set_note='Observer is on Earth; no Earth-center apparent sky direction is defined.')
    u=np.array(target['direction']);equ=Epoch(jd,dt).matrix@u
    target=dict(target,ra_deg=float(np.degrees(np.arctan2(equ[1],equ[0]))%360),dec_deg=float(np.degrees(np.arcsin(equ[2]))),frame='equator/equinox of date',units='degrees; AU or pc; magnitude',time_scale='TT input / TDB dynamics')
    alt=np.degrees(np.arcsin(np.clip(target['ground_direction'][2],-1,1))) if target.get('ground_direction') else None
    target['altitude_deg']=float(alt) if alt is not None else None
    # Bracket actual time-dependent topocentric rise and set rather than static hour-angle approximations.
    target['rise_set_note']='Rise/set uses a flat geometric horizon; refraction and terrain can shift observed events.'
    if s['time']['rotation_quality']=='assumed-rotation':
        target['rise_set_note']='Ancient/future local rise/set clock times are unsupported with assumed Earth rotation.'
        target['rise_jd_tt']=None;target['set_jd_tt']=None
    elif target.get('ground_direction'):
        dec=math.asin(np.clip(equ[2],-1,1));phi=math.radians(lat)
        cosh=-math.tan(phi)*math.tan(dec)
        if abs(cosh)>1:target['rise_set_note']='Circumpolar / never rises at this location (geometric approximation).'
        else:
            h=math.acos(cosh);lst=Epoch(jd,dt).sidereal+math.radians(lon);ra=math.atan2(equ[1],equ[0])
            target['rise_hours_ahead']=float(((ra-h-lst)%(2*math.pi))/(2*math.pi)*23.9344696)
            target['set_hours_ahead']=float(((ra+h-lst)%(2*math.pi))/(2*math.pi)*23.9344696)
            target['rise_set_note']='Approximate rise/set from fixed current declination; not event-grade predictions, especially for the Moon.'
    return target

@app.get('/api/coverage')
def coverage():
    EPHEMERIS.refresh()
    return dict(kernels=[dict(name=n,start_jd=min(s.start_jd for s in k.segments),end_jd=max(s.end_jd for s in k.segments)) for n,k in EPHEMERIS.kernels.items()],deep=jobs.coverage(),job=jobs.status(),manifest=json.loads((DATA/'manifest.json').read_text()) if (DATA/'manifest.json').exists() else {})
@app.get('/api/jobs')
def job_status():return jobs.status()
@app.post('/api/jobs')
def job_action(req:JobRequest):
    try:return jobs.request(req.action,req.end_year,req.chunk_years)
    except ValueError as e:raise HTTPException(422,str(e))

def comet_snapshot(epoch,basis,observer):return comets.snapshot(epoch,basis,observer)

@app.get('/api/comets')
def comet_list():
    return json_response(dict(comets=comets.catalog(),note='Only individually cached JPL Horizons apparitions are shown; nothing is extrapolated outside each interval. '+comets.TAIL_NOTE))

frontend=ROOT/'frontend/dist'
if frontend.exists():
    app.mount('/assets',StaticFiles(directory=frontend/'assets'),name='assets')
@app.get('/')
def index():
    if (frontend/'index.html').exists():return FileResponse(frontend/'index.html')
    return {'message':'Build frontend with npm run build --prefix frontend, then restart the server.'}

@app.get('/api/assets/{name}')
def asset(name:str):
    if name not in ('earth.jpg','moon.jpg'):raise HTTPException(404,'Unknown local asset')
    p=DATA/'assets'/name
    if not p.exists():raise HTTPException(404,'Asset not installed')
    return FileResponse(p)

@app.get('/api/constellations')
def constellations():
    # Selected modern Western asterisms (HIP identifiers); these are visual guides, not ancient cultural claims.
    return dict(lines=[[24436,25336],[25336,25930],[25930,26311],[26311,26727],[26727,27366],[27366,24436],[25930,24436],[26311,25336],
        [53910,54061],[54061,58001],[58001,59774],[59774,62956],[62956,65378],[65378,67301],[59774,54061],
        [11767,85822],[85822,82080],[82080,77055],[77055,79822],[79822,75097],[75097,72607],[72607,77055],
        [746,3179],[3179,4427],[4427,6686],[6686,8886],[91262,91971],[91971,92420],[92420,93194],[93194,92791],[92791,91971],
        [102098,100453],[100453,98110],[98110,95947],[100453,102488],[100453,97165],[97649,98036],[98036,97278],
        [80763,78401],[78401,78820],[80763,81266],[81266,82396],[82396,82514],[82514,82729],[82729,84143],[84143,86228],[86228,87073],[87073,86670],[86670,85927]],
        source='Hand-transcribed modern asterisms using Hipparcos identifiers; illustrative, not IAU boundaries')

@app.get('/api/trails')
@lru_cache(maxsize=8)
def trails(jd:float):
    from .ephemeris import BODIES
    periods={'Mercury':87.97,'Venus':224.7,'Earth':365.256,'Mars':686.98,'Jupiter':4332.6,'Saturn':10759.2,'Uranus':30688.5,'Neptune':60182.,'Pluto':90560.}
    out=[]
    for name,period in periods.items():
        positions=[]
        for t in np.linspace(jd-period/2,jd+period/2,160):
            try:
                p,_=EPHEMERIS.state(t,BODIES[name][0]);sun,_=EPHEMERIS.state(t,10);positions.append(((p-sun)/AU).tolist())
            except ValueError:break
        if len(positions)>2:out.append(dict(name=name,color=BODIES[name][3],positions=positions))
    return dict(trails=out,model='Ephemeris trajectory samples centered on the selected epoch; partial if coverage ends')

@app.get('/api/next-night')
def next_night(jd:float,lat:float=Query(51.4769,ge=-90,le=90),lon:float=Query(0,ge=-180,le=180)):
    from .ephemeris import apparent
    for t in np.arange(jd,jd+3,1/96):
        try:
            ep=Epoch(float(t));basis=local_basis(ep,lat,lon);earth,velocity=EPHEMERIS.state(ep.tdb1+ep.tdb2,399)
            sun,_,_=apparent(ep,earth+basis[2]*6378.137,velocity,10)
            alt=float(np.degrees(np.arcsin(np.clip((basis@sun)[2],-1,1))))
            if alt< -18:return dict(jd=float(t),note='Astronomical night: the Sun is more than 18° below your horizon. Clock times follow the selected Earth-rotation model.')
        except ValueError:raise HTTPException(422,'A planetary ephemeris is needed to find local night at this date.')
    return dict(jd=None,note='No astronomical night at this location in the next 72 hours. Try another date or location; atmosphere can be disabled to inspect stellar positions.')

@app.get('/api/calculation-progress/{identity}')
def calculation_state(identity:str):
    return calculation_progress.read(identity)


@app.get('/api/storage-coverage')
def storage_coverage():
    frames=frame_cache.statistics()
    for label in ('start','end'):
        jd=frames[label+'_jd'];frames[label+'_date']=jd_calendar(jd) if jd is not None else None
    intervals=sorted(r['interval_jd'] for r in jobs.coverage())
    merged=[]
    for a,b in intervals:
        if merged and a<=merged[-1][1]+1e-8:merged[-1][1]=max(merged[-1][1],b)
        else:merged.append([a,b])
    return dict(frames=frames,trajectories=dict(chunks=len(intervals),days=sum(b-a for a,b in merged),
        intervals=[dict(start_jd=a,end_jd=b,start_date=jd_calendar(a),end_date=jd_calendar(b)) for a,b in merged],
        note='Validated background reconstruction only; installed JPL ephemerides are additional coverage. Observer-specific sky frames may still need calculation.'))
