"""Prepare the DE441-seeded deep-time reconstruction (offline).

  asteroids  Integrate the 16 massive asteroids (with the planets, Earth+Moon merged at their barycenter) from the retained
             v3 checkpoint back to the DE441 start, saving their states at the hold-out and seed epochs.
             -> data/jobs/calibration/seed-asteroids.json
  holdout    Seed the full reduced model from DE441 at 6000 BCE and integrate 6,800 years back to 12,800 BCE (all inside
             DE441), recording the geocentric Moon and the planets. -> data/jobs/calibration/holdout.npz
  fit        Fit the lunar mean-anomaly correction to the hold-out against DE441 and check it on the independent v3 run.
             -> data/jobs/calibration/lunar_correction.json

NASA's DE441 is used wherever it exists; the reduced model only fills what DE441 does not cover. Nothing is deleted.
"""
import sys,json,math,time,warnings
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from backend.paths import DATA,ROOT
from backend import jobs
from backend.astrotime import calendar_jd
from backend.ephemeris import EPHEMERIS,AU

OUT=DATA/'jobs'/'calibration'
DE441_START=-3100015.5
SEED_JD=DE441_START+1.          # first epoch safely inside the DE441 segment
HOLDOUT_START=calendar_jd(-6000,1,1,12)
HOLDOUT_END=calendar_jd(-12800,1,1,12)
SAMPLE_DAYS=11.3                # incommensurate with the lunar month

def log(message):
    print(message,flush=True)
    with (ROOT/'LOG.md').open('a') as f:f.write(f'\n- {time.strftime("%Y-%m-%d %H:%M:%S %z")}: {message}\n')

