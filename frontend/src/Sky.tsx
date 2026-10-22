import {useEffect,useMemo,useRef} from 'react';
import * as T from 'three';
import {lunarGlow,lunarRelativeFlux,lunarTransmission} from './moonlight';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import type {Celestial,Settings,Snapshot} from './types';

import {starLabel} from './types';const LABEL_FONT='11px system-ui,"Kohinoor Devanagari","Devanagari Sangam MN","Noto Sans Devanagari",sans-serif';const LABEL_FONT_SELECTED=LABEL_FONT.replace('11px','600 13px');
const vertex=`attribute float magnitude;attribute float forced;attribute float diameter;uniform float pixelsPerRadian;uniform float halos;varying float vArea; varying vec3 vColor; varying float vFlux; uniform float exposure; uniform float threshold; void main(){vColor=color;vFlux=pow(10.,-.4*magnitude)*pow(2.,exposure);vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;float psf=halos*(2.5+2.*pow(max(vFlux,0.),.18));float disk=diameter*pixelsPerRadian;gl_PointSize=magnitude>threshold&&forced<.5?0.:max(1.,sqrt(psf*psf+disk*disk));vArea=max(1.,gl_PointSize*gl_PointSize);}`;
const fragment=`varying vec3 vColor;varying float vFlux;varying float vArea;uniform float daylight;void main(){float r=length(gl_PointCoord-.5)*2.;float psf=exp(-r*r*7.);float power=vFlux*72./vArea;vec3 light=vColor*power*psf;gl_FragColor=vec4((vec3(1.)-exp(-light))*(1.-daylight),1.);}`;
// Numerical single-scattering Rayleigh/Mie model, spherical exponential atmosphere.
// Clear standard atmosphere; omitted multiple scattering/ozone is disclosed in the science panel.
const skyFragment=`varying vec3 vWorld;uniform vec3 sunDirection;uniform float enabled;uniform float exposure;uniform float pollution;uniform float moonGlow;uniform float hasSun;const float PI=3.14159265;const float R=6360000.;const float A=6460000.;vec2 hit(vec3 o,vec3 d,float r){float b=dot(o,d),c=dot(o,o)-r*r,q=b*b-c;if(q<0.)return vec2(1e20,-1e20);return vec2(-b-sqrt(q),-b+sqrt(q));}void main(){if(enabled<.5){gl_FragColor=vec4(.0003,.0005,.001,1.);return;}vec3 d=normalize(vWorld-cameraPosition);if(hasSun<.5){float horizon=pow(max(0.,1.-abs(d.y)),5.);vec3 night=vec3(.001,.002,.004)+vec3(.004,.009,.018)*moonGlow+pollution*.001*vec3(1.,.65,.32)*(1.+horizon*3.);gl_FragColor=vec4(vec3(1.)-exp(-night*max(.5,pow(2.,exposure*.15))),1.);return;}vec3 origin=vec3(0.,R+10.,0.);vec2 bounds=hit(origin,d,A);float distance=max(0.,bounds.y);vec2 g=hit(origin,d,R);if(g.x>0.)distance=min(distance,g.x);vec3 betaR=vec3(5.8e-6,13.5e-6,33.1e-6);float betaM=21e-6;float opticalR=0.,opticalM=0.;vec3 sumR=vec3(0.),sumM=vec3(0.);float stepL=distance/16.;for(int i=0;i<16;i++){vec3 p=origin+d*(float(i)+.5)*stepL;float h=max(0.,length(p)-R);float r=exp(-h/8000.)*stepL,m=exp(-h/1200.)*stepL;opticalR+=r;opticalM+=m;vec2 shadow=hit(p,sunDirection,R);if(shadow.x>0.)continue;float sl=hit(p,sunDirection,A).y/6.;float sr=0.,sm=0.;for(int j=0;j<6;j++){float sh=max(0.,length(p+sunDirection*(float(j)+.5)*sl)-R);sr+=exp(-sh/8000.)*sl;sm+=exp(-sh/1200.)*sl;}vec3 tr=exp(-betaR*(opticalR+sr)-betaM*1.1*(opticalM+sm));sumR+=r*tr;sumM+=m*tr;}float mu=dot(d,sunDirection);float phaseR=3./(16.*PI)*(1.+mu*mu);float gg=.76;float phaseM=3./(8.*PI)*(1.-gg*gg)*(1.+mu*mu)/((2.+gg*gg)*pow(1.+gg*gg-2.*gg*mu,1.5));vec3 radiance=20.*(sumR*betaR*phaseR+sumM*betaM*phaseM)*hasSun;float horizon=pow(max(0.,1.-abs(d.y)),5.);vec3 night=vec3(.001,.002,.004)+vec3(.004,.009,.018)*moonGlow+pollution*.001*vec3(1.,.65,.32)*(1.+horizon*3.);vec3 c=radiance+night;c=vec3(1.)-exp(-c*max(.5,pow(2.,exposure*.15)));gl_FragColor=vec4(mix(vec3(.0003,.0005,.001),c,enabled),1.);}`;
const skyVertex=`varying vec3 vWorld;void main(){vec4 w=modelMatrix*vec4(position,1.);vWorld=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}`;

