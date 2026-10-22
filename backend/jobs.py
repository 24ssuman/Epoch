"""Resumable, multirate reduced-model reconstructions. All data stays local."""
from .paths import ROOT,DATA,guard
from .astrotime import MIN_YEAR,MAX_YEAR
import json,time,threading,traceback,os,sys,subprocess
import numpy as np
from functools import lru_cache
JOB_DIR=DATA/'jobs';LOCK=threading.Lock()
IDS=[10,1,2,399,301,4,5,6,7,8,9]
GMS=[132712440041.279419,22031.868551,324858.592,398600.435507,4902.800118,42828.375816,126712764.100,37940584.8418,5794556.4,6836527.10058,975.5]
VERSION='v5';SCHEMA='epoch-deep-v5';MOON_FRACTION=GMS[4]/(GMS[3]+GMS[4])
# v5 (v4 plus a local clock): the past run starts from NASA JPL DE441 at its first epoch (only the interval DE441 does not cover is integrated) and
# applies a lunar mean-anomaly correction calibrated against DE441 (scripts/deep_seed.py). v3 files are retained, unused.
DE441_START_JD=-3100015.5;SEED_JD=DE441_START_JD+1.
CALIBRATION=DATA/'jobs'/'calibration'
# The integrator clock counts days from the seed (ORIGIN), not from J2000: at |t| ~ 5.5e6 days every exact stop at a
# sample time rounds t by ~1e-9 day, which made eps 1e-9 and 1e-11 runs diverge ~10x faster (measured 2026-10-22).
ORIGIN_JD=SEED_JD
# Body, maximum segment days, polynomial degree. EMB + geocentric Moon avoids
# storing the lunar-frequency Earth wobble in every planetary segment.
PACK_CONFIG=[(10,128,18),(1,32,18),(2,64,16),(3,64,16),(301,16,18),(4,128,16),(5,512,16),(6,1024,16),(7,2048,16),(8,4096,16),(9,4096,18)]
STATE={'status':'idle','message':'Deep-time reconstruction has not been started.','completed':0,'total':0}

def log(s):
    with (ROOT/'LOG.md').open('a') as f:f.write(f'\n- {time.strftime("%Y-%m-%d %H:%M:%S %z")}: {s}\n')

def save_state(**kw):
    STATE.update(kw,pid=os.getpid());JOB_DIR.mkdir(exist_ok=True)
    tmp=JOB_DIR/f'status-{os.getpid()}.tmp';tmp.write_text(json.dumps(STATE,indent=2));os.replace(tmp,JOB_DIR/'status.json')

def status():
    p=JOB_DIR/'status.json'
    if not p.exists():return dict(STATE)
    s=json.loads(p.read_text())
    if s['status']=='running':
        try:os.kill(s.get('pid',0),0)
        except (ProcessLookupError,PermissionError):s.update(status='interrupted',message='Worker stopped; resume from its retained checkpoint.')
    control=JOB_DIR/'control.json'
    if control.exists() and json.loads(control.read_text()).get('queue_future') and s.get('direction')=='past':s['queued_targets']=[MAX_YEAR]
    return s

def request(action='start',end_year=MIN_YEAR,chunk_years=10,direction='past'):
    with LOCK:
        JOB_DIR.mkdir(exist_ok=True)
        if action=='pause':
            control=JOB_DIR/'control.json';config=json.loads(control.read_text()) if control.exists() else {};config['pause_requested']=True;control.write_text(json.dumps(config))
            return dict(status(),message='Pause requested; finishing the current validated checkpoint.')
        if action not in ('start','resume'):raise ValueError('Unknown job action')
        if status().get('status')=='running':return status()
        if not MIN_YEAR<=end_year<=MAX_YEAR or not .1<=chunk_years<=100:raise ValueError('Invalid reconstruction interval or chunk size')
        control=JOB_DIR/'control.json';config=json.loads(control.read_text()) if control.exists() else {}
        config['pause_requested']=False;control.write_text(json.dumps(config))
        output=(ROOT/'tmp/reconstruction.log').open('a')
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/reconstruct.py'),'--year',str(end_year),'--chunk-years',str(chunk_years)],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        output.close()
        # Return immediately; the worker records its own PID and initial state.
        return dict(status='starting',pid=process.pid,message='Launching offline reconstruction worker')

