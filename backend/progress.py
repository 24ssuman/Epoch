"""Per-request calculation progress, separate from long-running reconstruction jobs."""
import threading,time
from collections import OrderedDict
LOCK=threading.Lock();REQUESTS=OrderedDict();LATEST={}
STAGES=['Time scales & Earth orientation','Solar-system positions','Stellar motion propagation','Stellar light & angular sizes','Comets & response']

def begin(identity):
    client,_,number=identity.rpartition('-')
    client=client if number.isdigit() else identity
    with LOCK:
        LATEST[client]=identity
        REQUESTS[identity]=dict(id=identity,status='calculating',stage=STAGES[0],stage_index=0,stages_completed=0,total_stages=len(STAGES),processed=0,total=1,percent=0.,started=time.monotonic(),timings_ms={})
        while len(REQUESTS)>100:REQUESTS.popitem(last=False)
    def update(stage,processed=0,total=1,detail=''):
        with LOCK:
            s=REQUESTS.get(identity)
            if not s:return
            old=s['stage_index'];now=time.monotonic()
            if stage!=old:s['timings_ms'][STAGES[old]]=round((now-s.get('stage_started',s['started']))*1000,2);s['stage_started']=now
            s.update(stage=STAGES[min(stage,len(STAGES)-1)],stage_index=stage,stages_completed=min(stage,len(STAGES)),processed=int(processed),total=int(total),detail=detail,
                percent=round(min(99.9,(stage+processed/max(total,1))/len(STAGES)*100),1))
    def publish_preview(data):
        with LOCK:
            if identity in REQUESTS:REQUESTS[identity]['preview']=data
    def is_current():
        with LOCK:return LATEST.get(client)==identity
    update.is_current=is_current
    update.preview=publish_preview
    return update

def finish(identity,error=None,cached=False):
    with LOCK:
        s=REQUESTS.get(identity)
        if not s:return
        now=time.monotonic();s['timings_ms'][s['stage']]=round((now-s.get('stage_started',s['started']))*1000,2)
        s.update(status='error' if error else 'complete',percent=s['percent'] if error else 100.,stages_completed=s['stages_completed'] if error else len(STAGES),elapsed_ms=round((now-s['started'])*1000,1),error=error,cached=cached)

def read(identity):
    with LOCK:
        s=dict(REQUESTS.get(identity,dict(status='queued',percent=0,stage='Waiting for local service',stages_completed=0,total_stages=len(STAGES),processed=0,total=0)))
        if s.get('status')=='calculating':s['elapsed_ms']=round((time.monotonic()-s['started'])*1000,1)
        return {k:v for k,v in s.items() if k not in ('started','stage_started')}
