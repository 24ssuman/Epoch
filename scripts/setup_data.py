"""Explicit online installer. Runtime services never download data."""
import sys, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT,DATA,TMP,guard
import argparse, json, hashlib, time, gzip, csv, io
import threading
from concurrent.futures import ThreadPoolExecutor
MANIFEST_LOCK=threading.Lock()
import httpx
import numpy as np

NAIF='https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/'

def log(message):
    print(message,flush=True)
    with (ROOT/'LOG.md').open('a') as f: f.write(f'\n- {time.strftime("%Y-%m-%d %H:%M:%S %z")}: {message}\n')

def download(url,path,license='Source attribution; see URL'):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.stat().st_size>0:
        record(path,url,license); return path
    if path.suffix=='.bsp':
        return download_kernel(url,path,license)
    part=path.with_suffix(path.suffix+'.partial'); start=part.stat().st_size if part.exists() else 0
    with httpx.Client(follow_redirects=True,timeout=120) as c:
        with c.stream('GET',url,headers=({'Range':f'bytes={start}-','Accept-Encoding':'identity'} if start else {'Accept-Encoding':'identity'})) as r:
            r.raise_for_status()
            total=int(r.headers.get('content-length',0)); guard(total)
            append=start and r.status_code==206
            with part.open('ab' if append else 'wb') as f:
                for b in r.iter_bytes(1024*1024):
                    f.write(b)
            if total and not r.headers.get('content-encoding') and part.stat().st_size != total+(start if append else 0): raise RuntimeError('Truncated download')
    os.replace(part,path); record(path,url,license)
    log(f'Installed {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes); retained source and checksum.')
    return path

def record(path,url,license):
    with MANIFEST_LOCK:
        _record(path,url,license)