def build_sim(epsilon=1e-9,tide_scale=1.,jd=2451545.,asteroid_states=None,origin_jd=2451545.):
    """Reduced-model simulation (G=1, AU, days, t=0 at origin_jd, J2000 by default). Major bodies come from the JPL kernel at `jd`; the 16 asteroids
    from the installed J2000 JPL states, or from `asteroid_states` (list of (x,y,z,vx,vy,vz) in AU, AU/day) when seeding elsewhere."""
    import rebound,reboundx
    from .ephemeris import EPHEMERIS,AU
    sim=rebound.Simulation();sim.G=1.;sim.integrator='ias15';sim.integrator.epsilon=epsilon;sim.t=jd-origin_jd
    for target,gm in zip(IDS,GMS):
        p,v=EPHEMERIS.state(jd,target)
        sim.add(m=gm*86400**2/AU**3,x=p[0]/AU,y=p[1]/AU,z=p[2]/AU,vx=v[0]*86400/AU,vy=v[1]*86400/AU,vz=v[2]*86400/AU)
    perturbers=DATA/'kernels/asteroids.json'
    asteroids=json.loads(perturbers.read_text()) if perturbers.exists() else []
    if len(asteroids)!=16:raise RuntimeError('Install all 16 JPL massive asteroid states before reconstruction.')
    if asteroid_states is not None and len(asteroid_states)!=16:raise ValueError('Need 16 asteroid states')
    for k,a in enumerate(asteroids):
        if asteroid_states is not None:x,y,z,vx,vy,vz=asteroid_states[k]
        else:
            if jd!=2451545.:raise ValueError('Asteroid states are only installed at J2000; pass asteroid_states')
            x,y,z=np.array(a['position_km'])/AU;vx,vy,vz=np.array(a['velocity_km_s'])*86400/AU
        sim.add(m=a['gm_km3_s2']*86400**2/AU**3,x=x,y=y,z=z,vx=vx,vy=vy,vz=vz)
    extras=reboundx.Extras(sim);gr=extras.load_force('gr_full');gr.params['c']=299792.458*86400/AU;extras.add_force(gr)
    harmonics=extras.load_force('gravitational_harmonics');extras.add_force(harmonics)
    sim.particles[0].params['J2']=2.2e-7;sim.particles[0].params['R_eq']=695700/AU
    ra,dec=np.radians([286.13,63.87]);sim.particles[0].params['Omega']=(np.cos(ra)*np.cos(dec),np.sin(ra)*np.cos(dec),np.sin(dec))
    earth,moon=sim.particles[3],sim.particles[4]
    earth.params['J2']=1.08262668e-3;earth.params['R_eq']=6378.137/AU
    tides=extras.load_force('tides_constant_time_lag');extras.add_force(tides)
    earth.r=6378.137/AU;earth.params['k2']=.305;earth.params['tau']=638.*tide_scale/86400;earth.params['Omega']=(0.,0.,7.292115e-5*86400)
    moon.r=1737.4/AU;moon.params['k2']=.024059;moon.params['tau']=.1*tide_scale
    moon.params['Omega']=(0.,-np.sin(np.radians(23.44))*2*np.pi/27.321661,np.cos(np.radians(23.44))*2*np.pi/27.321661)
    return sim,extras

def copy_state(destination,source):
    destination.t=source.t;destination.dt=source.dt
    for a,b in zip(destination.particles,source.particles):a.x,a.y,a.z,a.vx,a.vy,a.vz=b.x,b.y,b.z,b.vx,b.vy,b.vz

def _durable_replace(tmp,final):
    # Flush to disk before the rename so a power cut leaves either the old file or the complete new one.
    with open(tmp,'rb+') as f:os.fsync(f.fileno())
    os.replace(tmp,final)

def save_checkpoint(sim,tag):
    """Resume point after a validated chunk: an atomically replaced single snapshot, plus an appended history archive."""
    latest=JOB_DIR/f'{tag}-{VERSION}-latest.bin';tmp=JOB_DIR/f'{tag}-{VERSION}-latest.{os.getpid()}.tmp'
    if tmp.exists():tmp.unlink()
    sim.save_to_file(str(tmp),delete_file=True);_durable_replace(tmp,latest)
    # History only; resuming never depends on it, so a torn append here cannot block a restart.
    try:sim.save_to_file(str(JOB_DIR/f'{tag}-{VERSION}.bin'),delete_file=False)
    except Exception as e:log(f'Checkpoint history append failed ({e}); the latest checkpoint is intact.')

