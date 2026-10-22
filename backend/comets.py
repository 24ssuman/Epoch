"""Comets from individually cached JPL Horizons apparitions (data/comets/*.npz), with schematic ion and dust tails.

Positions: barycentric JPL state samples, cubic spline inside each cached interval only (never extrapolated).
Brightness: JPL total magnitude m = M1 + 5 log10(delta) + k1 log10(r), with M1/k1 read from the cached Horizons response
(or a sourced override), plus the Marcus (2007, ICQ 29, 39) dust forward-scattering phase correction.
Tails: directions follow physics (ion tail anti-sunward; dust tail curved back along the orbit, away from the
direction of motion). Lengths, widths and surface brightness are an illustrative activity scaling, not a model of
the comet's real dust/gas production.
"""
from .paths import DATA
from .ephemeris import EPHEMERIS,AU
import json, re, threading
import numpy as np

TAIL_SAMPLES=16
TAIL_NOTE=('Tail directions are physical (ion tail anti-solar; dust tail curved behind the orbital motion). '
           'Tail length, width and brightness are an illustrative scaling with heliocentric distance and absolute magnitude, not a dust/plasma model.')
_LOCK=threading.Lock();_PACKS={}

def _photometry(text,fallback):
    m1=re.search(r'\bM1=\s*([-0-9.]+)',text);k1=re.search(r'\bk1=\s*([-0-9.]+)',text)
    try:return float(m1.group(1)),float(k1.group(1)),'JPL Horizons total-magnitude parameters M1, k1'
    except (AttributeError,ValueError):return fallback,10.,'Approximate H with activity exponent 4 (k1=10); JPL M1/k1 not found in cached response'

def _overrides():
    path=DATA/'comets'/'photometry_overrides.json'
    return {k:v for k,v in json.loads(path.read_text()).items() if isinstance(v,dict)} if path.exists() else {}

def packs():
    """Load each comet pack once (reloaded when its file changes)."""
    from scipy.interpolate import CubicSpline
    with _LOCK:
        for path in sorted((DATA/'comets').glob('*.npz')):
            overrides_file=DATA/'comets'/'photometry_overrides.json'
            dense=DATA/'comets'/'dense'/path.name  # optional finer JPL samples around a sungrazing perihelion
            stamp=(path.stat().st_mtime_ns,overrides_file.stat().st_mtime_ns if overrides_file.exists() else 0,dense.stat().st_mtime_ns if dense.exists() else 0)
            if path.name in _PACKS and _PACKS[path.name]['stamp']==stamp:continue
            with np.load(path) as g:times=g['jd'].copy();positions=g['position_km'].copy();meta=json.loads(str(g['metadata']))
            if dense.exists():
                with np.load(dense) as g:
                    keep=(g['jd']>times[0])&(g['jd']<times[-1]);times=np.concatenate([times,g['jd'][keep]]);positions=np.concatenate([positions,g['position_km'][keep]])
                times,unique=np.unique(times,return_index=True);positions=positions[unique]
            text=path.with_suffix('.txt').read_text(errors='replace') if path.with_suffix('.txt').exists() else ''
            m1,k1,photometry=_photometry(text,meta.get('H',10.))
            override=_overrides().get(meta['name'])
            if override:m1,k1,photometry=override['M1'],override['k1'],'Sourced override ('+override['source']+')'
            delta90=float((override or {}).get('delta90',1.));segments=(override or {}).get('segments')
            spline=CubicSpline(times,positions,axis=0)
            # Perihelion within the cached interval, from a coarse scan refined to the nearest half-day sample.
            coarse=times[::8];dist=[np.linalg.norm(spline(t)-EPHEMERIS.state(t,10)[0]) for t in coarse]
            k=int(np.argmin(dist));lo,hi=coarse[max(k-1,0)],coarse[min(k+1,len(coarse)-1)]
            fine=times[(times>=lo)&(times<=hi)];fd=[np.linalg.norm(spline(t)-EPHEMERIS.state(t,10)[0]) for t in fine]
            j=int(np.argmin(fd))
            _PACKS[path.name]=dict(stamp=stamp,times=times,spline=spline,velocity=spline.derivative(),meta=meta,M1=m1,k1=k1,photometry=photometry,delta90=delta90,segments=segments,
                                   perihelion_jd=float(fine[j]),perihelion_au=float(fd[j]/AU))
        return [p for name,p in sorted(_PACKS.items()) if (DATA/'comets'/name).exists()]