def _record(path,url,license):
    target=DATA/'manifest.json'; manifest=json.loads(target.read_text()) if target.exists() else {}
    digest=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
    manifest[str(path.relative_to(ROOT))]=dict(url=url,sha256=digest,bytes=path.stat().st_size,license=license,installed=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    target.write_text(json.dumps(manifest,indent=2))

def download_kernel(url,path,license):
    # Ranged chunks are retained under tmp/ as requested; downloads resume per chunk.
    with httpx.Client(follow_redirects=True,timeout=120) as c:
        r=c.head(url,headers={'Accept-Encoding':'identity'});r.raise_for_status();total=int(r.headers['content-length'])
    chunksize=1024*1024;directory=TMP/'downloads'/(path.name+'-1m');directory.mkdir(parents=True,exist_ok=True)
    pieces=[(i,start,min(total-1,start+chunksize-1)) for i,start in enumerate(range(0,total,chunksize))]
    needed=sum(end-start+1 for i,start,end in pieces if not (directory/str(i)).exists())+total
    guard(needed)
    def piece(spec):
        i,start,end=spec;p=directory/str(i)
        if p.exists() and p.stat().st_size==end-start+1:return p
        for attempt in range(4):
            try:
                with httpx.Client(follow_redirects=True,timeout=180) as c:
                    r=c.get(url,headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'})
                    r.raise_for_status()
                    if r.status_code!=206 or len(r.content)!=end-start+1:raise RuntimeError('Server did not honor bounded byte range')
                    p.write_bytes(r.content)
                return p
            except Exception:
                if attempt==3:raise
                time.sleep(2+attempt*2)
    log(f'Downloading {path.name} using resumable bounded ranges ({total:,} bytes)')
    with ThreadPoolExecutor(max_workers=16) as pool: list(pool.map(piece,pieces))
    part=path.with_suffix(path.suffix+'.partial')
    with part.open('wb') as f:
        for i,start,end in pieces:
            with (directory/str(i)).open('rb') as src:
                while b:=src.read(1024*1024):f.write(b)
    os.replace(part,path);record(path,url,license);log(f'Installed and checksummed {path.name}')
    return path

def hyg():
    p=download('https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv',DATA/'catalogs/hyg.csv','CC BY-SA 4.0; David Nash / HYG; underlying Hipparcos/Yale/Gliese catalogs')
    rows=[]
    def num(r,k,default=0.):
        try:return float(r[k])
        except (ValueError,KeyError):return default
    with p.open() as f:
        for r in csv.DictReader(f):
            if r['id']=='0':continue
            rows.append(dict(id='hip:'+r['hip'] if r['hip'] else 'hyg:'+r['id'],name=r['proper'] or (r['bayer']+' '+r['con']).strip() or ('HIP '+r['hip'] if r['hip'] else 'HD '+r['hd']),
                ra=num(r,'ra')*15,dec=num(r,'dec'),distance=num(r,'dist'),pmra=num(r,'pmra'),pmdec=num(r,'pmdec'),rv=num(r,'rv'),
                rv_known=bool(r.get('rv')),mag=num(r,'mag',15),bv=num(r,'ci',.65),epoch=2000.,source='HYG 4.1 / Hipparcos',spectral=r.get('spect',''),
                variable=bool(r.get('var')),hip=r.get('hip'),astrometry_error=None))
    (DATA/'catalogs/stars.json').write_text(json.dumps(rows,separators=(',',':')))
    log(f'Prepared {len(rows):,} HYG/Hipparcos stars; Gaia data is merged separately when available.')

def gaia():
    # UWS async job is retained across interruptions. Download only selected columns, not full spectra.
    state=DATA/'catalogs/gaia-job.json'; endpoint='https://gea.esac.esa.int/tap-server/tap/async'
    query='SELECT source_id,ra,dec,parallax,pmra,pmdec,radial_velocity,phot_g_mean_mag,bp_rp,ra_error,dec_error,parallax_error,pmra_error,pmdec_error,radial_velocity_error FROM gaiadr3.gaia_source WHERE phot_g_mean_mag <= 12'
    target=DATA/'catalogs/gaia.csv'
    if target.exists(): return merge_gaia(target)
    with httpx.Client(follow_redirects=True,timeout=120) as c:
        if state.exists(): url=json.loads(state.read_text())['url']
        else:
            r=c.post(endpoint,data={'REQUEST':'doQuery','LANG':'ADQL','QUERY':query,'FORMAT':'csv','PHASE':'RUN','MAXREC':'10000000'})
            r.raise_for_status();url=str(r.url)
            if url.rstrip('/')==endpoint.rstrip('/'): raise RuntimeError('Gaia job did not return a UWS job URL')
            state.write_text(json.dumps(dict(url=url,query=query)))
        log(f'Gaia G<=12 asynchronous query: {url}')
        for _ in range(600):
            r=c.get(url+'/phase');r.raise_for_status();phase=r.text.strip()
            if phase=='COMPLETED':break
            if phase in ('ERROR','ABORTED'): raise RuntimeError(c.get(url+'/error').text[:1000])
            time.sleep(3)
        else: raise RuntimeError('Gaia query remains pending; rerun --gaia to resume')
    download(url+'/results/result',target,'ESA/Gaia/DPAC; Gaia DR3 acknowledgement required')
    merge_gaia(target)

def merge_gaia(target):
    from scipy.spatial import cKDTree
    base=json.loads((DATA/'catalogs/stars.json').read_text())
    # Match in the common J2016 epoch to avoid duplicating high proper-motion bright stars.
    def xyz(ra,dec):
        ra=np.radians(ra);dec=np.radians(dec)
        return np.column_stack([np.cos(dec)*np.cos(ra),np.cos(dec)*np.sin(ra),np.sin(dec)])
    br=np.array([r['ra']+r['pmra']*16/(3.6e6*max(.001,np.cos(np.radians(r['dec'])))) for r in base])
    bd=np.array([r['dec']+r['pmdec']*16/3.6e6 for r in base]);tree=cKDTree(xyz(br,bd)); extra=[]
    for batch_start in [0]:
        with target.open() as f:
            for r in csv.DictReader(f):
                def n(k):
                    try:return float(r[k])
                    except (ValueError,KeyError):return None
                ra=n('ra');dec=n('dec');plx=n('parallax');g=n('phot_g_mean_mag')
                if ra is None or dec is None or g is None:continue
                d,idx=tree.query(xyz([ra],[dec])[0])
                item=dict(id='gaia:'+r['source_id'],name='Gaia DR3 '+r['source_id'],ra=ra,dec=dec,distance=1000/plx if plx and plx>0 else None,
                    pmra=n('pmra'),pmdec=n('pmdec'),rv=n('radial_velocity'),rv_known=n('radial_velocity') is not None,mag=g,
                    bv=None,bp_rp=n('bp_rp'),epoch=2016.,source='Gaia DR3',spectral='',variable=False,
                    astrometry_error={k:n(k) for k in ['ra_error','dec_error','parallax_error','pmra_error','pmdec_error','radial_velocity_error']})
                if d<2/206265:
                    old=base[idx]; item['name']=old['name'];item['id']=old['id'];item['bv']=old['bv'];item['mag']=old['mag'];item['spectral']=old['spectral'];item['variable']=old['variable'];item['source']+=' + Hipparcos V/B-V'
                    if item['rv'] is None and old['rv_known']:item['rv']=old['rv'];item['rv_known']=True
                    base[idx]=item
                else:extra.append(item)
    allstars=base+extra
    (DATA/'catalogs/stars.json').write_text(json.dumps(allstars,separators=(',',':')))
    log(f'Merged Gaia G<=12 with Hipparcos: {len(allstars):,} stars. Spectra are not bundled; colors use measured indices.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--extended',action='store_true');p.add_argument('--gaia',action='store_true');a=p.parse_args()
    for d in ['kernels','catalogs','comets','jobs']: (DATA/d).mkdir(exist_ok=True)
    if a.gaia: gaia()
    else:
        download(NAIF+'de440.bsp',DATA/'kernels/de440.bsp','NASA/JPL; public scientific data, retain attribution')
        hyg()
        if a.extended:
            for name in ['de441.bsp']:
                download(NAIF+name,DATA/'kernels'/name,'NASA/JPL; public scientific data, retain attribution')
