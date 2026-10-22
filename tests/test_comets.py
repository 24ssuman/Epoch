"""Comets: cached JPL windows only, sourced photometry, and tail geometry (ion anti-solar, dust lagging the motion)."""
import numpy as np,pytest
from fastapi.testclient import TestClient
from backend.app import app,compute_snapshot
from backend import comets

client=TestClient(app)

def test_comet_catalog_perihelia_match_jpl_elements():
    # JPL TP/QR are osculating two-body elements; the sampled minimum distance may differ by about a day / 0.01 AU.
    by={c['name']:c for c in client.get('/api/comets').json()['comets']}
    assert abs(by['Halley 1986']['perihelion_jd']-2446469.97)<1.5 and abs(by['Halley 1986']['perihelion_au']-.5749)<.02
    assert abs(by['Hale–Bopp 1997']['perihelion_jd']-2450539.63)<1 and abs(by['Hale–Bopp 1997']['perihelion_au']-.9146)<.01

def test_hale_bopp_brightness_uses_sourced_override():
    hb=next(c for c in compute_snapshot(2450539.6,22.57,88.36,0,0,200,max_magnitude=4.5,view='ground')['comets'] if c['name']=='Hale–Bopp 1997')
    assert -1.5<hb['magnitude']<0 and 'NSSDC' in hb['photometry_quality']

def test_tail_geometry_is_physical_in_direction():
    hb=next(c for c in compute_snapshot(2450539.6,22.57,88.36,0,0,200,max_magnitude=4.5)['comets'] if c['name']=='Hale–Bopp 1997')
    P=np.array(hb['position_au']);anti=P/np.linalg.norm(P)
    ion,dust=(next(t for t in hb['tails'] if t['kind']==k) for k in ('ion','dust'))
    axis=lambda t:(np.array(t['left']['points_au'])+np.array(t['right']['points_au']))/2
    ion_axis=axis(ion);d=ion_axis[-1]-ion_axis[0]
    assert np.dot(d/np.linalg.norm(d),anti)>.999                              # ion tail points straight away from the Sun
    pack=next(p for p in comets.packs() if p['meta']['name']=='Hale–Bopp 1997');V=pack['velocity'](2450539.6)
    dust_axis=axis(dust);bend=dust_axis[-1]-dust_axis[0]
    assert np.dot(bend/np.linalg.norm(bend),anti)>.5 and np.dot(bend,V)<0      # dust tail anti-solar but lagging the motion
    assert ion['intensity'][0]>ion['intensity'][-1] and len(ion['left']['ground_direction'])==comets.TAIL_SAMPLES

def test_no_comets_or_tails_outside_cached_windows_or_far_from_sun():
    assert compute_snapshot(2451545.,0,0,0,0,100,max_magnitude=4.5)['comets']==[]
    assert comets.tail_activity(5.,5.5)==(0.,0.) and comets.tail_activity(.6,5.5)[0]>comets.tail_activity(1.5,5.5)[0]

def test_comets_are_searchable_inside_their_window_only():
    assert [f['id'] for f in client.get('/api/search',params={'q':'hale','jd':2450539.6}).json() if f['type']=='comet']==['Hale–Bopp 1997']
    assert not [f for f in client.get('/api/search',params={'q':'hale','jd':2451545}).json() if f['type']=='comet']
    assert any(f['type']=='comet' for f in client.get('/api/search',params={'q':'comet','jd':2446470}).json())
    assert any(f['type']=='comet' for f in client.get('/api/search',params={'q':'धूमकेतु','jd':2446470}).json())

def test_peak_calibrated_comets_cite_sources_and_match_recorded_peaks():
    import json
    from backend.paths import DATA
    overrides={k:v for k,v in json.loads((DATA/'comets'/'photometry_overrides.json').read_text()).items() if isinstance(v,dict)}
    assert all(v.get('source') for v in overrides.values())
    assert {'Halley 1986','Halley 837','McNaught 2007','NEOWISE 2020','Ikeya–Seki 1965'}<=set(overrides)
    assert len({overrides[n]['M1'] for n in overrides if n.startswith('Halley ')})==1   # one comet, one brightness law
    names=[c['name'] for c in client.get('/api/comets').json()['comets']]
    assert len(names)>=29 and names.index('Halley 240 BCE')<names.index('Halley 1986')     # chronological list

def test_forward_scattering_phase_correction():
    assert abs(comets.phase_correction(90.))<1e-12                      # normalised at 90 degrees
    assert comets.phase_correction(170.)<comets.phase_correction(150.)<comets.phase_correction(120.)<0
    assert comets.phase_correction(170.,10.)<comets.phase_correction(170.,1.)   # dustier comets surge more

def test_tsuchinshan_atlas_peak_timing_emerges_from_geometry():
    # Calibration only fixes the overall level; the date of the forward-scattering peak comes from the geometry.
    from backend.ephemeris import EPHEMERIS,AU
    p=next(x for x in comets.packs() if x['meta']['name']=='Tsuchinshan–ATLAS 2024');best=(99,0)
    for jd in np.arange(2460580.5,2460600.5,.25):
        e,_=EPHEMERIS.state(jd,399);s,_=EPHEMERIS.state(jd,10);c=p['spline'](jd);P=(c-s)/AU
        m=p['M1']+5*np.log10(np.linalg.norm(c-e)/AU)+p['k1']*np.log10(np.linalg.norm(P))+comets.phase_correction(comets.phase_angle(P,(e-s)/AU),p['delta90'])
        best=min(best,(m,jd))
    assert abs(best[1]-2460592.5)<1.5 and -5.5<best[0]<-4.3            # 9 Oct 2024, about -4.9

@pytest.mark.parametrize('month,day,expected',[(6,15,5.74),(7,17,1.54),(7,29,-2.16),(8,10,1.26),(9,13,5.21)])
def test_halley_2061_matches_marcus_2023_forecast(month,day,expected):
    # Marcus (2023), ACM abstract 2348: forecast table for 1P/Halley in 2061 (0h UT, geocentric).
    from backend.ephemeris import EPHEMERIS
    from backend.astrotime import calendar_jd
    p=next(x for x in comets.packs() if x['meta']['name']=='Halley 2061');jd=calendar_jd(2061,month,day)
    earth,_=EPHEMERIS.state(jd,399);sun,_=EPHEMERIS.state(jd,10)
    assert abs(comets.magnitude(p,jd,p['spline'](jd),earth,sun)[0]-expected)<.05