def asteroids():
    import rebound,reboundx
    OUT.mkdir(parents=True,exist_ok=True)
    found=jobs.load_checkpoint('past',-1)
    if not found:raise SystemExit('No v3 past checkpoint to start from')
    full=found[0];mu=jobs.MOON_FRACTION
    sim=rebound.Simulation();sim.G=1.;sim.integrator='ias15';sim.t=full.t
    for i,p in enumerate(full.particles):
        if i==4:continue   # Moon merged into the Earth-Moon barycenter below
        if i==3:
            m=full.particles[4];sim.add(m=p.m+m.m,x=p.x*(1-mu)+m.x*mu,y=p.y*(1-mu)+m.y*mu,z=p.z*(1-mu)+m.z*mu,vx=p.vx*(1-mu)+m.vx*mu,vy=p.vy*(1-mu)+m.vy*mu,vz=p.vz*(1-mu)+m.vz*mu)
        else:sim.add(m=p.m,x=p.x,y=p.y,z=p.z,vx=p.vx,vy=p.vy,vz=p.vz)
    extras=reboundx.Extras(sim);gr=extras.load_force('gr');gr.params['c']=299792.458*86400/AU;extras.add_force(gr);sim.particles[0].params['gr_source']=1
    out={};start=time.monotonic()
    for label,jd in [('holdout',HOLDOUT_START),('seed',SEED_JD)]:
        sim.integrate(jd-2451545.,exact_finish_time=1)
        out[label]=dict(jd=jd,states=[[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles[10:]])
        print(label,'reached',2000+sim.t/365.25,f'{time.monotonic()-start:.0f}s',flush=True)
    meta=dict(source=f'Reduced-model integration from retained checkpoint {found[1].name} at year {2000+full.t/365.25:.1f}; planets, Earth-Moon barycenter, Pluto, 16 asteroids, solar GR.',
              frame='Solar-system barycentric ICRS (simulation frame)',units='AU, AU/day',time_scale='TDB',
              limitation='Asteroid states are not from NASA data at these epochs; JPL publishes none this early. Their perturbation of the planets is small.',**out)
    (OUT/'seed-asteroids.json').write_text(json.dumps(meta,indent=1))
    log(f'deep_seed asteroids: integrated 16 asteroid states back to the DE441 start ({time.monotonic()-start:.0f} s); saved data/jobs/calibration/seed-asteroids.json.')

def holdout():
    seed=json.loads((OUT/'seed-asteroids.json').read_text())['holdout']
    sim,_=jobs.build_sim(jd=HOLDOUT_START,asteroid_states=seed['states'])
    t0=sim.t;t1=HOLDOUT_END-2451545.;times=np.arange(t0,t1,-SAMPLE_DAYS)
    moon=np.zeros((len(times),6));planets=np.zeros((len(times)//20+1,len(jobs.IDS),3));start=time.monotonic()
    for k,t in enumerate(times):
        jobs.spin_at(sim,t);sim.integrate(t)
        e,m=sim.particles[3],sim.particles[4];moon[k]=[m.x-e.x,m.y-e.y,m.z-e.z,m.vx-e.vx,m.vy-e.vy,m.vz-e.vz]
        if k%20==0:planets[k//20]=[[p.x,p.y,p.z] for p in sim.particles[:len(jobs.IDS)]]
        if k%20000==0:print(f'{2000+t/365.25:.0f} {time.monotonic()-start:.0f}s',flush=True)
    np.savez_compressed(OUT/'holdout.npz',jd=times+2451545.,moon=moon,planet_jd=times[::20]+2451545.,planets=planets,ids=np.array(jobs.IDS),
        metadata=json.dumps(dict(source='Reduced model seeded from JPL DE441 at 6000 BCE (16 asteroids from seed-asteroids.json)',frame='ICRS',units='AU, AU/day',time_scale='TDB')))
    log(f'deep_seed holdout: integrated 6000 BCE -> 12800 BCE from DE441 ({time.monotonic()-start:.0f} s); data/jobs/calibration/holdout.npz.')

def shift_mean_anomaly(r,v,dM,mu):
    """Advance the osculating two-body mean anomaly of (r,v) by dM radians, keeping the other elements."""
    h=np.cross(r,v);rn=np.linalg.norm(r);ev=np.cross(v,h)/mu-r/rn;e=np.linalg.norm(ev)
    a=1/(2/rn-v@v/mu);p=ev/e;q=np.cross(h,p)/np.linalg.norm(h)
    E=math.atan2((r@q)/(a*math.sqrt(1-e*e)),(r@p)/a+e);M=E-e*math.sin(E)+dM;E=M
    for _ in range(30):E-=(E-e*math.sin(E)-M)/(1-e*math.cos(E))
    return a*(math.cos(E)-e)*p+a*math.sqrt(1-e*e)*math.sin(E)*q

def along_track(r,rk,vk):
    """Signed along-orbit angle (arcsec) from the reference direction rk to r; positive = ahead."""
    h=np.cross(rk,vk);h/=np.linalg.norm(h);u=rk/np.linalg.norm(rk);return math.atan2(r@np.cross(h,u),r@u)*206264.806

def fit():
    from scipy.optimize import least_squares
    EPHEMERIS.refresh();mu=(jobs.GMS[3]+jobs.GMS[4])*86400**2/AU**3
    g=np.load(OUT/'holdout.npz');pick=np.arange(0,len(g['jd']),40)
    jd=g['jd'][pick];moon=g['moon'][pick];tau=(jd-HOLDOUT_START)/36525
    ref=[]
    for j in jd:
        m,mv=EPHEMERIS.state(j,301);e,ev=EPHEMERIS.state(j,399);ref.append(((m-e)/AU,(mv-ev)*86400/AU))
    def residual(c):
        return np.array([along_track(shift_mean_anomaly(x[:3],x[3:],-(c[0]*t+c[1]*t*t+c[2]*t**3)/206264.806,mu),rk,vk) for x,t,(rk,vk) in zip(moon,tau,ref)])
    raw=residual(np.zeros(3));sol=least_squares(residual,[0.,12.9,0.]);res=sol.fun
    def angle(x,dM,rk):
        r=shift_mean_anomaly(x[:3],x[3:],dM,mu);return math.degrees(math.acos(np.clip(r@rk/np.linalg.norm(r)/np.linalg.norm(rk),-1,1)))*3600
    total=np.array([angle(x,-(sol.x[0]*t+sol.x[1]*t*t+sol.x[2]*t**3)/206264.806,rk) for x,t,(rk,_) in zip(moon,tau,ref)])
    uncorrected=np.array([angle(x,0.,rk) for x,(rk,_) in zip(moon,ref)])
    # independent check on the v3 run (started from DE440 at J2000, a different epoch and kernel)
    iv=jobs._intervals(jobs.index_stamp(),'v3');rng=np.random.default_rng(3);v3=[];v3raw=[]
    for (lo,hi),_ in iv[::4]:
        j=float(rng.uniform(lo,hi));md=jobs.deep_state(j,301,'v3');ed=jobs.deep_state(j,399,'v3')
        if md is None or EPHEMERIS.kernel(j)[0] is None:continue
        r=(md[0]-ed[0])/AU;v=(md[1]-ed[1])*86400/AU;t=(j-2451545)/36525
        m,_=EPHEMERIS.state(j,301);e,_=EPHEMERIS.state(j,399);rk=(m-e)/AU
        x=np.concatenate([r,v]);v3.append(angle(x,-(sol.x[0]*t+sol.x[1]*t*t+sol.x[2]*t**3)/206264.806,rk));v3raw.append(angle(x,0.,rk))
    # planets in the hold-out, as seen from Earth (no correction applied to planets)
    pl={}
    for k,(j,P) in enumerate(zip(g['planet_jd'],g['planets'])):
        if k%25:continue
        e,_=EPHEMERIS.state(j,399)  # particle 3 is the Earth itself in the simulation
        for name,i in [('Sun',0),('Mercury',1),('Venus',2),('Mars',5),('Jupiter',6),('Saturn',7),('Uranus',8),('Neptune',9)]:
            p,_=EPHEMERIS.state(j,jobs.IDS[i]);a=P[i]-P[3];b=(p-e)/AU
            pl.setdefault(name,[]).append(math.degrees(math.acos(np.clip(a@b/np.linalg.norm(a)/np.linalg.norm(b),-1,1)))*3600)
    result=dict(model='mean-anomaly shift dM = -(c1*tau + c2*tau^2 + c3*tau^3) arcsec, tau in Julian centuries from the seed epoch',
        coefficients_arcsec=dict(c1=float(sol.x[0]),c2=float(sol.x[1]),c3=float(sol.x[2])),implied_tidal_acceleration_arcsec_cy2=float(-2*sol.x[1]),
        fitted_on='Hold-out: reduced model seeded from DE441 at 6000 BCE, 6,800 years back to 12,800 BCE, compared with DE441',
        holdout_moon_arcsec=dict(uncorrected_rms=float(np.sqrt(np.mean(uncorrected**2))),uncorrected_max=float(uncorrected.max()),corrected_rms=float(np.sqrt(np.mean(total**2))),corrected_max=float(total.max()),n=int(len(total))),
        independent_v3_moon_arcsec=dict(uncorrected_rms=float(np.sqrt(np.mean(np.square(v3raw)))),corrected_rms=float(np.sqrt(np.mean(np.square(v3)))),corrected_max=float(max(v3)),n=len(v3),
            note='v3 started from DE440 at J2000; correction applied with tau from J2000'),
        holdout_planets_max_arcsec={k:float(max(v)) for k,v in pl.items()},
        limitation='Empirical: reproduces DE441 lunar mean motion over the 6,800-year hold-out. Before 13,200 BCE it assumes DE441-era tidal dissipation persists; real ancient dissipation is uncalibrated.')
    (OUT/'lunar_correction.json').write_text(json.dumps(result,indent=1))
    log(f'deep_seed fit: lunar correction c=({sol.x[0]:.3f}, {sol.x[1]:.4f}, {sol.x[2]:.5f}) arcsec; hold-out Moon rms {result["holdout_moon_arcsec"]["uncorrected_rms"]:.0f} -> {result["holdout_moon_arcsec"]["corrected_rms"]:.1f} arcsec (max {result["holdout_moon_arcsec"]["corrected_max"]:.1f}); independent v3 run rms {result["independent_v3_moon_arcsec"]["uncorrected_rms"]:.0f} -> {result["independent_v3_moon_arcsec"]["corrected_rms"]:.1f} arcsec.')
    print(json.dumps(result,indent=1))

def seedfit(centuries=5.):
    """Measure the linear (mean-motion offset) term at the real seed: integrate forward from the DE441 start into DE441
    coverage and fit c1 with c2, c3 fixed from the hold-out. On the hold-out, c1 from its first 2-5 centuries reproduced the
    full 68-century fit to 0.2"/cy."""
    from scipy.optimize import least_squares
    EPHEMERIS.refresh();mu=(jobs.GMS[3]+jobs.GMS[4])*86400**2/AU**3
    path=OUT/'lunar_correction.json';cal=json.loads(path.read_text());c=cal.get('holdout_coefficients_arcsec',cal['coefficients_arcsec'])
    seed=json.loads((OUT/'seed-asteroids.json').read_text())['seed']
    sim,_=jobs.build_sim(jd=SEED_JD,asteroid_states=seed['states']);t0=sim.t;start=time.monotonic();samples=[]
    for t in np.arange(t0+SAMPLE_DAYS,t0+centuries*36525,SAMPLE_DAYS):
        jobs.spin_at(sim,t);sim.integrate(t);e,m=sim.particles[3],sim.particles[4]
        samples.append((t+2451545.,np.array([m.x-e.x,m.y-e.y,m.z-e.z,m.vx-e.vx,m.vy-e.vy,m.vz-e.vz])))
    samples=samples[::10];tau=np.array([(j-SEED_JD)/36525 for j,_ in samples]);ref=[]
    for j,_ in samples:
        m,mv=EPHEMERIS.state(j,301);e,ev=EPHEMERIS.state(j,399);ref.append(((m-e)/AU,(mv-ev)*86400/AU))
    def resid(c1):
        return np.array([along_track(shift_mean_anomaly(x[:3],x[3:],-(c1*t+c['c2']*t*t+c['c3']*t**3)/206264.806,mu),rk,vk) for (_,x),t,(rk,vk) in zip(samples,tau,ref)])
    c1=float(least_squares(lambda x:resid(x[0]),[0.]).x[0]);res=resid(c1)
    cal['holdout_coefficients_arcsec']=c
    cal['coefficients_arcsec']=dict(c1=c1,c2=c['c2'],c3=c['c3'])
    cal['seed_fit']=dict(span_centuries=centuries,n=len(samples),c1=c1,rms_before_arcsec=float(np.sqrt(np.mean(resid(0.)**2))),rms_after_arcsec=float(np.sqrt(np.mean(res**2))),
        note='c1 measured forward from the DE441 start (JD -3,100,014.5) against DE441; c2, c3 from the 6000 BCE hold-out')
    path.write_text(json.dumps(cal,indent=1))
    log(f'deep_seed seedfit: c1 at the DE441 start = {c1:.3f} arcsec/cy (hold-out {c["c1"]:.3f}); {centuries:g}-century forward fit rms {cal["seed_fit"]["rms_after_arcsec"]:.1f} arcsec ({time.monotonic()-start:.0f} s).')
    print(json.dumps(cal['seed_fit'],indent=1))

if __name__=='__main__':
    {'asteroids':asteroids,'holdout':holdout,'fit':fit,'seedfit':seedfit}[sys.argv[1]]()
