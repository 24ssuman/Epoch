from .paths import DATA
import json, math, threading
from functools import wraps

def synchronized(method):
    @wraps(method)
    def wrapped(self,*args,**kwargs):
        with self.lock:return method(self,*args,**kwargs)
    return wrapped
import numpy as np
import erfa
from .sanskrit import SANSKRIT
STAR_LIMIT=5.76  # common apparent-magnitude limit: the faintest book-named star (Asterope, 5.756-5.761 over the interval)

PC_KM=3.085677581491367e13
class Catalog:
    def __init__(self):self.rows=[];self.stamp=0;self.cache={};self.lock=threading.RLock()
    @synchronized
    def load(self):
        p=DATA/'catalogs/stars.json'
        if not p.exists():return
        diameter_path=DATA/'catalogs/diameters.json';st=p.stat();ds=diameter_path.stat() if diameter_path.exists() else None
        stamp=(st.st_size,st.st_mtime_ns,(ds.st_size,ds.st_mtime_ns) if ds else None)
        if stamp==self.stamp:return
        self.rows=json.loads(p.read_text());self.stamp=stamp;self.cache={}
        for r in self.rows:
            if r['source'].startswith('HYG') and not r['rv']:r['rv_known']=False
        diameters=DATA/'catalogs/diameters.json';self.diameters=json.loads(diameters.read_text()) if diameters.exists() else {}
        self.ra=np.radians([r['ra'] for r in self.rows]);self.dec=np.radians([r['dec'] for r in self.rows])
        self.unit=np.column_stack([np.cos(self.dec)*np.cos(self.ra),np.cos(self.dec)*np.sin(self.ra),np.sin(self.dec)])
        east=np.column_stack([-np.sin(self.ra),np.cos(self.ra),np.zeros(len(self.rows))]);north=np.column_stack([-np.sin(self.dec)*np.cos(self.ra),-np.sin(self.dec)*np.sin(self.ra),np.cos(self.dec)])
        self.distance=np.array([r['distance'] if r['distance'] and 0<r['distance']<100000 else np.nan for r in self.rows])
        self.pm=np.array([[r['pmra'] or 0,r['pmdec'] or 0] for r in self.rows])/206264806.247
        self.tangent=east*self.pm[:,0,None]+north*self.pm[:,1,None]
        self.rv=np.array([r['rv'] or 0 for r in self.rows])*31557600/PC_KM
        self.epochs=np.array([r['epoch'] for r in self.rows]);self.mags=np.array([r['mag'] for r in self.rows])
        self.id_index={r['id']:i for i,r in enumerate(self.rows)}
        finite=np.nan_to_num(self.distance,nan=1.);self.velocity=self.tangent*finite[:,None]+self.unit*self.rv[:,None]
        self.speed2=np.sum(self.velocity*self.velocity,axis=1)
    @synchronized
    def screen_magnitudes(self,year):
        self.load();dt=year-self.epochs;known=np.isfinite(self.distance);mag=self.mags.copy()
        # Cheap distance-only screening. No apparent-coordinate, color or diameter work for excluded stars.
        d2=self.distance[known]**2+2*self.distance[known]*self.rv[known]*dt[known]+self.speed2[known]*dt[known]**2
        mag[known]+=2.5*np.log10(np.maximum(d2/self.distance[known]**2,1e-24))
        return mag
    @synchronized
    def propagate(self,year,indices=None):
        self.load()
        if not self.rows:return np.empty((0,3)),np.empty(0),[]
        idx=np.arange(len(self.rows)) if indices is None else np.asarray(indices)
        dt=year-self.epochs[idx];known=np.isfinite(self.distance[idx]);p=self.unit[idx]+self.tangent[idx]*dt[:,None]
        p[known]=self.unit[idx[known]]*self.distance[idx[known],None]+self.velocity[idx[known]]*dt[known,None]
        d=np.linalg.norm(p,axis=1);unit=p/np.maximum(d[:,None],1e-15)
        mag=self.mags[idx].copy();mag[known]+=5*np.log10(np.maximum(d[known]/self.distance[idx[known]],1e-12))
        return unit,mag,d
    @synchronized
    def book_mask(self):
        """Stars named in books/mahabharat_histroy.pdf. The common limit already includes them; this only keeps Asterope (up to 5.7605) at every epoch."""
        SANSKRIT.load()
        if self.cache.get('book_stamp')!=(SANSKRIT.stamp,self.stamp):
            mask=np.zeros(len(self.rows),dtype=bool);mask[[self.id_index[i] for i in SANSKRIT.book_ids() if i in self.id_index]]=True
            self.cache['book']=mask;self.cache['book_stamp']=(SANSKRIT.stamp,self.stamp)
        return self.cache['book']
    @synchronized
    def snapshot(self,epoch,basis,observer,velocity,limit=10000,progress=None,max_magnitude=12.,preview=None,statistics=None,only_id=None,view='space',horizon_only=False,detail=None):
        """view='ground' returns only horizon coordinates per star; 'space' adds ICRS directions for space cameras.
        horizon_only drops stars more than 2 degrees below the horizon (hidden by the ground). detail adds per-star
        provenance (defaults to True only for single-object requests)."""
        self.load()
        max_magnitude=min(max_magnitude,STAR_LIMIT)
        if not self.rows:return [],'missing-catalog'
        detail=only_id is not None if detail is None else detail;book=self.book_mask()
        if only_id is not None:
            j=self.id_index.get(only_id)
            candidates=np.array([j],dtype=int) if j is not None and (book[j] or self.screen_magnitudes(epoch.year)[j]<=max_magnitude+.5) else np.array([],dtype=int)
        else:
            estimate=self.screen_magnitudes(epoch.year);candidates=np.where((estimate<=max_magnitude+.5)|book)[0]
        if progress:progress(2,0,len(candidates),f'Brightness screen: {len(candidates):,} candidates; detailed faint-star work skipped')
        u,m,distances=self.propagate(epoch.year,candidates)
        # Work only on screened candidates, not three full-catalog scratch arrays.
        unit,mag,d=u,m,distances
        idx=candidates
        if progress:progress(2,len(candidates),len(candidates),'Candidate stellar space motions evaluated')
        dynamics='rectilinear space motion'
        # Galactic trajectories are generated by a separate resumable pack builder.
        pack=DATA/'catalogs/galactic.npz'
        if abs(epoch.year-2000)>500 and pack.exists():
            if self.cache.get('galactic_stamp')!=pack.stat().st_mtime:
                with np.load(pack) as packed:self.cache['galactic']={k:packed[k] for k in packed.files}
                self.cache['galactic_lookup']={int(v):i for i,v in enumerate(self.cache['galactic']['indices'])}
                self.cache['galactic_stamp']=pack.stat().st_mtime
            g=self.cache['galactic'];years=g['years'];lookup=self.cache['galactic_lookup']
            if years[0]<=epoch.year<=years[-1]:
                k=min(np.searchsorted(years,epoch.year),len(years)-1);k=max(1,k);t=(epoch.year-years[k-1])/(years[k]-years[k-1])
                for ci,j in enumerate(idx):
                    if int(j) in lookup and self.rows[j]['rv_known']:
                        x=lookup[int(j)];p=(1-t)*g['positions'][k-1,x]+t*g['positions'][k,x]
                        dist=np.linalg.norm(p);unit[ci]=p/dist;mag[ci]=self.mags[j]+5*np.log10(dist/self.distance[j]);d[ci]=dist
                dynamics='galpy MWPotential2014 where six-dimensional data available; rectilinear otherwise'
        order=np.flatnonzero((mag<=max_magnitude)|book[candidates])
        order=order[np.argsort(mag[order],kind='stable')][:limit]
        idx=candidates[order];unit=unit[order];mag=mag[order];d=d[order]
        v=velocity/299792.458;em=np.linalg.norm(observer)/149597870.7
        selected=unit.copy()
        known=np.isfinite(self.distance[idx])
        # Local topocentric annual parallax, then relativistic aberration.
        selected[known]-=observer[None,:]/PC_KM/np.maximum(d[known,None],1e-9)
        selected/=np.linalg.norm(selected,axis=1)[:,None]
        if np.linalg.norm(observer)>0:
            from .ephemeris import EPHEMERIS
            try:
                sun,_=EPHEMERIS.state(epoch.tdb1+epoch.tdb2,10);radial=observer-sun;em=np.linalg.norm(radial)/149597870.7
                selected=erfa.ldsun(selected,np.broadcast_to(radial/np.linalg.norm(radial),selected.shape),em)
            except ValueError:pass
        selected=erfa.ab(selected,np.broadcast_to(v,selected.shape),max(em,1.),np.sqrt(1-np.dot(v,v)))
        local=selected@basis.T
        # Below-horizon stars are hidden by the ground; refraction lifts at most ~0.6 degrees.
        keep=np.ones(len(idx),dtype=bool) if not horizon_only else local[:,2]>=-np.sin(np.radians(2.))
        if statistics is not None:statistics.update(screened=len(self.rows),propagated=len(candidates),prepared=int(keep.sum()),skipped_detailed=len(self.rows)-len(candidates),below_horizon_skipped=int((~keep).sum()),
            max_magnitude=max_magnitude,book_stars_always_shown=int(book[idx].sum()),priority='brightest apparent magnitude first',view=view)
        # Unit vectors rounded to 1e-9 (about 0.0002 arcsec) keep frames small without visible error.
        ground_dirs=np.round(local,9).tolist();icrs_dirs=np.round(selected,9).tolist();space_dirs=np.round(unit,9).tolist()
        static_stamp=(self.stamp,SANSKRIT.stamp)
        if self.cache.get('static_stamp')!=static_stamp:self.cache.update(static_stamp=static_stamp,static_fields={})
        static=self.cache['static_fields']
        result=[];previewed=False
        if progress:progress(3,0,len(idx),'Calculating stellar light, colors and measured angular sizes')
        for k,j in enumerate(idx):
            if progress and k%250==0:progress(3,k,len(idx),'Stars prepared for the renderer')
            if not keep[k]:continue
            r=self.rows[j];finite=np.isfinite(self.distance[j])
            if j not in static:
                bv=r.get('bv');bp=r.get('bp_rp')
                if bv is None:bv=.65 if bp is None else np.clip(.75*bp-.1,-.4,2.5)
                fields=SANSKRIT.fields(r['id'],r['name'],False,refresh=False)
                fields['color']=bv_rgb(float(bv))
                measured=self.diameters.get(r['id'])
                radius=measured['diameter_mas']/206264806.247/2*self.distance[j]*PC_KM if measured and finite else None
                static[j]=(fields,radius)
            fields,radius=static[j]
            item=dict(id=r['id'],**fields,type='star',ground_direction=ground_dirs[k],magnitude=round(float(mag[k]),3),
                distance_pc=float(f'{d[k]:.6g}') if finite else None)
            if detail:item.update(SANSKRIT.fields(r['id'],r['name'],True,refresh=False))
            if view=='space' or detail:item.update(direction=icrs_dirs[k],space_direction=space_dirs[k])
            if radius is not None:
                item.update(radius_km=float(radius),angular_radius_deg=float(np.degrees(np.arctan2(radius,d[k]*PC_KM))))
                if detail:item.update(diameter_measurement=self.diameters[r['id']],size_quality='Measured LD diameter; constant photospheric size assumed across time')
            if detail:item.update(quality='space-motion-extrapolation' if abs(epoch.year-r['epoch'])>200 else 'catalog-propagation',source=r['source'],
                motion_complete=bool(finite and r['rv_known'] and r['pmra'] is not None and r['pmdec'] is not None),
                spectral=r['spectral'],variable=r['variable'],astrometry_error=r['astrometry_error'],frame='ICRS apparent direction',time_scale='TDB',units={'distance':'pc','magnitude':'V for Hipparcos / G for Gaia'},validity_note='Measurement epoch '+str(r['epoch'])+'; motion and constant-luminosity assumptions apply away from that epoch',
                magnitude_note=f'Fainter than the {STAR_LIMIT} star limit; shown because the book names it.' if mag[k]>max_magnitude else None)
            result.append(item)
            if preview and not previewed and len(result)>=128:previewed=True;preview(result.copy())
        if progress:progress(3,len(idx),len(idx),'Bright-first star positions and light ready')
        return result,dynamics

def bv_rgb(bv):
    # Ballesteros temperature then blackbody sRGB approximation; not calibrated spectral reconstruction.
    bv=float(np.clip(bv,-.39,2.5));t=4600*(1/(.92*bv+1.7)+1/(.92*bv+.62))/100
    red=255 if t<=66 else 329.698727446*(t-60)**-.1332047592
    green=99.4708025861*math.log(t)-161.1195681661 if t<=66 else 288.1221695283*(t-60)**-.0755148492
    blue=255 if t>=66 else 0 if t<=19 else 138.5177312231*math.log(t-10)-305.0447927307
    return '#'+''.join(f'{int(np.clip(c,0,255)):02x}' for c in [red,green,blue])
CATALOG=Catalog()
