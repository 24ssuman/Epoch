"""Kernel selection, light time and apparent topocentric directions."""
from .paths import DATA
import numpy as np
from jplephem.spk import SPK
import erfa

AU=149597870.7
C=299792.458
BODIES={
 'Sun':(10,695700.,-26.74,'#fff2cf'),
 'Mercury':(1,2439.7,-.42,'#b6aca0'), 'Venus':(2,6051.8,-4.40,'#f4dfab'),
 'Earth':(399,6378.137,-3.99,'#78bafa'), 'Moon':(301,1737.4,-12.73,'#dad8ce'),
 'Mars':(4,3389.5,-1.52,'#e69b77'), 'Jupiter':(5,71492.,-9.40,'#e6d4b8'),
 'Saturn':(6,60268.,-8.88,'#e5d4a4'), 'Uranus':(7,25559.,-7.19,'#a6dedf'),
 'Neptune':(8,24764.,-6.87,'#739bdf'), 'Pluto':(9,1188.3,-1.0,'#b9ad9f')}

class Ephemeris:
    def __init__(self):self.kernels={};self.directory_stamp=None
    def refresh(self):
        directory=DATA/'kernels'
        token=(str(directory),directory.stat().st_mtime_ns if directory.exists() else None)
        if token==self.directory_stamp:return
        self.directory_stamp=token
        for name in ['de440.bsp','de441.bsp','de441_part-1.bsp','de441_part-2.bsp']:
            p=DATA/'kernels'/name
            if name not in self.kernels and p.exists():self.kernels[name]=SPK.open(str(p))
    def kernel(self,jd):
        self.refresh()
        for name,k in self.kernels.items():
            if any(s.center==0 and s.target==3 and s.start_jd<=jd<=s.end_jd for s in k.segments):return name,k
        return None,None
    @staticmethod
    def segment(kernel,center,target,jd):
        for segment in reversed(kernel.segments):
            if segment.center==center and segment.target==target and segment.start_jd<=jd<=segment.end_jd:
                return segment
        raise ValueError('No ephemeris segment for this body at the requested date')
    def state(self,jd,body):
        name,k=self.kernel(jd)
        if k is None:
            from .jobs import deep_state
            result=deep_state(jd,body)
            if result is None:raise ValueError('No validated ephemeris chunk for this date')
            return result
        if body==0:return np.zeros(3),np.zeros(3)
        if body in (399,301):
            p,v=self.segment(k,0,3,jd).compute_and_differentiate(jd)
            p2,v2=self.segment(k,3,body,jd).compute_and_differentiate(jd)
            return p+p2,(v+v2)/86400
        p,v=self.segment(k,0,body,jd).compute_and_differentiate(jd)
        return p,v/86400
    def source(self,jd):
        name,k=self.kernel(jd)
        if k:
            seg=self.segment(k,0,3,jd)
            return dict(model='JPL '+name.split('.')[0].upper(),quality='ephemeris',validity_jd=[seg.start_jd,seg.end_jd],
                        note='Fitted dynamical ephemeris; physical uncertainty increases away from observations. Giant planets use system barycenters.')
        return dict(model='REBOUND IAS15 reduced model',quality='extrapolated',validity_jd=None,note='Experimental reconstruction; numerical convergence is not historical accuracy.')

EPHEMERIS=Ephemeris()

def apparent(epoch,observer,observer_velocity,target):
    jd=epoch.tdb1+epoch.tdb2
    pt,_=EPHEMERIS.state(jd,target)
    for _ in range(4):
        light=np.linalg.norm(pt-observer)/C/86400
        pt,_=EPHEMERIS.state(jd-light,target)
    ray=pt-observer;distance=float(np.linalg.norm(ray));direction=ray/distance
    ps,_=EPHEMERIS.state(jd,10)
    sun_to_obs=observer-ps; em=float(np.linalg.norm(sun_to_obs)/AU)
    # Solar deflection is undefined at the solar center; extended solar disc is rendered separately.
    if target!=10:
        direction=erfa.ldsun(direction,sun_to_obs/np.linalg.norm(sun_to_obs),em)
    v=observer_velocity/C; bm1=np.sqrt(1-float(np.dot(v,v)))
    direction=erfa.ab(direction,v,em,bm1)
    return direction,distance,pt

# Planetary photometry: Mallama & Hilton (2018), Astronomy and Computing 25, 10-24, the models JPL Horizons uses for APmag
# (agreement with Horizons 2016-2036: <=0.002 mag Mercury/Venus/Jupiter/Neptune, 0.02 Saturn/Uranus, 0.11 Mars, which
# omits their rotational/seasonal terms; docs/NASA_CROSSCHECK.md G). Distances in AU, phase angle in radians.
SATURN_POLE=(40.589,-.036,83.537,-.004)   # IAU WGCCRE: RA0, RA rate, Dec0, Dec rate (deg, deg/century)
URANUS_POLE=(257.311,0.,-15.175,0.);URANUS_FLATTENING=1-24973./25559.

