/** Exact 100 ms samples. Index arithmetic avoids cumulative Julian-date drift. */
export const SAMPLE_SECONDS = .1;
export function sampleJD(origin:number,index:number,speed:number) {
  return Math.round((origin+index*speed*SAMPLE_SECONDS)*1e8)/1e8;
}
export function elapsedSamples(milliseconds:number) {
  return Math.max(0,Math.floor((milliseconds+1e-6)/(SAMPLE_SECONDS*1000)));
}
export type Ticket = {id:number;generation:number};
/** One active transport and one replaceable latest target. Invalidations also
 * guard responses from transports that ignore AbortSignal. */
export class LatestRequest<Q,R> {
  private generation=0;
  private serial=0;
  private active:{ticket:Ticket;controller:AbortController}|null=null;
  private queued:{request:Q;ticket:Ticket}|null=null;
  constructor(private handlers:{
    load:(request:Q,signal:AbortSignal,ticket:Ticket)=>Promise<R>;
    result:(result:R,request:Q,ticket:Ticket,elapsedMs:number)=>void;
    start?:(request:Q,ticket:Ticket)=>void;
    error?:(error:unknown,ticket:Ticket)=>void;
    idle?:()=>void;
  }){}
  isCurrent(ticket:Ticket) {
    return ticket.generation===this.generation&&ticket.id===this.active?.ticket.id;
  }
  invalidate() {
    this.generation++;this.queued=null;this.active?.controller.abort();
  }
  submit(request:Q,replace=false) {
    if(replace)this.invalidate();
    const ticket={id:++this.serial,generation:this.generation};
    if(this.active)this.queued={request,ticket};else void this.run(request,ticket);
    return ticket;
  }
  private async run(request:Q,ticket:Ticket) {
    const controller=new AbortController();this.active={controller,ticket};
    const started=performance.now();
    try {
      this.handlers.start?.(request,ticket);
      const result=await this.handlers.load(request,controller.signal,ticket);
      if(this.isCurrent(ticket))this.handlers.result(result,request,ticket,performance.now()-started);
    } catch(error) {
      if(this.isCurrent(ticket)&&!controller.signal.aborted)this.handlers.error?.(error,ticket);
    } finally {
      this.active=null;const next=this.queued;this.queued=null;
      if(next)void this.run(next.request,next.ticket);else this.handlers.idle?.();
    }
  }
}