def load_checkpoint(tag,sign):
    """Furthest-progressed readable checkpoint for this direction, or None. Unreadable files are skipped, not deleted."""
    import rebound,warnings
    best=None
    for path in (JOB_DIR/f'{tag}-{VERSION}-latest.bin',JOB_DIR/f'{tag}-{VERSION}.bin'):
        if not path.exists():continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore');candidate=rebound.Simulation(str(path))
        except Exception as e:log(f'Skipped unreadable checkpoint {path.name}: {e}');continue
        if best is None or sign*candidate.t>sign*best[0].t:best=(candidate,path)
    return best

def snapshot_state(sim):
    return dict(t=sim.t,dt=sim.dt,particles=[(p.x,p.y,p.z,p.vx,p.vy,p.vz) for p in sim.particles])

def restore_state(destination,state):
    destination.t=state['t'];destination.dt=state['dt']
    for a,b in zip(destination.particles,state['particles']):a.x,a.y,a.z,a.vx,a.vy,a.vz=b

def write_atomic_npz(path,**arrays):
    tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    with open(tmp,'wb') as f:np.savez_compressed(f,**arrays)
    _durable_replace(tmp,path)

def write_atomic_text(path,text):
    tmp=path.with_name(path.name+f'.{os.getpid()}.tmp');tmp.write_text(text);_durable_replace(tmp,path)

@lru_cache(maxsize=1)
def lunar_correction():
    """Calibrated lunar mean-anomaly correction (arcsec coefficients), or None if scripts/deep_seed.py fit has not run."""
    path=CALIBRATION/'lunar_correction.json'
    return json.loads(path.read_text()) if path.exists() else None

def shift_mean_anomaly(r,v,dM,mu):
    """Advance the osculating two-body mean anomaly of (r,v) by dM radians, keeping the other elements."""
    import math
    h=np.cross(r,v);rn=np.linalg.norm(r);ev=np.cross(v,h)/mu-r/rn;e=np.linalg.norm(ev)
    a=1/(2/rn-v@v/mu);p=ev/e;q=np.cross(h,p)/np.linalg.norm(h)
    E=math.atan2((r@q)/(a*math.sqrt(1-e*e)),(r@p)/a+e);M=E-e*math.sin(E)+dM;E=M
    for _ in range(30):E-=(E-e*math.sin(E)-M)/(1-e*math.cos(E))
    return a*(math.cos(E)-e)*p+a*math.sqrt(1-e*e)*math.sin(E)*q

def moon_offset(t,seed_jd=SEED_JD):
    """Mean-anomaly correction (rad) at simulation time t (days from J2000) for a run seeded at seed_jd. The reduced model
    lacks the Earth tide raised by the Moon (REBOUNDx's constant-time-lag tide couples bodies to particle 0, the Sun only),
    so the DE441 lunar secular acceleration is restored empirically."""
    c=lunar_correction()
    if c is None:return 0.
    k=c['coefficients_arcsec'];tau=(t+2451545.-seed_jd)/36525
    return -(k['c1']*tau+k['c2']*tau**2+k['c3']*tau**3)/206264.80624709636

def coordinates(sim,body,seed_jd=SEED_JD,origin_jd=2451545.):
    p=lambda index:np.array([sim.particles[index].x,sim.particles[index].y,sim.particles[index].z])
    if body==3:return p(3)*(1-MOON_FRACTION)+p(4)*MOON_FRACTION
    if body==301:
        e,m=sim.particles[3],sim.particles[4];r=p(4)-p(3);dM=moon_offset(sim.t+origin_jd-2451545.,seed_jd)
        if dM==0.:return r
        return shift_mean_anomaly(r,np.array([m.vx-e.vx,m.vy-e.vy,m.vz-e.vz]),dM,e.m+m.m)
    return p(IDS.index(body))

def spin_at(sim,t,origin_jd=2451545.):
    import erfa
    spin=erfa.ltpb(2000+(t+origin_jd-2451545.)/365.25).T@np.array([0.,0.,1.])
    sim.particles[3].params['Omega']=tuple(spin*7.292115e-5*86400)

