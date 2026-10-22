"""Offline checks against saved NASA data (JPL Horizons responses and NASA GSFC eclipse-site pages).

The data was saved by `scripts/crosscheck_nasa.py fetch`; see docs/NASA_CROSSCHECK.md for the full comparison.
"""
import json,math,re
import numpy as np,pytest,erfa
from scripts.crosscheck_nasa import REF,YEARS,JDS,APP,TARGET,astrometric,rows,sep,eclipse_rows,read_deltat_table,part_d,ECLIPSE_PAGES
from backend.astrotime import calendar_jd,delta_t,Epoch
from backend.ephemeris import EPHEMERIS

pytestmark=pytest.mark.skipif(not (REF/'geo-10.json').exists(),reason='NASA cross-check data not saved yet (scripts/crosscheck_nasa.py fetch)')

def test_geocentric_directions_match_horizons_everywhere():
    EPHEMERIS.refresh();worst=0.
    for name,cmd in APP.items():
        d=json.loads((REF/f'geo-{cmd}.json').read_text())
        for jd,row in zip([float(x) for x in d['query']['TLIST'].split(',')],rows(d)):
            ra,dec,delta=map(float,row[3:6])
            h=np.array([math.cos(math.radians(dec))*math.cos(math.radians(ra)),math.cos(math.radians(dec))*math.sin(math.radians(ra)),math.sin(math.radians(dec))])
            u,dist=astrometric(EPHEMERIS,jd,TARGET[name]);worst=max(worst,sep(u,h))
            assert abs(dist/149597870.7-delta)*149597870.7<1.,(name,jd)
    # DE440 (used by the app for 1550-2650) vs Horizons' DE441 is the largest term: 0.24 arcsec for the Moon in 1600
    assert worst<0.3

def test_delta_t_within_nasa_standard_error():
    table,_=read_deltat_table();assert len(table)>=25
    for year,value,error in table:
        if error is not None:assert abs(delta_t(year)-value)<=error,(year,delta_t(year),value,error)
        else:assert abs(delta_t(year)-value)<1.

def test_greatest_eclipse_time_agrees_with_nasa_canon_in_modern_era():
    eclipses=[r for y in (1801,1901,2001) for r in eclipse_rows(y)]
    assert len(eclipses)>250
    result=part_d(eclipses[::10])
    assert len(result)>15
    assert max(abs(x['time_diff_seconds']) for x in result)<2.   # measured: within 0.7 s
    assert max(abs(x['gamma_diff']) for x in result)<5e-4

def test_comet_splines_match_horizons_off_node():
    from backend import comets
    errors=[]
    for pack in comets.packs():
        key=re.sub(r'[^A-Za-z0-9]+','_',pack['meta']['name'])
        path=REF/f'comet-{key}-vec.json'
        if not path.exists():continue
        for row in rows(json.loads(path.read_text())):
            jd=float(row[0])
            if pack['times'][0]<=jd<=pack['times'][-1]:   # includes perihelion epochs; sungrazers use data/comets/dense samples
                errors.append(np.linalg.norm(pack['spline'](jd)-np.array([float(x) for x in row[2:5]])))
    assert len(errors)>140
    assert np.median(errors)<1. and max(errors)<100.   # measured: max 26 km (Kohoutek at perihelion); was 28,000 km before densifying

@pytest.mark.parametrize('year',[1000,3000])
def test_deep_time_sidereal_angle_matches_iau_gast(year):
    """The long-term-precession branch must agree with IAU 2006/2000A GAST to 1 arcsec 1,000 years from 2000 (it was off by
    25.6 deg before the sign fix, and by 138 arcsec before the equation of origins and nutation were added)."""
    jd=calendar_jd(year,1,1,12);e=Epoch(jd);assert e.frame_model.startswith('Vondrak')
    tt1=math.floor(jd);tt2=jd-tt1;gast=float(erfa.gst06a(tt1,tt2-e.dt/86400,tt1,tt2))
    assert abs((math.degrees(e.sidereal-gast)*3600+648000)%1296000-648000)<1.

def test_planet_magnitudes_match_horizons_apmag():
    """Mallama & Hilton (2018), as used by Horizons. Limits are the measured maxima rounded up (2016-2036, 30-day steps)."""
    from scripts.crosscheck_nasa import part_g
    g=part_g();limits={'Moon':.06,'Mercury':.01,'Venus':.01,'Mars':.12,'Jupiter':.01,'Saturn':.11,'Uranus':.01,'Neptune':.01}
    for name,limit in limits.items():
        diffs=[abs(x['diff']) for x in g if x['body']==name]
        assert len(diffs)>200 and max(diffs)<limit,(name,max(diffs))
    saturn=sorted(abs(x['diff']) for x in g if x['body']=='Saturn')
    assert saturn[-2]<.03   # only the unlit-ring-face date (April 2025) departs on purpose

def test_moon_phase_matches_horizons():
    """App phase geometry (geocentric observer) vs Horizons Sun-Moon-Earth angle (2016-2036, 30-day steps); the name follows the
    Moon-minus-Sun longitude, so waxing must hold for 0-180 degrees."""
    from backend.ephemeris import apparent,EPHEMERIS,moon_phase
    import erfa
    d=json.loads((REF/'mag-301.json').read_text());start=calendar_jd(2016,1,1,0);worst=0.;fractions=[]
    for i,row in enumerate(rows(d)):
        e=Epoch(start+30*i);jd=e.tdb1+e.tdb2;earth,ev=EPHEMERIS.state(jd,399);sun,_=EPHEMERIS.state(jd,10)
        u,dist,moon=apparent(e,earth,ev,301);su,_,_=apparent(e,earth,ev,10)
        phase=math.degrees(math.acos(np.clip((sun-moon)@(earth-moon)/np.linalg.norm(sun-moon)/np.linalg.norm(earth-moon),-1,1)))
        worst=max(worst,abs(phase-float(row[9])));f=(1+math.cos(math.radians(phase)))/2
        lon,waxing,name=moon_phase(su,u,erfa.ltpecl(e.year),f);fractions.append(f)
        assert waxing==(lon<180) and (name.startswith('Waxing') or name in ('New Moon','Full Moon','First Quarter')) is (waxing or name in ('New Moon','Full Moon'))
    assert worst<.02,worst   # degrees; measured 0.012
    assert min(fractions)<.05 and max(fractions)>.95
