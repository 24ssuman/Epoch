import {useId} from 'react';
import {lunarGlow} from './moonlight';
import type {Snapshot} from './types';

/** Orthographic terminator for the calculated illuminated fraction; diagram is
 * schematic, with the lit limb on the right for waxing and left for waning. */
export function phasePath(fraction:number) {
 const f=Math.max(0,Math.min(1,fraction)),terminator=1-2*f;
 return `M64 14 A50 50 0 0 1 64 114 A${Math.abs(terminator)*50} 50 0 0 ${terminator>=0?0:1} 64 14 Z`;
}
export default function MoonPhase({snapshot}:{snapshot:Snapshot|null}) {
 const glowId=useId();
 const moon=snapshot?.bodies.find(b=>b.id==='Moon');
 if(!moon||moon.phase_fraction===undefined)return <section className="moon-phase"><p>{snapshot?'Moon phase is unavailable at this date. Validated planetary data is required.':'Preparing the Moon phase…'}</p></section>;
 const fraction=Math.max(0,Math.min(1,moon.phase_fraction));
 const glow=lunarGlow(moon.magnitude,fraction);
 const d=snapshot!.date;
 return <section className="moon-phase" aria-label="Current Moon phase">
  <div className="moon-summary"><svg className="moon-phase-disc" viewBox="0 0 128 128" role="img" aria-label={`${moon.phase_name??'Moon'}; ${(fraction*100).toFixed(1)} percent illuminated`}>
   <defs><filter id={glowId} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>
   <circle cx="64" cy="64" r="50" fill="#141c26"/>
   <path d={phasePath(fraction)} fill="#e9edf4" stroke="#e9edf4" strokeWidth="3" opacity={glow*2} filter={`url(#${glowId})`} transform={moon.waxing===false?'translate(128 0) scale(-1 1)':undefined}/>
   <path d={phasePath(fraction)} fill="#e0dfd8" transform={moon.waxing===false?'translate(128 0) scale(-1 1)':undefined}/>
   <circle cx="64" cy="64" r="50" fill="none" stroke="#aab6c32b"/>
  </svg>
  <div><h2>{moon.phase_name??'Moon phase'}</h2>
  <div className="moon-illumination"><strong>{(fraction*100).toFixed(1)}<span>%</span></strong><span>illuminated</span></div></div></div>
  <p className="moon-direction">{moon.waxing?'Waxing':'Waning'} · {moon.altitude_deg!==undefined?moon.altitude_deg>=0?'Above your horizon':'Below your horizon':'Horizon unavailable'}</p>
  <p className="moon-date">{d.day}/{d.month}/{d.display_year} {d.era} · {String(Math.floor(d.hour)).padStart(2,'0')}:{String(Math.floor((d.hour%1)*60)).padStart(2,'0')} TT · Gregorian</p>
  <p className="muted">For your observing location. Glow follows phase and distance; its appearance and disk size are illustrative.</p>
  <p className="moon-source">{snapshot!.source.model} · topocentric phase<br/>TT input / TDB dynamics</p>
 </section>;
}
