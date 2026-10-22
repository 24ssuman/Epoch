"""Standalone offline worker. Survives local web-server restarts."""
import sys,argparse,os,json
try:os.nice(10)
except (AttributeError,OSError):pass
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.jobs import run,JOB_DIR
from backend.astrotime import MIN_YEAR
p=argparse.ArgumentParser();p.add_argument('--year',type=int,default=MIN_YEAR);p.add_argument('--chunk-years',type=float,default=10)
p.add_argument('--no-future',action='store_true',help='do not start the 2000 -> 5,000 CE run automatically after the past run completes')
a=p.parse_args()
# Launching from the terminal means "run": clear a pause left by the website, as its Start/Resume button does.
control=JOB_DIR/'control.json';config=json.loads(control.read_text()) if control.exists() else {}
config['pause_requested']=False
if a.no_future:config['queue_future']=False
JOB_DIR.mkdir(exist_ok=True);control.write_text(json.dumps(config))
run(a.year,a.chunk_years)
