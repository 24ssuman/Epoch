/** Lunar light scaling: Krisciunas & Schaefer (1991), PASP 103, Eq. 9.
 * https://articles.adsabs.harvard.edu/pdf/1991PASP..103.1033K
 * The backend magnitude includes phase and observer distance. These relative
 * fluxes do not include eclipses, opposition surge, or reconstructed weather.
 * Halo opacity/width are display choices, not measured radiance or halo angles.
 */
export function lunarRelativeFlux(magnitude:number|undefined,fraction:number) {
 if(!Number.isFinite(fraction)||fraction<=0)return 0;
 const f=Math.max(0,Math.min(1,fraction));
 const angle=Math.acos(2*f-1)*180/Math.PI;
 const m=Number.isFinite(magnitude)?magnitude!:-12.73+.026*angle+4e-9*angle**4;
 return Math.max(0,Math.min(2,10**(-.4*(m+12.73))));
}
export function lunarGlow(magnitude:number|undefined,fraction:number,exposure=4,daylight=0) {
 const flux=lunarRelativeFlux(magnitude,fraction);
 const gain=2**((Math.max(-2,Math.min(10,exposure))-4)*.5);
 return .28*(1-Math.exp(-3*flux*gain))*(1-Math.max(0,Math.min(1,daylight)));
}
export function lunarTransmission(altitude:number,atmosphere:boolean) {
 if(!Number.isFinite(altitude)||altitude<=0)return 0;
 if(!atmosphere)return 1;
 const air=1/(Math.sin(altitude*Math.PI/180)+.50572*(altitude+6.07995)**-1.6364);
 return 10**(-.4*.2*air);
}