function vector(a:number[],ground=false){return ground?new T.Vector3(a[0],a[2],-a[1]):new T.Vector3(a[0],a[2],-a[1]);}
// Comet tail: additive ribbon fading along the tail and to zero at both edges (bright along its axis), so it reads as diffuse light.
function updateGeometry(geo:T.BufferGeometry,attributes:Record<string,{values:number[];size:number}>) {
 const growing=Object.entries(attributes).some(([name,{values}])=>!geo.getAttribute(name)||geo.getAttribute(name).array.length<values.length);
 if(growing)geo.dispose();
 for(const [name,{values,size}] of Object.entries(attributes)){
  let attr=geo.getAttribute(name) as T.BufferAttribute|undefined;
  if(!attr||attr.array.length<values.length){const capacity=size*2**Math.ceil(Math.log2(Math.max(1,Math.ceil(values.length/size))));attr=new T.BufferAttribute(new Float32Array(capacity),size);attr.setUsage(T.DynamicDrawUsage);geo.setAttribute(name,attr);}
  (attr.array as Float32Array).set(values);attr.needsUpdate=true;
 }
 geo.setDrawRange(0,attributes.position.values.length/3);

}
function ribbon(mesh:T.Mesh,left:T.Vector3[],right:T.Vector3[],intensity:number[],hex:string,gain:number){const c=new T.Color(hex);const pos:number[]=[],col:number[]=[];const center=left.map((l,i)=>l.clone().add(right[i]).multiplyScalar(.5));
 const push=(p:T.Vector3,k:number)=>{pos.push(p.x,p.y,p.z);const g=k*gain;col.push(c.r*g,c.g*g,c.b*g);};
 for(let i=0;i<left.length-1;i++)for(const edge of [left,right]){const a=intensity[i],b=intensity[i+1];push(edge[i],0);push(center[i],a);push(edge[i+1],0);push(center[i],a);push(center[i+1],b);push(edge[i+1],0);}
 updateGeometry(mesh.geometry,{position:{values:pos,size:3},color:{values:col,size:3}});mesh.frustumCulled=false;
}
function cometGain(magnitude:number,exposure:number){return .55*Math.sqrt(Math.min(1,Math.pow(10,-.4*(magnitude-1))))*Math.pow(2,(exposure-4)*.5);}
// Point the Earth observer camera along the calculated object direction.
function aim(s:{camera:T.PerspectiveCamera;controls:OrbitControls;dirty:boolean},o:Celestial){
 if(o.ground_direction){s.camera.position.copy(vector(o.ground_direction).multiplyScalar(-.0001));s.controls.target.set(0,0,0);s.controls.update();s.dirty=true;}
}
function centroid(objs:Celestial[]):Celestial{const v=[0,0,0];for(const o of objs)for(let k=0;k<3;k++)v[k]+=o.ground_direction![k];const n=Math.hypot(v[0],v[1],v[2])||1;return {...objs[0],ground_direction:v.map(x=>x/n)};}
// Reticle: soft glow, dark-edged ring and four gapped ticks, drawn on the 2D overlay.
function drawReticle(ctx:CanvasRenderingContext2D,x:number,y:number,R:number,color:string){
 const glow=ctx.createRadialGradient(x,y,R*.6,x,y,R*2.4);glow.addColorStop(0,color+'48');glow.addColorStop(1,color+'00');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(x,y,R*2.4,0,Math.PI*2);ctx.fill();
 ctx.lineCap='round';for(const [width,stroke] of [[4.5,'rgba(0,0,0,.65)'],[2,color]] as const){ctx.lineWidth=width;ctx.strokeStyle=stroke;ctx.beginPath();ctx.arc(x,y,R,0,Math.PI*2);ctx.stroke();ctx.beginPath();for(let k=0;k<4;k++){const a=k*Math.PI/2;ctx.moveTo(x+Math.cos(a)*(R+5),y+Math.sin(a)*(R+5));ctx.lineTo(x+Math.cos(a)*(R+15),y+Math.sin(a)*(R+15));}ctx.stroke();}}
