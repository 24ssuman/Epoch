"""Measured stellar diameters for the prominent-star atlas; no inferred radius from brightness."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA
from scripts.setup_data import download,record,log
import csv,json,re,gzip
p=download('https://cdsarc.cds.unistra.fr/ftp/II/345/jmdc.dat.gz',DATA/'catalogs/jmdc.dat.gz','JMMC Measured Stellar Diameters Catalogue, Duvert 2016 / Chelli et al. 2016 A&A 589 A112; original measurement references retained')
lookup={}
with (DATA/'catalogs/hyg.csv').open() as f:
 for r in csv.DictReader(f):
  identity='hip:'+r['hip'] if r['hip'] else 'hyg:'+r['id']
  for field,prefix in [('hd','HD'),('hip','HIP')]:
   if r[field]:lookup[prefix+str(int(r[field]))]=identity
rows={}
for line in gzip.decompress(p.read_bytes()).decode().splitlines():
 try:
  if line[334:335]=='1':continue # Ambiguous unresolved component identification.
  key=re.sub(r'\s+','',line[:28]).upper();identity=lookup.get(key)
  if not identity:continue
  diameter=float(line[68:75]);error=float(line[76:84]);bib=line[314:333].strip();year=int(bib[:4])
  if not 0<error<diameter*.25 or diameter<=0:continue
  candidate=dict(diameter_mas=diameter,error_mas=error,band=line[85:95].strip(),bibcode=bib,method=line[104:105],notes=line[109:313].strip(),kind='measured limb-darkened diameter',source='JMMC JMDC II/345; '+bib,source_url='https://ui.adsabs.harvard.edu/abs/'+bib+'/abstract',year=year)
  previous=rows.get(identity)
  if previous is None or (year,-error/diameter)>(previous['year'],-previous['error_mas']/previous['diameter_mas']):rows[identity]=candidate
 except (ValueError,IndexError):continue
path=DATA/'catalogs/diameters.json';path.write_text(json.dumps(rows,indent=2));record(path,'https://cdsarc.cds.unistra.fr/ftp/II/345/','JMMC JMDC; source references retained; ambiguous component measurements excluded')
log(f'Installed directly measured limb-darkened diameters for {len(rows)} identified stars. Unknown stellar radii remain unknown.')
