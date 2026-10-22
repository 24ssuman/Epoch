"""Independent reference and behavioral checks. No runtime network required."""
from backend.paths import ROOT,DATA
from backend.astrotime import calendar_jd,jd_calendar,Epoch,local_basis
from backend.ephemeris import EPHEMERIS,body_snapshot,brightness,AU
from backend.catalog import CATALOG
import pytest,numpy as np,json,math,socket

@pytest.mark.parametrize('year',[-14999,-13200,-1000,-1,0,1,1582,1900,2000,2026,5000])
@pytest.mark.parametrize('calendar',['gregorian','julian'])
def test_calendar_roundtrip(year,calendar):
    jd=calendar_jd(year,7,12,6.25,calendar);d=jd_calendar(jd,calendar)
    assert (d['year'],d['month'],d['day'])==(year,7,12)
    assert abs(d['hour']-6.25)<1e-6

def test_known_julian_dates_and_bce_boundary():
    assert calendar_jd(2000,1,1,12)==2451545.
    assert calendar_jd(1582,10,15,calendar='gregorian')==calendar_jd(1582,10,5,calendar='julian')
    assert calendar_jd(1)-calendar_jd(0)==366
    assert jd_calendar(calendar_jd(0))['display_year']==1
    with pytest.raises(ValueError):calendar_jd(1900,2,29)
    assert calendar_jd(1900,2,29,calendar='julian')
    with pytest.raises(ValueError):calendar_jd(-15000)  # 15,001 BCE: outside the supported interval
    with pytest.raises(ValueError):calendar_jd(5001)
    assert jd_calendar(calendar_jd(-14999))['display_year']==15000  # 15,000 BCE is the earliest supported year

@pytest.mark.parametrize('year',[-14999,-10000,0,2000,5000])
@pytest.mark.parametrize('lat',[-90,-33.9,0,51.4769,90])
def test_basis_is_right_handed_orthonormal(year,lat):
    e=Epoch(calendar_jd(year));b=local_basis(e,lat,88.3)
    assert np.max(np.abs(b@b.T-np.eye(3)))<1e-12
    assert abs(np.linalg.det(b)-1)<1e-12

def test_deep_rotation_is_never_claimed_measured():
    assert Epoch(calendar_jd(-14999)).rotation_quality=='assumed-rotation'
    assert Epoch(calendar_jd(5000)).rotation_quality=='assumed-rotation'

def test_magnitude_inverse_square():
    assert abs(brightness('Sun',1,2,0)-brightness('Sun',1,1,0)-5*np.log10(2))<1e-12
    assert brightness('Venus',1,1,0)<brightness('Venus',1,1,np.pi/2)

def test_prominent_star_values_and_color_order():
    CATALOG.load();e=Epoch(2451545);b=local_basis(e,0,0)
    stars,_=CATALOG.snapshot(e,b,np.zeros(3),np.zeros(3),500)
    sirius=next(s for s in stars if s['name']=='Sirius');betelgeuse=next(s for s in stars if s['name']=='Betelgeuse')
    assert -1.6<sirius['magnitude']< -1.3
    assert 2.5<sirius['distance_pc']<2.8
    def rgb(x):return [int(x[i:i+2],16) for i in [1,3,5]]
    sr=rgb(sirius['color']);br=rgb(betelgeuse['color'])
    assert br[0]/max(br[2],1)>sr[0]/max(sr[2],1)
    assert sirius['magnitude']<betelgeuse['magnitude']

def test_stellar_size_is_measured_and_smaller_than_moon():
    CATALOG.load()
    if not CATALOG.diameters:pytest.skip('JMDC diameter pack pending installation')
    e=Epoch(2451545);stars,_=CATALOG.snapshot(e,local_basis(e,0,0),np.zeros(3),np.zeros(3),300,detail=True)
    sirius=next(s for s in stars if s['name']=='Sirius')
    assert 5.5<sirius['angular_radius_deg']*7200000<6.5 # mas diameter
    assert 1.5<sirius['radius_km']/695700<2
    assert sirius['angular_radius_deg']<.00001
    assert 'measured' in sirius['diameter_measurement']['kind']

def test_horizons_apparent_positions():
    p=DATA/'references/horizons.json'
    assert p.exists(),'Saved Horizons reference data is required'
    refs=json.loads(p.read_text());assert len(refs)>=27
    residuals=[]
    for r in refs:
        e=Epoch(r['jd_tt']);basis=local_basis(e,r['lat'],r['lon'])
        bodies,_,_=body_snapshot(e,basis,r['lat'],r['lon'],0)
        body=next(b for b in bodies if b['name']==r['name'])
        u=e.matrix@np.array(body['direction']);ra=np.degrees(np.arctan2(u[1],u[0]))%360;dec=np.degrees(np.arcsin(u[2]))
        separation=np.hypot(((ra-r['ra_deg']+180)%360-180)*np.cos(np.radians(dec)),dec-r['dec_deg'])*3600
        residuals.append(dict(name=r['name'],jd_tt=r['jd_tt'],separation_arcsec=separation,altitude_residual_arcsec=(body['altitude_deg']-r['alt_deg'])*3600))
        assert separation<(2 if body['name']=='Moon' else 1),(r,separation)
    # The report is an explicitly requested artifact, retained within the workspace.
    (ROOT/'docs/modern-validation.json').write_text(json.dumps(dict(source='Saved JPL Horizons topocentric airless TT reference cases; IAU76/80 vs IAU06 frame bias included',cases=residuals),indent=2))