# Marcus (2007) compound Henyey-Greenstein dust phase function, each term normalised to 1 at phase angle 90 deg;
# delta90 is the dust-to-gas brightness ratio at 90 deg (1 = "usual" comet, 10 = dusty). Known to underestimate the
# surge beyond ~173 deg (Li et al. 2015, arXiv:1503.00387).
FS_G_FORWARD,FS_G_BACK,FS_K=.9,-.6,.95
def phase_correction(phase_deg,delta90=1.):
    """Magnitude change from dust scattering at this Sun-comet-observer phase angle (negative = brighter); 0 at 90 deg."""
    c=np.cos(np.radians(phase_deg))
    hg=lambda g:((1+g*g)/(1+g*g+2*g*c))**1.5
    dust=FS_K*hg(FS_G_FORWARD)+(1-FS_K)*hg(FS_G_BACK)
    return float(-2.5*np.log10(delta90/(1+delta90)*dust+1/(1+delta90)))

def phase_angle(P,observer_helio):
    """Sun-comet-observer angle in degrees from heliocentric comet and observer positions."""
    to_sun=-P;to_observer=observer_helio-P
    return float(np.degrees(np.arccos(np.clip(np.dot(to_sun,to_observer)/np.linalg.norm(to_sun)/np.linalg.norm(to_observer),-1,1))))

def photometry_at(p,jd):
    """(M1, k1, delta90) at this time. A pack may give separate pre/post-perihelion laws with delta90 ramped linearly over
    +/- ramp_days around perihelion (Marcus 2023 Halley model); otherwise one law applies throughout."""
    seg=p.get('segments')
    if not seg:return p['M1'],p['k1'],p['delta90']
    dt=jd-p['perihelion_jd'];law=seg['pre'] if dt<0 else seg['post'];ramp=seg.get('ramp_days',0)
    d=law['delta90'] if not ramp or abs(dt)>=ramp else seg['pre']['delta90']+(seg['post']['delta90']-seg['pre']['delta90'])*(dt+ramp)/(2*ramp)
    return law['M1'],law['k1'],d

def magnitude(p,jd,comet_bary,observer_bary,sun_bary):
    """Total visual magnitude and its parts for barycentric comet/observer/Sun positions (km)."""
    M1,k1,delta90=photometry_at(p,jd);P=(comet_bary-sun_bary)/AU;delta=np.linalg.norm(comet_bary-observer_bary)/AU
    phase=phase_angle(P,(observer_bary-sun_bary)/AU);scatter=phase_correction(phase,delta90)
    return float(M1+5*np.log10(delta)+k1*np.log10(np.linalg.norm(P))+scatter),phase,scatter,(M1,k1,delta90)

def _date_label(jd):
    from .astrotime import jd_calendar
    d=jd_calendar(jd);return f"{d['day']} {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d['month']-1]} {d['display_year']} {d['era']}"

def catalog():
    """Cached apparitions for the comet list: validity window, perihelion and brightness parameters."""
    return [dict(id=p['meta']['name'],name=p['meta']['name'],start_jd=float(p['times'][0]),end_jd=float(p['times'][-1]),perihelion_jd=p['perihelion_jd'],perihelion_date=_date_label(p['perihelion_jd']),
                 perihelion_au=p['perihelion_au'],M1=p['M1'],k1=p['k1'],source=p['meta']['source']) for p in sorted(packs(),key=lambda p:p['perihelion_jd'])]

def tail_activity(r,M1):
    """Illustrative tail scale (AU) and visibility factor. Tails switch on inside ~4 AU and grow toward the Sun."""
    on=float(np.clip((4.-r)/2.5,0.,1.))
    length=float(min(1.,.15*10**(-.2*(M1-5.5))*max(r,.05)**-1.5))*on
    return length,on

def _ribbon(points,widths,side):
    return points+side*widths[:,None],points-side*widths[:,None]

