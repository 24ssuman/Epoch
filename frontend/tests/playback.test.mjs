import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const source=readFileSync(new URL('../src/playback.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {LatestRequest,sampleJD,elapsedSamples}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function harness(){const pending=[],shown=[],errors=[];let active=0,maxActive=0;
 const scheduler=new LatestRequest({load:(request,signal)=>{active++;maxActive=Math.max(active,maxActive);return new Promise((resolve,reject)=>pending.push({request,signal,resolve:v=>{active--;resolve(v);},reject:e=>{active--;reject(e);}}));},result:(result,request)=>shown.push([request,result]),error:e=>errors.push(e)});
 return {scheduler,pending,shown,errors,max:()=>maxActive};
}
test('100 ms samples preserve speed, skipped wall-clock steps and reverse exact dates',()=>{
 const origin=2461335.12345678,speed=1/24;
 assert.equal(elapsedSamples(99),0);assert.equal(elapsedSamples(100),1);assert.equal(elapsedSamples(975),9);
 assert.equal(sampleJD(origin,36000,speed),Math.round((origin+speed*3600)*1e8)/1e8);
 const forward=Array.from({length:100},(_,i)=>sampleJD(origin,i,speed));
 assert.deepEqual(Array.from({length:100},(_,i)=>sampleJD(origin,99-i,speed)),forward.toReversed());
});
test('one transport and one latest pending target; slow frames are still displayed',async()=>{
 const h=harness();h.scheduler.submit(1);h.scheduler.submit(2);h.scheduler.submit(3);
 assert.equal(h.pending.length,1);h.pending[0].resolve('first');await flush();
 assert.deepEqual(h.shown,[[1,'first']]);assert.equal(h.pending[1].request,3);
 h.pending[1].resolve('latest');await flush();assert.equal(h.max(),1);assert.deepEqual(h.shown,[[1,'first'],[3,'latest']]);
});
test('observer/view/model/date generations reject stale responses even when abort is ignored',async()=>{
 for(const change of ['observer','view','model','date','reverse','pause']){
  const h=harness();h.scheduler.submit('old');h.scheduler.submit('queued-old');h.scheduler.invalidate();h.scheduler.submit(change);
  assert.ok(h.pending[0].signal.aborted);h.pending[0].resolve('stale');await flush();assert.deepEqual(h.shown,[]);
  assert.equal(h.pending[1].request,change);h.pending[1].resolve('current');await flush();assert.deepEqual(h.shown,[[change,'current']]);assert.equal(h.max(),1);
 }
});
test('paused scrubbing replaces requests and pause/resume does not replay old queued work',async()=>{
 const h=harness();h.scheduler.submit('playing');h.scheduler.submit('old-next');h.scheduler.submit('paused-target',true);
 h.pending[0].reject(new Error('aborted'));await flush();assert.deepEqual(h.errors,[]);assert.equal(h.pending[1].request,'paused-target');
 h.pending[1].resolve('paused');await flush();h.scheduler.submit('resumed');h.pending[2].resolve('new');await flush();
 assert.deepEqual(h.shown,[['paused-target','paused'],['resumed','new']]);
});
test('current failures are reported and pending work continues',async()=>{
 const h=harness();h.scheduler.submit(1);h.scheduler.submit(2);h.pending[0].reject(new Error('failure'));await flush();
 assert.equal(h.errors.length,1);h.pending[1].resolve('ok');await flush();assert.deepEqual(h.shown,[[2,'ok']]);
});