function disposeGroup(g:T.Group){g.traverse(o=>{const m=o as T.Mesh;m.geometry?.dispose();const mats=m.material?Array.isArray(m.material)?m.material:[m.material]:[];mats.forEach(x=>{const tex=(x as T.MeshPhongMaterial).map;if(tex&&!tex.userData.persistent)tex.dispose();x.dispose();});});g.clear();}
export default function Sky({snapshot,settings,onSelect,onOrientation,lat,lon,focus,selectedId,tracking,onFov,onRelease,watch,watchLock,watchCenterId,frameToken}:{snapshot:Snapshot|null;settings:Settings;onSelect:(v:Celestial)=>void;onOrientation:(v:{az:number;alt:number})=>void;lat:number;lon:number;focus:Celestial|null;selectedId:string|null;tracking:boolean;onFov:(v:number)=>void;onRelease:()=>void;watch:{id:string;color:string}[];watchLock:'center'|'frame'|null;watchCenterId:string|null;frameToken:number}){
 const host=useRef<HTMLDivElement>(null); const state=useRef<{renderer:T.WebGLRenderer;scene:T.Scene;camera:T.PerspectiveCamera;controls:OrbitControls;dynamic:T.Group;sky:T.Mesh;labels:HTMLCanvasElement;objects:Celestial[];dirty:boolean;constellations?:Promise<any>;generation:number;pool:Map<string,T.Object3D>;labelWidths:Map<string,number>;renders:number;picks:{object:Celestial;x:number;y:number}[];settings:Settings;snapshot:Snapshot|null;perf:{frames:number;draws:number;since:number;updates:number[];buildMs:number;drawMs:number}}|null>(null);
 const highlightId=useRef<string|null>(null);const meter=useRef<HTMLDivElement>(null);
 const props=useRef({onSelect,onOrientation,settings,snapshot,selectedId,tracking,onFov,onRelease,watch,watchLock});props.current={onSelect,onOrientation,settings,snapshot,selectedId,tracking,onFov,onRelease,watch,watchLock};
 // Labels and camera-only settings do not touch scene geometry.
 const stable=useMemo(()=>settings,[JSON.stringify({...settings,fov:0,starNames:false,planetNames:false,cometNames:false,labelLimit:0,sanskritNames:false})]);
 useEffect(()=>{
  const el=host.current!;let renderer:T.WebGLRenderer;
  try{renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});}catch{el.innerHTML='<div class="webgl-error">WebGL2 is required. Enable graphics acceleration in your browser.</div>';return;}
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.;el.appendChild(renderer.domElement);
  const scene=new T.Scene();const camera=new T.PerspectiveCamera(65,1,.000001,1e5);const controls=new OrbitControls(camera,renderer.domElement);camera.position.set(0,-.00004,-.0001);controls.target.set(0,0,0);controls.enablePan=false;controls.enableZoom=false;controls.minDistance=.0001;controls.maxDistance=.00011;controls.enableDamping=true;controls.dampingFactor=.08;
  const sky=new T.Mesh(new T.SphereGeometry(9000,40,24),new T.ShaderMaterial({side:T.BackSide,depthWrite:false,vertexShader:skyVertex,fragmentShader:skyFragment,uniforms:{sunDirection:{value:new T.Vector3(0,-1,0)},enabled:{value:1},exposure:{value:1},pollution:{value:0},moonGlow:{value:0},hasSun:{value:0}}}));scene.add(sky);
  const dynamic=new T.Group();scene.add(dynamic);const labels=document.createElement('canvas');labels.className='sky-labels';el.appendChild(labels);
  state.current={renderer,scene,camera,controls,dynamic,sky,labels,objects:[],picks:[],settings:props.current.settings,snapshot:null,dirty:true,generation:0,pool:new Map(),labelWidths:new Map(),renders:0,perf:{frames:0,draws:0,since:performance.now(),updates:[],buildMs:0,drawMs:0}};
  // Render on demand: only after camera motion (including damping), a new frame/setting, a resize or an async asset. The atmosphere shader is too costly to redraw 60 times a second while idle.
  controls.addEventListener('change',()=>{if(state.current)state.current.dirty=true;});
  const resize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);labels.width=w*devicePixelRatio;labels.height=h*devicePixelRatio;labels.style.width=w+'px';labels.style.height=h+'px';camera.aspect=w/h;camera.updateProjectionMatrix();if(state.current)state.current.dirty=true;};const ro=new ResizeObserver(resize);ro.observe(el);resize();
  // Callback cadence, actual draws, and accepted exact frames are separate measurements.
  const tickMeter=(s:NonNullable<typeof state.current>)=>{const p=s.perf;p.frames++;const now=performance.now();if(now-p.since<500)return;while(p.updates.length&&p.updates[0]<now-2000)p.updates.shift();const span=(now-p.since)/1000;const cache=s.snapshot?.playback_cache?.timings_ms;const requestMs=s.snapshot?.delivery?.request_ms;if(meter.current){meter.current.dataset.geometries=String(s.renderer.info.memory.geometries);meter.current.dataset.textures=String(s.renderer.info.memory.textures);meter.current.dataset.programs=String(s.renderer.info.programs?.length??0);const calculationMs=s.snapshot?.playback_cache?.hit?0:s.snapshot?.calculation.timings_ms.total_ms;const cacheMs=cache?((cache.key_ms??0)+(cache.lookup_ms??0)+(cache.store_ms??0)):undefined;meter.current.dataset.requestMs=String(requestMs??0);meter.current.dataset.calculationMs=String(calculationMs??0);meter.current.dataset.cacheMs=String(cacheMs??0);meter.current.dataset.updateMs=String(p.buildMs);meter.current.dataset.drawMs=String(p.drawMs);meter.current.textContent=`${Math.round(p.frames/span)} browser fps · ${(p.draws/span).toFixed(1)} renders/s · ${(p.updates.length/2).toFixed(1)} exact updates/s`;meter.current.title=`Request ${requestMs?.toFixed(0)??'—'} ms · calculation ${calculationMs?.toFixed(0)??'—'} ms · cache ${cacheMs?.toFixed(0)??'—'} ms · scene update ${p.buildMs.toFixed(1)} ms · redraw ${p.drawMs.toFixed(1)} ms CPU (GPU time excluded)`;}p.frames=0;p.draws=0;p.since=now;};
  let raf=0,lastOrient=0,orientTimer=0;const reportOrientation=()=>{const d=new T.Vector3();camera.getWorldDirection(d);props.current.onOrientation({az:(T.MathUtils.radToDeg(Math.atan2(d.x,-d.z))+360)%360,alt:T.MathUtils.radToDeg(Math.asin(d.y))});};const animate=()=>{raf=requestAnimationFrame(animate);const s=state.current!;tickMeter(s);const moved=controls.update();if(!moved&&!s.dirty)return;const drawStart=performance.now();s.dirty=false;s.renders++;s.perf.draws++;const sunUp=(s.snapshot?.bodies.find(b=>b.id==='Sun')?.altitude_deg??-90)>0;s.dynamic.traverse(o=>{if(!o.visible)return;const material=(o as T.Points).material as T.ShaderMaterial;if(material?.uniforms?.pixelsPerRadian){material.uniforms.pixelsPerRadian.value=labels.clientHeight/(2*Math.tan(T.MathUtils.degToRad(camera.fov/2)));}});sky.position.copy(camera.position);renderer.render(scene,camera);const ctx=labels.getContext('2d')!;const w=labels.clientWidth,h=labels.clientHeight;ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);ctx.clearRect(0,0,w,h);ctx.font=LABEL_FONT;s.picks=[];const occupied:{x:number;y:number;width:number}[]=[];
   const wc=new Map(props.current.watch.map(w=>[w.id,w.color]));const forcedIds=new Set<string>(wc.keys());if(props.current.selectedId)forcedIds.add(props.current.selectedId);const forced=forcedIds.size?s.objects.filter(o=>forcedIds.has(o.id)):[];for(let i=-forced.length;i<s.objects.length;i++){const obj=i<0?forced[i+forced.length]:s.objects[i];if(i>=0&&forcedIds.has(obj.id))continue;if(!obj.ground_direction)continue;if(s.settings.ground&&obj.ground_direction[2]<-.02)continue;const p=vector(obj.ground_direction).multiplyScalar(100);
    const pos=p.clone().project(camera);if(pos.z>1||pos.z< -1||Math.abs(pos.x)>1.05||Math.abs(pos.y)>1.05)continue;const x=(pos.x+1)*w/2,y=(1-pos.y)*h/2;s.picks.push({object:obj,x,y});
    const star=obj.type==='star'&&obj.id!=='Sun';const enabled=obj.type==='comet'?s.settings.cometNames:star?s.settings.starNames:s.settings.planetNames;
    const chosen=i<0;// the selected/searched object is always named, in front of every filter and first in line for space
    if(!chosen){if(star&&s.settings.atmosphere&&s.settings.sunlight&&sunUp)continue;if(star&&(obj.magnitude??20)>s.settings.starLimit&&!obj.book_star)continue;if(!enabled||(star&&(obj.magnitude??20)>s.settings.labelLimit&&!(s.settings.sanskritNames&&obj.book_star)))continue;}
    const text=starLabel(obj,s.settings.sanskritNames);ctx.font=chosen?LABEL_FONT_SELECTED:LABEL_FONT;const widthKey=(chosen?'selected:':'normal:')+text;let width=s.labelWidths.get(widthKey);if(width===undefined){width=ctx.measureText(text).width;s.labelWidths.set(widthKey,width);}if(!chosen&&occupied.some(r=>Math.abs(r.y-y)<17&&x<r.x+r.width+12&&x+width+12>r.x))continue;let ly=y-(chosen?10:6);if(chosen)for(let t=0;t<4&&occupied.some(r=>Math.abs(r.y-(ly+6))<17&&x<r.x+r.width+12&&x+width+16>r.x);t++)ly+=17;// tracked names step down rather than overlap each other
    occupied.push({x,y:chosen?ly+6:y,width});ctx.fillStyle=chosen?wc.get(obj.id)??'#ffe29a':star?'#9ba6b9':obj.color;ctx.shadowColor='#000';ctx.shadowBlur=chosen?7:5;ctx.fillText(text,x+(chosen?14:8),ly);ctx.shadowBlur=0;if(chosen)ctx.font=LABEL_FONT;
   }
   // "Center in view" highlight: a gold reticle (soft glow, dark-edged ring, four gapped ticks) so the object is easy to find. Drawn on the 2D overlay, so it follows the object as time advances. Static, not pulsing, to keep render-on-demand.
   const ringRadius=(o:Celestial,min:number)=>Math.max(min,(T.MathUtils.degToRad(o.angular_radius_deg??0)*h/(2*Math.tan(T.MathUtils.degToRad(camera.fov/2))))+min-10);
   const mark=highlightId.current?s.picks.find(p=>p.object.id===highlightId.current):undefined;
   if(mark)drawReticle(ctx,mark.x,mark.y,ringRadius(mark.object,22),'#ffd86b');
   for(const w of props.current.watch){const p=s.picks.find(q=>q.object.id===w.id);if(p)drawReticle(ctx,p.x,p.y,ringRadius(p.object,16),w.color);}
   {
    const dirs=[['N',0],['E',90],['S',180],['W',270]] as const;ctx.font='600 12px system-ui';for(const [n,a]of dirs){const rad=a*Math.PI/180;const p=new T.Vector3(Math.sin(rad)*100,1,-Math.cos(rad)*100).project(camera);if(p.z<1&&Math.abs(p.x)<1){ctx.fillStyle='#c6b998';ctx.fillText(n,(p.x+1)*w/2,(1-p.y)*h/2+22);}}
   }
   // Orientation readout: throttled while moving, plus a trailing update once the camera settles.
   const now=performance.now();clearTimeout(orientTimer);if(now-lastOrient>150){lastOrient=now;reportOrientation();}orientTimer=window.setTimeout(reportOrientation,200);s.perf.drawMs=performance.now()-drawStart;
  };animate();
  let down={x:0,y:0};const pointerdown=(e:PointerEvent)=>{down={x:e.clientX,y:e.clientY};};const click=(e:MouseEvent)=>{if(Math.hypot(e.clientX-down.x,e.clientY-down.y)>5)return;const r=el.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;const hit=state.current!.picks.map(p=>({...p,d:Math.hypot(p.x-x,p.y-y)})).sort((a,b)=>a.d-b.d)[0];if(hit&&hit.d<22)props.current.onSelect(hit.object);};const pointerup=(e:PointerEvent)=>{if((props.current.tracking||props.current.watchLock)&&Math.hypot(e.clientX-down.x,e.clientY-down.y)>5)props.current.onRelease();};
  // From Earth view: wheel changes the field of view; the point under the cursor stays under the cursor (zoom about the centre while tracking).
  const wheel=(e:WheelEvent)=>{const s=state.current;if(!s||s.settings.fullSky)return;e.preventDefault();const r=renderer.domElement.getBoundingClientRect();const nx=(e.clientX-r.left)/r.width*2-1,ny=-((e.clientY-r.top)/r.height*2-1);const dy=Math.max(-120,Math.min(120,e.deltaMode===1?e.deltaY*33:e.deltaY));const fov=T.MathUtils.clamp(camera.fov*Math.exp(dy*.0015),.01,109.6);if(fov===camera.fov)return;
   camera.updateMatrixWorld();const ray=()=>new T.Vector3(nx,ny,.5).unproject(camera).sub(camera.position).normalize();const before=ray();camera.fov=fov;camera.updateProjectionMatrix();if(!props.current.tracking&&!props.current.watchLock){const after=ray();camera.position.applyQuaternion(new T.Quaternion().setFromUnitVectors(after,before));}controls.update();s.dirty=true;props.current.onFov(fov);};
  renderer.domElement.addEventListener('pointerdown',pointerdown);renderer.domElement.addEventListener('pointerup',pointerup);renderer.domElement.addEventListener('click',click);renderer.domElement.addEventListener('wheel',wheel,{passive:false});
  return()=>{renderer.domElement.removeEventListener('pointerdown',pointerdown);renderer.domElement.removeEventListener('pointerup',pointerup);renderer.domElement.removeEventListener('click',click);renderer.domElement.removeEventListener('wheel',wheel);cancelAnimationFrame(raf);clearTimeout(orientTimer);ro.disconnect();controls.dispose();disposeGroup(dynamic);sky.geometry.dispose();(sky.material as T.Material).dispose();renderer.dispose();el.replaceChildren();state.current=null;};
 },[]);
 useEffect(()=>{
  const s=state.current;if(!s)return;const buildStart=performance.now();const accepted=s.snapshot!==snapshot;s.settings=settings;s.snapshot=snapshot;const generation=++s.generation;const {camera}=s;
  camera.fov=settings.fullSky?130:settings.fov;camera.updateProjectionMatrix();s.dynamic.children.forEach(o=>o.visible=false);s.objects=[];s.dirty=true;
  const useObject=<O extends T.Object3D>(key:string,create:()=>O):O=>{let obj=s.pool.get(key) as O|undefined;if(!obj){obj=create();s.pool.set(key,obj);s.dynamic.add(obj);}obj.visible=true;return obj;};
  const tailMesh=(key:string)=>useObject(key,()=>new T.Mesh(new T.BufferGeometry(),new T.MeshBasicMaterial({vertexColors:true,transparent:true,depthWrite:false,blending:T.AdditiveBlending,side:T.DoubleSide})));

  const sm=s.sky.material as T.ShaderMaterial;sm.uniforms.enabled.value=settings.atmosphere?1:0;sm.uniforms.exposure.value=settings.exposure;sm.uniforms.pollution.value=settings.pollution;
  if(!snapshot)return;
  const sun=snapshot.bodies.find(b=>b.id==='Sun');const moon=snapshot.bodies.find(b=>b.id==='Moon');const sunAlt=sun?.altitude_deg??-90;// Sunlight off is a nonphysical aid: the Sun stays in place but scatters no light, so stars and planets show by day.
  const daylight=settings.atmosphere&&settings.sunlight?T.MathUtils.smoothstep(sunAlt,-12,0):0;
  sm.uniforms.hasSun.value=sun&&settings.sunlight?1:0;sm.uniforms.sunDirection.value=sun?.ground_direction?vector(sun.ground_direction):new T.Vector3(0,-1,0);sm.uniforms.moonGlow.value=moon?lunarRelativeFlux(moon.magnitude,moon.phase_fraction??0)*lunarTransmission(moon.altitude_deg??-90,settings.atmosphere):0;
  function displayed(obj:Celestial):Celestial{
   if(!obj.ground_direction||!settings.atmosphere)return obj;
   let a=[...obj.ground_direction];let alt=T.MathUtils.radToDeg(Math.asin(T.MathUtils.clamp(a[2],-1,1)));
   if(settings.refraction&&alt> -1&&alt<89){const correction=1.02/Math.tan(T.MathUtils.degToRad(alt+10.3/(alt+5.11)))/60;const h=T.MathUtils.degToRad(alt+correction),az=Math.atan2(a[0],a[1]);a=[Math.sin(az)*Math.cos(h),Math.cos(az)*Math.cos(h),Math.sin(h)];}
   const air=alt> -1?1/(Math.sin(T.MathUtils.degToRad(Math.max(0,alt)))+.50572*Math.pow(Math.max(0,alt)+6.07995,-1.6364)):40;const c=new T.Color(obj.color);c.multiply(new T.Color(Math.exp(-.03*air),Math.exp(-.065*air),Math.exp(-.15*air)));
   return {...obj,ground_direction:a,magnitude:(obj.magnitude??0)+.2*air,color:'#'+c.getHexString()};
  }
  const stars=snapshot.stars.map(displayed);const displayedBodies=snapshot.bodies.map(displayed),displayedComets=snapshot.comets.map(displayed);const positions:number[]=[],colors:number[]=[],mags:number[]=[],forced:number[]=[],diameters:number[]=[];
  for(const obj of stars){let a=obj.ground_direction;if(!a)continue;if(settings.ground&&a[2]<-.02)continue;const p=vector(a).multiplyScalar(100);positions.push(p.x,p.y,p.z);const c=new T.Color(obj.color);colors.push(c.r,c.g,c.b);mags.push(obj.magnitude??12);forced.push(obj.book_star?1:0);diameters.push(T.MathUtils.degToRad(2*(obj.angular_radius_deg??0)));}
  const stellarPoints=useObject('stars',()=>{const points=new T.Points(new T.BufferGeometry(),new T.ShaderMaterial({vertexShader:vertex,fragmentShader:fragment,vertexColors:true,transparent:true,depthWrite:false,blending:T.AdditiveBlending,uniforms:{halos:{value:1},pixelsPerRadian:{value:1},exposure:{value:1},threshold:{value:5.76},daylight:{value:0}}}));points.frustumCulled=false;return points;});
  updateGeometry(stellarPoints.geometry,{position:{values:positions,size:3},color:{values:colors,size:3},magnitude:{values:mags,size:1},forced:{values:forced,size:1},diameter:{values:diameters,size:1}});
  const mat=stellarPoints.material as T.ShaderMaterial;mat.uniforms.halos.value=settings.halos?1:0;mat.uniforms.pixelsPerRadian.value=s.labels.clientHeight/(2*Math.tan(T.MathUtils.degToRad(camera.fov/2)));mat.uniforms.exposure.value=settings.exposure;mat.uniforms.threshold.value=Math.min(settings.starLimit,12);mat.uniforms.daylight.value=daylight;
  s.objects=[...displayedBodies,...displayedComets,...stars.filter(o=>(o.magnitude??20)<=settings.starLimit||o.book_star)];
  {
   if(settings.ground){const ground=useObject('ground',()=>new T.Mesh(new T.SphereGeometry(800,48,24),new T.MeshBasicMaterial({side:T.BackSide})));ground.material.color.set(daylight>.5?'#172520':'#05090b');ground.scale.set(1,.001,1);ground.position.y=-1.2;}
   for(const comet of displayedComets){const gain=cometGain(comet.magnitude??8,settings.exposure)*(1-daylight);if(gain<=0.002)continue;const toV=(a:number[])=>vector(a).multiplyScalar(88);const hidden=(a:number[])=>settings.ground&&a[2]<-.02;
    for(const tail of comet.tails??[]){const L=tail.left.ground_direction,R=tail.right.ground_direction;const k=tail.intensity.map((v,i)=>hidden(L[i])||hidden(R[i])?0:v*tail.visibility*(tail.kind==='dust'?1:.85));ribbon(tailMesh('ground-tail:'+comet.id+':'+tail.kind),L.map(toV),R.map(toV),k,tail.color,gain);}}
   for(const body of [...displayedBodies,...displayedComets]){if(!body.ground_direction)continue;if(settings.ground&&body.ground_direction[2]<-.02)continue;const pos=vector(body.ground_direction).multiplyScalar(90);let r=Math.tan(T.MathUtils.degToRad(body.angular_radius_deg??0))*90;const angularTrue=r;r=settings.markers?Math.max(.07,r):Math.max(1e-9,r);
    const mesh=useObject('ground-body:'+body.id,()=>new T.Mesh(new T.SphereGeometry(1,20,12),new T.MeshBasicMaterial()));mesh.material.color.set(body.color);mesh.scale.setScalar(r);mesh.position.copy(pos);
    if(body.id!=='Sun'&&body.id!=='Moon'&&angularTrue<.04){const point=useObject('body-point:'+body.id,()=>{const p=new T.Points(new T.BufferGeometry(),mat);p.frustumCulled=false;return p;});const col=new T.Color(body.color);updateGeometry(point.geometry,{position:{values:[pos.x,pos.y,pos.z],size:3},color:{values:[col.r,col.g,col.b],size:3},magnitude:{values:[body.magnitude??10],size:1},forced:{values:[0],size:1},diameter:{values:[T.MathUtils.degToRad(2*(body.angular_radius_deg??0))],size:1}});}

    if(body.id==='Moon'&&(body.altitude_deg??-90)>0){
     const glow=lunarGlow(body.magnitude,body.phase_fraction??0,settings.exposure,daylight);
     if(glow>1e-5){const halo=useObject('moon-glow',()=>{const m=new T.Mesh(new T.PlaneGeometry(2,2),new T.ShaderMaterial({transparent:true,depthWrite:false,depthTest:true,blending:T.AdditiveBlending,uniforms:{pixelsPerRadian:{value:1},diskRadius:{value:1},strength:{value:0},tint:{value:new T.Color('#e3e8f0')}},
      vertexShader:'uniform float pixelsPerRadian;uniform float diskRadius;varying vec2 vUv;varying float vDisk;void main(){vUv=uv;vec4 c=modelViewMatrix*vec4(0.,0.,0.,1.);float radius=max(diskRadius*5.,max(0.,-c.z)*8./pixelsPerRadian);vDisk=diskRadius/max(radius,1e-9);c.xy+=position.xy*radius;gl_Position=projectionMatrix*c;}',
      fragmentShader:'uniform float strength;uniform vec3 tint;varying vec2 vUv;varying float vDisk;void main(){float r=length((vUv-.5)*2.);float outside=smoothstep(vDisk*.98,vDisk*1.15,r);float glow=(exp(-8.*r*r)+.18*exp(-2.5*r*r))*(1.-smoothstep(.8,1.,r))*outside;gl_FragColor=vec4(tint*strength*glow,1.);}'}));m.frustumCulled=false;m.renderOrder=-2;return m;});
      halo.position.copy(pos);halo.material.uniforms.diskRadius.value=Math.max(angularTrue,1e-9);halo.material.uniforms.strength.value=glow;halo.material.uniforms.tint.value.set(body.color);
     }
    }
    if(body.id!=='Sun'&&body.type!=='comet'&&angularTrue>.08&&sun?.ground_direction){
     // Phase: lit from the Sun-from-Moon direction built from both topocentric vectors (parallax included). Lommel-Seeliger
     // shading; the unlit side is transparent (the sky shows) but writes depth and draws before the stars, so it hides them.
     const toSun=vector(sun.ground_direction).multiplyScalar(sun.distance_au??1).sub(vector(body.ground_direction).multiplyScalar(body.distance_au??0)).normalize();
     const lit=useObject('phase:'+body.id,()=>new T.Mesh(new T.SphereGeometry(1,64,48),new T.ShaderMaterial({transparent:true,depthWrite:true,uniforms:{sunDir:{value:toSun},tint:{value:new T.Color(body.color)}},
      vertexShader:'varying vec3 vN;varying vec3 vView;void main(){vec4 w=modelMatrix*vec4(position,1.);vN=normalize(mat3(modelMatrix)*normal);vView=normalize(cameraPosition-w.xyz);gl_Position=projectionMatrix*viewMatrix*w;}',
      fragmentShader:'uniform vec3 sunDir;uniform vec3 tint;varying vec3 vN;varying vec3 vView;void main(){vec3 n=normalize(vN);float mu0=dot(n,sunDir);float mu=max(dot(n,normalize(vView)),0.);float ls=2.*max(mu0,0.)/(max(mu0,0.)+mu+1e-4);gl_FragColor=vec4(tint*min(ls,1.25),smoothstep(-.004,.012,mu0));}'})));
     lit.scale.setScalar(r*1.001);lit.material.uniforms.sunDir.value.copy(toSun);lit.material.uniforms.tint.value.set(body.color);lit.position.copy(pos);lit.renderOrder=-1;mesh.visible=false;}
   }
  }
  if(settings.grid)useObject('grid:'+settings.ground,()=>{
   {
    const vertices:number[]=[];const point=(az:number,alt:number)=>{const a=T.MathUtils.degToRad(az),h=T.MathUtils.degToRad(alt);return new T.Vector3(98*Math.cos(h)*Math.sin(a),98*Math.sin(h),-98*Math.cos(h)*Math.cos(a));};
    for(let alt=settings.ground?0:-75;alt<=75;alt+=15)for(let az=0;az<360;az+=3){const a=point(az,alt),b=point(az+3,alt);vertices.push(a.x,a.y,a.z,b.x,b.y,b.z);}
    for(let az=0;az<360;az+=30)for(let alt=settings.ground?0:-90;alt<90;alt+=3){const a=point(az,alt),b=point(az,alt+3);vertices.push(a.x,a.y,a.z,b.x,b.y,b.z);}
    const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(vertices,3));return new T.LineSegments(geometry,new T.LineBasicMaterial({color:'#6c809c',transparent:true,opacity:.2}));
   }
  });

  const current=()=>state.current===s&&s.generation===generation;
  if(settings.constellations){s.constellations??=fetch('/api/constellations').then(r=>{if(!r.ok)throw Error('Constellation data unavailable');return r.json();});s.constellations.then(data=>{if(!current()||!s.settings.constellations)return;const map=new Map(snapshot.stars.map(x=>[x.id,x]));const lines:number[]=[];for(const pair of data.lines??[]){const a=map.get('hip:'+pair[0]),b=map.get('hip:'+pair[1]);if(!a||!b)continue;const av=a.ground_direction,bv=b.ground_direction;if(!av||!bv)continue;if(settings.ground&&(av[2]<0||bv[2]<0))continue;for(const x of [av,bv]){const p=vector(x).multiplyScalar(99);lines.push(p.x,p.y,p.z);}}const line=useObject('constellations',()=>new T.LineSegments(new T.BufferGeometry(),new T.LineBasicMaterial({color:'#7d91ac',transparent:true,opacity:.25})));line.frustumCulled=false;updateGeometry(line.geometry,{position:{values:lines,size:3}});s.dirty=true;}).catch(()=>{s.constellations=undefined;});}
  s.perf.buildMs=performance.now()-buildStart;if(accepted&&!snapshot.preview)s.perf.updates.push(buildStart);
 },[snapshot,stable,lat,lon]);
 useEffect(()=>{const s=state.current;if(s){s.settings=settings;s.dirty=true;}},[settings]);
 const watchKey=watch.map(w=>w.id+w.color).join(',')+'|'+watchLock+'|'+watchCenterId;
 useEffect(()=>{if(state.current)state.current.dirty=true;},[selectedId,watchKey]);
 useEffect(()=>{const s=state.current;if(!s)return;s.camera.fov=settings.fullSky?130:settings.fov;s.camera.updateProjectionMatrix();s.dirty=true;},[settings.fov,settings.fullSky]);
 useEffect(()=>{highlightId.current=focus?.id??null;const s=state.current;if(!s)return;s.dirty=true;if(!focus)return;aim(s,s.objects.find(x=>x.id===focus.id)??focus);},[focus]);
 // View lock: each new sky frame re-aims at the target's displayed position, so it stays centred as time moves. The target is the tracked group (centre one / group centroid) or the single Center-in-view object; nothing locks otherwise.
 // Frame: leave the tracked objects where they are on screen and pan only as far as needed to keep each ring AND its name fully inside the free area (inside the top bar, timeline, azimuth readout, open side panel and object card). Too big to fit: centre their bounding box. Behind the camera: bring the group to the middle first. All in screen pixels.
 const aboveHorizon=(o?:Celestial):o is Celestial=>!!o&&(o.ground_direction?.[2]??-1)>0;
 const followTarget=(s:NonNullable<typeof state.current>):Celestial|undefined=>{
  const objs=watch.map(w=>s.objects.find(o=>o.id===w.id)).filter((o):o is Celestial=>!!o&&!!o.ground_direction&&aboveHorizon(o));if(!objs.length)return;
  const cam=s.camera;cam.updateMatrixWorld();const W=s.labels.clientWidth,H=s.labels.clientHeight;const pts=objs.map(o=>vector(o.ground_direction!).multiplyScalar(100).project(cam));
  if(pts.some(p=>p.z>1||p.z<-1))return centroid(objs);
  const ctx=s.labels.getContext('2d')!;ctx.font=LABEL_FONT_SELECTED;
  const root=host.current,hr=root?.getBoundingClientRect();const rect=(sel:string)=>{const e=root?.parentElement?.querySelector(sel);if(!e||!hr)return null;const r=e.getBoundingClientRect();return r.width>0?{l:r.left-hr.left,r:r.right-hr.left,t:r.top-hr.top,b:r.bottom-hr.top}:null;};
  let x0=12,x1=W-12,y0=12,y1=H-12;const top=rect('.topbar'),tl=rect('.orientation')??rect('.timeline'),lp=rect('.settings-panel')??rect('.left-rail'),oc=rect('.object-card')??rect('.bright-card');
  if(top)y0=Math.max(y0,top.b+8);if(tl)y1=Math.min(y1,tl.t-8);const tlb=rect('.timeline');if(tlb)y1=Math.min(y1,tlb.t-8);if(lp)x0=Math.max(x0,lp.r+8);if(oc)x1=Math.min(x1,oc.l-8);
  const boxes=objs.map((o,i)=>{const px=(pts[i].x+1)*W/2,py=(1-pts[i].y)*H/2;const tw=ctx.measureText(starLabel(o,settings.sanskritNames)).width;return {l:px-32,r:px+14+tw+8,t:py-32,b:py+32+17*(objs.length-1)};});// ring + ticks to the left, name to the right, extra room below for names stacked apart
  const bb={l:Math.min(...boxes.map(x=>x.l)),r:Math.max(...boxes.map(x=>x.r)),t:Math.min(...boxes.map(x=>x.t)),b:Math.max(...boxes.map(x=>x.b))};
  const shift=(lo:number,hi:number,a:number,b:number)=>hi-lo>b-a?(lo+hi)/2-(a+b)/2:hi>b?hi-b:lo<a?lo-a:0;
  const dx=shift(bb.l,bb.r,x0,x1),dy=shift(bb.t,bb.b,y0,y1);if(Math.abs(dx)<.5&&Math.abs(dy)<.5)return;
  const d=new T.Vector3(dx/(W/2),-dy/(H/2),.5).unproject(cam).sub(cam.position).normalize();return {...objs[0],ground_direction:[d.x,-d.z,d.y]};};
 const lockTarget=(s:NonNullable<typeof state.current>):Celestial|undefined=>{
  if(watchLock==='center'){const id=watchCenterId??watch[0]?.id;const o=s.objects.find(x=>x.id===id);return aboveHorizon(o)?o:undefined;}
  if(watchLock==='frame')return followTarget(s);
  if(tracking&&focus){const o=s.objects.find(x=>x.id===focus.id);return aboveHorizon(o)?o:undefined;}};
 useEffect(()=>{const s=state.current;if(!s)return;for(let k=0;k<(watchLock==='frame'?3:1);k++){const o=lockTarget(s);if(!o)break;aim(s,o);}},[snapshot,tracking,watchKey]);
 // Zoom out to fit all (button in the Track panel): set the field of view so the farthest tracked object sits inside the view (80% margin so rings clear the top bar and timeline, 8° floor), then centre on the group.
 useEffect(()=>{const s=state.current;if(!s||!frameToken)return;const objs=watch.map(w=>s.objects.find(o=>o.id===w.id)).filter((o):o is Celestial=>!!o&&!!o.ground_direction);if(!objs.length)return;const c=centroid(objs);aim(s,c);const cv=vector(c.ground_direction!);let theta=0;for(const o of objs)theta=Math.max(theta,cv.angleTo(vector(o.ground_direction!)));const t=Math.min(theta*1.8,1.3);const fov=T.MathUtils.clamp(T.MathUtils.radToDeg(2*Math.atan(Math.tan(t)/Math.min(1,s.camera.aspect))),8,109.6);s.camera.fov=fov;s.camera.updateProjectionMatrix();s.dirty=true;props.current.onFov(fov);},[frameToken]);
 return <><div className="sky-host" ref={host} aria-label="Interactive astronomical sky. Drag to look around; scroll to zoom."/><div className="fps-meter" ref={meter} title="Browser callback FPS · actual renders/s · accepted exact sky updates/s (last 2 s) · request wall time · science calculation · cache overhead · scene update and redraw CPU time (GPU time not included; cached calculation time is the original calculation)" aria-hidden="true"/></>;
}