def tails(P,V,observer_helio,M1):
    """Heliocentric ion and dust tail ribbons (AU). Each edge is TAIL_SAMPLES points from the head outward."""
    r=np.linalg.norm(P);length,on=tail_activity(r,M1)
    if length<1e-5:return []
    s=np.linspace(0.,1.,TAIL_SAMPLES);anti=P/r
    vperp=V-np.dot(V,anti)*anti;vperp=vperp/np.linalg.norm(vperp) if np.linalg.norm(vperp)>0 else np.zeros(3)
    normal=np.cross(P,V);normal=normal/np.linalg.norm(normal) if np.linalg.norm(normal)>0 else np.array([0.,0.,1.])
    out=[]
    # Ion (plasma) tail: straight, anti-solar, narrow; ribbon turned broadside to the observer.
    ion=P+np.outer(s*length,anti);view=P-observer_helio;side=np.cross(anti,view);side=side/np.linalg.norm(side) if np.linalg.norm(side)>0 else normal
    out.append(dict(kind='ion',color='#8ec5ff',edges=_ribbon(ion,(.008+.035*s)*length,side),intensity=(1-s)**2))
    # Dust tail: lags behind the motion, so it bends away from the velocity within the orbital plane and fans out.
    dust_len=.65*length;dirs=anti[None,:]-.75*s[:,None]*vperp[None,:];dirs/=np.linalg.norm(dirs,axis=1)[:,None]
    dust=P+np.cumsum(np.vstack([np.zeros(3),dirs[1:]*np.diff(s)[:,None]*dust_len]),axis=0)
    side=np.cross(dirs[len(dirs)//2],normal);side=side/np.linalg.norm(side) if np.linalg.norm(side)>0 else vperp
    out.append(dict(kind='dust',color='#ffe8c2',edges=_ribbon(dust,(.02+.17*s)*dust_len,side),intensity=(1-s)**1.4))
    for t in out:t['visibility']=on
    return out

def snapshot(epoch,basis,observer):
    out=[];jd=epoch.tdb1+epoch.tdb2
    for p in packs():
        times=p['times']
        if not times[0]<=jd<=times[-1]:continue
        spline=p['spline'];pt=spline(jd);t=jd
        for _ in range(3):
            t=jd-np.linalg.norm(pt-observer)/299792.458/86400
            if not times[0]<=t<=times[-1]:break
            pt=spline(t)
        ray=pt-observer;dist=np.linalg.norm(ray);u=ray/dist;local=basis@u
        sun,_=EPHEMERIS.state(jd,10);P=(pt-sun)/AU;r=float(np.linalg.norm(P));delta=dist/AU
        V=p['velocity'](t)/AU  # AU/day, barycentric; the Sun's own motion is negligible for tail direction
        observer_helio=(observer-sun)/AU
        mag,phase,scatter,(M1,k1,delta90)=magnitude(p,t,pt,observer,sun)
        tail_out=[]
        for tail in tails(P,V,observer_helio,p['M1']):
            edges=[]
            for edge in tail['edges']:
                bary=sun/AU+edge;rays=bary-observer/AU;dirs=rays/np.linalg.norm(rays,axis=1)[:,None]
                edges.append(dict(points_au=np.round(edge,7).tolist(),ground_direction=np.round(dirs@basis.T,7).tolist()))
            tail_out.append(dict(kind=tail['kind'],color=tail['color'],intensity=np.round(tail['intensity'],3).tolist(),visibility=tail['visibility'],left=edges[0],right=edges[1]))
        name=p['meta']['name']
        out.append(dict(id=name,name=name,type='comet',direction=u.tolist(),ground_direction=local.tolist(),position_au=P.tolist(),
            distance_au=float(delta),heliocentric_distance_au=r,magnitude=float(mag),color='#b5e5d3',quality='cached-JPL-apparition',source=p['meta']['source'],
            validity_jd=[float(times[0]),float(times[-1])],perihelion_jd=p['perihelion_jd'],perihelion_au=p['perihelion_au'],
            photometry_quality=f"{p['photometry']}: m = {M1:g} + 5 log10(delta) + {k1:g} log10(r) + forward-scattering term ({scatter:+.2f} mag at phase {phase:.0f} deg; Marcus 2007, delta90={delta90:.2g})",phase_angle_deg=phase,forward_scattering_mag=scatter,tails=tail_out,tail_note=TAIL_NOTE,
            sanskrit_name=f'Dhūmaketu ({name})',sanskrit_devanagari=f'धूमकेतु ({name})',sanskrit_basis='book',
            sanskrit_note='The book uses Dhuma-Ketu, literally "smoking flag or banner", for comets (p.44); it does not name this comet.',sanskrit_source='Oak (2011), PDF p. 44',
            frame='ICRS apparent direction; heliocentric ICRS AU for position_au and tails',time_scale='TDB',units={'distance_au':'AU','magnitude':'total visual magnitude (approximate)'}))
    return out