def _pole(spec,jd):
    T=(jd-2451545.)/36525;ra,dec=np.radians([spec[0]+spec[1]*T,spec[2]+spec[3]*T]);return np.array([np.cos(dec)*np.cos(ra),np.cos(dec)*np.sin(ra),np.sin(dec)])

def _sublatitude(pole,planet,point):
    u=point-planet;return float(np.degrees(np.arcsin(np.clip(u@pole/np.linalg.norm(u),-1,1))))

def photometric_geometry(name,jd,planet,observer,sun):
    """Extra geometry the Saturn and Uranus laws need (signed sub-observer and sub-solar latitudes, degrees)."""
    if name=='Saturn':p=_pole(SATURN_POLE,jd);return dict(sub_observer_lat=_sublatitude(p,planet,observer),sub_solar_lat=_sublatitude(p,planet,sun),jd=jd)
    if name=='Uranus':
        p=_pole(URANUS_POLE,jd);g=lambda la:float(np.degrees(np.arctan(np.tan(np.radians(la))/(1-URANUS_FLATTENING)**2)))  # planetographic
        return dict(sub_observer_lat=g(_sublatitude(p,planet,observer)),sub_solar_lat=g(_sublatitude(p,planet,sun)),jd=jd)
    return dict(jd=jd)

def brightness(name,r,delta,phase,geometry=None):
    if name=='Sun':return -26.74+5*np.log10(max(delta,1e-12))
    if name=='Moon':
        a=phase*180/np.pi
        return -12.73+.026*abs(a)+4e-9*a**4+5*np.log10(max(delta*AU/384400,1e-9))
    a=float(np.degrees(phase));g=geometry or {};base=5*np.log10(max(r*delta,1e-15))
    if name=='Mercury':return base-.613+6.3280e-2*a-1.6336e-3*a**2+3.3644e-5*a**3-3.4265e-7*a**4+1.6893e-9*a**5-3.0334e-12*a**6
    if name=='Venus':return base+(-4.384-1.044e-3*a+3.687e-4*a**2-2.814e-6*a**3+8.938e-9*a**4 if a<163.7 else 236.05828-2.81914*a+8.39034e-3*a**2)
    if name=='Earth':return base-3.99-1.060e-3*a+2.054e-4*a**2
    if name=='Mars':return base+(-1.601+2.267e-2*a-1.302e-4*a**2 if a<=50 else -.367-.02573*a+3.445e-4*a**2)
    if name=='Jupiter':
        if a<=12:return base-9.395-3.7e-4*a+6.16e-4*a**2
        x=a/180;return base-9.428-2.5*np.log10(1-1.507*x-.363*x**2-.062*x**3+2.809*x**4-1.876*x**5)
    if name=='Saturn':
        be,bs=g.get('sub_observer_lat'),g.get('sub_solar_lat')
        if be is not None and be*bs>0:
            # rings lit and seen from the lit side: effective tilt = geometric mean of sub-observer and sub-solar ring latitudes
            sb=np.sqrt(np.sin(np.radians(abs(be)))*np.sin(np.radians(abs(bs))))
            if a<=6.5 and np.degrees(np.arcsin(sb))<=27:return base-8.914-1.825*sb+.026*a-.378*sb*np.exp(-2.25*a)
        if a<=6:return base-8.95-3.7e-4*a+6.16e-4*a**2   # globe only
        return base-8.94+2.446e-4*a+2.672e-4*a**2-1.505e-6*a**3+4.767e-9*a**4
    if name=='Uranus':
        lat=(abs(g.get('sub_observer_lat',0.))+abs(g.get('sub_solar_lat',0.)))/2
        return base-7.110-8.4e-4*lat+(6.587e-3*a+1.045e-4*a**2 if a>3.1 else 0.)
    if name=='Neptune':
        y=2000+(g.get('jd',2451545.)-2451545.)/365.25;v0=-6.89 if y<1980 else -7.00 if y>2000 else -6.89-.0055*(y-1980)
        return base+v0+(7.944e-3*a+9.617e-5*a**2 if a>1.9 else 0.)
    return base+BODIES[name][2]+.001*a   # Pluto: H=-1.0, weak phase term

