"""Calendar arithmetic and explicitly graded Earth-rotation assumptions."""
import math
import erfa
import numpy as np
from dataclasses import dataclass
from functools import lru_cache

@lru_cache(maxsize=1)
def iers_table():
    from astropy.utils import iers
    iers.conf.auto_download=False
    return iers.IERS_A.open(iers.IERS_A_FILE)

MIN_YEAR, MAX_YEAR = -14999, 5000  # astronomical years: 15,000 BCE through 5,000 CE. To extend, see README 'Extending the date range'.

def calendar_jd(year, month=1, day=1, hour=0., calendar='gregorian'):
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f'Date must be within {1-MIN_YEAR:,} BCE–{MAX_YEAR:,} CE')
    if not 1 <= month <= 12 or not 0 <= hour < 24:
        raise ValueError('Invalid month or hour')
    leap = year % 4 == 0 and (calendar == 'julian' or year % 100 != 0 or year % 400 == 0)
    days = [31, 29 if leap else 28, 31,30,31,30,31,31,30,31,30,31]
    if not 1 <= day <= days[month-1]: raise ValueError('Invalid day for month')
    y, m = (year-1, month+12) if month <= 2 else (year, month)
    a = math.floor(y/100)
    b = 2-a+math.floor(a/4) if calendar == 'gregorian' else 0
    return math.floor(365.25*(y+4716))+math.floor(30.6001*(m+1))+day+b-1524.5+hour/24

def jd_calendar(jd, calendar='gregorian'):
    z = math.floor(jd+0.5); f = jd+0.5-z
    if calendar == 'gregorian':
        alpha = math.floor((z-1867216.25)/36524.25)
        a = z+1+alpha-math.floor(alpha/4)
    else: a=z
    b=a+1524; c=math.floor((b-122.1)/365.25); d=math.floor(365.25*c); e=math.floor((b-d)/30.6001)
    day=b-d-math.floor(30.6001*e); month=e-1 if e < 14 else e-13; year=c-4716 if month>2 else c-4715
    return dict(year=year,month=month,day=day,hour=f*24,era='BCE' if year<=0 else 'CE',display_year=1-year if year<=0 else year)

def delta_t(y):
    # Espenak & Meeus. Beyond -1999..3000 this is a scenario, not a calibrated prediction.
    if y < -500 or y >= 2150: return -20+32*((y-1820)/100)**2
    if y < 500:
        u=y/100; return 10583.6-1014.41*u+33.78311*u**2-5.952053*u**3-.1798452*u**4+.022174192*u**5+.0090316521*u**6
    if y < 1600:
        u=(y-1000)/100; return 1574.2-556.01*u+71.23472*u**2+.319781*u**3-.8503463*u**4-.005050998*u**5+.0083572073*u**6
    if y < 1700:
        t=y-1600; return 120-.9808*t-.01532*t*t+t**3/7129
    if y < 1800:
        t=y-1700; return 8.83+.1603*t-.0059285*t*t+.00013336*t**3-t**4/1174000
    if y < 1860:
        t=y-1800; return 13.72-.332447*t+.0068612*t**2+.0041116*t**3-.00037436*t**4+.0000121272*t**5-.0000001699*t**6+.000000000875*t**7
    if y < 1900:
        t=y-1860; return 7.62+.5737*t-.251754*t*t+.01680668*t**3-.0004473624*t**4+t**5/233174
    if y < 1920:
        t=y-1900; return -2.79+1.494119*t-.0598939*t*t+.0061966*t**3-.000197*t**4
    if y < 1941:
        t=y-1920; return 21.20+.84493*t-.0761*t*t+.0020936*t**3
    if y < 1961:
        t=y-1950; return 29.07+.407*t-t*t/233+t**3/2547
    if y < 1986:
        t=y-1975; return 45.45+1.067*t-t*t/260-t**3/718
    if y < 2005:
        t=y-2000; return 63.86+.3345*t-.060374*t*t+.0017275*t**3+.000651814*t**4+.00002373599*t**5
    if y < 2050:
        t=y-2000; return 62.92+.32217*t+.005589*t*t
    return -20+32*((y-1820)/100)**2-.5628*(2150-y)

NUTATION_YEARS = 4000  # beyond this the IAU 2000A fundamental-argument polynomials are not trusted; mean equator used

@lru_cache(maxsize=1)
def _cio_spline():
    # s(t) = -integral (X dY - Y dX)/(1+Z) dt from J2000, with X,Y,Z the Vondrak mean CIP (IERS Conventions 2010 eq. 5.13).
    # Matches erfa.s06 to 0.03" within 1000 years of J2000 (periodic nutation terms of s, < 1 mas, are omitted).
    from scipy.integrate import cumulative_trapezoid
    from scipy.interpolate import CubicSpline
    years=np.arange(MIN_YEAR-200.,MAX_YEAR+202.,2.)
    pole=np.array([erfa.ltpequ(y) for y in years]);t=(years-2000)/100
    x,y,z=pole.T;rate=(x*np.gradient(y,t)-y*np.gradient(x,t))/(1+z)
    s=-cumulative_trapezoid(rate,t,initial=0)
    return CubicSpline(years,s-np.interp(2000.,years,s))

