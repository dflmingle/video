import fs from 'node:fs';import {chromium} from 'playwright';
const b=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const p=await b.newPage();await p.goto('http://127.0.0.1:5267/v22.html?capture=1&variant=V22-C&camera=B&environment=NewScene');await p.waitForFunction(()=>window.ready,null,{timeout:180000});
 const result=await p.evaluate(async()=>{
  const T=await import('/node_modules/three/build/three.module.js'),r=window.sceneRuntime,S=r.simulation,C=r.config;
  const frames=Array.from({length:S.frames},(_,f)=>({time:f/60,points:S.units.map((u,i)=>({i,u,p:r.row(f/60,i),h:r.armies.audit[u.model].calibration.targetHeadHeight}))}));
  const c=new T.PerspectiveCamera(42,2/3,.1,600);
  function setup(center,zoom){c.position.set(0,240,center+100);c.lookAt(0,0,center);c.zoom=zoom;c.updateMatrixWorld(true);c.updateProjectionMatrix()}
  function fit(center,mode){setup(center,1);let zoom=10;for(const frame of frames)for(const q of frame.points){if(mode==='keySubjects'&&q.u.team!=='blue'&&q.u.color!=='yellow')continue;for(const y of [0,q.h]){const v=new T.Vector3(q.p[0],y,q.p[1]).project(c);zoom=Math.min(zoom,.94/Math.max(Math.abs(v.x),Math.abs(v.y)))}}return zoom;}
  function optimize(mode){let lo=-80,hi=0;for(let i=0;i<32;i++){const a=lo+(hi-lo)/3,b=hi-(hi-lo)/3;if(fit(a,mode)<fit(b,mode))lo=a;else hi=b;}const center=(lo+hi)/2,zoom=fit(center,mode);return {mode,center,zoom,increaseVersusV22Opening:zoom/1.35-1};}
  const all=optimize('allSoldiers'),key=optimize('keySubjects');
  function fractions(center,zoom){setup(center,zoom);return [frames[0],frames[Math.round(frames.length/2)],frames.at(-1)].map(frame=>({time:frame.time,visible:Object.fromEntries(['blue','red','orange','yellow'].map(team=>{const qs=frame.points.filter(q=>team==='blue'?q.u.team==='blue':q.u.color===team);const n=qs.filter(q=>{const v=new T.Vector3(q.p[0],q.h/2,q.p[1]).project(c);return Math.abs(v.x)<.98&&Math.abs(v.y)<.98}).length;return [team,{visible:n,total:qs.length}]}))}));}
  return {allSoldiers:all,allSoldiersFractions:fractions(all.center,all.zoom),keySubjects:key,keySubjectsFractions:fractions(key.center,key.zoom),fixed20:{center:key.center,zoom:1.35*1.2,coverage:fractions(key.center,1.35*1.2)},fixed35:{center:key.center,zoom:1.35*1.35,coverage:fractions(key.center,1.35*1.35)},assumptions:'V22-C all recorded frames; unchanged FOV42, height240, inclination (offsetZ100); projected feet/head only, 6% NDC margin. Preliminary feasibility, no visual camera approval.'};
 });fs.writeFileSync('docs/v22r/fixed-framing-budget.json',JSON.stringify(result,null,2));console.log(JSON.stringify({all:result.allSoldiers,key:result.keySubjects}));
}finally{await b.close()}