def test_polar_day_and_night():
    for month,expected in [(6,True),(12,False)]:
        e=Epoch(calendar_jd(2026,month,21,12));b,_,_=body_snapshot(e,local_basis(e,89.9,0),89.9,0,0)
        sun=next(x for x in b if x['name']=='Sun');assert (sun['altitude_deg']>0)==expected

def test_true_angular_sizes_change_with_distance():
    for jd in [calendar_jd(2026,1,1),calendar_jd(2026,7,1)]:
        e=Epoch(jd);b,_,_=body_snapshot(e,local_basis(e,0,0),0,0,0)
        sun=next(x for x in b if x['name']=='Sun')
        assert abs(sun['angular_radius_deg']-np.degrees(np.arctan2(sun['radius_km'],sun['distance_au']*AU)))<1e-12
        assert .25<sun['angular_radius_deg']<.28

def test_runtime_works_with_external_network_disabled(monkeypatch):
    def fail(*args,**kwargs):raise AssertionError('Runtime attempted a network request')
    monkeypatch.setattr(socket.socket,'connect',fail)
    from backend.app import snapshot_cached,comet_snapshot
    s=snapshot_cached(2451545.,51.4769,0,0,0,500)
    assert s['solar_system_available'] and len(s['stars'])==500
    assert not comet_snapshot(Epoch(calendar_jd(-14999)),np.eye(3),np.zeros(3))

def test_rebound_force_model_and_convergence():
    from backend.jobs import build_sim,IDS
    a,extras=build_sim();b,extras_b=build_sim(1e-11)
    assert a.N==27
    a.integrate(30.);b.integrate(30.)
    delta=np.array([[p.x,p.y,p.z] for p in a.particles])-np.array([[p.x,p.y,p.z] for p in b.particles])
    assert np.max(np.linalg.norm(delta,axis=1))*AU<.1
    # Independent JPL comparison is a model-discrepancy check, not merely a second integrator.
    for i,body in enumerate(IDS):
        p,_=EPHEMERIS.state(2451575.,body)
        assert np.linalg.norm(np.array([a.particles[i].x,a.particles[i].y,a.particles[i].z])*AU-p)<500


def test_de441_selects_segment_for_requested_ancient_date():
    from backend.ephemeris import EPHEMERIS
    for year in (-10000,-2000,4000):
        jd=calendar_jd(year)
        name,kernel=EPHEMERIS.kernel(jd)
        assert '441' in name
        selected=EPHEMERIS.segment(kernel,0,3,jd)
        assert selected.start_jd<=jd<=selected.end_jd
        earth,velocity=EPHEMERIS.state(jd,399)
        assert np.isfinite(earth).all() and np.isfinite(velocity).all()
        source=EPHEMERIS.source(jd)
        assert source['validity_jd']==[selected.start_jd,selected.end_jd]

def test_deep_time_orientation_is_continuous_with_iau_model():
    """Vondrak + IAU 2000A nutation + equation of origins (integrated CIO locator) must join the IAU 2006/2000A branch."""
    import erfa
    from backend.astrotime import cio_locator
    for year in (1499,2501):
        jd=calendar_jd(year,1,1,12);e=Epoch(jd);assert e.frame_model.startswith('Vondrak') and 'nutation' in e.frame_model
        t1=math.floor(jd);t2=jd-t1;gast=float(erfa.gst06a(t1,t2-e.dt/86400,t1,t2))
        assert abs(((e.sidereal-gast)*206264.806+648000)%1296000-648000)<1.   # arcsec
        assert np.max(np.abs(e.matrix-erfa.pnm06a(t1,t2)))<5e-6               # ~1 arcsec
        x,y=erfa.bpn2xy(erfa.ltpb(e.year));assert abs(cio_locator(e.year)-erfa.s06(t1,t2,x,y))<5e-7   # 0.1 arcsec
    assert 'nutation omitted' in Epoch(calendar_jd(-13000)).frame_model

def test_mean_anomaly_shift_identities():
    from backend.jobs import shift_mean_anomaly
    r=np.array([0.0026,0.0003,0.0001]);v=np.array([-0.00006,0.00058,0.00002]);mu=8.997e-10   # Earth+Moon, AU^3/day^2
    assert np.allclose(shift_mean_anomaly(r,v,0.,mu),r,rtol=0,atol=1e-14)
    assert np.allclose(shift_mean_anomaly(r,v,2*np.pi,mu),r,rtol=0,atol=1e-12)
    moved=shift_mean_anomaly(r,v,1e-3,mu);h=np.cross(r,v)
    assert abs(moved@h)<1e-18 and np.cross(r,moved)@h>0      # stays in the orbit plane, moves forward

def test_no_reconstruction_where_jpl_covers(tmp_path,monkeypatch):
    from backend import jobs
    monkeypatch.setattr(jobs,'JOB_DIR',tmp_path);monkeypatch.setattr(jobs,'log',lambda s:None)
    jobs.run(5000,direction='future')
    s=json.loads((tmp_path/'status.json').read_text());assert s['status']=='complete' and 'DE440/DE441' in s['message']