def moon_phase(sun_dir,moon_dir,ecliptic_pole,fraction):
    """Phase of the Moon from apparent directions (unit vectors, same frame). Returns the Moon-minus-Sun ecliptic longitude
    (degrees, 0-360: 0 new, 90 first quarter, 180 full, 270 last quarter, the definition NASA's phase tables use), waxing,
    and a name from the illuminated fraction: <3% New, 3-47% Crescent, 47-53% Quarter, 53-97% Gibbous, >97% Full."""
    s,m,p=np.asarray(sun_dir),np.asarray(moon_dir),np.asarray(ecliptic_pole)
    d=float(np.degrees(np.arctan2(np.cross(s,m)@p,s@m-(s@p)*(m@p))))%360;waxing=d<180
    if fraction<.03:name='New Moon'
    elif fraction>.97:name='Full Moon'
    elif .47<=fraction<=.53:name='First Quarter' if waxing else 'Last Quarter'
    else:name=('Waxing ' if waxing else 'Waning ')+('Crescent' if fraction<.5 else 'Gibbous')
    return d,waxing,name

def body_snapshot(epoch,basis,lat,lon,elevation,progress=None):
    jd=epoch.tdb1+epoch.tdb2; earth,ev=EPHEMERIS.state(jd,399)
    # WGS84 geodetic observer -> ICRS. Sidereal basis incorporates precession/nutation.
    phi=np.radians(lat); f=1/298.257223563;e2=f*(2-f);n=6378.137/np.sqrt(1-e2*np.sin(phi)**2)
    north_shift=(-(n+elevation/1000)*np.cos(phi)*np.sin(phi)+(n*(1-e2)+elevation/1000)*np.sin(phi)*np.cos(phi))
    up_distance=(n+elevation/1000)*np.cos(phi)**2+(n*(1-e2)+elevation/1000)*np.sin(phi)**2
    offset=basis[2]*up_distance+basis[1]*north_shift
    obs=earth+offset
    spin_axis=epoch.matrix.T@np.array([0.,0.,1.])
    ov=ev+np.cross(spin_axis*7.292115e-5,offset)
    sun,_=EPHEMERIS.state(jd,10);out=[]
    if progress:progress(1,0,len(BODIES),'Evaluating local JPL / reconstruction trajectories')
    for index,(name,(target,radius,_,color)) in enumerate(BODIES.items()):
        if progress:progress(1,index,len(BODIES),name+': light time, parallax and apparent direction')
        p,_=EPHEMERIS.state(jd,target)
        if name=='Earth':
            out.append(dict(id=name,name=name,position_au=((p-sun)/AU).tolist(),radius_km=radius,color=color,type='planet',direction=None,ground_direction=None))
            continue
        direction,distance,retarded=apparent(epoch,obs,ov,target)
        local=basis@direction;alt=np.degrees(np.arcsin(np.clip(local[2],-1,1)));az=np.degrees(np.arctan2(local[0],local[1]))%360
        r=float(np.linalg.norm(retarded-sun)/AU)
        phase=0. if name=='Sun' else float(np.arccos(np.clip(np.dot(sun-retarded,obs-retarded)/(np.linalg.norm(sun-retarded)*distance),-1,1)))
        if name=='Sun':sun_direction=direction
        if name=='Moon':
            r=1.;import erfa
            longitude,waxing,phase_name=moon_phase(sun_direction,direction,erfa.ltpecl(epoch.year),(1+np.cos(phase))/2)
            moon_extra=dict(phase_angle_deg=float(np.degrees(phase)),elongation_longitude_deg=longitude,waxing=waxing,phase_name=phase_name,
                            phase_note='Topocentric illuminated fraction and Moon-minus-Sun ecliptic longitude (0 new, 90 first quarter, 180 full, 270 last quarter).')
        else:moon_extra={}
        ra=np.degrees(np.arctan2(direction[1],direction[0]))%360;dec=np.degrees(np.arcsin(direction[2]))
        out.append(dict(id=name,name=name,type='moon' if name=='Moon' else 'star' if name=='Sun' else 'planet',direction=direction.tolist(),ground_direction=local.tolist(),
            position_au=((p-sun)/AU).tolist(),radius_km=radius,color=color,distance_au=distance/AU,ra_deg=ra,dec_deg=dec,
            altitude_deg=float(alt),azimuth_deg=float(az),phase_fraction=(1+np.cos(phase))/2,**moon_extra,
            magnitude=float(brightness(name,max(r,1e-9),distance/AU,phase,photometric_geometry(name,jd,retarded,obs,sun))),angular_radius_deg=float(np.degrees(np.arctan2(radius,distance))),
            frame='ICRS apparent direction / heliocentric ICRS positions',time_scale='TDB',units={'position':'AU','radius':'km','angles':'degrees'},size_quality='Equatorial radius; spherical or axisymmetric visual approximation',photometry_quality='Mallama & Hilton (2018) model, as used by JPL Horizons' if name not in ('Moon','Pluto') else 'empirical phase law',**EPHEMERIS.source(jd)))
    if progress:progress(1,len(BODIES),len(BODIES),'Solar-system geometry ready')
    return out,obs,ov