def cio_locator(year):
    """CIO locator s (radians) at a Julian epoch, from the long-term pole."""
    return float(_cio_spline()(year))

@dataclass
class Epoch:
    jd: float
    offset: float = 0.
    def __post_init__(self):
        self.calendar = jd_calendar(self.jd)
        calendar_year = self.calendar['year']+(self.calendar['month']-.5)/12
        self.year = float(erfa.epj(math.floor(self.jd),self.jd-math.floor(self.jd)))
        self.tt1 = math.floor(self.jd); self.tt2 = self.jd-self.tt1
        self.dt = delta_t(calendar_year)+self.offset
        self.polar_motion=(0.,0.)
        self.rotation_quality = 'historical-model' if -1999 <= self.year <= 3000 else 'assumed-rotation'
        # Measured UT1 and leap seconds only within the bundled IERS interval.
        if 1973 <= self.year <= 2027:
            try:
                from astropy.time import Time
                from astropy.utils import iers
                iers.conf.auto_download=False
                t=Time(self.tt1,self.tt2,format='jd',scale='tt')
                table=iers_table()
                if float(table['MJD'][0].value) <= t.mjd <= float(table['MJD'][-1].value):
                    with iers.earth_orientation_table.set(table):
                        self.dt=float((t.tt.jd1-t.ut1.jd1+t.tt.jd2-t.ut1.jd2)*86400)+self.offset
                    row=int(np.clip(np.searchsorted(table['MJD'].value,t.mjd),0,len(table)-1))
                    self.rotation_quality='predicted-IERS' if str(table['UT1Flag'][row]).strip()=='P' else 'measured-IERS'
                    xp,yp=table.pm_xy(t);self.polar_motion=(float(xp.to_value('rad')),float(yp.to_value('rad')))
            except (ValueError,ImportError,TypeError): pass
        self.ut1 = self.tt1 + (self.tt2-self.dt/86400)
        # Geocentric Fairhead–Bretagnon periodic TT->TDB; deep-time approximation flagged.
        correction=float(erfa.dtdb(self.tt1,self.tt2,0.,0.,0.,0.)) if 1600 < self.year < 2400 else 0.
        self.tdb1=self.tt1; self.tdb2=self.tt2+correction/86400
        if abs(self.year-2000) <= 500:
            self.matrix=erfa.pnm06a(self.tt1,self.tt2)
            self.sidereal=float(erfa.gst06a(self.tt1,self.tt2-self.dt/86400,self.tt1,self.tt2))
            self.frame_model='IAU 2006/2000A'
        else:
            # Vondrak (2011) long-term precession, plus IAU 2000A nutation while its argument polynomials stay credible.
            self.matrix=erfa.ltpb(self.year)
            nutated=abs(self.year-2000) <= NUTATION_YEARS
            if nutated:
                dpsi,deps=erfa.nut06a(self.tt1,self.tt2)
                eps=math.acos(float(np.clip(erfa.ltpequ(self.year)@erfa.ltpecl(self.year),-1,1)))  # Vondrak mean obliquity
                self.matrix=erfa.numat(eps,dpsi,deps)@self.matrix
            # Sidereal angle = Earth rotation angle (from UT1) minus the equation of origins. The CIO locator s is
            # integrated from the Vondrak pole (cio_locator); the IAU s06 polynomial diverges beyond ~1000 years.
            era=float(erfa.era00(self.tt1,self.tt2-self.dt/86400))
            self.sidereal=era-float(erfa.eors(self.matrix,cio_locator(self.year)))
            self.frame_model=('Vondrak 2011 long-term precession'+(' + IAU 2000A nutation' if nutated else '; mean equator (nutation omitted)')+
                              '; equation of origins with integrated CIO locator')
    def metadata(self):
        return dict(jd_tt=[self.tt1,self.tt2],jd_tdb=[self.tdb1,self.tdb2],jd_ut1=self.ut1,delta_t_seconds=self.dt,
                    rotation_quality=self.rotation_quality,frame_model=self.frame_model,
                    time_note='Date entry is TT. UTC is not extrapolated into prehistory or the distant future.')

def local_basis(epoch, lat, lon):
    phi=math.radians(lat);lam=math.radians(lon)
    east=np.array([-math.sin(lam),math.cos(lam),0.])
    north=np.array([-math.sin(phi)*math.cos(lam),-math.sin(phi)*math.sin(lam),math.cos(phi)])
    up=np.array([math.cos(phi)*math.cos(lam),math.cos(phi)*math.sin(lam),math.sin(phi)])
    polar=erfa.pom00(*epoch.polar_motion,float(erfa.sp00(epoch.tt1,epoch.tt2)))
    spin=erfa.rz(epoch.sidereal,np.eye(3))
    return np.array([east,north,up])@polar@spin@epoch.matrix