def run(end_year,chunk_years=10,direction='past'):
    try:
        from .astrotime import calendar_jd
        from .ephemeris import EPHEMERIS,AU
        import rebound
        JOB_DIR.mkdir(exist_ok=True);guard(15_000_000)
        tag='past' if end_year<2000 else 'future';sign=-1 if tag=='past' else 1
        origin=ORIGIN_JD;end=calendar_jd(end_year)-origin   # local clock: days from the seed epoch
        if EPHEMERIS.kernel(end+origin)[0]:
            # NASA's DE440/DE441 already cover the whole requested interval; nothing to reconstruct.
            save_state(status='complete',direction=tag,target_year=end_year,model=SCHEMA,message='Requested interval is covered by JPL DE440/DE441; no reconstruction needed.')
            log(f'{tag} reconstruction to {end_year} not needed: JPL DE440/DE441 cover it.');return
        if tag!='past':raise ValueError('Only the past beyond DE441 needs reconstruction')
        seed_path=CALIBRATION/'seed-asteroids.json'
        if not seed_path.exists() or lunar_correction() is None:raise RuntimeError('Run scripts/deep_seed.py asteroids, holdout and fit first (DE441 seed and lunar calibration).')
        seed=json.loads(seed_path.read_text())['seed']
        sim,extras=build_sim(jd=SEED_JD,asteroid_states=seed['states'],origin_jd=origin);resumed=load_checkpoint(tag,sign)
        if resumed:copy_state(sim,resumed[0]);log(f'Resuming {tag} reconstruction from checkpoint {resumed[1].name} at {2000+(sim.t+origin-2451545)/365.25:.1f} (astronomical year).')
        else:log(f'Seeding {tag} reconstruction from JPL DE441 at JD {SEED_JD} (13,201 BCE); asteroids from {seed_path.name}.')
        chunk=chunk_years*365.25*sign
        start_clock=time.monotonic();initial=sim.t;done=0
        save_state(status='running',message='Benchmarking a multirate trajectory chunk',direction=tag,target_year=end_year,model=SCHEMA,completed=0,
            limitations=['Starts from JPL DE441 at 13,201 BCE; reduced dynamics (16 massive asteroids, 1PN relativity, J2) only beyond DE441',
                        'Lunar tidal secular acceleration restored by a correction calibrated on a 6,800-year DE441 hold-out; ancient dissipation itself is uncalibrated',
                        'No lunar libration model or calibrated physical confidence intervals'])
        log(f'Started/resumed {tag} multirate IAS15 reconstruction at JD {sim.t+origin:.4f} (local clock {sim.t:.4f} d from the seed).')
        while sign*(end-sim.t)>1e-7:
            control=JOB_DIR/'control.json'
            if control.exists() and json.loads(control.read_text()).get('pause_requested'):
                save_state(status='paused',message='Paused at retained validated checkpoint');return
            guard(15_000_000)
            t0=sim.t;t1=t0+sign*min(abs(chunk),abs(end-t0));events=[];payload={};samples={};probes=[]
            start_state=snapshot_state(sim)  # common chunk start for the independent checks below
            for body,step,degree in PACK_CONFIG:
                nsegments=max(1,int(np.ceil(abs(t1-t0)/step)));edges=np.linspace(t0,t1,nsegments+1)
                nodes=np.cos(np.pi*(np.arange(degree+1)+.5)/(degree+1))
                samples[body]=np.zeros((nsegments,degree+1,3));payload[f'edges_{body}']=edges+origin
                for segment,(left,right) in enumerate(zip(edges[:-1],edges[1:])):
                    times=(left+right)/2+(right-left)/2*nodes
                    events.extend((float(t),body,segment,k) for k,t in enumerate(times))
                    # Independent off-node probes; never validate only at interpolation nodes.
                    for x in [-.57,-.07,.63]:probes.append(((left+right)/2+(right-left)/2*x,body,segment,x))
            events.sort(key=lambda e:sign*e[0]);last_spin=None
            for event_index,(t,body,segment,k) in enumerate(events):
                if last_spin is None or abs(t-last_spin)>16:spin_at(sim,t,origin);last_spin=t
                sim.integrate(t);samples[body][segment,k]=coordinates(sim,body,origin_jd=origin)
                if event_index%500==0:
                    save_state(status='running',message='Integrating and fitting trajectory samples',chunk_progress=round(event_index/max(len(events),1)*65,1),samples_processed=event_index,samples_total=len(events),current_year=2000+(t+origin-2451545)/365.25)
            sim.integrate(t1)
            for body,step,degree in PACK_CONFIG:
                nodes=np.cos(np.pi*(np.arange(degree+1)+.5)/(degree+1))
                payload[f'coeff_{body}']=np.array([np.polynomial.chebyshev.chebfit(nodes,s,degree) for s in samples[body]])
            storage={k:v for k,v in payload.items() if not k.startswith('coeff_')}
            quantization={}
            for body,_,_ in PACK_CONFIG:
                c=payload[f'coeff_{body}'];head=c[:,:4].copy();tail=c[:,4:].astype('float32')
                decoded=np.concatenate([head,tail.astype('float64')],axis=1)
                # Coefficient-norm bound on positional quantization error over [-1,1].
                bound=float(np.max(np.sum(np.linalg.norm(c-decoded,axis=2),axis=1))*AU)
                if bound>.5:tail=c[:,4:].copy();decoded=c;bound=0.
                payload[f'coeff_{body}']=decoded;quantization[str(body)]=bound
                storage[f'head_{body}']=head;storage[f'tail_{body}']=tail
            # Independent tighter integration from the common checkpoint.
            check,check_extras=build_sim(1e-11,jd=SEED_JD,asteroid_states=seed['states'],origin_jd=origin)
            restore_state(check,start_state)
            errors={str(body):0. for body,_,_ in PACK_CONFIG};reference={};last_spin=None
            probes.sort(key=lambda e:sign*e[0])
            for index,(t,body,segment,x) in enumerate(probes):
                if last_spin is None or abs(t-last_spin)>16:spin_at(check,t,origin);last_spin=t
                check.integrate(float(t));actual=coordinates(check,body,origin_jd=origin)
                predicted=np.polynomial.chebyshev.chebval(x,payload[f'coeff_{body}'][segment])
                errors[str(body)]=max(errors[str(body)],float(np.linalg.norm(actual-predicted)*AU))
                name,kernel=EPHEMERIS.kernel(origin+t)
                if kernel:
                    if body==3:
                        e,_=EPHEMERIS.state(origin+t,399);m,_=EPHEMERIS.state(origin+t,301);p=e*(1-MOON_FRACTION)+m*MOON_FRACTION
                    elif body==301:
                        m,_=EPHEMERIS.state(origin+t,301);e,_=EPHEMERIS.state(origin+t,399);p=m-e
                    else:p,_=EPHEMERIS.state(origin+t,body)
                    reference[str(body)]=max(reference.get(str(body),0.),float(np.linalg.norm(actual*AU-p)))
                if index%250==0:save_state(status='running',message='Checking independent off-node interpolation and tighter integration',chunk_progress=65+round(index/max(len(probes),1)*25,1))
            check.integrate(t1)
            endpoint=np.array([[p.x,p.y,p.z] for p in sim.particles]);checkend=np.array([[p.x,p.y,p.z] for p in check.particles])
            convergence=float(np.max(np.linalg.norm(endpoint-checkend,axis=1))*AU)
            variant,variant_extras=build_sim(1e-9,tide_scale=2.,jd=SEED_JD,asteroid_states=seed['states'],origin_jd=origin)
            restore_state(variant,start_state)
            # Use the same 16-day spin-orientation cadence for parameter sensitivity.
            for t in np.linspace(t0,t1,max(2,int(abs(t1-t0)/16)+1))[1:]:spin_at(variant,float(t),origin);variant.integrate(float(t))
            varied=np.array([[p.x,p.y,p.z] for p in variant.particles]);sensitivity=np.linalg.norm(endpoint-varied,axis=1)*AU
            report=dict(schema=SCHEMA,storage_quantization_bound_km=quantization,interval_jd=[min(t0,t1)+origin,max(t0,t1)+origin],quality='experimental-extrapolation',
                independent_off_node_max_error_km=errors,endpoint_local_convergence_km=convergence,jpl_residual_max_km=reference,
                tidal_lag_factor_two_local_sensitivity_km=sensitivity[:len(IDS)].tolist(),seed=dict(source='JPL DE441',jd=SEED_JD),lunar_correction=lunar_correction()['coefficients_arcsec'],
                tidal_note='REBOUNDx CTL tides couple only to the Sun here; the lunar tidal acceleration is the calibrated mean-anomaly correction.',
                sensitivity_note='Common chunk initial conditions; local sensitivity, not accumulated or calibrated confidence intervals.',
                physical_uncertainty='Not calibrated. Lunar libration, dissipation history and additional perturbations are not fully modelled.',
                accepted=bool(np.isfinite(convergence) and convergence<10 and all(np.isfinite(v) and v<2 for v in errors.values())))
            name=f'{tag}-{VERSION}-{int(abs(t0)):09d}';reportpath=JOB_DIR/(name+'.json')
            if not report['accepted']:
                write_atomic_text(reportpath,json.dumps(report,indent=2))
                save_state(status='failed-validation',message='Chunk held back: interpolation/convergence gate failed. Files preserved.',last_report=report);return
            # Data first, then the report that marks it accepted, then the resume point. An interruption at any step
            # leaves the previous checkpoint in place, and resuming recomputes and overwrites this chunk identically.
            write_atomic_npz(JOB_DIR/(name+'.npz'),**storage);write_atomic_text(reportpath,json.dumps(report,indent=2))
            save_checkpoint(sim,tag)
            done+=1;elapsed=time.monotonic()-start_clock;rate=abs(sim.t-initial)/max(elapsed,1e-9)
            save_state(status='running',message='Validated chunk published; computing next interval',completed=done,chunk_progress=100,current_year=2000+(sim.t+origin-2451545)/365.25,
                target_year=end_year,seconds_elapsed=elapsed,simulated_years_per_second=rate/365.25,eta_seconds=abs(end-sim.t)/rate,last_report=report)
            log(f'Published validated {tag} chunk {report["interval_jd"]}; off-node max {max(errors.values()):.6g} km, local convergence {convergence:.6g} km. Separate physical limitations remain.')
            _intervals.cache_clear();_pack.cache_clear()
        save_state(status='complete',message='Requested interval generated. Reduced-model physical limitations still apply.')
        log(f'Completed requested {tag} reduced-model interval through {end_year}.')
        control=JOB_DIR/'control.json';config=json.loads(control.read_text()) if control.exists() else {}
        if end_year==MIN_YEAR and config.get('queue_future'):
            config['queue_future']=False;control.write_text(json.dumps(config));log('Queued future extension dropped: JPL DE441 covers the whole future interval through 5,000 CE.')
    except Exception as e:
        save_state(status='error',message=str(e),traceback=traceback.format_exc());log(f'Reconstruction stopped safely: {e}')

