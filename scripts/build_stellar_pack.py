"""Build a bounded six-dimensional galactic stellar-motion pack, fully offline."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA,TMP,guard
os.environ.setdefault('OMP_NUM_THREADS','2')
import json,time,hashlib,argparse
import numpy as np
from backend.catalog import CATALOG
from backend.astrotime import MIN_YEAR,MAX_YEAR
from scripts.setup_data import log,record

def build(limit_mag=6.5):
    from galpy.orbit import Orbit
    from galpy.potential import MWPotential2014
    from galpy.util import conversion
    CATALOG.load();rows=CATALOG.rows
    if not rows:raise RuntimeError('Install stellar catalog first')
    # Propagate each catalog reference epoch to J2000 before initializing Galactic trajectories.
    _,_,dist=CATALOG.propagate(2000.)
    supported=np.where(np.isfinite(CATALOG.distance)&np.array([r['rv_known'] and r['pmra'] is not None and r['pmdec'] is not None for r in rows]))[0]
    # Retain stars that are or become within a magnitude-12 render limit in the requested interval.
    possible=CATALOG.mags.copy()
    for yr in np.linspace(MIN_YEAR,MAX_YEAR,25):possible=np.minimum(possible,CATALOG.propagate(yr)[1])
    indices=supported[possible[supported]<=limit_mag]
    years=np.unique(np.concatenate([[float(MIN_YEAR)],np.arange(np.ceil(MIN_YEAR/1000.)*1000.,MAX_YEAR+1.,1000.),[2000.]]))
    guard(len(years)*len(indices)*3*4*2+50_000_000)
    catalog_digest=hashlib.file_digest((DATA/'catalogs/stars.json').open('rb'),'sha256').hexdigest()
    digest=hashlib.sha256(catalog_digest.encode()+indices.tobytes()+years.tobytes()+b'fixed-ICRS-galpy-v2').hexdigest()
    ro,vo=8.122,229.;scale=conversion.time_in_Gyr(vo,ro)
    pos=np.zeros((len(years),len(indices),3),dtype='float32')
    packdir=DATA/'catalogs/stellar-checkpoints';packdir.mkdir(exist_ok=True)
    (packdir/'README.md').write_text('# Stellar checkpoints\nResumable galpy batches. These files are retained; rebuild when the source catalog checksum changes.\n')
    for start in range(0,len(indices),512):
        idx=indices[start:start+512];checkpoint=packdir/f'{digest[:10]}-{start:07d}.npz'
        if checkpoint.exists():
            with np.load(checkpoint) as g:pos[:,start:start+len(idx)]=g['position']
            continue
        init=[]
        for j in idx:
            r=rows[j]
            # Space-motion catalog propagation to J2000, including radial velocity and perspective acceleration.
            import erfa
            parallax=1/r['distance'];ra=np.radians(r['ra']);dec=np.radians(r['dec'])
            p=erfa.pmsafe(ra,dec,(r['pmra'] or 0)/206264806.247/max(np.cos(dec),1e-8),(r['pmdec'] or 0)/206264806.247,parallax,r['rv'] or 0,2451545.,(r['epoch']-2000)*365.25,2451545.,0.)
            init.append([np.degrees(p[0]),np.degrees(p[1]),1/p[4]/1000,p[2]*206264806.247*np.cos(p[1]),p[3]*206264806.247,p[5]])
        for direction in [-1,1]:
            y=years[years<=2000] if direction<0 else years[years>=2000]
            if direction<0:y=y[::-1]
            ts=(y-2000)*1e-9/scale
            sun=Orbit(ro=ro,vo=vo,zo=.0208,solarmotion='schoenrich');sun.integrate(ts,MWPotential2014,method='dop853_c',progressbar=False)
            stars=Orbit(np.array(init),radec=True,ro=ro,vo=vo,zo=.0208,solarmotion='schoenrich');stars.integrate(ts,MWPotential2014,method='dop853_c',progressbar=False)
            # Translate the observer with the Sun while keeping ICRS axes fixed.
            # Orbit.ra(obs=Sun) rotates axes with the observer and also flattens vector times;
            # use the documented fixed Galactocentric->heliocentric transform explicitly.
            from galpy.util import coords
            sx=stars.x(ts)-sun.x(ts)[None,:]+float(sun.x(0.))
            sy=stars.y(ts)-sun.y(ts)[None,:]+float(sun.y(0.))
            sz=stars.z(ts)-sun.z(ts)[None,:]+float(sun.z(0.))
            helio=coords.galcenrect_to_XYZ(sx.ravel(),sy.ravel(),sz.ravel(),Xsun=float(sun.x(0.)),Zsun=float(sun.z(0.)))
            lb=coords.XYZ_to_lbd(helio[:,0],helio[:,1],helio[:,2],degree=True)
            rd=coords.lb_to_radec(lb[:,0],lb[:,1],degree=True,epoch=None)
            ra=np.radians(rd[:,0]).reshape(len(idx),len(ts));dec=np.radians(rd[:,1]).reshape(len(idx),len(ts));d=lb[:,2].reshape(len(idx),len(ts))*1000
            coordinates=np.stack([d*np.cos(dec)*np.cos(ra),d*np.cos(dec)*np.sin(ra),d*np.sin(dec)],axis=-1).transpose(1,0,2)
            for k,year in enumerate(y):pos[np.where(years==year)[0][0],start:start+len(idx)]=coordinates[k]
        np.savez_compressed(checkpoint,position=pos[:,start:start+len(idx)])
        log(f'Galactic trajectories: {min(start+512,len(indices))}/{len(indices)} supported stars checkpointed')
    path=DATA/'catalogs/galactic.npz';np.savez_compressed(path,years=years,indices=indices,positions=pos,catalog_sha256=catalog_digest,configuration_sha256=digest,
        model='galpy MWPotential2014; ro=8.122 kpc, vo=229 km/s, zo=0.0208 kpc; Schoenrich solar motion')
    record(path,'https://docs.galpy.org/en/v1.12.0/','galpy BSD; source catalog attribution applies')
    log(f'Completed Galactic stellar-motion pack: {len(indices)} stars, {len(years)} epochs; absent velocities still use flagged rectilinear estimates')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--limit-mag',type=float,default=6.5);args=parser.parse_args();build(args.limit_mag)
