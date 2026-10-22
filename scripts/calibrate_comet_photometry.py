"""Peak-calibrate comet brightness where JPL's M1/k1 miss the recorded apparition (offline; writes photometry_overrides.json).

The light-curve shape m = M1 + 5 log10(delta) + k1 log10(r) is kept (JPL k1, or the conventional k1 = 10, n = 4, when JPL
gives none); only M1 is shifted so the model's brightest geocentric magnitude inside the cached window, including the
Marcus (2007) forward-scattering term, equals a recorded peak. Recorded peaks are themselves estimates; each entry keeps its source.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from backend.paths import DATA
from backend import comets
from backend.ephemeris import EPHEMERIS,AU

# name: (recorded peak magnitude, source, note)
TARGETS={
 'Great Comet 1811':(0.0,'https://en.wikipedia.org/wiki/Great_Comet_of_1811 ; https://esky.glyphweb.com/comets/greatcometof1811.html','Magnitude about 0 in October 1811.'),
 'Donati 1858':(0.5,'https://ssd.jpl.nasa.gov/sb/great_comets.html ; https://en.wikipedia.org/wiki/Comet_Donati','Recorded as magnitude 0-1; midpoint used.'),
 'Great September Comet 1882':(-17.0,'https://en.wikipedia.org/wiki/Great_Comet_of_1882','Approximate estimate at perihelion (daylight, near the Sun). Fragment B orbit.'),
 'Great January Comet 1910':(-5.0,'https://en.wikipedia.org/wiki/Great_January_Comet_of_1910 ; https://www.astronomy.com/science/postcards-from-the-oort-cloud-sending-comets-through-the-mail/','About -5 at perihelion, partly forward scattering.'),
 'Ikeya–Seki 1965':(-10.0,'https://en.wikipedia.org/wiki/Comet_Ikeya%E2%80%93Seki ; https://www.astronomy.com/science/15-greatest-comets-of-our-time/','About -10 at perihelion (some estimates -11). Fragment A orbit.'),
 'NEOWISE 2020':(0.75,'https://en.wikipedia.org/wiki/Comet_NEOWISE ; https://alpo-astronomy.org/cometblog/?m=202007','Recorded as magnitude 0.5-1 near perihelion; midpoint used.'),
 'McNaught 2007':(-5.5,'https://en.wikipedia.org/wiki/Comet_McNaught ; https://www.virtualtelescope.eu/?p=13961','Estimated peak -5.5 (NASA APOD gives -5).'),
 'Tsuchinshan–ATLAS 2024':(-4.9,'https://www.irida-observatory.org/CCD/C2023A3_2024.10.23/C2023A3_24.10.23.html (COBS reports) ; https://skyandtelescope.org/astronomy-news/observing-news/get-ready-for-comet-tsuchinshan-atlas-the-best-is-yet-to-come/','Peak about -4.9 shortly after 9 Oct 2024, a forward-scattering spike (now modelled); COBS consensus 1-2 in early October.'),
}
# Halley: Marcus's published photometric model for 1P, used for every cached apparition (one comet, one model).
HALLEY_MODEL=dict(method='published model (Marcus 2023)',segments=dict(pre=dict(M1=4.,k1=10.,delta90=2.),post=dict(M1=3.4,k1=7.5,delta90=5.),ramp_days=20),
    M1=4.,k1=10.,source='Marcus, J. N. (2023), Forward Scattering Brightness Enhancement of Halley\'s Comet in 2061, Asteroids Comets Meteors 2023, abstract 2348 (https://www.hou.usra.edu/meetings/acm2023/eposter/2348.pdf)',
    note='m90 = H0 + 5 log delta + 2.5 n log r with H0, n = 4, 4 before perihelion and 3.4, 3.0 after; delta90 = 2 before and 5 after perihelion, interpolated as 3.5 + 0.075 (t - T) near perihelion; plus the Marcus (2007) scattering function.')

def base_photometry(pack):
    path=next(p for p in (DATA/'comets').glob('*.npz') if json.loads(str(np.load(p)['metadata']))['name']==pack['meta']['name'])
    text=path.with_suffix('.txt').read_text(errors='replace') if path.with_suffix('.txt').exists() else ''
    m1,k1,how=comets._photometry(text,None)
    return (m1,k1,'JPL') if 'JPL Horizons' in how else (None,10.,'assumed k1=10 (n=4)')

# Recorded peaks are observations, so only moments at least this far from the Sun count, except comets recorded in daylight beside it.
MIN_ELONGATION=15.
DAYLIGHT_PEAKS={'Great September Comet 1882','Ikeya–Seki 1965','Great January Comet 1910','McNaught 2007','Tsuchinshan–ATLAS 2024'}

def peak_offset(pack,k1):
    """Brightest observable geocentric magnitude with M1 = 0 in the window (distance, activity and forward-scattering terms)."""
    best=np.inf;limit=0. if pack['meta']['name'] in DAYLIGHT_PEAKS else MIN_ELONGATION
    for jd in pack['times'][::2]:
        try:earth,_=EPHEMERIS.state(jd,399);sun,_=EPHEMERIS.state(jd,10)
        except ValueError:continue
        c=pack['spline'](jd);P=(c-sun)/AU;phase=comets.phase_angle(P,(earth-sun)/AU)
        a,b=sun-earth,c-earth
        if np.degrees(np.arccos(np.clip(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b),-1,1)))<limit:continue
        best=min(best,5*np.log10(np.linalg.norm(c-earth)/AU)+k1*np.log10(np.linalg.norm(P))+comets.phase_correction(phase,pack['delta90']))
    return best

if __name__=='__main__':
    path=DATA/'comets'/'photometry_overrides.json';overrides=json.loads(path.read_text())
    packs={p['meta']['name']:p for p in comets.packs()}
    for name,(peak,source,note) in TARGETS.items():
        if name not in packs:continue
        m1,k1,how=base_photometry(packs[name]);M1=peak-peak_offset(packs[name],k1)
        overrides[name]=dict(M1=round(float(M1),2),k1=k1,method='peak-calibrated',recorded_peak=peak,
            reason=f'JPL M1/k1 {"absent" if m1 is None else f"({m1:g}, {k1:g})"} do not match the recorded peak; k1 {how}; M1 shifted to match.',source=source,note=note)
        print(f'{name:28s} M1={M1:6.2f} k1={k1:5.2f} -> peak {peak}')
    for name in packs:
        if name.startswith('Halley '):overrides[name]=dict(HALLEY_MODEL)
    print('Halley apparitions: Marcus (2023) model')
    path.write_text(json.dumps(overrides,ensure_ascii=False,indent=1))