def index_stamp():
    p=JOB_DIR/'status.json'
    # A validated report is published before status; directory membership must
    # invalidate the index immediately, including the report/status rename gap.
    return (str(JOB_DIR),JOB_DIR.stat().st_mtime_ns if JOB_DIR.exists() else 0,p.stat().st_mtime_ns if p.exists() else 0)
@lru_cache(maxsize=4)
def _intervals(stamp,version=VERSION):
    result=[]
    for p in JOB_DIR.glob(f'*-{version}-*.json'):  # served: current version only (v3 chunks lie inside DE441 coverage)
        from .frame_cache import report_metadata
        try:
            st=p.stat();interval=report_metadata(str(p),st.st_size,st.st_mtime_ns)
        except OSError:continue
        if interval is not None and p.with_suffix('.npz').exists():result.append((interval,p.with_suffix('.npz')))
    return sorted(result,key=lambda x:x[0][0])
@lru_cache(maxsize=3)
def _pack(path,size=None,mtime=None):
    with np.load(path) as g:return {k:g[k] for k in g.files}

def deep_state(jd,body,version=VERSION):
    from .ephemeris import AU
    if body==0:return np.zeros(3),np.zeros(3)
    def evaluate(g,target):
        edges=g[f'edges_{target}'];indices=np.where((np.minimum(edges[:-1],edges[1:])<=jd)&(np.maximum(edges[:-1],edges[1:])>=jd))[0]
        if not len(indices):return None
        k=int(indices[0]);left,right=edges[k:k+2];x=2*(jd-left)/(right-left)-1;c=g[f'coeff_{target}'][k] if f'coeff_{target}' in g else np.concatenate([g[f'head_{target}'][k],g[f'tail_{target}'][k].astype('float64')],axis=0)
        pos=np.polynomial.chebyshev.chebval(x,c)*AU
        vel=np.polynomial.chebyshev.chebval(x,np.polynomial.chebyshev.chebder(c))*2/(right-left)*AU/86400
        return pos,vel
    for interval,path in _intervals(index_stamp(),version):
        if not interval[0]<=jd<=interval[1]:continue
        st=path.stat();g=_pack(str(path),st.st_size,st.st_mtime_ns)
        if body in (399,301):
            emb=evaluate(g,3);geo=evaluate(g,301)
            if emb is None or geo is None:return None
            factor=-MOON_FRACTION if body==399 else 1-MOON_FRACTION
            return emb[0]+factor*geo[0],emb[1]+factor*geo[1]
        return evaluate(g,body)
    return None

def coverage():
    result=[]
    for interval,path in _intervals(index_stamp()):result.append(json.loads(path.with_suffix('.json').read_text()))
    return result
